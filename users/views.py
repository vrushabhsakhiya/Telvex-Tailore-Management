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
        try:
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data={
                'secret': settings.RECAPTCHA_PRIVATE_KEY,
                'response': recaptcha_response
            }, timeout=4) # Tightened timeout
            result = r.json()
            if not result.get('success'):
                 messages.error(request, 'reCAPTCHA verification failed. Please try again.')
                 return redirect('register')
        except requests.exceptions.Timeout:
            messages.error(request, 'reCAPTCHA service timed out. Please try again.')
            return redirect('register')
        except Exception as e:
            # Fallback for network issues or API down
            if settings.DEBUG:
                messages.warning(request, f'reCAPTCHA error: {e}. Skipping check for Dev.')
            else:
                messages.error(request, 'reCAPTCHA service unavailable. Please try later.')
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

            messages.success(request, 'Shop account created successfully! Please wait for admin approval.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Error: {e}')
            return redirect('register')

    try:
        request.session['register_load_time'] = time.time()
    except Exception:
        # Fails gracefully if session DB table isn't fully migrated yet
        pass
        
    return render(request, 'register.html', {'hide_marketing_sidebar': True})

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
        try:
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data={
                'secret': settings.RECAPTCHA_PRIVATE_KEY,
                'response': recaptcha_response
            }, timeout=4) # Tightened timeout
            if not r.json().get('success'):
                 messages.error(request, 'reCAPTCHA verification failed. Please try again.')
                 return render(request, LOGIN_TEMPLATE)
        except requests.exceptions.Timeout:
             messages.error(request, 'reCAPTCHA service timed out. Please try again.')
             return render(request, LOGIN_TEMPLATE)
        except Exception as e:
            # Fallback for network issues or API down
            if settings.DEBUG:
                messages.warning(request, f'reCAPTCHA error: {e}. Skipping check for Dev.')
            else:
                messages.error(request, 'reCAPTCHA service unavailable. Please try later.')
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
                # Use a try-except for email to prevent 500 errors on Render if SMTP is wrong/slow
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
                # Clear the OTP since it wasn't sent
                user.otp_code = None
                user.save()
                
                if settings.DEBUG:
                    messages.warning(request, f'Email delivery failed. Dev OTP: {otp}. Error: {str(e)}')
                else:
                    messages.error(request, 'SMTP Error: Failed to send OTP email. Please ensure your email settings are correct on Render.')
                    # Log the actual error for the developer if possible, but don't crash the request
                    print(f"CRITICAL: SMTP Failure: {e}")
                    return redirect('login')

            request.session['pending_otp_token'] = temp_token
            return redirect('verify_otp')
        else:
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
    
    return render(request, LOGIN_TEMPLATE)

def verify_otp_view(request):
    token = request.session.get('pending_otp_token')
    if not token:
        return redirect('login')
    
    ip = request.META.get('REMOTE_ADDR')
    cache_key = f'ratelimit_otp_{ip}'
    attempts = cache.get(cache_key, 0)
    if attempts >= 10: 
         messages.error(request, 'Too many OTP attempts. Please wait.')
         return redirect('login')
    cache.set(cache_key, attempts + 1, 300)

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user = User.objects.get(id=payload['user_id'])
    except Exception:
        return redirect('login')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        if settings.DEBUG:
            print(f"DEBUG: Verifying OTP for {user.email}. Received: '{otp}', Expected: '{user.otp_code}', Expired: {user.otp_expiry <= timezone.now()}")
            
        if otp == user.otp_code and user.otp_expiry > timezone.now():
            login(request, user)
            user.otp_code = None
            user.is_verified = True
            user.save()
            
            final_payload = {
                'user_id': user.id,
                'username': user.username,
                'iat': int(time.time()),
                'exp': int(time.time()) + 86400 * 7 # 7 days
            }
            final_token = jwt.encode(final_payload, settings.SECRET_KEY, algorithm='HS256')
            
            request.session.pop('pending_otp_token', None)
            response = redirect('dashboard')
            response.set_cookie('access_token', final_token, httponly=True, secure=settings.SESSION_COOKIE_SECURE)
            return response
        else:
            messages.error(request, 'Invalid or expired OTP')

    return render(request, 'otp_verify.html', {'email': user.email})

def staff_login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        shop_email = request.POST.get('shop_email', '').strip()
        staff_name = request.POST.get('staff_name', '').strip()
        pin = request.POST.get('pin', '').strip()

        user = User.objects.filter(email=shop_email).first()
        if user and hasattr(user, 'shop_profile'):
            shop = user.shop_profile
            if staff_name in shop.bill_creators and shop.staff_pins.get(staff_name) == pin:
                login(request, user)
                payload = {
                    'user_id': user.id,
                    'username': user.username,
                    'staff_name': staff_name,
                    'staff_role': shop.staff_roles.get(staff_name, 'Staff'),
                    'iat': int(time.time()),
                    'exp': int(time.time()) + 86400 * 7 
                }
                token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
                messages.success(request, f"Welcome back, {staff_name}!")
                response = redirect('dashboard')
                response.set_cookie('access_token', token, httponly=True, secure=settings.SESSION_COOKIE_SECURE)
                return response
            
        messages.error(request, 'Invalid Shop Email, Staff Name, or PIN.')
        
    return render(request, 'staff_login.html', {'hide_marketing_sidebar': True})

