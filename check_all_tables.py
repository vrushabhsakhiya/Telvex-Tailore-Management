import os
import django
from django.db import connections

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def check_tables(db_name):
    print(f"\nChecking tables in {db_name}:")
    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            tables = cursor.fetchall()
            for t in tables:
                print(f"  - {t[0]}")
    except Exception as e:
        print(f"Error: {e}")

check_tables('main')
check_tables('talvex_shop_1')
check_tables('talvex_shop_2')
