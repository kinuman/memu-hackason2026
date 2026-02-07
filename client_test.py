import os
import requests
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MEMU_SERVER_URL = os.getenv("MEMU_SERVER_URL", "http://localhost:8000")
USER_ID = "test_user_001" 

def chat_with_bot(user_id, message):
    """Chat with the bot via the MemU server."""
    payload = {
        "user_id": user_id,
        "message": message
    }
    try:
        response = requests.post(f"{MEMU_SERVER_URL}/chat", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error chatting: {e}")
        return None

def main():
    print("=== MemU Agent CLI (Gemini Powered) ===")
    print(f"User ID: {USER_ID}")
    print("Type 'exit' or 'quit' to stop.")
    print("-------------------------")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except EOFError:
            break

        if not user_input:
            continue
            
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        # Send to server (which handles Memory RAG + Gemini)
        print(" > Agent thinking...")
        result = chat_with_bot(USER_ID, user_input)
        
        if result and "reply" in result:
            print(f"\nAgent: {result['reply']}")
        else:
            print("\nAgent: (Error or no response)")

if __name__ == "__main__":
    main()
