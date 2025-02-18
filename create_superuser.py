import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pecuaria_project.settings')
django.setup()

from django.contrib.auth.models import User

# Criar superusuário se não existir
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
