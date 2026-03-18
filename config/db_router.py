"""
Database router for multi-tenant architecture.
Routes queries to appropriate database based on model and shop context.
"""

from django.conf import settings

class MultiTenantRouter:
    """
    Routes database queries based on app and shop context.
    """
    
    # Models that should always go to the main database
    MAIN_DB_MODELS = {
        'users.User': 'main',
        'users.ShopProfile': 'main',
        'auth.User': 'main',
        'auth.Group': 'main',
        'auth.Permission': 'main',
        'contenttypes.ContentType': 'main',
        'sessions.Session': 'main',
        'admin.LogEntry': 'main',
    }
    
    # Apps that should always go to the main database
    MAIN_DB_APPS = {
        'auth',
        'contenttypes',
        'sessions',
        'admin',
        'django_recaptcha',
    }
    
    # Apps that should go to shop-specific databases
    SHOP_DB_APPS = {
        'customers',
        'store',
    }
    
    def db_for_read(self, model, **hints):
        """Suggest the database to read from."""
        return self._get_database_for_model(model, hints)
    
    def db_for_write(self, model, **hints):
        """Suggest the database to write to."""
        return self._get_database_for_model(model, hints)
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same database."""
        db_set = {'main'}
        if hasattr(settings, 'DATABASES'):
            db_set.update(settings.DATABASES.keys())
        
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Determine if migration should run on this database."""
        # Main database migrations
        if db == 'main':
            return app_label in self.MAIN_DB_APPS or app_label == 'users'
        
        # Shop database migrations
        if db.startswith('talvex_shop_'):
            return app_label in self.SHOP_DB_APPS
        
        return False
    
    def _get_database_for_model(self, model, hints):
        """Determine which database a model should use."""
        model_key = f"{model._meta.app_label}.{model._meta.model_name}"
        
        # Check explicit model routing
        if model_key in self.MAIN_DB_MODELS:
            return self.MAIN_DB_MODELS[model_key]
        
        # Check app-level routing
        if model._meta.app_label in self.MAIN_DB_APPS:
            return 'main'
        
        if model._meta.app_label in self.SHOP_DB_APPS:
            # Get shop database from hints or current context
            shop_db = hints.get('shop_db')
            if shop_db:
                return shop_db
            
            # Try to get from thread-local storage (set by middleware)
            try:
                from .thread_local import get_current_shop_db
                current_db = get_current_shop_db()
                if current_db:
                    return current_db
            except ImportError:
                pass
        
        return 'main'  # Default fallback
