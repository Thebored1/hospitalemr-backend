import os, sys, django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from core.models import Area, DoctorReferral, AgentAssignment, AgentAssignmentDoctorStatus
from django.contrib.auth import get_user_model
User = get_user_model()

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    # 1. Check amit_field user
    try:
        user = User.objects.get(username='amit_field')
        f.write(f"User: {user.username} | is_staff: {user.is_staff} | role: {user.role}\n\n")
    except User.DoesNotExist:
        f.write("User 'amit_field' not found!\n")
        sys.exit()

    # 2. Check which areas have amit_field as agent
    f.write("=== AREAS WITH amit_field AS AGENT ===\n")
    areas = Area.objects.filter(agent=user)
    for a in areas:
        doc_count = DoctorReferral.objects.filter(address_details__area=a).count()
        f.write(f"  Area: {a.name} (ID: {a.id}) | Doctors: {doc_count}\n")
    f.write(f"Total areas: {areas.count()}\n\n")

    # 3. Check all assignments for amit_field
    f.write("=== ALL ASSIGNMENTS FOR amit_field ===\n")
    assignments = AgentAssignment.objects.filter(agent=user)
    for a in assignments:
        f.write(f"  Assignment: {a.area.name} | Area.agent={a.area.agent} | Date: {a.assigned_at}\n")
    f.write(f"Total assignments: {assignments.count()}\n\n")

    # 4. Check all areas
    f.write("=== ALL AREAS (agent field) ===\n")
    for a in Area.objects.all():
        f.write(f"  {a.name} (ID: {a.id}) -> agent: {a.agent}\n")

    # 5. Simulate API query
    f.write("\n=== SIMULATED API QUERY ===\n")
    assigned_area_ids = Area.objects.filter(agent=user).values_list('id', flat=True)
    from django.db.models import Q
    doctors = DoctorReferral.objects.filter(
        Q(address_details__area_id__in=assigned_area_ids)
    ).distinct()
    f.write(f"Doctors found (before exclusions): {doctors.count()}\n")
    for d in doctors:
        area_name = d.address_details.area.name if d.address_details and d.address_details.area else "None"
        f.write(f"  ID: {d.id} | {d.name} | Area: {area_name}\n")

print("Done - see debug_output.txt")
