"""
Quick test script to verify shop database registration.
Run this after starting Django to check if databases are registered.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from users.models import ShopProfile

print("=" * 60)
print("SHOP DATABASE REGISTRATION TEST")
print("=" * 60)

# Check registered databases
print(f"\nRegistered databases: {list(settings.DATABASES.keys())}")

# Check shop profiles
shops = ShopProfile.objects.filter(database_name__isnull=False).exclude(database_name='')
print(f"\nShop profiles with databases: {shops.count()}")

for shop in shops:
    db_name = shop.database_name
    is_registered = db_name in settings.DATABASES
    status = "✓ REGISTERED" if is_registered else "✗ NOT REGISTERED"
    print(f"  Shop {shop.id} ({shop.shop_name}): {db_name} - {status}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
