import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_project.settings')
django.setup()

from core.models import User

def create_admin():
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        print("Superuser 'admin' created successfully with password 'admin'")
    else:
        print("Superuser 'admin' already exists.")

if __name__ == '__main__':
    create_admin()
