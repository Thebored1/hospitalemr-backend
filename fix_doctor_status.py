import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')

try:
    django.setup()
except Exception:
    pass

from core.models import DoctorReferral

def fix_data():
    print("--- FIXING INCONSISTENT DATA ---")
    # Find doctors who are 'Referred' (Visited) but have NO trip linked
    # This state hides them from the App (pending list) but they aren't actually on a trip
    
    inconsistent_docs = DoctorReferral.objects.filter(status='Referred', trip__isnull=True)
    count = inconsistent_docs.count()
    print(f"Found {count} inconsistent doctors.")
    
    if count > 0:
        print("Resetting status to 'Assigned'...")
        updated = inconsistent_docs.update(status='Assigned')
        print(f"Updated {updated} doctors.")
    else:
        print("No inconsistent data found.")

if __name__ == '__main__':
    fix_data()