def logout_view(request):
    logout(request)
    response = redirect('login')
    response.delete_cookie('access_token')
    messages.info(request, 'Logged out successfully.')
    return response

@login_required
def admin_delete_user(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, 'Unauthorized access.')
        return redirect('dashboard')
    
    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_superuser:
        messages.error(request, 'Cannot delete superuser.')
        return redirect('dashboard')
        
    target_user.delete()
    messages.success(request, f'User {target_user.email} removed.')
    return redirect('dashboard')

@login_required
def settings_view(request):
    if hasattr(request, 'staff_name') and request.staff_name:
        messages.error(request, 'Staff members cannot access settings.')
        return redirect('dashboard')
        
    shop = ShopProfile.objects.filter(user=request.user).first()
    return render(request, 'settings.html', {'shop': shop, 'active_page': 'settings'})

def _handle_logo_upload(request, shop):
    if not request.FILES.get('logo'):
        return
    logo_file = request.FILES['logo']
    upload_path = f"uploads/users/{request.user.id}/shop/logo/"
    target_dir = os.path.join(settings.MEDIA_ROOT, upload_path)
    os.makedirs(target_dir, exist_ok=True)
    fs = FileSystemStorage(location=target_dir, base_url=f"{settings.MEDIA_URL}{upload_path}")
    filename = fs.save(logo_file.name, logo_file)
    shop.logo = fs.url(filename)

def _handle_qr_upload(request, shop):
    if not request.FILES.get('upi_qr'):
        return
    shop.upi_qr = request.FILES['upi_qr']

@login_required
def delete_staff(request, staff_name):
    if hasattr(request, 'staff_name') and request.staff_name:
        return redirect('dashboard')
    if request.method == 'POST':
        shop = get_object_or_404(ShopProfile, user=request.user)
        if staff_name in shop.bill_creators:
            creators = list(shop.bill_creators)
            creators.remove(staff_name)
            shop.bill_creators = creators
            roles = dict(shop.staff_roles)
            if staff_name in roles: del roles[staff_name]
            shop.staff_roles = roles
            pins = dict(shop.staff_pins)
            if staff_name in pins: del pins[staff_name]
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
        _handle_logo_upload(request, shop)
        if request.POST.get('delete_logo'): shop.logo = ''
        _handle_qr_upload(request, shop)
        if request.POST.get('delete_qr'): shop.upi_qr = None
        shop.save()
        messages.success(request, 'Shop profile updated successfully!')
    except Exception as e:
        messages.error(request, f"Error: {e}")
    return redirect('settings')

@login_required
def protected_media(request, path):
    document_root = os.path.abspath(settings.MEDIA_ROOT)
    clean_path = os.path.normpath(path).lstrip(os.sep)
    full_path = os.path.abspath(os.path.join(document_root, clean_path))
    if os.path.commonpath([document_root, full_path]) != document_root: raise Http404()
    path_parts = clean_path.replace('\\', '/').split('/')
    if len(path_parts) >= 3 and path_parts[0] == 'uploads' and path_parts[1] == 'users':
        try:
            if int(path_parts[2]) != request.user.id: return HttpResponse("Forbidden", status=403)
        except ValueError: raise Http404()
    if os.path.exists(full_path): return FileResponse(open(full_path, 'rb'))
    raise Http404()

import csv
from customers.models import Customer
from store.models import Order, Category, Measurement

def _get_export_data(data_type, user, date_range):
    if data_type == 'orders': return Order.objects.filter(user=user, created_at__date__range=date_range)
    if data_type == 'customers': return Customer.objects.filter(user=user, created_date__date__range=date_range)
    if data_type == 'measurements': return Measurement.objects.filter(user=user, date__date__range=date_range)
    if data_type == 'bills': return Order.objects.filter(user=user, created_at__date__range=date_range)
    return Order.objects.none()

def _write_csv_data(writer, data_type, queryset):
    if data_type == 'orders':
        writer.writerow(['Order ID', 'Customer', 'Mobile', 'Total Amount', 'Advance', 'Balance', 'Work Status', 'Payment Status', 'Delivery Date'])
        for o in queryset: writer.writerow([o.id, o.customer.name, o.customer.mobile, o.total_amt, o.advance, o.balance, o.work_status, o.payment_status, o.delivery_date])
    elif data_type == 'customers':
        writer.writerow(['Name', 'Mobile', 'Gender', 'City', 'Area', 'Total Orders', 'Pending Balance'])
        for c in queryset: writer.writerow([c.name, c.mobile, c.gender, c.city, c.area, c.orders.count(), c.total_pending])
    elif data_type == 'measurements':
        writer.writerow(['Customer', 'Mobile', 'Category', 'Date', 'Measurements', 'Remarks'])
        for m in queryset: writer.writerow([m.customer.name, m.customer.mobile, m.category.name, m.date.date(), str(m.measurements_json), m.remarks])
    elif data_type == 'bills':
        writer.writerow(['Bill ID', 'Customer', 'Total', 'Paid', 'Balance', 'Date'])
        for o in queryset: writer.writerow([o.id, o.customer.name, o.total_amt, o.advance, o.balance, o.created_at.date()])

