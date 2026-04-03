from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse, Http404, JsonResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.translation import gettext as _
import jwt
import time
import json
import urllib.parse
from datetime import datetime, timedelta
import random
import string
from django.utils import timezone
import os
from .models import User, ShopProfile

from django.core.cache import cache

LOGIN_TEMPLATE = 'login.html'

def register_view(request):
    if request.method == 'POST':
        # 0. IP Rate Limiting
        ip = request.META.get('REMOTE_ADDR')
        cache_key = f'ratelimit_reg_{ip}'
        attempts = cache.get(cache_key, 0)
        if attempts >= 3: # 3 register attempts per hour
             messages.error(request, 'Too many registration attempts. Please try again in an hour.')
             return redirect('register')
        cache.set(cache_key, attempts + 1, 3600)

        # 1. Honeypot check (Bot Protection)
        if request.POST.get('website'):
            # Silently redirect bots to success to waste their time 
            # or just return success without creating account.
            messages.success(request, 'Shop account created successfully! Please login.')
            return redirect('login')

        # 2. Velocity Check (No Human registers in < 5 seconds)
        reg_start = request.session.get('register_load_time', 0)
        time_diff = time.time() - reg_start
        if reg_start > 0 and time_diff < 5:
             # Too fast, probably a bot
             messages.error(request, 'Registration failed. Please try again.')
             return redirect('register')

        # 3. reCAPTCHA Validation
        recaptcha_response = request.POST.get('g-recaptcha-response')
        if not recaptcha_response:
             messages.error(request, 'Please complete the reCAPTCHA.')
             return redirect('register')
             
        import requests
        data = {
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': recaptcha_response
        }
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
        result = r.json()
        if not result.get('success'):
             messages.error(request, 'reCAPTCHA verification failed. Please try again.')
             return redirect('register')

        owner_name = request.POST.get('owner_name')
        shop_name = request.POST.get('shop_name')
        mobile = request.POST.get('mobile')
        email = request.POST.get('email')
        address = request.POST.get('address', '')
        gst_no = request.POST.get('gst_no', '')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, 'Passwords do not match')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return redirect('register')

        try:
            # Create User (username = email for simplicity)
            user = User.objects.create_user(username=email, email=email, password=password)
            user.first_name = owner_name
            user.is_admin = True # The person signing up is the shop owner/admin
            user.save()

            # Create Shop Profile with provided data (is_approved=False by default)
            ShopProfile.objects.create(
                user=user, 
                shop_name=shop_name,
                mobile=mobile,
                address=address,
                gst_no=gst_no
            )

            messages.success(request, 'Shop account created successfully! Please wait for admin approval before logging in.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Error: {e}')
            return redirect('register')

    try:
        request.session['register_load_time'] = time.time()
    except Exception:
        # Fails gracefully if session DB table isn't fully migrated yet
        pass
        
    return render(request, 'register.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('username') # Form uses 'username' name for email input
        password = request.POST.get('password')
        
        # 0. IP Rate Limiting (Brute Force Protection)
        ip = request.META.get('REMOTE_ADDR')
        cache_key = f'ratelimit_login_{ip}'
        attempts = cache.get(cache_key, 0)
        if attempts >= 10: # Max 10 attempts per IP per 5 mins
             messages.error(request, 'Too many failed login attempts from this network. Please wait.')
             return render(request, LOGIN_TEMPLATE)
        cache.set(cache_key, attempts + 1, 300)

        # 1. reCAPTCHA Validation
        recaptcha_response = request.POST.get('g-recaptcha-response')
        if not recaptcha_response:
             messages.error(request, 'Please complete the reCAPTCHA.')
             return render(request, LOGIN_TEMPLATE)
             
        import requests
        r = requests.post('https://www.google.com/recaptcha/api/siteverify', data={
            'secret': settings.RECAPTCHA_PRIVATE_KEY,
            'response': recaptcha_response
        })
        if not r.json().get('success'):
             messages.error(request, 'reCAPTCHA verification failed. Please try again.')
             return render(request, LOGIN_TEMPLATE)

        # 2. Basic Rate Limiting / Lock Check
        user_candidate = User.objects.filter(username=email).first() or User.objects.filter(email=email).first()
        if user_candidate and user_candidate.locked_until and user_candidate.locked_until > timezone.now():
            messages.error(request, 'Account locked due to multiple failed attempts. Please try again later.')
            return render(request, LOGIN_TEMPLATE)

        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # Success! Reset failure count
            user.failed_attempts = 0
            user.locked_until = None
            
            # Start 2FA Flow
            otp = ''.join(random.choices(string.digits, k=6))
            user.otp_code = otp
            user.otp_expiry = timezone.now() + timedelta(minutes=10)
            user.save()

            # Generate JWT for temporary 2FA session
            payload = {
                'user_id': user.id,
                'exp': int(time.time()) + 600, # 10 minutes
                'type': '2fa_pending'
            }
            temp_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            # Send OTP via Email (Real Email Sending)
            email_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                <h2 style="color: #6366f1; text-align: center;">Teivex Security</h2>
                <p>Hello,</p>
                <p>You requested a login OTP for your Teivex account. Please use the code below to complete your login:</p>
                <div style="background: #f1f5f9; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #1e293b; border-radius: 8px; margin: 20px 0;">
                    {otp}
                </div>
                <p style="color: #64748b; font-size: 14px;">This code will expire in 10 minutes. If you did not request this, please ignore this email or contact support.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="text-align: center; color: #94a3b8; font-size: 12px;">&copy; {timezone.now().year} Telvex. All rights reserved.</p>
            </div>
            """
            
            try:
                send_mail(
                    subject='Login OTP - Telvex',
                    message=f'Your login OTP is: {otp}. It expires in 10 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=email_html,
                    fail_silently=False,
                )
                messages.info(request, f'OTP sent to your email: {user.email}')
            except Exception as e:
                # Fallback for dev if email not configured
                if settings.DEBUG:
                    messages.warning(request, f'Email delivery failed. Dev OTP: {otp}. Error: {str(e)}')
                else:
                    messages.error(request, 'Failed to send OTP. Please contact support.')
                    return redirect('login')

            # Store in session and redirect
            request.session['pending_otp_token'] = temp_token
            return redirect('verify_otp')
        else:
            # Failed attempt: Increment counter
            if user_candidate:
                user_candidate.failed_attempts += 1
                if user_candidate.failed_attempts >= 5:
                    user_candidate.locked_until = timezone.now() + timedelta(minutes=5)
                    messages.error(request, 'Too many failed attempts. Account locked for 5 minutes.')
                else:
                    messages.error(request, f'Invalid credentials. {5 - user_candidate.failed_attempts} attempts remaining.')
                user_candidate.save()
            else:
                messages.error(request, 'Invalid email or password')
    
    return render(request, 'login.html')

def verify_otp_view(request):
    token = request.session.get('pending_otp_token')
    if not token:
        return redirect('login')
    
    # IP Rate Limiting for OTP Verification
    ip = request.META.get('REMOTE_ADDR')
    cache_key = f'ratelimit_otp_{ip}'
    attempts = cache.get(cache_key, 0)
    if attempts >= 10: # Max 10 attempts per 5 mins
         messages.error(request, 'Too many OTP attempts. Please wait.')
         return redirect('login')
    cache.set(cache_key, attempts + 1, 300)

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user = User.objects.get(id=payload['user_id'])
    except Exception:
        return redirect('login')

    if request.method == 'POST':
        otp = request.POST.get('otp')
        if otp == user.otp_code and user.otp_expiry > timezone.now():
            # Final Login
            if not user.is_superuser and hasattr(user, 'shop_profile') and not user.shop_profile.is_approved:
                messages.warning(request, 'Your shop account is awaiting admin approval.')
                return redirect('login')

            login(request, user)
            user.otp_code = None
            user.is_verified = True
            user.save()
            
            # Generate Long-lived JWT for extra security layer / API access
            final_payload = {
                'user_id': user.id,
                'username': user.username,
                'iat': int(time.time()),
                'exp': int(time.time()) + 86400 * 7 # 7 days
            }
            final_token = jwt.encode(final_payload, settings.SECRET_KEY, algorithm='HS256')
            
            request.session.pop('pending_otp_token', None)
            response = redirect('home')
            response.set_cookie('access_token', final_token, httponly=True, secure=True)
            return response
        else:
            messages.error(request, 'Invalid or expired OTP')

    return render(request, 'otp_verify.html', {'email': user.email})

def staff_login_view(request):
    """
    Separate login for staff members using Shop Email + Staff Name + PIN.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        shop_email = request.POST.get('shop_email', '').strip()
        staff_name = request.POST.get('staff_name', '').strip()
        pin = request.POST.get('pin', '').strip()

        user = User.objects.filter(email=shop_email).first()
        if user and hasattr(user, 'shop_profile'):
            shop = user.shop_profile
            # Validate Staff and PIN
            if staff_name in shop.bill_creators and shop.staff_pins.get(staff_name) == pin:
                # Login as the Shop Owner
                login(request, user)
                
                # Generate Long-lived JWT with Staff Claims
                payload = {
                    'user_id': user.id,
                    'username': user.username,
                    'staff_name': staff_name,                 # Custom Claim
                    'staff_role': shop.staff_roles.get(staff_name, 'Staff'), # Custom Claim
                    'iat': int(time.time()),
                    'exp': int(time.time()) + 86400 * 7 # 7 days
                }
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
                
                messages.success(request, f"Welcome back, {staff_name}!")
                response = redirect('home')
                response.set_cookie('access_token', token, httponly=True, secure=True)
                return response
            
        messages.error(request, 'Invalid Shop Email, Staff Name, or PIN.')
        
    return render(request, 'staff_login.html')

def logout_view(request):
    logout(request)
    response = redirect('login')
    response.delete_cookie('access_token')
    messages.info(request, 'Logged out successfully.')
    return response

@login_required
def admin_delete_user(request, user_id):
    """
    Admin only: Remove a shop owner and all their data.
    """
    if not request.user.is_superuser:
        messages.error(request, 'Unauthorized access.')
        return redirect('dashboard')
    
    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_superuser:
        messages.error(request, 'Cannot delete superuser.')
        return redirect('dashboard')
        
    target_user.delete() # CASCADE will remove ShopProfile, Orders, Customers etc.
    messages.success(request, f'User {target_user.email} and all associated data removed.')
    return redirect('dashboard')

@login_required
def settings_view(request):
    if hasattr(request, 'staff_name') and request.staff_name:
        messages.error(request, 'Staff members cannot access settings.')
        return redirect('dashboard')
        
    shop = ShopProfile.objects.filter(user=request.user).first()
    return render(request, 'settings.html', {'shop': shop, 'active_page': 'settings'})

def _handle_logo_upload(request, shop):
    """Helper to save shop logo."""
    if not request.FILES.get('logo'):
        return
    
    logo_file = request.FILES['logo']
    from django.core.files.storage import FileSystemStorage
    upload_path = f"uploads/users/{request.user.id}/shop/"
    target_dir = os.path.join(settings.MEDIA_ROOT, upload_path)
    os.makedirs(target_dir, exist_ok=True)
    
    fs = FileSystemStorage(location=target_dir, base_url=f"{settings.MEDIA_URL}{upload_path}")
    filename = fs.save(logo_file.name, logo_file)
    shop.logo = fs.url(filename)

def send_whatsapp_notification(mobile, message):
    """
    Utility to open WhatsApp with a pre-filled message.
    Used for order ready / bill sent notifications.
    """
    encoded_msg = urllib.parse.quote(message)
    # Remove non-digits and add 91 if needed
    clean_mobile = ''.join(filter(str.isdigit, str(mobile)))
    if len(clean_mobile) == 10:
        clean_mobile = "91" + clean_mobile
    
    return f"https://wa.me/{clean_mobile}?text={encoded_msg}"

@login_required
def delete_staff(request, staff_name):
    if hasattr(request, 'staff_name') and request.staff_name:
        return redirect('dashboard')
        
    """
    Removes a staff member from the shop's bill_creators list and roles.
    """
    if request.method == 'POST':
        shop = get_object_or_404(ShopProfile, user=request.user)
        if staff_name in shop.bill_creators:
            creators = list(shop.bill_creators)
            creators.remove(staff_name)
            shop.bill_creators = creators
            
            roles = dict(shop.staff_roles)
            if staff_name in roles:
                del roles[staff_name]
            shop.staff_roles = roles
            
            pins = dict(shop.staff_pins)
            if staff_name in pins:
                del pins[staff_name]
            shop.staff_pins = pins
            
            shop.save()
            messages.success(request, f"Staff '{staff_name}' removed.")
        return redirect('settings')
    return redirect('settings')

@login_required
def update_shop_profile(request):
    if hasattr(request, 'staff_name') and request.staff_name:
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('settings')
        
    try:
        shop = ShopProfile.objects.filter(user=request.user).first()
        if not shop:
            shop = ShopProfile.objects.create(user=request.user, shop_name=request.user.first_name)
        
        # Core details
        shop.shop_name = request.POST.get('shop_name', shop.shop_name)
        shop.mobile = request.POST.get('mobile', shop.mobile)
        shop.whatsapp = request.POST.get('whatsapp', shop.whatsapp)
        shop.email = request.POST.get('email', shop.email)
        shop.upi_id = request.POST.get('upi_id', shop.upi_id)
        shop.gst_no = request.POST.get('gst_no', shop.gst_no)
        shop.address = request.POST.get('address', shop.address)
        shop.pincode = request.POST.get('pincode', shop.pincode)
        shop.state = request.POST.get('state', shop.state)
        shop.terms = request.POST.get('terms', shop.terms)
        
        # Staff logic
        new_staff_name = request.POST.get('new_staff_name', '').strip()
        new_staff_role = request.POST.get('new_staff_role', 'Staff').strip()
        new_staff_pin = request.POST.get('new_staff_pin', '').strip()
        
        if new_staff_name:
            creators = list(shop.bill_creators)
            if new_staff_name not in creators:
                creators.append(new_staff_name)
                shop.bill_creators = creators
                
                roles = dict(shop.staff_roles)
                roles[new_staff_name] = new_staff_role
                shop.staff_roles = roles
                
                if new_staff_pin:
                    pins = dict(shop.staff_pins)
                    pins[new_staff_name] = new_staff_pin
                    shop.staff_pins = pins
        
        # Logo logic
        _handle_logo_upload(request, shop)
        if request.POST.get('delete_logo'):
            shop.logo = ''
            
        shop.save()
        messages.success(request, 'Shop profile updated successfully!')
        
    except Exception as e:
        messages.error(request, f"Error updating profile: {str(e)}")
        
    return redirect('settings')

@login_required
def protected_media(request, path):
    """
    Serves media files only if they belong to the authenticated user.
    Path expected: 'uploads/users/<user_id>/...'
    """
    # 1. Basic Traversal Protection
    document_root = os.path.abspath(settings.MEDIA_ROOT)
    clean_path = os.path.normpath(path).lstrip(os.sep)
    full_path = os.path.abspath(os.path.join(document_root, clean_path))
    
    if os.path.commonpath([document_root, full_path]) != document_root:
         raise Http404("Access Denied")

    # 2. Ownership Verification
    # Expected path structure: uploads/users/<user_id>/...
    # We allow 'public' assets if needed, but for now strict lockdown on 'uploads/users/'
    
    path_parts = clean_path.replace('\\', '/').split('/')
    
    if len(path_parts) >= 3 and path_parts[0] == 'uploads' and path_parts[1] == 'users':
        try:
            param_user_id = int(path_parts[2])
            if param_user_id != request.user.id:
                # Security Violation: User trying to access another user's files
                return HttpResponse("Forbidden: You do not have permission to access this file.", status=403)
        except ValueError:
            # path didn't have a valid int for user_id
            raise Http404("Invalid Path")

    if os.path.exists(full_path):
        return FileResponse(open(full_path, 'rb'))
    raise Http404

from django.http import HttpResponse
import csv
from customers.models import Customer
from store.models import Order, Category, Reminder, Measurement

def _get_export_data(data_type, user, date_range):
    """Filters data for export based on type."""
    if data_type == 'orders':
        return Order.objects.filter(user=user, created_at__date__range=date_range)
    elif data_type == 'customers':
        return Customer.objects.filter(user=user, created_date__date__range=date_range)
    elif data_type == 'measurements':
        return Measurement.objects.filter(user=user, date__date__range=date_range)
    elif data_type == 'bills': # Added for 'bills' data type
        return Order.objects.filter(user=user, created_at__date__range=date_range)
    return Order.objects.none()

def _write_csv_data(writer, data_type, queryset):
    """Helper method to handle the field mappings for different CSV exports."""
    if data_type == 'orders':
        writer.writerow(['Order ID', 'Customer', 'Mobile', 'Total Amount', 'Advance', 'Balance', 'Work Status', 'Payment Status', 'Delivery Date'])
        for o in queryset: 
            writer.writerow([
                o.id, o.customer.name, o.customer.mobile, o.total_amt, 
                o.advance, o.balance, o.work_status, o.payment_status, o.delivery_date
            ])
    elif data_type == 'customers':
        writer.writerow(['Name', 'Mobile', 'Gender', 'City', 'Area', 'Total Orders', 'Pending Balance'])
        for c in queryset: 
            writer.writerow([
                c.name, c.mobile, c.gender, c.city, c.area, c.orders.count(), c.total_pending
            ])
    elif data_type == 'measurements':
        writer.writerow(['Customer', 'Mobile', 'Category', 'Date', 'Measurements', 'Remarks'])
        for m in queryset: 
            writer.writerow([
                m.customer.name, m.customer.mobile, m.category.name,
                m.date.date(), str(m.measurements_json), m.remarks
            ])
    elif data_type == 'bills':
        writer.writerow(['Bill/Order ID', 'Customer', 'Total', 'Paid', 'Balance', 'Date'])
        for o in queryset:
            writer.writerow([
                o.id, o.customer.name, o.total_amt, o.advance, o.balance, o.created_at.date()
            ])

@login_required
def export_custom_data(request):
    if hasattr(request, 'staff_name') and request.staff_name:
        return redirect('dashboard')

    if request.method != 'POST':
        return redirect('settings')
        
    try:
        params = request.POST
        date_range = [params.get('start_date'), params.get('end_date')]
        data_type = params.get('data_type')
        
        export_dir = os.path.join(settings.MEDIA_ROOT, 'exports', timezone.now().strftime('%Y/%m'))
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"{data_type}_{params.get('start_date')}_to_{params.get('end_date')}.csv"
        file_path = os.path.join(export_dir, filename)
        
        queryset = _get_export_data(data_type, request.user, date_range)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            _write_csv_data(writer, data_type, queryset)
        
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)
        return response
    except Exception as e:
        messages.error(request, f"Export failed: {str(e)}")
        return redirect('settings')

