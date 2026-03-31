"""
Database manager for creating and managing shop-specific databases.
"""

import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from django.conf import settings
from django.db import connection
from django.core.management import call_command
from .models import ShopProfile

logger = logging.getLogger(__name__)

class ShopDatabaseManager:
    """
    Manages creation and configuration of shop-specific databases.
    """
    
    @staticmethod
    def create_shop_database(shop_id, shop_name):
        """
        Create a new database for a shop.
        
        Args:
            shop_id: The shop's primary key
            shop_name: The shop's name (used for database naming)
        
        Returns:
            str: The database name that was created
        """
        # Generate database name
        db_name = f"talvex_shop_{shop_id}"
        
        # Get connection parameters from main database
        main_db_config = settings.DATABASES['main']
        host = main_db_config.get('HOST', 'localhost')
        port = main_db_config.get('PORT', '5432')
        user = main_db_config.get('USER', '')
        password = main_db_config.get('PASSWORD', '')
        
        # Connect to PostgreSQL (not to a specific database)
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        try:
            # Create the database
            cursor.execute(f"CREATE DATABASE {db_name}")
            logger.info(f"Created database: {db_name}")
            
            # Register the database in Django settings
            if not ShopDatabaseManager.ensure_database_registered(shop_id):
                raise Exception(f"Failed to register database {db_name}")
            
            # Run migrations for the new database
            ShopDatabaseManager._migrate_shop_database(db_name)
            
            return db_name
            
        except Exception as e:
            logger.error(f"Failed to create database {db_name}: {e}")
            # If database creation fails, try to clean up
            try:
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            except:
                pass
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def _register_shop_database(db_name):
        """Register a new shop database in Django settings."""
        main_db_config = settings.DATABASES['main']
        
        # Create database configuration for the shop
        shop_db_config = main_db_config.copy()
        shop_db_config.update({
            'NAME': db_name,
        })
        
        # Add to DATABASES setting
        settings.DATABASES[db_name] = shop_db_config
    
    @staticmethod
    def _migrate_shop_database(db_name):
        """Run migrations for shop-specific apps on the new database."""
        # Migrate only shop-specific apps
        shop_apps = ['customers', 'store']
        
        for app in shop_apps:
            try:
                call_command('migrate', app, database=db_name, verbosity=0)
                logger.info(f"Migrated {app} for {db_name}")
            except Exception as e:
                logger.warning(f"Failed to migrate {app} for {db_name}: {e}")
    
    @staticmethod
    def drop_shop_database(shop_id):
        """
        Drop a shop's database.
        
        Args:
            shop_id: The shop's primary key
        """
        db_name = f"talvex_shop_{shop_id}"
        
        # Get connection parameters
        main_db_config = settings.DATABASES['main']
        host = main_db_config['HOST']
        port = main_db_config['PORT']
        user = main_db_config['USER']
        password = main_db_config['PASSWORD']
        
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
            # Drop connections to the database
            cursor.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_name}'
                  AND pid <> pg_backend_pid()
            """)
            
            # Drop the database
            cursor.execute(f"DROP DATABASE {db_name}")
            
            # Remove from Django settings
            if db_name in settings.DATABASES:
                del settings.DATABASES[db_name]
                
        except Exception as e:
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_shop_database_name(shop_id):
        """Get the database name for a shop."""
        return f"talvex_shop_{shop_id}"
    
    @staticmethod
    def shop_database_exists(shop_id):
        """Check if a shop's database exists."""
        db_name = f"talvex_shop_{shop_id}"
        return db_name in settings.DATABASES
    
    @staticmethod
    def get_database_config(db_name: str) -> dict:
        """
        Generate database configuration for a shop database.
        
        Args:
            db_name: Database name
            
        Returns:
            dict: Database configuration matching main database except NAME
        """
        # Get main database configuration as template
        main_db_config = settings.DATABASES.get('main', settings.DATABASES['default'])
        
        # Create shop database configuration based on main template
        shop_db_config = main_db_config.copy()
        shop_db_config.update({
            'NAME': db_name,
            'ATOMIC_REQUESTS': False,
        })
        
        return shop_db_config
    
    @staticmethod
    def ensure_database_registered(shop_id: int) -> bool:
        """
        Ensure a shop's database is registered in Django settings.
        
        Args:
            shop_id: Shop's primary key
            
        Returns:
            bool: True if registered (or already registered), False on failure
        """
        db_name = f"talvex_shop_{shop_id}"
        
        # Check if already registered
        if db_name in settings.DATABASES:
            logger.debug(f"Database {db_name} already registered")
            return True
        
        try:
            # Get configuration
            config = ShopDatabaseManager.get_database_config(db_name)
            
            # Register in Django settings
            settings.DATABASES[db_name] = config
            logger.info(f"Registered database: {db_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register database {db_name}: {e}")
            # Clean up if registration failed
            if db_name in settings.DATABASES:
                del settings.DATABASES[db_name]
            return False
