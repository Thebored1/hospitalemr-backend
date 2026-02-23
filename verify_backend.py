import requests
import json
import time

BASE_URL = 'http://127.0.0.1:8000/api'

def test_backend():
    # Wait for server to start
    print("Waiting for server...")
    time.sleep(2)
    
    # 1. Login to get Token
    print("1. Testing Login...")
    try:
        response = requests.post(f'{BASE_URL}/api-token-auth/', data={'username': 'admin', 'password': 'admin123'})
        if response.status_code == 200:
            token = response.json().get('token')
            print(f"   Success! Token: {token[:10]}...")
        else:
            print(f"   Failed! Status: {response.status_code}, Body: {response.text}")
            return
    except Exception as e:
        print(f"   Failed to connect: {e}") 
        return

    headers = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}

    # 2. Create a Task
    print("\n2. Testing Create Task...")
    task_data = {
        "title": "Fix AC in OP",
        "description": "AC unit leaking water",
        "status": "Open",
        "allotted_budget": "5000",
        "fix_by": "2023-12-31T12:00:00Z",
        "location": "OP Ward",
        "issue_category": "Electrical"
    }
    response = requests.post(f'{BASE_URL}/tasks/', headers=headers, json=task_data)
    if response.status_code == 201:
        print("   Success! Task Created.")
    else:
        print(f"   Failed! Status: {response.status_code}, Body: {response.text}")

    # 3. Create Doctor Referral
    print("\n3. Testing Create Doctor Referral...")
    referral_data = {
        "name": "Dr. House",
        "contact_number": "1234567890",
        "address": "Princeton",
        "specialization": "Diagnostic",
        "additional_details": "Very grumpy",
        "status": "New"
    }
    response = requests.post(f'{BASE_URL}/doctor-referrals/', headers=headers, json=referral_data)
    if response.status_code == 201:
        print("   Success! Referral Created.")
    else:
        print(f"   Failed! Status: {response.status_code}, Body: {response.text}")

    print("\nVerification Complete.")

if __name__ == "__main__":
    test_backend()
