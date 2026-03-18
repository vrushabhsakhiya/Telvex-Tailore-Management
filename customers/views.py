from django.shortcuts import render, redirect, get_object_or_404
import os
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.db import IntegrityError
from django.utils import timezone
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from datetime import date
from .models import Customer
from .forms import CustomerForm
from users.models import ShopProfile

from django.views.decorators.csrf import ensure_csrf_cookie

@login_required
@ensure_csrf_cookie
def customer_list(request):
    query = request.GET.get('q', '')
    gender_filter = request.GET.get('gender', '')
    status_filter = request.GET.get('status', '') # Pending/Paid
    date_filter = request.GET.get('date', '')

    # Month Navigation
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    current_date = timezone.now().date()
    # Default to current month if not specified
    if year and month and year.isdigit() and month.isdigit():
         target_date = date(int(year), int(month), 1)
    else:
         target_date = date(current_date.year, current_date.month, 1)

    # Calculate Prev/Next Month
    if target_date.month == 1:
        prev_month = 12
        prev_year = target_date.year - 1
    else:
        prev_month = target_date.month - 1
        prev_year = target_date.year
        
    if target_date.month == 12:
        next_month = 1
        next_year = target_date.year + 1
    else:
        next_month = target_date.month + 1
        next_year = target_date.year
        
    month_nav = {
        'current': target_date.strftime('%B %Y'),
        'prev_url': f"?year={prev_year}&month={prev_month}",
        'next_url': f"?year={next_year}&month={next_month}"
    }


    # Start with base query
    customers = Customer.objects.filter(user=request.user).annotate(
        annotated_balance=Sum('orders__balance', default=0),
        total_orders=Count('orders')
    ).order_by('-id')

    # Apply Filters
    if query:
        # Global Search
        customers = customers.filter(Q(name__icontains=query) | Q(mobile__icontains=query))
        month_nav = None # Hide nav on search
    else:
        # Apply Month Filter ONLY if not searching (optional, or keeping it strictly separated)
        # Assuming we want to show customers JOINED this month by default? 
        # Or just show ALL and let month nav filter 'created_date'? 
        # Given 'customers.html' has the nav, let's filter by created_date to make it useful.
        # But if user wants to see ALL customers, they might use Search? 
        # Let's filter by created_date month/year if not searching.
        customers = customers.filter(
            created_date__year=target_date.year,
            created_date__month=target_date.month
        )
    
    if gender_filter:
        customers = customers.filter(gender=gender_filter)
    
    if date_filter:
        customers = customers.filter(last_visit__date=date_filter)

    if status_filter == 'pending':
        customers = customers.filter(annotated_balance__gt=0)
    elif status_filter == 'paid':
        customers = customers.filter(annotated_balance=0)
    
    paginator = Paginator(customers, 10) # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Handle Add Customer (POST)
    if request.method == 'POST':
        form = CustomerForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                customer = form.save(commit=False)
                customer.user = request.user
                
                # Handle photo upload manually if needed, or rely on FileField if model had one.
                # Since model has CharField for photo, we need to handle saving file and path.
                # However, for now let's assume standard file upload handling or basic path storage if 'photo' is just a string.
                # Wait, model says photo is CharField. We need to handle file saving.
                # Let's temporarily skip actual file save to disk logic to keep it simple or use FileSystemStorage if strictly needed.
                # For this stage, we might just store the filename if uploaded.
                if 'photo' in request.FILES:
                     fs = FileSystemStorage()
                     file = request.FILES['photo']
                     filename = fs.save(file.name, file)
                     customer.photo = filename # Store relative path/filename

                customer.save()
                messages.success(request, 'Customer added successfully!')
                return redirect('customers')
            except IntegrityError:
                 messages.error(request, f"Customer with mobile {form.cleaned_data['mobile']} already exists.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return render(request, 'customers.html', {
        'customers': page_obj,
        'pagination': page_obj,
        'month_nav': month_nav if month_nav else None,
        't': lambda x: x, # Temporary translation dummy
        'active_page': 'customers',
        'form': CustomerForm() # Form for Add Modal including Captcha
    })