@login_required
def download_backup(request):
    if hasattr(request, 'staff_name') and request.staff_name:
        return redirect('dashboard')
    
    from django.core import serializers
    from django.http import HttpResponse
    from store.models import Category, Order, Measurement, Reminder
    from customers.models import Customer
    
    # Securely collect ONLY the current user's data
    user_data = []
    user_data.extend(ShopProfile.objects.filter(user=request.user))
    user_data.extend(Category.objects.filter(user=request.user))
    user_data.extend(Customer.objects.filter(user=request.user))
    user_data.extend(Measurement.objects.filter(user=request.user))
    user_data.extend(Order.objects.filter(user=request.user))
    user_data.extend(Reminder.objects.filter(user=request.user))
    
    # Serialize to a secure JSON dump
    json_data = serializers.serialize('json', user_data)
    
    filename = f"talvex_secure_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    response = HttpResponse(json_data, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def reset_data(request):
    if hasattr(request, 'staff_name') and request.staff_name:
        return redirect('dashboard')

    if request.method == 'POST':
        # Delete Everything for this user except Account and ShopProfile
        try:
            Order.objects.filter(user=request.user).delete()
            Measurement.objects.filter(user=request.user).delete()
            Reminder.objects.filter(user=request.user).delete()
            Category.objects.filter(user=request.user, is_custom=True).delete() # Only custom cats? Or all? User owns all cats usually.
            Customer.objects.filter(user=request.user).delete()
            
            messages.success(request, 'All system data (Orders, Customers, Measurements) has been reset successfully.')
        except Exception as e:
            messages.error(request, f'Error resetting data: {str(e)}')
            
    return redirect('settings')

