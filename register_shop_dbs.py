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

def get_existing_shop_databases():
    """Get list of existing shop databases"""
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database='postgres'
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT datname 
        FROM pg_database 
        WHERE datname LIKE 'talvex_shop_%' 
        ORDER BY datname
    """)
    shop_dbs = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return shop_dbs

def register_shop_databases():
    """Register all existing shop databases in Django settings"""
    shop_dbs = get_existing_shop_databases()
    
    print(f"Found {len(shop_dbs)} shop databases: {shop_dbs}")
    
    for db_name in shop_dbs:
        if db_name not in settings.DATABASES:
            shop_db_config = main_config.copy()
            shop_db_config.update({
                'NAME': db_name,
                'ATOMIC_REQUESTS': False,
            })
            settings.DATABASES[db_name] = shop_db_config
            print(f"  ✓ Registered {db_name}")
        else:
            print(f"  - {db_name} already registered")

register_shop_databases()
print(f"\nTotal databases in Django settings: {len(settings.DATABASES)}")
print("Shop databases are now registered. Please restart your Django server.")
