"""Full system audit: data integrity, API logic, edge cases."""
import os, sys, django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from core.models import (
    Area, DoctorReferral, AgentAssignment, AgentAssignmentDoctorStatus,
    Address, Trip, User
)
from django.db.models import Q, Count

issues = []

def check(label, condition, detail=""):
    status = "OK" if condition else "ISSUE"
    entry = f"[{status}] {label}"
    if detail:
        entry += f"\n       {detail}"
    if not condition:
        issues.append(label)
    return entry

with open('audit_output.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 60 + "\n")
    f.write("       FULL SYSTEM AUDIT\n")
    f.write("=" * 60 + "\n\n")

    # ===== 1. DATA INTEGRITY =====
    f.write("--- 1. DATA INTEGRITY ---\n\n")

    # 1a. Orphan doctors (no address)
    orphans = DoctorReferral.objects.filter(address_details__isnull=True)
    f.write(check(
        "Orphan doctors (no address link)",
        orphans.count() == 0,
        f"Found {orphans.count()}: {[d.name for d in orphans[:5]]}" if orphans.exists() else ""
    ) + "\n")

    # 1b. Addresses with no area
    bad_addrs = Address.objects.filter(area__isnull=True)
    f.write(check(
        "Addresses with no area",
        bad_addrs.count() == 0,
        f"Found {bad_addrs.count()}" if bad_addrs.exists() else ""
    ) + "\n")

    # 1c. Doctors with status='Referred' but no trip (inconsistent)
    inconsistent = DoctorReferral.objects.filter(status='Referred', trip__isnull=True)
    f.write(check(
        "Doctors with status='Referred' but no trip (stale data)",
        inconsistent.count() == 0,
        f"Found {inconsistent.count()}: {[d.name for d in inconsistent[:5]]}" if inconsistent.exists() else ""
    ) + "\n")

    # 1d. Doctors with trip set but status != 'Referred'
    trip_no_status = DoctorReferral.objects.filter(trip__isnull=False).exclude(status='Referred')
    f.write(check(
        "Doctors with trip but status != 'Referred'",
        trip_no_status.count() == 0,
        f"Found {trip_no_status.count()}: {[(d.name, d.status) for d in trip_no_status[:5]]}" if trip_no_status.exists() else ""
    ) + "\n")

    # 1e. Duplicate doctor names in same area
    from django.db.models import Count as C2
    dupes = DoctorReferral.objects.values('name', 'address_details__area').annotate(
        cnt=C2('id')
    ).filter(cnt__gt=1)
    f.write(check(
        "Duplicate doctor names in same area",
        dupes.count() == 0,
        f"Found {dupes.count()} groups" if dupes.exists() else ""
    ) + "\n")

    # ===== 2. ASSIGNMENT INTEGRITY =====
    f.write("\n--- 2. ASSIGNMENT INTEGRITY ---\n\n")

    # 2a. Areas with agent but no matching assignment
    areas_with_agent = Area.objects.filter(agent__isnull=False)
    for area in areas_with_agent:
        has_assignment = AgentAssignment.objects.filter(agent=area.agent, area=area).exists()
        f.write(check(
            f"Area '{area.name}' agent={area.agent} has matching assignment",
            has_assignment,
            "No AgentAssignment record exists!" if not has_assignment else ""
        ) + "\n")

    # 2b. Assignments without doctor statuses
    assignments = AgentAssignment.objects.all()
    for a in assignments:
        status_count = AgentAssignmentDoctorStatus.objects.filter(assignment=a).count()
        doctor_count = DoctorReferral.objects.filter(address_details__area=a.area).count()
        f.write(check(
            f"Assignment '{a.agent.username} -> {a.area.name}' has doctor statuses",
            status_count == doctor_count,
            f"Statuses: {status_count}, Doctors in area: {doctor_count}" if status_count != doctor_count else f"All {status_count} doctors tracked"
        ) + "\n")

    # 2c. Assignment area.agent mismatch (assignment exists but area.agent points elsewhere)
    for a in assignments:
        f.write(check(
            f"Assignment '{a}' area.agent matches assignment.agent",
            a.area.agent == a.agent or a.area.agent is None,
            f"area.agent={a.area.agent}, assignment.agent={a.agent}" if a.area.agent != a.agent else ""
        ) + "\n")

    # ===== 3. TRIP INTEGRITY =====
    f.write("\n--- 3. TRIP INTEGRITY ---\n\n")

    trips = Trip.objects.all()
    f.write(f"Total trips: {trips.count()}\n")
    for t in trips:
        f.write(f"  Trip {t.id} | Agent: {t.agent} | Status: {t.status} | Start: {t.start_time}\n")
        # Check if any doctors point to this trip
        docs_on_trip = DoctorReferral.objects.filter(trip=t)
        f.write(f"    Doctors on this trip: {docs_on_trip.count()}\n")

    # ===== 4. USER/ROLE CHECK =====
    f.write("\n--- 4. USER/ROLE CHECK ---\n\n")

    advisors = User.objects.filter(role='advisor')
    for u in advisors:
        area_count = Area.objects.filter(agent=u).count()
        f.write(f"Advisor: {u.username} | is_staff={u.is_staff} | Areas assigned: {area_count}\n")

    # ===== 5. API SIMULATION FOR EACH ADVISOR =====
    f.write("\n--- 5. API SIMULATION (doctors per advisor) ---\n\n")

    for u in advisors:
        assigned_area_ids = Area.objects.filter(agent=u).values_list('id', flat=True)
        all_docs = DoctorReferral.objects.filter(
            Q(address_details__area_id__in=assigned_area_ids)
        ).distinct()

        # Check exclusions
        current_assignments = AgentAssignment.objects.filter(
            agent=u, area_id__in=assigned_area_ids
        )
        inactive_ids = set(AgentAssignmentDoctorStatus.objects.filter(
            assignment__in=current_assignments, is_active=False
        ).values_list('doctor_id', flat=True))
        visited_ids = set(AgentAssignmentDoctorStatus.objects.filter(
            assignment__in=current_assignments, is_visited=True
        ).values_list('doctor_id', flat=True))

        final_docs = all_docs.exclude(id__in=inactive_ids | visited_ids)

        f.write(f"Advisor: {u.username}\n")
        f.write(f"  Areas: {list(assigned_area_ids)}\n")
        f.write(f"  All doctors: {all_docs.count()}\n")
        f.write(f"  Excluded (inactive): {len(inactive_ids)}\n")
        f.write(f"  Excluded (visited): {len(visited_ids)}\n")
        f.write(f"  Final (app shows): {final_docs.count()}\n\n")

    # ===== SUMMARY =====
    f.write("\n" + "=" * 60 + "\n")
    f.write(f"TOTAL ISSUES FOUND: {len(issues)}\n")
    for i, issue in enumerate(issues, 1):
        f.write(f"  {i}. {issue}\n")
    if not issues:
        f.write("  No issues found! System is clean.\n")
    f.write("=" * 60 + "\n")

print(f"Audit complete. Found {len(issues)} issue(s). See audit_output.txt")