from django.core.mail import send_mail

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        # Try finding by email field first, then username
        user = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
        
        if user:
            otp = ''.join(random.choices(string.digits, k=6))
            user.otp_code = otp
            user.otp_expiry = timezone.now() + timedelta(minutes=15)
            user.save()
            
            request.session['reset_email'] = user.email 
            
            # Send Reset Email (Real Email Sending)
            reset_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                <h2 style="color: #ef4444; text-align: center;">Telvex Password Reset</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password. Use the secret OTP below to proceed:</p>
                <div style="background: #fef2f2; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; color: #991b1b; border-radius: 8px; margin: 20px 0; border: 1px dashed #ef4444;">
                    {otp}
                </div>
                <p style="color: #64748b; font-size: 14px;">This code is valid for 15 minutes. <strong>Never share this OTP with anyone.</strong></p>
                <p style="color: #64748b; font-size: 14px;">If you didn't request a password reset, you can safely ignore this email.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="text-align: center; color: #94a3b8; font-size: 12px;">&copy; {timezone.now().year} Telvex. All rights reserved.</p>
            </div>
            """

            try:
                send_mail(
                    subject='Password Reset OTP - Telvex',
                    message=f'Your secret OTP to reset your password is: {otp}. Valid for 15 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL, 
                    recipient_list=[user.email],
                    html_message=reset_html,
                    fail_silently=False,
                )
                messages.success(request, f'Password reset OTP sent to {user.email}.')
            except Exception as e:
                if settings.DEBUG:
                    messages.warning(request, f"Failed to send reset email. Dev OTP: {otp}. Error: {str(e)}")
                else:
                    messages.error(request, "Failed to send reset email. Please try again.")

            return redirect('reset_password')
        else:
            messages.error(request, 'No account found with that email.')
            
    return render(request, 'forgot_password.html')

def reset_password_view(request):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')
        
        session_email = request.session.get('reset_email')
        
        if not session_email:
            messages.error(request, 'Session expired. Please try again.')
            return redirect('forgot_password')
            
        user = User.objects.filter(email=session_email).first() or User.objects.filter(username=session_email).first()
        
        if not user or user.otp_code != otp or (user.otp_expiry and user.otp_expiry < timezone.now()):
            messages.error(request, 'Invalid or expired OTP.')
            return redirect('reset_password')
            
        if password != confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'reset_password.html')
            
        # Success
        user.set_password(password)
        user.otp_code = None # Clear OTP
        user.otp_expiry = None
        user.failed_attempts = 0 # Reset lock if they were locked
        user.locked_until = None
        user.save()
        
        del request.session['reset_email']
        messages.success(request, 'Password reset successfully. Please login.')
        return redirect('login')
            
    return render(request, 'reset_password.html')

@login_required
def approve_shops_view(request):
    """
    Super Admin view to list and approve pending shop registrations.
    """
    if not request.user.is_superuser:
        messages.error(request, 'Unauthorized access.')
        return redirect('dashboard')
    
    pending_shops = ShopProfile.objects.filter(is_approved=False).select_related('user')
    
    if request.method == 'POST':
        shop_id = request.POST.get('shop_id')
        action = request.POST.get('action') # 'approve' or 'reject'
        
        shop = get_object_or_404(ShopProfile, id=shop_id)
        if action == 'approve':
            shop.is_approved = True
            shop.save()
            messages.success(request, f"Shop '{shop.shop_name}' approved!")
        elif action == 'reject':
            messages.info(request, f"Review for '{shop.shop_name}' completed.")

        return redirect('approve_shops')

    return render(request, 'approve_shops.html', {'pending_shops': pending_shops})
