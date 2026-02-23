import os
import django
import sys

# Setup Django environment
sys.path.append('c:\\Users\\paper\\StudioProjects\\hospitalemr\\backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospitalemr_backend.settings')
django.setup()

from core.models import Trip, DoctorReferral, User
from django.utils import timezone

def fix_orphaned_referrals():
    orphaned_referrals = DoctorReferral.objects.filter(trip__isnull=True)
    count = orphaned_referrals.count()
    
    if count == 0:
        print("No orphaned doctor referrals found. Everything looks good.")
        return

    print(f"Found {count} orphaned doctor referrals. Creating a default trip...")

    # We need a user to assign the trip to.
    # We'll try to use the first user, or create one if none exist (unlikely if referrals exist)
    # Ideally, we should group by agent and create a trip for each agent.
    
    # Get distinct agents from orphaned referrals
    agent_ids = orphaned_referrals.values_list('agent', flat=True).distinct()
    
    for agent_id in agent_ids:
        try:
            agent = User.objects.get(pk=agent_id)
            # Create a "Legacy Trip" for this agent to hold old referrals
            trip = Trip.objects.create(
                agent=agent,
                status='COMPLETED',
                additional_expenses="Legacy Data Migration",
                start_time=timezone.now()
            )
            
            # Update referrals for this agent
            updated = DoctorReferral.objects.filter(trip__isnull=True, agent=agent).update(trip=trip)
            print(f"Created migration trip for agent {agent.username} and assigned {updated} referrals.")
            
        except User.DoesNotExist:
            print(f"Agent with ID {agent_id} not found. Skipping referrals for this agent.")

if __name__ == '__main__':
    fix_orphaned_referrals()
