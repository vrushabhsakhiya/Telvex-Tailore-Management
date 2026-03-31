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
                
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                # Token crashed or expired
                logout(request)
                response = redirect('login')
                response.delete_cookie('access_token')
                return response

        return self.get_response(request)
    
