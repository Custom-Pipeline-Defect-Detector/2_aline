import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"

def test_document_processing_api():
    print("Testing Document Processing API...")
    
    # First, register and login to get a token
    print("\n1. Registering and logging in...")
    try:
        # Register a test user
        register_data = {
            "email": "testuser@example.com",
            "name": "Test User",
            "password": "password123",
            "role_name": "Manager"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
        print(f"Registration: {response.status_code}")
        if response.status_code != 200:
            print(f"Registration response: {response.text}")
    except Exception as e:
        print(f"Registration failed: {e}")
        return

    # Login to get token
    try:
        login_data = {
            "username": "testuser@example.com",
            "password": "password123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
        print(f"Login: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            print(f"Login successful, token type: {token_data['token_type']}")
            auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        else:
            print(f"Login response: {response.text}")
            return
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # Test document processing endpoints
    print("\n2. Testing document processing endpoints...")
    
    # Create a temporary test file
    test_file_path = "test_upload.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test document for processing.\nIt contains some sample text for testing purposes.")
    
    # Test upload endpoint
    print("\n3. Testing document upload...")
    try:
        with open(test_file_path, "rb") as f:
            files = {'file': f}
            response = requests.post(f"{BASE_URL}/api/document-processing/upload", files=files, headers=auth_headers)
            print(f"Upload: {response.status_code}")
            if response.status_code == 200:
                upload_result = response.json()
                print(f"Upload successful: {json.dumps(upload_result, indent=2)}")
                document_id = upload_result.get('id')
            else:
                print(f"Upload response: {response.text}")
                document_id = None
    except Exception as e:
        print(f"Upload failed: {e}")
        document_id = None

    # Test getting all documents
    print("\n4. Testing get all documents...")
    try:
        response = requests.get(f"{BASE_URL}/api/document-processing/all", headers=auth_headers)
        print(f"Get all documents: {response.status_code}")
        if response.status_code == 200:
            documents_result = response.json()
            print(f"Documents retrieved: {len(documents_result.get('documents', []))} documents")
            if documents_result.get('documents'):
                document_id = documents_result['documents'][0]['id']
        else:
            print(f"Get all documents response: {response.text}")
    except Exception as e:
        print(f"Get all documents failed: {e}")

    # Test document status if we have a document ID
    if document_id:
        print(f"\n5. Testing document status for ID: {document_id}...")
        try:
            response = requests.get(f"{BASE_URL}/api/document-processing/status/{document_id}", headers=auth_headers)
            print(f"Document status: {response.status_code}")
            if response.status_code == 200:
                status_result = response.json()
                print(f"Status: {json.dumps(status_result, indent=2)}")
            else:
                print(f"Document status response: {response.text}")
        except Exception as e:
            print(f"Document status failed: {e}")

        # Test document processing
        print(f"\n6. Testing document processing for ID: {document_id}...")
        try:
            response = requests.post(f"{BASE_URL}/api/document-processing/process/{document_id}", headers=auth_headers)
            print(f"Document processing: {response.status_code}")
            if response.status_code == 200:
                process_result = response.json()
                print(f"Processing result: {json.dumps(process_result, indent=2)}")
            else:
                print(f"Document processing response: {response.text}")
        except Exception as e:
            print(f"Document processing failed: {e}")

        # Check status again after processing
        print(f"\n7. Checking status after processing for ID: {document_id}...")
        try:
            response = requests.get(f"{BASE_URL}/api/document-processing/status/{document_id}", headers=auth_headers)
            print(f"Post-processing status: {response.status_code}")
            if response.status_code == 200:
                status_result = response.json()
                print(f"Post-processing status: {json.dumps(status_result, indent=2)}")
            else:
                print(f"Post-processing status response: {response.text}")
        except Exception as e:
            print(f"Post-processing status failed: {e}")

    # Clean up test file
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print(f"\n8. Cleaned up test file: {test_file_path}")

    print("\nDocument processing API tests completed!")

if __name__ == "__main__":
    test_document_processing_api()