import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_user(username, email, password, role):
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(username, email, password, role=role)
        print(f"User '{username}' created with role '{role}'.")
    else:
        print(f"User '{username}' already exists.")

# Create Advisor
create_user('advisor', 'advisor@example.com', 'advisor123', 'advisor')

# Create Maintenance
create_user('maintenance', 'maintenance@example.com', 'maintenance123', 'maintenance')
