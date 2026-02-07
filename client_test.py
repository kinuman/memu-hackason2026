import os
import requests
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configuration
MEMU_SERVER_URL = "http://localhost:8000"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USER_ID = "test_user_001" # In a real app, this would be dynamic

# Check for API Key
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found in environment variables.")
    print("Please create a .env file with OPENAI_API_KEY=your_key_here")
    # For demonstration purposes, we might want to ask for input if not found
    # OPENAI_API_KEY = input("Enter your OpenAI API Key: ").strip()

# Initialize OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def save_memory(user_id, text):
    """Save a memory to the MemU server."""
    payload = {
        "user_id": user_id,
        "content": text,
        "resource_type": "text"
    }
    try:
        response = requests.post(f"{MEMU_SERVER_URL}/resources/", json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error saving memory: {e}")
        return None

def query_memory(user_id, question):
    """Retrieve relevant memories from the MemU server."""
    params = {"user_id": user_id, "query": question}
    try:
        response = requests.get(f"{MEMU_SERVER_URL}/search/deep", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error querying memory: {e}")
        return None

def generate_chat_response(user_input, context_memories):
    """Generate a response using OpenAI based on context."""
    if not client:
        return "Error: OpenAI API Key is missing. Please configure it to use the chatbot."

    # Format memories for the prompt
    memory_context = ""
    if context_memories and "results" in context_memories:
        items = context_memories["results"].get("items", [])
        if items:
            memory_context = "\n".join([f"- {item.get('content', '')}" for item in items])

    system_prompt = f"""You are a helpful AI assistant with long-term memory.
    
Here are some relevant memories from past conversations with this user:
{memory_context if memory_context else "No relevant memories found."}

Instructions:
1. Use the memories above to provide a personalized and context-aware answer.
2. If the user asks about something you remember, refer to it explicitly.
3. If the memories are not relevant to the current query, answer naturally based on your general knowledge.
4. Be concise and friendly.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Or gpt-3.5-turbo
            messages=messages,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {e}"

def main():
    print("=== MemU Chatbot Demo ===")
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

        # 1. Retrieve Context
        print("\n[memU Memory Retrieval...]")
        memories = query_memory(USER_ID, user_input)
        
        # Display retrieved memories
        if memories and "results" in memories:
            items = memories["results"].get("items", [])
            if items:
                for item in items:
                    content = item.get("content", "No content")
                    # Simple date formatting if timestamp exists
                    timestamp = item.get("timestamp", "")[:10] 
                    print(f' > 過去の関連する記憶を発見: "{content[:50]}..." ({timestamp})')
            else:
                 print(" > 関連する記憶は見つかりませんでした。")
        else:
             print(" > 記憶の取得に失敗しました。")

        # 2. Generate Response
        print(" > コンテキストを再構築中...")
        print(" > 回答を生成します。")
        bot_response = generate_chat_response(user_input, memories)
        
        print(f"\nBot: {bot_response}")

        # 3. Save Interaction (User input and Bot response)
        # We save the interaction so the bot remembers this conversation later
        print("\n[memU Memory Storage...]")
        print(" > 新しい記憶を保存中...")
        save_memory(USER_ID, f"User asked: {user_input}\nBot answered: {bot_response}")
        print(" > 保存完了")

if __name__ == "__main__":
    main()
