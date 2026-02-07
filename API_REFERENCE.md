# MemU API Reference for AI Agents 
 
 ## Overview 
 MemU is an agentic memory layer for LLM applications. This API reference provides endpoints for memory operations including memorization, retrieval, and category management. 
 
 ## Base URL 
 `https://api.memu.so` 
 
 ## Authentication 
 All API requests require a Bearer token in the Authorization header: 
 ``` 
 Authorization: Bearer YOUR_API_KEY 
 Content-Type: application/json 
 ``` 
 
 --- 
 
 ## Endpoints Overview 
 
 | Method | Endpoint | Description | 
 |--------|----------|-------------| 
 | POST | /api/v3/memory/memorize | Register a memorization task | 
 | GET | /api/v3/memory/memorize/status/{task_id} | Get memorization task status | 
 | POST | /api/v3/memory/categories | List memory categories | 
 | POST | /api/v3/memory/retrieve | Retrieve memories using semantic search | 
 | POST | /api/v3/memory/delete | Delete user or agent memories | 
 
 --- 
 
 ## 1. Memorize Conversation 
 
 Register a memorization task to extract and store memories from a conversation. 
 
 **Endpoint:** `POST /api/v3/memory/memorize` 
 
 **Request Body:** 
 ```json 
 { 
   "conversation": [ 
     { 
       "role": "user", 
       "name": "John", 
       "created_at": "2024-01-15T10:30:00Z", 
       "content": "I love playing tennis on weekends" 
     }, 
     { 
       "role": "assistant", 
       "name": "Coach", 
       "created_at": "2024-01-15T10:30:15Z", 
       "content": "That's great! Tennis is an excellent way to stay active." 
     }, 
     { 
       "role": "user", 
       "name": "John", 
       "created_at": "2024-01-15T10:31:00Z", 
       "content": "I usually play at the local club every Saturday morning." 
     } 
   ], 
   "user_id": "user_123", 
   "user_name": "John Doe", 
   "agent_id": "agent_456", 
   "agent_name": "Tennis Coach AI", 
   "session_date": "2024-01-15T10:30:00Z" 
 } 
 ``` 
 
 **Parameters:** 
 - `conversation` (array, required): Array of messages (minimum 3 messages) 
   - `role` (string, required): "user" or "assistant" 
   - `name` (string, optional): Display name of sender 
   - `created_at` (string, optional): ISO 8601 timestamp 
   - `content` (string, required): Message content 
 - `user_id` (string, required): Unique user identifier 
 - `user_name` (string, optional): Display name for user 
 - `agent_id` (string, required): Unique agent identifier 
 - `agent_name` (string, optional): Display name for agent 
 - `session_date` (string, optional): ISO 8601 session timestamp 
 
 **Response (200 OK):** 
 ```json 
 { 
   "task_id": "task_789abc123def", 
   "status": "PENDING", 
   "message": "Memorization task registered successfully" 
 } 
 ``` 
 
 **Python Example:** 
 ```python 
 import requests 
 from datetime import datetime 
 
 url = " `https://api.memu.so/api/v3/memory/memorize` " 
 headers = { 
     "Authorization": "Bearer YOUR_API_KEY", 
     "Content-Type": "application/json" 
 } 
 
 payload = { 
     "conversation": [ 
         {"role": "user", "content": "Hello, how are you?"}, 
         {"role": "assistant", "content": "I'm doing great!"}, 
         {"role": "user", "content": "I love programming in Python."} 
     ], 
     "user_id": "user_123", 
     "agent_id": "agent_456" 
 } 
 
 response = requests.post(url, json=payload, headers=headers) 
 result = response.json() 
 print(f"Task ID: {result['task_id']}") 
 ``` 
 
 --- 
 
 ## 2. Get Task Status 
 
 Get the status of a memorization task. 
 
 **Endpoint:** `GET /api/v3/memory/memorize/status/{task_id}` 
 
 **Path Parameters:** 
 - `task_id` (string, required): Task ID from memorize endpoint 
 
 **Response (200 OK):** 
 ```json 
 { 
   "task_id": "task_789abc123def", 
   "status": "SUCCESS", 
   "created_at": "2024-01-15T10:30:00Z", 
   "completed_at": "2024-01-15T10:30:45Z" 
 } 
 ``` 
 
 **Status Values:** 
 - `PENDING`: Task is waiting to be processed 
 - `PROCESSING`: Task is currently being processed 
 - `SUCCESS`: Task completed successfully 
 - `FAILED`: Task failed with error 
 
 **Python Example:** 
 ```python 
 import requests 
 import time 
 
 def wait_for_task_completion(task_id, api_key, timeout=120): 
     url = f" `https://api.memu.so/api/v3/memory/memorize/status/{task_id}` " 
     headers = {"Authorization": f"Bearer {api_key}"} 
     
     start_time = time.time() 
     while time.time() - start_time < timeout: 
         response = requests.get(url, headers=headers) 
         result = response.json() 
         status = result.get("status") 
         
         if status == "SUCCESS": 
             return result 
         elif status == "FAILED": 
             raise Exception("Task failed") 
         
         time.sleep(5) 
     
     raise TimeoutError("Task did not complete within timeout") 
 ``` 
 
 --- 
 
 ## 3. List Memory Categories 
 
 Retrieve all memory categories for a user/agent combination. 
 
 **Endpoint:** `POST /api/v3/memory/categories` 
 
 **Request Body:** 
 ```json 
 { 
   "user_id": "user_123", 
   "agent_id": "agent_456" 
 } 
 ``` 
 
 **Parameters:** 
 - `user_id` (string, required): Unique user identifier 
 - `agent_id` (string, required): Unique agent identifier 
 
 **Response (200 OK):** 
 ```json 
 { 
   "categories": [ 
     { 
       "name": "personal info", 
       "description": "User's basic info, preferences, and important life facts", 
       "user_id": "user_123", 
       "agent_id": "agent_456", 
       "summary": "# Personal Info\n## Interests & Hobbies\n- The user loves hiking in mountains\n## Career\n- The user is 25 years old and just started their first job" 
     }, 
     { 
       "name": "preferences", 
       "description": "User preferences, likes, dislikes across various domains", 
       "user_id": "user_123", 
       "agent_id": "agent_456", 
       "summary": "# Preferences\n## Food & Dining\n- The user prefers spicy food\n- The user is vegetarian" 
     } 
   ] 
 } 
 ``` 
 
 **Python Example:** 
 ```python 
 import requests 
 
 url = " `https://api.memu.so/api/v3/memory/categories` " 
 headers = { 
     "Authorization": "Bearer YOUR_API_KEY", 
     "Content-Type": "application/json" 
 } 
 
 payload = { 
     "user_id": "user_123", 
     "agent_id": "agent_456" 
 } 
 
 response = requests.post(url, json=payload, headers=headers) 
 result = response.json() 
 
 for category in result.get("categories", []): 
     print(f"Category: {category['name']}") 
     print(f"Summary: {category['summary']}\n") 
 ``` 
 
 --- 
 
 ## 4. Retrieve Memories 
 
 Retrieve memories using semantic search. 
 
 **Endpoint:** `POST /api/v3/memory/retrieve` 
 
 **Request Body (String Query):** 
 ```json 
 { 
   "user_id": "user_123", 
   "agent_id": "agent_456", 
   "query": "What sports does the user enjoy?" 
 } 
 ``` 
 
 **Request Body (Message List with Query Rewriting):** 
 ```json 
 { 
   "user_id": "user_123", 
   "agent_id": "agent_456", 
   "query": [ 
     {"role": "user", "content": "I want to be more active this year"}, 
     {"role": "assistant", "content": "That's a great goal! What kind of activities interest you?"}, 
     {"role": "user", "content": "What sports do I usually enjoy?"} 
   ] 
 } 
 ``` 
 
 **Parameters:** 
 - `user_id` (string, required): Unique user identifier 
 - `agent_id` (string, required): Unique agent identifier 
 - `query` (string | array, required): Search query (string or message list) 
 
 **Response (200 OK):** 
 ```json 
 { 
   "rewritten_query": "What sports and physical activities does the user enjoy?", 
   "categories": [ 
     { 
       "name": "sports_activities", 
       "description": "Sports and fitness related activities", 
       "summary": "User enjoys tennis and outdoor sports" 
     } 
   ], 
   "items": [ 
     { 
       "memory_type": "preference", 
       "content": "John enjoys playing tennis on weekends at the local club every Saturday morning." 
     }, 
     { 
       "memory_type": "habit", 
       "content": "John prefers outdoor sports and physical activities." 
     } 
   ], 
   "resources": [ 
     { 
       "modality": "image", 
       "resource_url": " `https://example.com/tennis-photo.jpg` ", 
       "caption": "Tennis match at local club", 
       "content": "Photo from Saturday tennis session" 
     } 
   ] 
 } 
 ``` 
 
 **Python Example:** 
 ```python 
 import requests 
 
 url = " `https://api.memu.so/api/v3/memory/retrieve` " 
 headers = { 
     "Authorization": "Bearer YOUR_API_KEY", 
     "Content-Type": "application/json" 
 } 
 
 payload = { 
     "user_id": "user_123", 
     "agent_id": "agent_456", 
     "query": "What sports does the user enjoy?" 
 } 
 
 response = requests.post(url, json=payload, headers=headers) 
 result = response.json() 
 
 print(f"Rewritten query: {result['rewritten_query']}") 
 
 for item in result.get("items", []): 
     print(f"[{item['memory_type']}] {item['content']}") 
 ``` 
 
 --- 
 
 ## 5. Delete Memories 
 
 Delete memories for a user. If agent_id is provided, delete only that agent's memories. 
 
 **Endpoint:** `POST /api/v3/memory/delete` 
 
 **Request Body:** 
 ```json 
 { 
   "user_id": "user_123", 
   "agent_id": "agent_456" 
 } 
 ``` 
 
 **Parameters:** 
 - `user_id` (string, required): Unique user identifier 
 - `agent_id` (string, optional): If provided, delete only this agent's memories 
 
 **Response (200 OK):** 
 ```json 
 "Memories deleted successfully" 
 ``` 
 
 **Python Example:** 
 ```python 
 import requests 
 
 url = " `https://api.memu.so/api/v3/memory/delete` " 
 headers = { 
     "Authorization": "Bearer YOUR_API_KEY", 
     "Content-Type": "application/json" 
 } 
 
 payload = { 
     "user_id": "user_123", 
     "agent_id": "agent_456" 
 } 
 
 response = requests.post(url, json=payload, headers=headers) 
 print(response.json()) 
 ``` 
 
 --- 
 
 ## Error Handling 
 
 **Common Error Codes:** 
 | Status Code | Error Type | Description | Solution | 
 |-------------|------------|-------------|----------| 
 | 400 | Bad Request | Invalid request parameters | Check request body structure | 
 | 401 | Unauthorized | Missing or invalid API key | Verify Authorization header | 
 | 404 | Not Found | Resource not found | Check task_id or user_id exists | 
 | 422 | Validation Error | Request validation failed | Check parameter types and values | 
 | 500 | Server Error | Internal server error | Retry request or contact support | 
 
 **Validation Error Response (422):** 
 ```json 
 { 
   "detail": [ 
     { 
       "loc": ["body", "user_id"], 
       "msg": "field required", 
       "type": "value_error.missing" 
     } 
   ] 
 } 
 ``` 
 
 --- 
 
 ## Rate Limits 
 
 | Plan | Concurrent Tasks | 
 |------|------------------| 
 | Free | 4 max | 
 
 --- 
 
 ## Quick Start Example 
 
 ```python 
 import requests 
 import time 
 
 API_KEY = "YOUR_API_KEY" 
 BASE_URL = " `https://api.memu.so` " 
 HEADERS = { 
     "Authorization": f"Bearer {API_KEY}", 
     "Content-Type": "application/json" 
 } 
 
 # Step 1: Memorize a conversation 
 memorize_response = requests.post( 
     f"{BASE_URL}/api/v3/memory/memorize", 
     headers=HEADERS, 
     json={ 
         "conversation": [ 
             {"role": "user", "content": "Hi, my name is Alice"}, 
             {"role": "assistant", "content": "Nice to meet you, Alice!"}, 
             {"role": "user", "content": "I love hiking and photography"} 
         ], 
         "user_id": "alice_001", 
         "agent_id": "assistant_001" 
     } 
 ) 
 task_id = memorize_response.json()["task_id"] 
 print(f"Task started: {task_id}") 
 
 # Step 2: Wait for task completion 
 while True: 
     status_response = requests.get( 
         f"{BASE_URL}/api/v3/memory/memorize/status/{task_id}", 
         headers=HEADERS 
     ) 
     status = status_response.json()["status"] 
     if status == "SUCCESS": 
         print("Memorization complete!") 
         break 
     elif status == "FAILED": 
         print("Memorization failed!") 
         break 
     time.sleep(5) 
 
 # Step 3: Retrieve memories 
 retrieve_response = requests.post( 
     f"{BASE_URL}/api/v3/memory/retrieve", 
     headers=HEADERS, 
     json={ 
         "user_id": "alice_001", 
         "agent_id": "assistant_001", 
         "query": "What are Alice's hobbies?" 
     } 
 ) 
 memories = retrieve_response.json() 
 print(f"Found memories: {memories}") 
 ``` 
 
 --- 
 
 ## Support 
 - Documentation: `https://memu.pro/docs` 
 - Website: `https://memu.pro` 
 - Contact: `https://memu.pro/contact` 
 
 --- 
 This file is designed for AI coding agents to understand and use the MemU API.