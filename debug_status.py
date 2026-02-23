import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')

try:
    django.setup()
except Exception:
    pass

from core.models import Area, DoctorReferral

def run():
    with open('debug_output.txt', 'w', encoding='utf-8') as f:
        f.write("--- STATUS CHECK ---\n")
        try:
            area = Area.objects.filter(name__icontains='West End').first()
            if not area:
                f.write("West End not found\n")
                return
                
            docs = DoctorReferral.objects.filter(address_details__area=area)
            f.write(f"Total Doctors: {docs.count()}\n")
            
            names = []
            for d in docs:
                f.write(f"ID: {d.id} | Name: {d.name} | Status: {d.status} | Trip: {d.trip_id}\n")
                names.append(d.name)
            
            f.write(f"Unique Names: {len(set(names))}\n")
                
        except Exception as e:
            f.write(str(e))

if __name__ == '__main__':
    run()
