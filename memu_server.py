import os
import sys
import tempfile
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import json
import requests
from dotenv import load_dotenv

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

from memu.app import MemoryService


# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
# import google.generativeai as genai  <-- Removed to avoid dependency hell

# Check Python version
is_compatible = sys.version_info >= (3, 10)

# Configure API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FORGE_API_KEY = os.getenv("BUILT_IN_FORGE_API_KEY") or os.getenv("VITE_FRONTEND_FORGE_API_KEY")

def generate_gemini_rest(api_key, prompt):
    """Direct REST API call to avoid library issues"""
    # Using gemini-2.0-flash-lite-001 for better rate limit handling
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=15)
            if response.status_code == 429:
                wait_time = 5 * (attempt + 1)
                print(f"Rate limit hit (429), retrying in {wait_time} seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"REST API Error: {e}")
            if attempt == max_retries - 1:
                if 'response' in locals() and hasattr(response, 'status_code') and response.status_code != 200:
                     print(f"Response: {response.text}")
                raise e
            time.sleep(1)

if GEMINI_API_KEY:
    print(f"✓ Gemini API Key detected: {GEMINI_API_KEY[:10]}... (Using REST Mode)")
else:
    print("⚠ GEMINI_API_KEY not found in environment variables")

if FORGE_API_KEY:
    print(f"✓ Forge API Key detected: {FORGE_API_KEY[:10]}...")
else:
    print("⚠ Forge API Key not found (Optional)")

# Mock MemoryService if memu cannot be imported or as a fallback
class MockMemoryService:
    def __init__(self):
        self.storage_file = "memu_storage.json"
        self.memories = []
        self.resources = []
        self._load_from_disk()
        print("✓ Using Persistent MockMemoryService with JSON persistence")

    def _load_from_disk(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memories = data.get("memories", [])
                    self.resources = data.get("resources", [])
                    print(f"Loaded {len(self.memories)} memories from {self.storage_file}")
            except Exception as e:
                print(f"Error loading storage: {e}")

    def _save_to_disk(self):
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "memories": self.memories,
                    "resources": self.resources
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving storage: {e}")

    async def memorize(self, resource_url: str, modality: str, user: Dict[str, str]) -> Dict[str, Any]:
        # Read content
        with open(resource_url, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse content if it has user prefix
        # "[User: {request.user_id}] {request.content}"
        actual_content = content
        if "]" in content:
            actual_content = content.split("]", 1)[1].strip()
            
        memory_item = {
            "id": f"mem_{len(self.memories)+1}",
            "content": actual_content,
            "user_id": user.get("user_id"),
            "timestamp": "2025-02-07T12:00:00Z" # In real app use datetime.now().isoformat()
        }
        self.memories.append(memory_item)
        self.resources.append({"url": resource_url, "modality": modality})
        
        self._save_to_disk()
        
        return {
            "items": [memory_item],
            "categories": [],
            "resource": {"id": "res_1"}
        }

    async def retrieve(self, queries: List[Dict[str, str]], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query_text = queries[0].get("content", "").lower()
        results = []
        for mem in self.memories:
            # Simple keyword matching for mock
            if any(word in mem["content"].lower() for word in query_text.split()):
                results.append(mem)
        
        # If no match, just return all or some (limit to 5)
        if not results and self.memories:
            results = self.memories[-5:]
        elif len(results) > 5:
            results = results[-5:]
            
        return {
            "items": results,
            "query": query_text
        }

# Try to import memu
memory_service: Any = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory_service
    
    # Try to use real MemoryService if API key is available
    if GEMINI_API_KEY or os.getenv("REACT_APP_API_KEY"):
        api_key = GEMINI_API_KEY or os.getenv("REACT_APP_API_KEY")
        print(f"✓ Initializing MemU with Gemini... (Key: {api_key[:5]}...)")
        try:
            # Configure MemoryService with Gemini
            memory_service = MemoryService(
                llm_profiles={
                    "default": {
                        "provider": "gemini",
                        "api_key": api_key,
                        "chat_model": "gemini-flash-latest",
                        "embed_model": "gemini-embedding-001",
                        "base_url": "https://generativelanguage.googleapis.com/v1beta",
                        "client_backend": "httpx"
                    }
                },
                memorize_config={"memory_categories": []},
                retrieve_config={"method": "llm"} # Use LLM-based retrieval/ranking to avoid embedding issues if any
            )
            # Force context ready
            memory_service._context.categories_ready = True
        except Exception as e:
            print(f"Error initializing MemU: {e}")
            import traceback
            traceback.print_exc()
            memory_service = MockMemoryService()
    else:
        print("⚠ No API Key found. Using MockMemoryService.")
        memory_service = MockMemoryService()

    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for frontend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

class ResourceRequest(BaseModel):
    user_id: str
    content: str
    resource_type: str = "text"

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/resources/")
async def save_resource(request: ResourceRequest):
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")
    
    try:
        # Create temp file for content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(f"[User: {request.user_id}] {request.content}")
            temp_file = f.name
            
        try:
            result = await memory_service.memorize(
                resource_url=temp_file,
                modality="text", # default to text
                user={"user_id": request.user_id}
            )
            return {
                "status": "success",
                "message": "Memory saved",
                "items_created": len(result.get("items", [])),
                "data": result
            }
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            
    except Exception as e:
        print(f"Error saving resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/deep")
async def search_deep(user_id: str, query: str):
    if not memory_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")
        
    try:
        result = await memory_service.retrieve(
            queries=[{"role": "user", "content": query}],
            # context={"user_id": user_id} 
        )
        
        return {
            "query": query,
            "results": result
        }
    except Exception as e:
        print(f"Error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- In-Memory Cache for Hackathon Demo ---
response_cache = {}

def get_cached_response(prompt):
    return response_cache.get(prompt)

def cache_response(prompt, response):
    # Simple LRU-like behavior: limit cache size
    if len(response_cache) > 100:
        response_cache.pop(next(iter(response_cache)))
    response_cache[prompt] = response

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # 1. Retrieve Context (Always perform retrieval first)
    memories = await search_deep(request.user_id, request.message)
    items = memories.get("results", {}).get("items", [])
    memory_context = "\n".join([f"- {item.get('content', '')}" for item in items])
    
    # 2. Try Generating Response with Gemini (REST API)
    reply = ""
    error_detail = ""
    used_model = False
    
    if GEMINI_API_KEY:
        try:
            prompt = f"""You are a helpful AI assistant with long-term memory.
            
            Relevant memories:
            {memory_context if memory_context else "No relevant memories found."}
            
            User: {request.message}
            Assistant:"""
            
            # Check Cache First
            cached = get_cached_response(prompt)
            if cached:
                print("✓ Cache Hit! Returning cached response.")
                reply = cached + " (Cached)"
                used_model = True
            else:
                # Switching to gemini-flash-latest for potentially better stability
                # Direct REST call using v1beta endpoint
                model_name = "gemini-flash-latest"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
                headers = {'Content-Type': 'application/json'}
                data = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                
                import time
                max_retries = 3
                last_error = ""
                for attempt in range(max_retries):
                    try:
                        response = requests.post(url, headers=headers, json=data, timeout=12)
                        if response.status_code == 429:
                            wait_time = 3 * (attempt + 1) # Slightly shorter wait for Render
                            print(f"Rate limit hit (429), retrying in {wait_time}s... ({attempt+1}/{max_retries})")
                            time.sleep(wait_time)
                            last_error = "Rate Limited (429)"
                            continue
                        
                        response.raise_for_status()
                        result = response.json()
                        reply = result['candidates'][0]['content']['parts'][0]['text']
                        cache_response(prompt, reply)
                        used_model = True
                        break
                    except Exception as e:
                        last_error = str(e)
                        print(f"Attempt {attempt+1} failed: {e}")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                
                if not reply:
                    error_detail = f"Last error: {last_error}"

        except Exception as e:
            print(f"Gemini API Exception: {e}")
            error_detail = f"Exception: {str(e)}"
            
    # Fallback response
    if not reply:
        reply = f"Sorry, I couldn't generate a response at the moment. (Error: {error_detail})"
        if not GEMINI_API_KEY:
            reply = "Please configure GEMINI_API_KEY in .env file to enable AI responses."

    # 3. Memorize the interaction
    if reply and memory_service and used_model:
        try:
            # Create a temp file for the conversation
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
                json.dump([
                    {"role": "user", "content": request.message, "name": request.user_id},
                    {"role": "assistant", "content": reply, "name": "Assistant"}
                ], f, ensure_ascii=False)
                temp_file = f.name
            
            try:
                # Memorize the conversation
                await memory_service.memorize(
                    resource_url=temp_file,
                    modality="conversation",
                    user={"user_id": request.user_id}
                )
                print(f"✓ Memorized interaction for user {request.user_id}")
            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
        except Exception as e:
             print(f"Error memorizing interaction: {e}")

    return {"reply": reply}

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.1"}

@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, 'index.html'))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
