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


@receiver(post_save, sender=ShopProfile)
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
    if created and not instance.database_name:
        try:
            # Create the shop database (this also registers it)
            db_name = ShopDatabaseManager.create_shop_database(
                instance.pk, 
                instance.shop_name or f"shop_{instance.pk}"
            )
            
            # Update the shop profile with the database name
            # Use update_fields to avoid triggering this signal again
            instance.database_name = db_name
            instance.save(update_fields=['database_name'])
            
            logger.info(
                f"Successfully created and registered database for shop {instance.pk}: {db_name}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to create database for shop {instance.pk} "
                f"(name: {instance.shop_name}): {e}"
            )
            
            # Delete the shop profile to maintain consistency
            # This prevents orphaned ShopProfile records without databases
            try:
                instance.delete()
                logger.info(f"Rolled back: deleted ShopProfile {instance.pk}")
            except Exception as delete_error:
                logger.error(f"Failed to rollback ShopProfile {instance.pk}: {delete_error}")
            
            # Re-raise the original exception to inform the caller
            raise Exception(f"Failed to create shop database: {e}")


@receiver(post_delete, sender=ShopProfile)
def delete_shop_database(sender, instance, **kwargs):
    """
    Delete the shop's database when the shop profile is deleted.
    
    This ensures cleanup of shop-specific databases when shops are removed.
    Errors are logged but don't prevent the ShopProfile deletion.
    """
    if instance.database_name:
        try:
            ShopDatabaseManager.drop_shop_database(instance.pk)
            logger.info(f"Deleted database for shop {instance.pk}: {instance.database_name}")
            
        except Exception as e:
            # Log the error but don't prevent deletion
            # The ShopProfile is already being deleted, so we just log the cleanup failure
            logger.warning(
                f"Failed to delete shop database {instance.database_name} "
                f"for shop {instance.pk}: {e}"
            )

