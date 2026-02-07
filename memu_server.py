import os
import sys
import tempfile
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
import json

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# Check Python version
is_compatible = sys.version_info >= (3, 10)

# Mock MemoryService if memu cannot be imported
class MockMemoryService:
    def __init__(self):
        self.storage_file = "memu_storage.json"
        self.memories = []
        self.resources = []
        self._load_from_disk()
        print("⚠ Using MockMemoryService with JSON persistence")

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
            "timestamp": "2025-02-07T12:00:00Z"
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
    
    if is_compatible:
        try:
            # Add src to path
            src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            
            from memu.app import MemoryService
            
            # Check for keys
            api_key = os.getenv("OPENAI_API_KEY", "dummy-key")
            
            llm_profiles = {
                "default": {
                    "provider": "openai",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": api_key,
                    "chat_model": "gpt-4o-mini",
                    "client_backend": "sdk",
                },
                "embedding": {
                    "provider": "openai",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": api_key,
                    "embed_model": "text-embedding-3-small",
                    "client_backend": "sdk",
                },
            }
            
            try:
                # Use inmemory database
                memory_service = MemoryService(
                    llm_profiles=llm_profiles,
                    database_config={"metadata_store": {"provider": "inmemory"}}
                )
                print("✓ MemU Memory Service initialized")
            except Exception as e:
                print(f"✗ Failed to initialize MemU: {e}")
                print("Falling back to MockMemoryService")
                memory_service = MockMemoryService()
        except Exception as e:
            print(f"✗ Failed to import MemU: {e}")
            memory_service = MockMemoryService()
    else:
        print(f"⚠ Python version {sys.version.split()[0]} is too old for MemU (requires 3.10+)")
        memory_service = MockMemoryService()
    
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

class ResourceRequest(BaseModel):
    user_id: str
    content: str
    resource_type: str = "text"

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
