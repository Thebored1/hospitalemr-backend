import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from core.models import DoctorReferral, Specialization, Qualification

def sync_data():
    print("Synchronizing specialization and qualification master tables...")

    # 1. Sync Specializations
    specs = DoctorReferral.objects.exclude(specialization__isnull=True).exclude(specialization='').values_list('specialization', flat=True).distinct()
    spec_count = 0
    for name in specs:
        # Use simple name match (strip leading/trailing space)
        clean_name = name.strip()
        if clean_name:
            _, created = Specialization.objects.get_or_create(name=clean_name)
            if created:
                spec_count += 1
    
    print(f"Created {spec_count} new specialization records.")

    # 2. Sync Qualifications
    quals = DoctorReferral.objects.exclude(degree_qualification__isnull=True).exclude(degree_qualification='').values_list('degree_qualification', flat=True).distinct()
    qual_count = 0
    for name in quals:
        clean_name = name.strip()
        if clean_name:
            _, created = Qualification.objects.get_or_create(name=clean_name)
            if created:
                qual_count += 1
    
    print(f"Created {qual_count} new qualification records.")
    print("Synchronization completed successfully!")

if __name__ == "__main__":
    sync_data()
