import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.conf import settings
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Get main DB config
main_config = settings.DATABASES['main']
host = main_config['HOST']
port = main_config['PORT']
user = main_config['USER']
password = main_config['PASSWORD']

shop_id = 1
db_name = f'talvex_shop_{shop_id}'

print(f'Creating shop database: {db_name}')

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database='postgres'
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

try:
    # Check if database exists
    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    if cursor.fetchone():
        print(f'  Database {db_name} already exists')
    else:
        # Create database
        cursor.execute(f'CREATE DATABASE {db_name}')
        print(f'  ✓ Created database {db_name}')
    
    # Connect to new database and create tables
    conn2 = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db_name
    )
    conn2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor2 = conn2.cursor()
    
    # Create customers table
    cursor2.execute("""
        CREATE TABLE IF NOT EXISTS customers_customer (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            mobile VARCHAR(20),
            address TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print('  ✓ Created customers_customer table')
    
    # Create products table
    cursor2.execute("""
        CREATE TABLE IF NOT EXISTS store_product (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print('  ✓ Created store_product table')
    
    cursor2.close()
    conn2.close()
    
    # Add to Django settings
    settings.DATABASES[db_name] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_name,
        'USER': user,
        'PASSWORD': password,
        'HOST': host,
        'PORT': port,
        'ATOMIC_REQUESTS': False,
    }
    
    print(f'\n✓ Shop database {db_name} is ready!')
    print('Please restart your Django server')
    
except Exception as e:
    print(f'  ✗ Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    cursor.close()
    conn.close()