@login_required
def delete_customer(request, id):
    if request.method == 'POST':
        customer = get_object_or_404(Customer, id=id, user=request.user)
        
        # Check if customer has any pending orders or dues
        has_pending_orders = customer.orders.exclude(work_status='Delivered').exists()
        has_dues = customer.orders.filter(balance__gt=0).exists()
        
        if has_pending_orders or has_dues:
            messages.warning(request, 'Cannot delete customer. There are pending orders or unpaid dues.')
            return redirect('customers')
            
        customer.delete()
        messages.success(request, 'Customer deleted successfully.')
    return redirect('customers')

# Note: Edit is handled via sidebar/modal in frontend, which might invoke a different view or reuse this if we make it smarter.
# For now, let's keep it simple. The current UI uses `editCurrentCustomer` JS which populates the Add Modal.
# So standard POST to `customer_list` creates new. We need logic to UPDATE if ID is present.

@login_required
def customer_save(request):
    # This view handles both Create and Update based on presence of customer_id
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        if customer_id:
            customer = get_object_or_404(Customer, id=customer_id, user=request.user)
            form = CustomerForm(request.POST, request.FILES, instance=customer)
        else:
            form = CustomerForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.user = request.user
                
                if 'photo' in request.FILES:
                     shop = ShopProfile.objects.filter(user=request.user).first()
                     shop_folder = shop.shop_name.replace(' ', '_') if shop and shop.shop_name else 'default_shop'
                     
                     now = timezone.now()
                     secure_path = f"uploads/users/{request.user.id}/{shop_folder}/customers/{now.year}/{now.month}/"
                     
                     target_dir = os.path.join(settings.MEDIA_ROOT, secure_path)
                     os.makedirs(target_dir, exist_ok=True)
                     
                     fs = FileSystemStorage(location=target_dir, base_url=f"{settings.MEDIA_URL}{secure_path}")
                     file = request.FILES['photo']
                     
                     # Generate unique filename
                     filename = fs.save(file.name, file)
                     obj.photo = fs.url(filename)

                obj.save()
                messages.success(request, 'Customer saved successfully!')
                
                # If New Customer -> Redirect to Measurement (Category Selection)
                if not customer_id:
                     return redirect('add_measurement', customer_id=obj.id)
                     
            except IntegrityError:
                messages.error(request, f"Customer with mobile {form.cleaned_data['mobile']} already exists.")
        else:
             for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
                    
    return redirect('customers')


@login_required
def api_customer_details(request, id):
    customer = get_object_or_404(Customer, id=id, user=request.user)
    
    # Get IDs of measurements already in the draft cart to hide them from profile lookup
    draft_cart = request.session.get('draft_cart', [])
    used_msmt_ids = [item.get('measurement_id') for item in draft_cart if item.get('measurement_id')]
    
    # Get the latest measurement for each category
    # We query all and filter in Python for simplicity and order preservation
    all_msmts = customer.measurements.all().select_related('category').order_by('-date')
    
    latest_msmts = {}
    for m in all_msmts:
        if m.id in used_msmt_ids:
            continue # Skip if already being reused in current draft
            
        cat_name = m.category.name
        if cat_name not in latest_msmts:
            latest_msmts[cat_name] = m
    
    msmt_data = []
    # Sort categories alphabetically or keep date order? Let's use date order (reverse).
    # We already have them from all_msmts which was ordered by date.
    for cat_name, m in latest_msmts.items():
        msmt_data.append({
             'id': m.id,
             'category': m.category.name,
             'date': m.date.strftime('%d %b %Y'),
             'time': m.date.strftime('%I:%M %p'),
             'data': m.measurements_json,
             'remarks': m.remarks
        })
        
    # Pending Balance Calculation
    total_pending = 0
    total_orders = customer.orders.count()
    for o in customer.orders.all():
         total_pending += o.balance
         
    return JsonResponse({
         'id': customer.id,
         'name': customer.name,
         'mobile': customer.mobile,
         'photo': customer.photo or '',
         'gender': customer.gender,
         'total_pending': total_pending,
         'total_orders': total_orders,
         'measurements': msmt_data
    })
