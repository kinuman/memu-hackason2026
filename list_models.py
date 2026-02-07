import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv(".env.local")
api_key = os.getenv("GEMINI_API_KEY")

async def main():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            for model in data.get("models", []):
                print(f"Name: {model['name']}")
                print(f"Supported Generation Methods: {model.get('supportedGenerationMethods', [])}")
                print("-" * 20)
        else:
            print(f"Error: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    asyncio.run(main())