import requests
import json

BASE_URL = 'http://127.0.0.1:8000'
USERNAME = 'advisor'
PASSWORD = 'apassword' # Assuming default password you might have set, or I'll try to find it. checking setup logic.

# Actually, I'll use the creating script or just try to get token
# Wait, let's look at how users were created.
# I'll use a script that imports django models directly to force-create a token or log in?
# No, "runserver" is running. I should hit the live server.
# I need the password.

# Alternative: Use Django Test Client in a script that sets up the environment!
import os
import django
import sys

# Setup Django environment
sys.path.append('c:\\Users\\paper\\StudioProjects\\hospitalemr\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from rest_framework.test import APIClient
from core.models import User

try:
    user = User.objects.get(username='advisor')
    client = APIClient()
    client.force_authenticate(user=user)
    
    print(f"Fetching referrals for user: {user.username} (ID: {user.id})")
    
    response = client.get('/api/doctor-referrals/')
    
    if response.status_code == 200:
        data = response.json()
        print(f"Status Code: {response.status_code}")
        print(f"Count: {len(data)}")
        if len(data) > 0:
            print("First item JSON:")
            print(json.dumps(data[0], indent=2))
            
            print("\nScan of all 'trip' values:")
            for item in data:
                print(f"ID: {item['id']}, Name: {item['name']}, Trip: {item.get('trip')}")
        else:
            print("No data returned.")
    else:
        print(f"Error: {response.status_code}")
        print(response.content)

except User.DoesNotExist:
    print("User 'advisor' not found!")
except Exception as e:
    print(f"Error: {e}")
