import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to sys.path
src_path = os.path.abspath("src")
sys.path.insert(0, src_path)

from memu.app import MemoryService

# Load env
load_dotenv(".env.local")
api_key = os.getenv("GEMINI_API_KEY")

async def main():
    if not api_key:
        print("No API Key found")
        return

    print(f"Testing with API Key: {api_key[:5]}...")

    try:
        service = MemoryService(
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
            retrieve_config={"method": "llm"}
        )
        service._context.categories_ready = True
        
        print("Service initialized.")
        
        # Test Memorize
        import tempfile
        import json
        
        conversation = [
            {"role": "user", "content": "Hello, my name is Kinu. I like coding.", "name": "Kinu"},
            {"role": "assistant", "content": "Nice to meet you Kinu! Coding is fun.", "name": "Assistant"}
        ]
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(conversation, f)
            temp_file = f.name
            
        print("Memorizing conversation...")
        result = await service.memorize(resource_url=temp_file, modality="conversation", user={"user_id": "kinu_test"})
        print("Memorize result:", json.dumps(result, indent=2, ensure_ascii=False, default=str))
        
        os.unlink(temp_file)
        
        # Test Retrieve
        print("\nRetrieving...")
        retrieve_result = await service.retrieve(
            queries=[{"role": "user", "content": "What is my name?"}],
            # context={"user_id": "kinu_test"} # Context usually handled by memory user wrapper or service knows user?
            # Actually MemoryService.retrieve doesn't take user_id directly in signature shown in memu_server.py
            # Let's check signature in source code if needed.
        )
        print("Retrieve result:", json.dumps(retrieve_result, indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
