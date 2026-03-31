"""
Database router for multi-tenant architecture.
Routes queries to appropriate database based on model and shop context.
"""

from django.conf import settings

class MultiTenantRouter:
    """
    Simplified router for deployment. Routes all queries to the main database.
    Multi-tenancy is handled via the 'user' foreign key on all models.
    """
    
    def db_for_read(self, model, **hints):
        return 'main'
    
    def db_for_write(self, model, **hints):
        return 'main'
    
    def allow_relation(self, obj1, obj2, **hints):
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Allow all migrations on the main database
        return db == 'main'
