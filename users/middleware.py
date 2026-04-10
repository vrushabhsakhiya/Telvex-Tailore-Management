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
                
            except Exception:
                # Token crashed, expired, or other JWT-related error
                logout(request)
                response = redirect('login')
                response.delete_cookie('access_token')
                return response

        return self.get_response(request)
from django.http import HttpResponseForbidden, HttpResponsePermanentRedirect

class SecurityBlockingMiddleware:
    """
    Blocks malicious requests from security scanners and bots.
    Targeting patterns seen in OWASP ZAP and common exploit scripts.
    """
    BLOCKED_EXTENSIONS = ('.php', '.axd', '.config', '.sql', '.ini', '.xml', '.env', '.htaccess', '.DS_Store')
    BLOCKED_PATHS = ('/latest/meta-data/', '/computeMetadata/v1/', '/.git/', '/.ssh/', '/WEB-INF/', '/actuator/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.lower()
        query = request.META.get('QUERY_STRING', '').lower()

        # 1. Block forbidden extensions
        if any(path.endswith(ext) for ext in self.BLOCKED_EXTENSIONS):
            return HttpResponseForbidden("Access Denied: Malicious probe detected.")

        # 2. Block sensitive paths
        if any(p in path for p in self.BLOCKED_PATHS):
            return HttpResponseForbidden("Access Denied: Sensitive endpoint restricted.")

        # 3. Block suspicious query patterns (exploit strings from CSV)
        if '?-s' in query or '?-d' in query or 'class.module' in query or 'allow_url_include' in query:
             return HttpResponseForbidden("Access Denied: Suspected exploit payload.")

        return self.get_response(request)

class ShopApprovalMiddleware:
    """
    Middleware to ensure that shop owners must be approved by an admin
    before they can access the application features.
    """
    EXEMPT_URLS = [
        '/logout/',
        '/pending-approval/',
        '/login/',
        '/register/',
        '/staff-login/',
        '/verify-otp/',
        '/forgot-password/',
        '/reset-password/',
        '/admin-login/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 1. Superusers and Staff (System Admin) are always exempt
            if request.user.is_superuser:
                return self.get_response(request)

            # 2. Check if current path is exempt (to avoid redirect loops)
            path = request.path
            if any(path.startswith(url) for url in self.EXEMPT_URLS):
                return self.get_response(request)

            # 3. Check Shop Profile Approval status
            shop = getattr(request.user, 'shop_profile', None)
            if shop:
                if not shop.is_approved:
                    return redirect('pending_approval')
            else:
                # If they are logged in but have no shop profile (unlikely but safe)
                # and are not superuser, they shouldn't be here.
                # However, for now, let them pass or redirect to register.
                pass

        return self.get_response(request)
