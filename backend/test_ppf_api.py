"""Test script to verify PPF API is working"""
import requests
import json

# You'll need to replace this with your actual token
# Get it from browser localStorage or login first
TOKEN = "your_token_here"

def test_ppf_api():
    base_url = "http://localhost:8000/api/v1/ppf"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("Testing PPF API endpoints...\n")
    
    # Test 1: Get all PPF accounts
    print("1. GET /api/v1/ppf/")
    response = requests.get(f"{base_url}/", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print(f"Number of accounts: {len(data)}")
    else:
        print(f"Error: {response.text}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Get PPF summary
    print("2. GET /api/v1/ppf/summary")
    response = requests.get(f"{base_url}/summary", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    print("To use this script:")
    print("1. Open browser console")
    print("2. Run: localStorage.getItem('token')")
    print("3. Copy the token and paste it in this script")
    print("4. Run: python test_ppf_api.py")
    print("\nOr just run the fetch command in browser console as suggested.")

# Made with Bob
