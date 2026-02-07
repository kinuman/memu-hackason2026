import os
import sys
import tempfile
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import google.generativeai as genai

# Check Python version
is_compatible = sys.version_info >= (3, 10)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
    # Force use of our robust MockService for Hackathon reliability unless explicitly overridden
    # This ensures consistency across environments (Render/Local)
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
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

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

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # 1. Retrieve Context (Always perform retrieval first)
    memories = await search_deep(request.user_id, request.message)
    items = memories.get("results", {}).get("items", [])
    memory_context = "\n".join([f"- {item.get('content', '')}" for item in items])
    
    # 2. Try Generating Response with Gemini
    reply = ""
    used_model = False
    
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"""You are a helpful AI assistant with long-term memory.
            
Relevant memories:
{memory_context if memory_context else "No relevant memories found."}

User: {request.message}
Assistant:"""
            response = model.generate_content(prompt)
            reply = response.text
            used_model = True
        except Exception as e:
            print(f"Gemini API Error (Quota or Other): {e}")
            # Fallback will be handled below
            pass

    # 3. Fallback / Offline Mode
    if not reply:
        if items:
            # Simple retrieval-based response
            reply = f"I'm in offline memory mode. I recall: {items[0].get('content')}... regarding your message '{request.message}'."
        else:
            # Echo response
            reply = f"Offline Mode: I received '{request.message}' but have no specific memories about it yet."
        
        if not GEMINI_API_KEY:
             reply += " (Note: AI API Key not configured)"
        else:
             reply += " (Note: AI Service temporarily unavailable)"

    # 4. Save Interaction (Even in offline mode, we record the conversation)
    try:
        await save_resource(ResourceRequest(
            user_id=request.user_id, 
            content=f"User: {request.message}\nAssistant: {reply}"
        ))
    except Exception as e:
        print(f"Error saving interaction: {e}")

    return {"reply": reply}

@app.get("/")
async def root():
    return FileResponse('static/index.html')

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
