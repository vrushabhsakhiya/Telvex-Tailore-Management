import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.db import connection, connections
from django.core.management import call_command

print("Checking for django_session table...")

with connection.cursor() as c:
    c.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'django_session'")
    exists = c.fetchone()
    
    if exists:
        print("✓ django_session table exists")
    else:
        print("✗ django_session table missing - creating now...")
        # Run migrations for sessions only
        call_command('migrate', 'sessions', verbosity=2)
        print("Session table created!")
        
print("\nChecking all configured databases:")
for db_name in connections:
    print(f"  Database: {db_name}")
    conn = connections[db_name]
    try:
        with conn.cursor() as c:
            c.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'django_session'")
            exists = c.fetchone()
            print(f"    django_session exists: {bool(exists)}")
    except Exception as e:
        print(f"    Error: {e}")
