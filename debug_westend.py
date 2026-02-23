import os
import sys
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

from core.models import Area, DoctorReferral

def inspect_west_end():
    print("==================================================")
    print("       INSPECTING WEST END DATA (CHECKING DUPLICATES)")
    print("==================================================")
    
    # 1. Find the Area
    areas = Area.objects.filter(name__icontains='West End')
    target_area = areas.first()
    
    if not target_area:
        print("ERROR: 'West End' area not found.")
        return

    print(f"Target Area: {target_area.name} (ID: {target_area.id})")
    
    # 2. Check Doctors via Address Link
    docs = DoctorReferral.objects.filter(address_details__area=target_area)
    print(f"TOTAL RECORDS: {docs.count()}")
    
    print("\n--- Listing Doctors ---")
    print(f"{'ID':<6} | {'Name':<20} | {'Status':<10} | {'Trip':<10}")
    print("-" * 60)
    
    names = []
    for doc in docs:
         print(f"{doc.id:<6} | {doc.name:<20} | {doc.status:<10} | {doc.trip_id if doc.trip else 'None':<10}")
         names.append(doc.name)
         
    unique_names = set(names)
    print("\n--- Summary ---")
    print(f"Total Rows: {len(names)}")
    print(f"Unique Names: {len(unique_names)}")
    
    if len(names) > len(unique_names):
        print("\n[CONCLUSION] Duplicates Detected! App likely shows only Unique Names.")
    else:
        print("\n[CONCLUSION] No Duplicates. Discrepancy is elsewhere.")

if __name__ == '__main__':
    inspect_west_end()
