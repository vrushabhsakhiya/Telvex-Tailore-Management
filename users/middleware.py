import jwt
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import logout
from .models import User, ShopProfile
from config.thread_local import set_current_shop_db, clear_current_shop_db

class JWTSessionMiddleware:
    """
    Middleware to verify the Access Token cookie on every request.
    If the user is authenticated via session but the JWT token is missing 
    or invalid, it forces a logout for extra security.
    Also sets the shop database context for multi-tenancy.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            token = request.COOKIES.get('access_token')
            
            if not token:
                # Session exists but no JWT cookie - security violation or expired
                logout(request)
                return redirect('login')

            try:
                # Validate the token
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                
                # Attach staff details if logged in as staff
                request.staff_name = payload.get('staff_name')
                request.staff_role = payload.get('staff_role')
                
                # Set shop database context
                self._set_shop_database_context(request)
                
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                # Token crashed or expired
                logout(request)
                response = redirect('login')
                response.delete_cookie('access_token')
                return response

        return self.get_response(request)
    
    def _set_shop_database_context(self, request):
        """Set the shop database context for the current request."""
        try:
            # Get the user's shop profile
            shop_profile = getattr(request.user, 'shop_profile', None)
            
            if shop_profile and shop_profile.database_name:
                db_name = shop_profile.database_name
                
                if db_name not in settings.DATABASES:
                    main_db_config = settings.DATABASES['main']
                    shop_db_config = main_db_config.copy()
                    shop_db_config.update({
                        'NAME': db_name,
                        'ATOMIC_REQUESTS': False,
                    })
                    settings.DATABASES[db_name] = shop_db_config
                
                # Set the shop database in thread-local storage
                set_current_shop_db(db_name)
            else:
                # Clear any existing shop database context
                clear_current_shop_db()
                
        except Exception as e:
            # If anything goes wrong, clear the context
            clear_current_shop_db()
            print(f"Warning: Failed to set shop database context: {e}")
