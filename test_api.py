import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("Testing API endpoints...")
    
    # Test health endpoint
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test registration
    try:
        register_data = {
            "email": "admin@example.com",
            "name": "Admin User",
            "password": "password123",
            "role_name": "Manager"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        print(f"Registration: {response.status_code}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
        else:
            print(f"User registered: {response.json()}")
    except Exception as e:
        print(f"Registration failed: {e}")
    
    # Test login
    try:
        login_data = {
            "username": "admin@example.com",
            "password": "password123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
        print(f"Login: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            print(f"Login successful, token type: {token_data['token_type']}")
            
            # Test getting proposals with auth
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            response = requests.get(f"{BASE_URL}/api/proposals", headers=headers)
            print(f"Proposals: {response.status_code}")
            if response.status_code == 200:
                proposals = response.json()
                print(f"Found {len(proposals)} proposals")
                for prop in proposals[:5]:
                    print(f"  ID: {prop.get('id')}, Table: {prop.get('target_table')}, Action: {prop.get('proposed_action')}")
            else:
                print(f"Proposals response: {response.text}")
        else:
            print(f"Login response: {response.text}")
    except Exception as e:
        print(f"Login failed: {e}")

if __name__ == "__main__":
    test_api()