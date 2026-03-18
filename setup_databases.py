#!/usr/bin/env python
"""
Setup script for multi-tenant database architecture.
Creates the main database and prepares for shop-specific databases.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

def create_main_database():
    """Create the main database if it doesn't exist."""
    
    # Database configuration from environment
    db_name = 'talvex_main'
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', 'postgres')
    
    print(f"Using database configuration:")
    print(f"  Host: {host}:{port}")
    print(f"  User: {user}")
    print(f"  Database: {db_name}")
    
    print(f"Creating main database: {db_name}")
    
    # Connect to PostgreSQL (not to a specific database)
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
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            # Create the database
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"✓ Database '{db_name}' created successfully")
        else:
            print(f"✓ Database '{db_name}' already exists")
            
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return False
    finally:
        cursor.close()
        conn.close()
    
    return True

def run_migrations():
    """Run Django migrations for the main database."""
    print("Running migrations for main database...")
    
    try:
        # Run migrations
        os.system(f"python {os.path.dirname(__file__)}/manage.py migrate --database=main")
        print("✓ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"✗ Migration error: {e}")
        return False

def main():
    """Main setup function."""
    print("=== Talvex Multi-Tenant Database Setup ===")
    print()
    
    # Create main database
    if not create_main_database():
        print("Setup failed: Could not create main database")
        sys.exit(1)
    
    print()
    
    # Run migrations
    if not run_migrations():
        print("Setup failed: Could not run migrations")
        sys.exit(1)
    
    print()
    print("=== Setup Complete ===")
    print("Main database 'talvex_main' is ready!")
    print()
    print("Next steps:")
    print("1. Create a superuser: python manage.py createsuperuser --database=main")
    print("2. Register shops through the admin panel or API")
    print("3. Each shop will automatically get its own database")
    print()
    print("Database structure:")
    print("- Main database (talvex_main): Users, ShopProfiles, global data")
    print("- Shop databases (talvex_shop_{id}): Customers, Products, Bills")

if __name__ == '__main__':
    main()
