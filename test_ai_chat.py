import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Authorization token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NzI0NjA5MzgsInN1YiI6InRlc3RAZXhhbXBsZS5jb20ifQ.wjG-PA0DLQqt69EyyeCodXOLxaI1x69jied0XohtJmg"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_ai_chat():
    print("Testing AI Chat functionality...")
    
    # Create a new session
    print("\n1. Creating a new AI chat session...")
    session_data = {"title": "Test Chat Session"}
    response = requests.post(f"{BASE_URL}/api/ai/sessions", headers=HEADERS, json=session_data)
    
    if response.status_code == 200:
        session_info = response.json()
        session_id = session_info['id']
        print(f"   Session created successfully with ID: {session_id}")
    else:
        print(f"   Failed to create session: {response.status_code} - {response.text}")
        return
    
    # Send a message to the session
    print("\n2. Sending a message to the AI...")
    message_data = {"message": "Hello, can you tell me about the projects in the system?"}
    response = requests.post(f"{BASE_URL}/api/ai/sessions/{session_id}/messages", headers=HEADERS, json=message_data)
    
    if response.status_code == 200:
        reply = response.json()
        print(f"   AI Reply: {reply['reply']}")
        print(f"   Memory Updated: {reply['memory_updated']}")
    else:
        print(f"   Failed to send message: {response.status_code} - {response.text}")
        
    # Try another message
    print("\n3. Sending another message to test AI response...")
    message_data = {"message": "What can you help me with regarding documents?"}
    response = requests.post(f"{BASE_URL}/api/ai/sessions/{session_id}/messages", headers=HEADERS, json=message_data)
    
    if response.status_code == 200:
        reply = response.json()
        print(f"   AI Reply: {reply['reply']}")
        print(f"   Memory Updated: {reply['memory_updated']}")
    else:
        print(f"   Failed to send message: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_ai_chat()