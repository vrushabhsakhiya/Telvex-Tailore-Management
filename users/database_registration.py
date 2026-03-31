"""
Database registration module for multi-tenant architecture.
Handles discovery and registration of shop databases at application startup.
"""

import logging
from typing import Dict, Tuple
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


def table_exists(table_name: str, database: str = 'default') -> bool:
    """
    Check if a table exists in the given database.
    
    Args:
        table_name: Name of the table to check
        database: Database alias to check in
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        from django.db import connections
        with connections[database].cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name=%s)",
                [table_name],
            )
            return cursor.fetchone()[0]
    except Exception:
        return False


def register_all_shop_databases() -> Dict[str, any]:
    """
    Discover and register all shop databases at startup.
    
    Queries the ShopProfile table to find all shops with database_name set,
    then registers each database in Django's DATABASES setting.
    
    Returns:
        dict: {
            'success': int,  # Count of successfully registered databases
            'failed': int,   # Count of failed registrations
            'errors': list   # List of error messages
        }
    """
    result = {
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    # Check if the table exists before querying
    # This prevents errors during first deployment before migrations run
    if not table_exists('users_shopprofile', 'default'):
        logger.debug("ShopProfile table does not exist yet, skipping registration")
        return result

    try:
        # Import here to avoid circular imports
        from .models import ShopProfile
        
        # Query all shops with database_name set
        shops = ShopProfile.objects.filter(
            database_name__isnull=False
        ).exclude(database_name='')
        
        logger.info(f"Discovered {shops.count()} shop databases to register")
        
        # Register each shop database
        for shop in shops:
            db_name = shop.database_name
            
            # Skip if already registered
            if db_name in settings.DATABASES:
                logger.debug(f"Database {db_name} already registered, skipping")
                result['success'] += 1
                continue
            
            # Get database configuration
            config = _get_database_config(db_name)
            
            # Validate configuration
            is_valid, error_msg = validate_database_config(config)
            if not is_valid:
                logger.warning(
                    f"Invalid configuration for shop {shop.id} "
                    f"(database: {db_name}): {error_msg}"
                )
                result['failed'] += 1
                result['errors'].append(f"Shop {shop.id}: {error_msg}")
                continue
            
            # Register the database
            if register_shop_database(db_name, config):
                result['success'] += 1
                logger.info(f"Successfully registered database: {db_name}")
            else:
                result['failed'] += 1
                error_msg = f"Failed to register database: {db_name}"
                result['errors'].append(f"Shop {shop.id}: {error_msg}")
                logger.warning(f"Shop {shop.id}: {error_msg}")
                
    except Exception as e:
        logger.error(f"Error during shop database registration: {e}")
        result['errors'].append(f"Registration process error: {str(e)}")
    
    return result


def register_shop_database(db_name: str, config: Dict) -> bool:
    """
    Register a single shop database in Django settings.
    
    Args:
        db_name: Database name (e.g., 'talvex_shop_1')
        config: Database configuration dict
        
    Returns:
        bool: True if registration successful, False otherwise
    """
    try:
        # Add to Django's DATABASES setting
        settings.DATABASES[db_name] = config
        
        # Test the connection
        if not test_database_connection(db_name):
            # Remove from settings if connection fails
            del settings.DATABASES[db_name]
            logger.warning(f"Connection test failed for {db_name}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error registering database {db_name}: {e}")
        # Clean up if registration failed
        if db_name in settings.DATABASES:
            del settings.DATABASES[db_name]
        return False


def validate_database_config(config: Dict) -> Tuple[bool, str]:
    """
    Validate database configuration parameters.
    
    Args:
        config: Database configuration dict
        
    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = ['ENGINE', 'NAME', 'USER', 'HOST', 'PORT']
    
    # Check for required fields
    for field in required_fields:
        if field not in config:
            return False, f"Missing required field: {field}"
        if not config[field]:
            return False, f"Empty value for required field: {field}"
    
    # Validate ENGINE
    if 'postgresql' not in config['ENGINE']:
        return False, f"Unsupported database engine: {config['ENGINE']}"
    
    # Validate PORT is numeric
    try:
        int(config['PORT'])
    except (ValueError, TypeError):
        return False, f"Invalid PORT value: {config['PORT']}"
    
    return True, ""


def test_database_connection(db_name: str) -> bool:
    """
    Test if a database connection can be established.
    
    Args:
        db_name: Database name to test
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        # Get connection from Django's connection handler
        connection = connections[db_name]
        
        # Force connection attempt with timeout
        connection.ensure_connection()
        
        # Test with a simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return True
        
    except OperationalError as e:
        logger.debug(f"Connection test failed for {db_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error testing connection for {db_name}: {e}")
        return False
    finally:
        # Close the connection to avoid keeping it open
        if db_name in connections:
            try:
                connections[db_name].close()
            except:
                pass


def _get_database_config(db_name: str) -> Dict:
    """
    Generate database configuration for a shop database.
    
    Args:
        db_name: Database name
        
    Returns:
        dict: Database configuration
    """
    # Get main database configuration as template
    main_db_config = settings.DATABASES.get('main', settings.DATABASES['default'])
    
    # Create shop database configuration by copying
    shop_db_config = main_db_config.copy()
    shop_db_config.update({
        'NAME': db_name,
        'ATOMIC_REQUESTS': False,
    })
    
    return shop_db_config
