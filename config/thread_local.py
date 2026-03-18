"""
Thread-local storage for managing current shop database context.
"""

import threading
from contextlib import contextmanager

# Thread-local storage
_thread_locals = threading.local()

def get_current_shop_db():
    """Get the current shop database from thread-local storage."""
    return getattr(_thread_locals, 'shop_db', None)

def set_current_shop_db(shop_db):
    """Set the current shop database in thread-local storage."""
    _thread_locals.shop_db = shop_db

def clear_current_shop_db():
    """Clear the current shop database from thread-local storage."""
    if hasattr(_thread_locals, 'shop_db'):
        delattr(_thread_locals, 'shop_db')

@contextmanager
def shop_db_context(shop_db):
    """Context manager for temporarily setting shop database."""
    old_db = get_current_shop_db()
    try:
        set_current_shop_db(shop_db)
        yield
    finally:
        if old_db:
            set_current_shop_db(old_db)
        else:
            clear_current_shop_db()
