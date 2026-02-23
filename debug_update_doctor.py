import os
import django
import sys
import json

# Setup Django environment
sys.path.append('c:\\Users\\paper\\StudioProjects\\hospitalemr\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from rest_framework.test import APIClient
from core.models import User, Trip, DoctorReferral

def run_test():
    try:
        user = User.objects.get(username='advisor')
        client = APIClient()
        client.force_authenticate(user=user)
        
        # 1. Get an active trip or create one
        trip = Trip.objects.filter(agent=user, status='ONGOING').first()
        if not trip:
            print("No ongoing trip found. Creating dummy trip...")
            trip = Trip.objects.create(agent=user, status='ONGOING')
        
        print(f"Using Trip ID: {trip.id}")

        # 2. Create a new doctor referral
        print("Creating new doctor referral...")
        create_resp = client.post('/api/doctor-referrals/', {
            'name': 'Test Pending Doc',
            'contact_number': '123',
            'address': 'Test Addr',
            'specialization': 'Test Spec',
            'degree_qualification': 'MBBS',
            'additional_details': 'None',
            'status': 'New Referral'
        }, format='json')
        
        if create_resp.status_code != 201:
            print(f"Failed to create doc: {create_resp.content}")
            return
            
        doc_id = create_resp.data['id']
        print(f"Created Doctor ID: {doc_id}")
        
        # 3. Verify it is pending
        doc = DoctorReferral.objects.get(id=doc_id)
        print(f"Initial State -> Trip: {doc.trip}, Status: {doc.status}")
        
        # 4. Patch update to link trip and change status
        print("Patching doctor to link trip and update status...")
        patch_resp = client.patch(f'/api/doctor-referrals/{doc_id}/', {
            'trip': trip.id,
            'status': 'Visited',
            'remarks': 'Visited via patch'
        }, format='json')
        
        if patch_resp.status_code != 200:
             print(f"Failed to patch doc: {patch_resp.content}")
             return

        print("Patch response data:", json.dumps(patch_resp.data, indent=2))
        
        # 5. Verify final state
        doc.refresh_from_db()
        print(f"Final State -> Trip: {doc.trip}, Status: {doc.status}")
        
        if doc.trip is not None and doc.status == 'Visited':
            print("SUCCESS: Doctor correctly updated.")
        else:
            print("FAILURE: Doctor update did not stick.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    run_test()