@login_required
def export_custom_data(request):
    if hasattr(request, 'staff_name') and request.staff_name: return redirect('dashboard')
    if request.method != 'POST': return redirect('settings')
    try:
        data_type = request.POST.get('data_type')
        date_range = [request.POST.get('start_date'), request.POST.get('end_date')]
        queryset = _get_export_data(data_type, request.user, date_range)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data_type}_export.csv"'
        writer = csv.writer(response)
        _write_csv_data(writer, data_type, queryset)
        return response
    except Exception as e:
        messages.error(request, f"Export failed: {e}")
        return redirect('settings')

@login_required
def download_backup(request):
    if hasattr(request, 'staff_name') and request.staff_name: return redirect('dashboard')
    from django.core import serializers
    from store.models import Category, Order, Measurement, Reminder
    user_data = list(ShopProfile.objects.filter(user=request.user))
    user_data += list(Category.objects.filter(user=request.user))
    user_data += list(Customer.objects.filter(user=request.user))
    user_data += list(Measurement.objects.filter(user=request.user))
    user_data += list(Order.objects.filter(user=request.user))
    user_data += list(Reminder.objects.filter(user=request.user))
    json_data = serializers.serialize('json', user_data)
    response = HttpResponse(json_data, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="backup.json"'
    return response

@login_required
def reset_data(request):
    if hasattr(request, 'staff_name') and request.staff_name: return redirect('dashboard')
    if request.method == 'POST':
        from store.models import Order, Measurement, Reminder, Category
        Order.objects.filter(user=request.user).delete()
        Measurement.objects.filter(user=request.user).delete()
        Reminder.objects.filter(user=request.user).delete()
        Category.objects.filter(user=request.user, is_custom=True).delete()
        Customer.objects.filter(user=request.user).delete()
        messages.success(request, 'Data reset.')
    return redirect('settings')

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email=email).first() or User.objects.filter(username=email).first()
        
        if user:
            otp = ''.join(random.choices(string.digits, k=6))
            user.otp_code = otp
            user.otp_expiry = timezone.now() + timedelta(minutes=15)
            user.save()
            
            request.session['reset_email'] = user.email
            
            try:
                send_mail(
                    'Password Reset OTP',
                    f'Your verification code is: {otp}. It will expire in 15 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, 'Verification code sent to your email.')
                return redirect('reset_password')
            except Exception as e:
                if settings.DEBUG:
                    messages.warning(request, f"Email failed. Code: {otp}. Error: {e}")
                else:
                    messages.error(request, 'Failed to send verification email. Please check your Render environment variables.')
                    print(f"CRITICAL: Password Reset SMTP Failure: {e}")
                    return redirect('forgot_password')
        else:
            messages.error(request, 'Account not found.')
            
    return render(request, 'forgot_password.html', {'hide_marketing_sidebar': True})

def reset_password_view(request):
    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        pwd = request.POST.get('password', '')
        conf = request.POST.get('confirm_password', '')
        email = request.session.get('reset_email')
        
        if not email:
            messages.error(request, 'Session expired. Please start again.')
            return redirect('forgot_password')
            
        user = User.objects.filter(email=email).first()
        
        if not user or not user.otp_code:
            messages.error(request, 'Invalid request.')
            return redirect('forgot_password')
            
        if user.otp_code != otp:
            messages.error(request, 'Incorrect verification code.')
            return render(request, 'reset_password.html')
            
        if timezone.now() > user.otp_expiry:
            messages.error(request, 'Verification code expired.')
            return redirect('forgot_password')
            
        if pwd != conf:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'reset_password.html')
            
        if len(pwd) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'reset_password.html')
            
        user.set_password(pwd)
        user.otp_code = None
        user.otp_expiry = None
        user.save()
        
        request.session.pop('reset_email', None)
        messages.success(request, 'Password reset successful! Please sign in.')
        return redirect('login')
        
    return render(request, 'reset_password.html', {'hide_marketing_sidebar': True})

def heartbeat(request):
    """Simple heartbeat view for uptime monitoring (prevent Render cold starts)."""
    return HttpResponse("OK", status=200)

@login_required
def approve_shops_view(request):
    if not request.user.is_superuser: return redirect('dashboard')
    pending_shops = ShopProfile.objects.filter(is_approved=False)
    if request.method == 'POST':
        shop = get_object_or_404(ShopProfile, id=request.POST.get('shop_id'))
        if request.POST.get('action') == 'approve':
            shop.is_approved = True
            shop.save()
            messages.success(request, 'Approved!')
        return redirect('approve_shops')
    return render(request, 'approve_shops.html', {'pending_shops': pending_shops})

@login_required
def pending_approval_view(request):
    shop = ShopProfile.objects.filter(user=request.user).first()
    if shop and shop.is_approved: return redirect('dashboard')
    return render(request, 'pending_approval.html')