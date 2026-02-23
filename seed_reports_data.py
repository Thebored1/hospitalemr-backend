import os
import django
import random
from decimal import Decimal
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from core.models import User, DoctorReferral, PatientReferral, Admission, PaymentCategory, Area, Address, Specialization, Qualification

def seed_data():
    print("Seeding test data for reports...")
    
    # 1. Ensure Payment Categories
    categories = [
        ('Cash', 'CASH'),
        ('Ayushman Bharat', 'AYUSHMAN'),
        ('Ayushman Package', 'AYU_PKG'),
        ('Insurance', 'INS'),
    ]
    pay_cats = []
    for name, code in categories:
        cat, _ = PaymentCategory.objects.get_or_create(name=name, code=code)
        pay_cats.append(cat)
    print(f"Verified {len(pay_cats)} payment categories.")

    # 2. Ensure Agents (Advisors)
    agent_names = ['Rahul Marketing', 'Suresh Advisor', 'Priya Sales', 'Amit Field']
    agents = []
    for name in agent_names:
        username = name.lower().replace(' ', '_')
        agent, created = User.objects.get_or_create(
            username=username,
            defaults={'first_name': name.split()[0], 'last_name': name.split()[1], 'role': 'advisor'}
        )
        if created:
            agent.set_password('password123')
            agent.save()
        agents.append(agent)
    print(f"Verified {len(agents)} agents.")

    # 3. Ensure Areas & Doctors
    area_names = ['Downtown', 'North Zone', 'West End', 'Sector 5']
    doctors = []
    specializations = ['Cardiology', 'Orthopedics', 'General Medicine', 'Neurology', 'Pediatrics', 'MD']
    
    # Create master specializations
    for spec_name in specializations:
        Specialization.objects.get_or_create(name=spec_name)
        
    # Ensure MD is in master if not there
    Specialization.objects.get_or_create(name='MD')
    Qualification.objects.get_or_create(name='MBBS')
    Qualification.objects.get_or_create(name='MD')

    for i in range(10):
        area_name = random.choice(area_names)
        area, _ = Area.objects.get_or_create(name=area_name, defaults={'city': 'Nagpur', 'pincode': '440001'})
        
        addr = Address.objects.create(area=area, street=f"Street {i+1}", pincode="440001")
        
        spec = random.choice(specializations)
        doc = DoctorReferral.objects.create(
            name=f"Dr. {random.choice(['Kapoor', 'Sharma', 'Verma', 'Patel', 'Deshmukh'])} {i+1}",
            contact_number=f"987654321{i}",
            specialization=spec,
            degree_qualification=random.choice(['MBBS', 'MD']),
            address_details=addr,
            status='Assigned'
        )
        doctors.append(doc)
    print(f"Created {len(doctors)} doctors.")

    # 4. Create Patient Referrals and Admissions
    patient_names = [
        'Anil Gupta', 'Sunita Rao', 'Vijay Kumar', 'Ramesh Singh', 'Meena Devi',
        'Sanjay Patil', 'Kavita Iyer', 'Rajesh Khan', 'Pooja Tiwari', 'Arun Joshi',
        'Deepak More', 'Sneha Kulkarni', 'Vivek Agrawal', 'Lata Mangeshkar', 'Kishore Kumar',
        'Amitabh B', 'Shah Rukh K', 'Salman K', 'Aamir K', 'Hrithik R'
    ]

    admission_types = ['OPD', 'IPD']
    
    for i in range(20):
        agent = random.choice(agents)
        doctor = random.choice(doctors)
        cat = random.choice(pay_cats)
        pat_name = patient_names[i]
        
        # Create Patient Referral
        referral = PatientReferral.objects.create(
            agent=agent,
            patient_name=pat_name,
            age=random.randint(20, 70),
            gender=random.choice(['Male', 'Female']),
            phone=f"90000000{i:02d}",
            illness="Test Illness",
            status='Admitted'
        )
        
        # Create Admission
        adm_type = random.choice(admission_types)
        
        # Charges
        bed = Decimal(random.randint(1000, 5000)) if adm_type == 'IPD' else Decimal('0.00')
        nursing = Decimal(random.randint(500, 2000)) if adm_type == 'IPD' else Decimal('0.00')
        consult = Decimal(random.randint(500, 1500))
        invest = Decimal(random.randint(1000, 10000))
        proc = Decimal(random.randint(5000, 50000)) if random.random() > 0.5 else Decimal('0.00')
        
        Admission.objects.create(
            patient_name=pat_name,
            patient_referral=referral,
            referred_by_doctor=doctor,
            admission_type=adm_type,
            payment_category=cat,
            status='ADMITTED',
            bed_charges=bed,
            nursing_charges=nursing,
            doctor_consultation_charges=consult,
            investigation_charges=invest,
            procedural_surgical_charges=proc,
            other_charges=Decimal(random.randint(100, 1000))
        )
    
    print(f"Created 20 patient referrals and admissions.")
    print("Data seeding completed successfully!")

if __name__ == "__main__":
    seed_data()
