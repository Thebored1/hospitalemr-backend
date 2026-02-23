import os, sys, django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from core.models import DoctorReferral
from django.db.models import Count

with open('audit_output.txt', 'w', encoding='utf-8') as f:
    f.write("=== DUPLICATE DOCTOR INVESTIGATION ===\n\n")
    
    dupes = DoctorReferral.objects.values(
        'name', 'address_details__area__name'
    ).annotate(cnt=Count('id')).filter(cnt__gt=1)
    
    for d in dupes:
        f.write(f"DUPLICATE: '{d['name']}' in '{d['address_details__area__name']}' ({d['cnt']} copies)\n")
        copies = DoctorReferral.objects.filter(
            name=d['name'],
            address_details__area__name=d['address_details__area__name']
        ).order_by('created_at')
        for c in copies:
            f.write(f"  ID: {c.id} | Status: {c.status} | Trip: {c.trip_id} | Created: {c.created_at}\n")
        f.write("\n")
    
    # Also list ALL doctors grouped by area
    f.write("=== ALL DOCTORS BY AREA ===\n\n")
    from core.models import Area
    for area in Area.objects.all():
        docs = DoctorReferral.objects.filter(address_details__area=area).order_by('name')
        f.write(f"Area: {area.name} ({docs.count()} doctors)\n")
        for d in docs:
            f.write(f"  ID: {d.id} | {d.name} | Status: {d.status} | Spec: {d.specialization}\n")
        f.write("\n")

print("Done - see audit_output.txt")
