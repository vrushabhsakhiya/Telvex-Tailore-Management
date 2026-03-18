import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.db import connection

# SQL to create django_session table manually
sql = """
CREATE TABLE IF NOT EXISTS django_session (
    session_key varchar(40) NOT NULL PRIMARY KEY,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);
CREATE INDEX IF NOT EXISTS django_session_expire_date_a5c62663 ON django_session (expire_date);
"""

print("Creating django_session table manually...")
with connection.cursor() as c:
    c.execute(sql)
    print("✓ Table created successfully")
    
    # Verify
    c.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'django_session'")
    exists = c.fetchone()
    print(f"\nVerification: django_session exists = {bool(exists)}")
