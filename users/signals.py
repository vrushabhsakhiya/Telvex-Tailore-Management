"""
Django signals for shop database management.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import ShopProfile
from .database_manager import ShopDatabaseManager

logger = logging.getLogger(__name__)


# @receiver(post_save, sender=ShopProfile)
def create_shop_database(sender, instance, created, **kwargs):
    """
    Automatically create and register database when ShopProfile is created.
    
    This signal handler:
    1. Creates a new PostgreSQL database for the shop
    2. Registers it in Django's DATABASES setting
    3. Runs migrations for shop-specific apps
    4. Updates the ShopProfile with the database name
    5. Rolls back (deletes ShopProfile) if any step fails
    """
    pass # Disabled for single-database multi-tenant model

# @receiver(post_delete, sender=ShopProfile)
def delete_shop_database(sender, instance, **kwargs):
    """
    Delete the shop's database when the shop profile is deleted.
    
    This ensures cleanup of shop-specific databases when shops are removed.
    Errors are logged but don't prevent the ShopProfile deletion.
    """
    pass # Disabled for single-database multi-tenant model
