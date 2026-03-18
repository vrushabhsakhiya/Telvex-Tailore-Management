import logging
import sys
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    
    def ready(self):
        """Called when Django starts. Register signals and shop databases."""
        # Import signals to register them
        import users.signals
        
        # Skip database registration during migrations or specific commands
        if self._is_migration_command():
            logger.debug("Skipping shop database registration during migration command")
            return
        
        # Register all shop databases
        try:
            from .database_registration import register_all_shop_databases
            result = register_all_shop_databases()
            
            # Log results
            logger.info(
                f"Shop database registration complete: "
                f"{result['success']} successful, {result['failed']} failed"
            )
            
            # Log errors if any
            if result['errors']:
                for error in result['errors']:
                    logger.warning(f"Registration error: {error}")
                    
        except Exception as e:
            logger.error(f"Critical error during shop database registration: {e}")
            # Don't raise - allow application to start even if registration fails
    
    def _is_migration_command(self) -> bool:
        """Check if current command is a migration command or other command that should skip registration."""
        # Check for migration commands
        migration_commands = ['migrate', 'makemigrations', 'showmigrations', 'sqlmigrate']
        
        for cmd in migration_commands:
            if cmd in sys.argv:
                return True
        
        # Also skip for certain management commands that don't need database access
        skip_commands = ['collectstatic', 'compilemessages', 'makemessages']
        for cmd in skip_commands:
            if cmd in sys.argv:
                return True
        
        return False

