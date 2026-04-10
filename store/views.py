from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.base import ContentFile
import os
import io
from xhtml2pdf import pisa
from customers.models import Customer
from users.models import ShopProfile
from .models import Order, Category, Reminder, Measurement

def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

@login_required
def dashboard(request):
    today = timezone.now().date()
    user = request.user
    
    # Existing Stats...
    total_customers = Customer.objects.filter(user=user).count()
    total_revenue = Order.objects.filter(user=user).aggregate(Sum('total_amt'))['total_amt__sum'] or 0
    total_pending = Order.objects.filter(user=user).aggregate(Sum('balance'))['balance__sum'] or 0
    pending_delivery = Order.objects.filter(user=user, work_status__in=['Working', 'Ready to Deliver', 'Processing']).count()
    delivery_today_count = Order.objects.filter(user=user, delivery_date=today).exclude(work_status='Delivered').count()
    
    # Advanced: Monthly Revenue Trend (Last 6 Months)
    from django.db.models.functions import TruncMonth
    revenue_trend = Order.objects.filter(user=user, created_at__date__gte=today - timedelta(days=180)) \
        .annotate(month=TruncMonth('created_at')) \
        .values('month') \
        .annotate(total=Sum('total_amt')) \
        .order_by('month')

    # Advanced: Top Customers (Optimized: Removed N+1 Query)
    top_customers = Customer.objects.filter(user=user) \
        .annotate(spend=Sum('order__total_amt')) \
        .filter(spend__gt=0) \
        .order_by('-spend')[:5]

    # Advanced: Upcoming Deliveries (Next 7 Days)
    upcoming_deliveries = Order.objects.filter(
        user=user, 
        delivery_date__range=[today + timedelta(days=1), today + timedelta(days=7)]
    ).exclude(work_status='Delivered').select_related('customer').order_by('delivery_date')

    stats = {
        "total_customers": total_customers,
        "total_revenue": total_revenue,
        "pending_balance": total_pending,
        "pending_delivery": pending_delivery,
        "delivery_today": delivery_today_count,
        "monthly_revenue": Order.objects.filter(user=user, created_at__month=today.month).aggregate(Sum('total_amt'))['total_amt__sum'] or 0,
        "monthly_pending": Order.objects.filter(user=user, created_at__month=today.month).aggregate(Sum('balance'))['balance__sum'] or 0,
        "monthly_customers": Customer.objects.filter(user=user, created_date__month=today.month).count(),
    }
    
    context = {
        'stats': stats,
        'todays_orders': Order.objects.filter(user=user, created_at__date=today).select_related('customer').order_by('-id'),
        'upcoming_deliveries': upcoming_deliveries,
        'top_customers': top_customers,
        'revenue_trend': list(revenue_trend),
        'active_page': 'dashboard',
        'shop': ShopProfile.objects.filter(user=user).first(),
    }
    return render(request, 'dashboard.html', context)

@login_required
def orders_list(request):
    query = request.GET.get('q', '')
    gender_filter = request.GET.get('gender', '')
    status_filter = request.GET.get('status', '') # Pending, Paid, etc
    
    # Month Navigation
    import calendar
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
    
    # Filter Orders by Month
    orders = Order.objects.filter(
        user=request.user,
        created_at__year=target_date.year,
        created_at__month=target_date.month
    ).select_related('customer').order_by('-id')

    if query:
        # If searching, we might want to search globally or just this month. 
        # Let's search GLOBALLY if query is present, ignoring month filter for better UX,
        # OR keep month filter. Given the UI has specific month nav, user likely expects month scope unless they use global search.
        # But generally search should find anything. Let's override month filter for Search.
        orders = Order.objects.filter(user=request.user).select_related('customer').order_by('-id')
        orders = orders.filter(Q(customer__name__icontains=query) | Q(customer__mobile__icontains=query) | Q(id__icontains=query))

    if status_filter:
        if status_filter == 'pending':
            orders = orders.filter(balance__gt=0)
        elif status_filter == 'paid':
            orders = orders.filter(balance=0)
    
    if gender_filter:
        orders = orders.filter(customer__gender=gender_filter)

    work_status_filter = request.GET.get('work_status')
    if work_status_filter:
        orders = orders.filter(work_status=work_status_filter)

    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders.html', {
        'orders': page_obj,
        'pagination': page_obj,
        'month_nav': month_nav if not query else None, # Hide nav if global search
        'active_page': 'orders',
        'shop': ShopProfile.objects.filter(user=request.user).first(),
    })

@login_required
def delete_order(request, id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=id, user=request.user)
        order.delete()
        messages.success(request, 'Order deleted successfully.')
    return redirect('orders')

@login_required
def orders_update_details(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Update fields
        order.work_status = request.POST.get('status')
        delivery_date = request.POST.get('delivery_date')
        if delivery_date:
            order.delivery_date = delivery_date
            
        order.total_amt = float(request.POST.get('total_amt', 0))
        order.advance = float(request.POST.get('advance', 0))
        order.payment_mode = request.POST.get('payment_mode')
        
        # Recalculate balance
        order.balance = order.total_amt - order.advance
        if order.balance <= 0:
            order.payment_status = 'Paid'
            order.balance = 0
        elif order.advance > 0:
            order.payment_status = 'Half-Payment'
        else:
            order.payment_status = 'Pending'
            
        order.save()
        messages.success(request, 'Order updated successfully.')
        return redirect('orders')
    
    return redirect('orders')

@login_required
def measurements_list(request):
    # Get all measurements for the user
    all_measurements = Measurement.objects.filter(user=request.user).select_related('customer', 'category').order_by('-date')
    
    # Group measurements by customer in a professional way
    from collections import defaultdict
    customer_groups = defaultdict(lambda: {'categories': set(), 'last_date': None, 'customer': None})
    
    for m in all_measurements:
        cid = m.customer.id
        if not customer_groups[cid]['customer']:
            customer_groups[cid]['customer'] = m.customer
        customer_groups[cid]['categories'].add(m.category.name)
        if not customer_groups[cid]['last_date'] or m.date > customer_groups[cid]['last_date']:
            customer_groups[cid]['last_date'] = m.date
            
    # Convert to list and sort by last_date DESC
    grouped_list = []
    for cid, data in customer_groups.items():
        grouped_list.append({
            'customer': data['customer'],
            'categories': sorted(data['categories']),
            'last_date': data['last_date']
        })
    grouped_list.sort(key=lambda x: x['last_date'], reverse=True)
    
    # Pagination
    paginator = Paginator(grouped_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'measurements.html', {
        'measurements': page_obj,
        'pagination': page_obj,
        'active_page': 'measurements'
    })

@login_required
def customer_measurement_history(request, id):
    customer = get_object_or_404(Customer, id=id, user=request.user)
    measurements = Measurement.objects.filter(user=request.user, customer=customer).select_related('category').order_by('-date')
    
    return render(request, 'measurement_history.html', {
        'customer': customer,
        'measurements': measurements
    })

@login_required
def bills_list(request):
    # Similar to orders but focused on financial aspects
    # In Flask app, 'bills' were essentially orders with payment info
    orders = Order.objects.filter(user=request.user).select_related('customer').order_by('-id')
    
    # Filtering
    q = request.GET.get('q')
    if q:
        orders = orders.filter(Q(customer__name__icontains=q) | Q(customer__mobile__icontains=q))
        
    status = request.GET.get('status')
    if status == 'pending':
        orders = orders.filter(balance__gt=0)
    elif status == 'paid':
        orders = orders.filter(balance=0)
        
    gender_filter = request.GET.get('gender')
    if gender_filter:
        orders = orders.filter(customer__gender=gender_filter)
        
    # Month Navigation
    import calendar
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

    # Filter Orders by Month (if not searching)
    if not q:
        orders = orders.filter(
            created_at__year=target_date.year,
            created_at__month=target_date.month
        )
    
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Shop Profile for Bill Creators
    shop = ShopProfile.objects.filter(user=request.user).first()
    
    return render(request, 'bills.html', {
        'bills': page_obj,
        'pagination': page_obj,
        'active_page': 'bills',
        'shop': shop,
        'month_nav': month_nav if not q else None
    })

def _get_payment_status(advance, total):
    if advance >= total and total > 0:
        return 'Paid'
    if advance > 0:
        return 'Half-Payment'
    return 'Pending'

@login_required
def bills_update(request):
    # Updates payment details for a bill (order)
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        order.total_amt = float(request.POST.get('total_amt', 0))
        order.advance = float(request.POST.get('advance', 0))
        order.payment_mode = request.POST.get('payment_mode')

        # Bill Creator
        creator = request.POST.get('bill_created_by')
        if creator and creator not in ('System', 'Unknown'):
             order.bill_created_by = creator
        elif not order.bill_created_by:
             order.bill_created_by = request.user.first_name
        
        # Update Work Status
        if work_status := request.POST.get('work_status'):
            order.work_status = work_status
        
        # Status derivation
        order.payment_status = _get_payment_status(order.advance, order.total_amt)
             
        # Also delivery date might be updated here
        if request.POST.get('delivery_date'):
            order.delivery_date = request.POST.get('delivery_date')

        if order.balance <= 0 or order.payment_status == 'Paid':
             # Auto-generate invoice when paid or updated
             shop = ShopProfile.objects.filter(user=request.user).first()
             generate_invoice_pdf(order, shop)
        
        order.save()
        messages.success(request, 'Bill payment updated.')
        
    return redirect('bills')

@login_required
def view_invoice(request, id):
    order = get_object_or_404(Order, id=id, user=request.user)
    shop = ShopProfile.objects.filter(user=request.user).first()
    
    # Fallback to prevent VariableDoesNotExist if shop is missing
    if not shop:
        shop = type('DummyShop', (), {
            'shop_name': 'My Shop',
            'mobile': '',
            'address': '',
            'gst_no': '',
            'upi_id': '',
            'terms': '',
            'logo': None,
            'staff_roles': {}
        })
    
    # Generate UPI QR Link if UPI ID exists
    upi_qr_url = ""
    bill_created_role = ""
    if hasattr(shop, 'upi_id') and shop.upi_id:
        # Standard UPI format: upi://pay?pa=ID&pn=NAME&am=AMOUNT&cu=INR
        import urllib.parse
        # Ensure amount has 2 decimal places
        formatted_balance = f"{order.balance:.2f}"
        upi_qr_url = f"upi://pay?pa={shop.upi_id}&pn={urllib.parse.quote(getattr(shop, 'shop_name', 'Shop'))}&am={formatted_balance}&cu=INR"
    
    # Get role of the person who created this bill
    if order.bill_created_by and hasattr(shop, 'staff_roles'):
        bill_created_role = shop.staff_roles.get(order.bill_created_by, "")

    return render(request, 'invoice.html', {
        'order': order, 
        'shop': shop, 
        'upi_qr_url': upi_qr_url,
        'bill_created_role': bill_created_role,
        'is_public': False, 
        'download_mode': False
    })

def generate_invoice_pdf(order, shop):
    """
    Generates a PDF for the order and saves it to:
    1. media/invoices/YYYY/MM/Order_ID.pdf
    2. media/backups/invoices/YYYY/MM/Order_ID.pdf
    Also saves a CSV record.
    """
    try:
        # Fallback for shop
        if not shop:
            shop = type('DummyShop', (), {'shop_name': 'My Shop', 'logo': None, 'address': '', 'mobile': '', 'upi_id': '', 'terms': ''})

        # Render HTML
        context = {'order': order, 'shop': shop, 'is_public': False, 'download_mode': True}
        html_string = render_to_string('invoice.html', context)
        
        # Determine Paths
        now = timezone.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        
        relative_path = f"invoices/{year}/{month}"
        backup_path = f"backups/{relative_path}"
        
        full_dir = os.path.join(settings.MEDIA_ROOT, relative_path)
        full_backup_dir = os.path.join(settings.MEDIA_ROOT, backup_path)
        
        os.makedirs(full_dir, exist_ok=True)
        os.makedirs(full_backup_dir, exist_ok=True)
        
        filename = f"Invoice_{order.id}_{order.customer.name.replace(' ', '_')}.pdf"
        file_path = os.path.join(full_dir, filename)
        backup_file_path = os.path.join(full_backup_dir, filename)
        
        # Generate PDF
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), result)
        
        if not pdf.err:
            # Save to Primary Location
            with open(file_path, 'wb') as f:
                f.write(result.getvalue())
                
            # Save to Backup Location
            with open(backup_file_path, 'wb') as f:
                f.write(result.getvalue())
                
            # Save Metadata to CSV
            csv_file = os.path.join(full_dir, "metadata.csv")
            header = "Order ID,Date,Customer,Amount,Balance,PDF Path\n"
            data = f"{order.id},{now.date()},{order.customer.name},{order.total_amt},{order.balance},{filename}\n"
            
            mode = 'a' if os.path.exists(csv_file) else 'w'
            with open(csv_file, mode) as f:
                if mode == 'w': f.write(header)
                f.write(data)
                
            return file_path
            
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

@login_required
def save_pdf_copy(request, id):
    # This endpoint can be used to manually trigger backup or save from JS if needed
    # But for "Auto-Save" we will call the utility directly in update/create views.
    if request.method == 'POST':
        order = get_object_or_404(Order, id=id, user=request.user)
        shop = ShopProfile.objects.filter(user=request.user).first()
        path = generate_invoice_pdf(order, shop)
        if path:
            return JsonResponse({'status': 'success', 'path': path})
        return JsonResponse({'status': 'error'}, status=500)
    return JsonResponse({'status': 'success'})

@login_required
def categories_list(request):
    male_categories = Category.objects.filter(user=request.user, gender='male').order_by('-id')
    female_categories = Category.objects.filter(user=request.user, gender='female').order_by('-id')
    return render(request, 'custom_categories.html', {
        'male_categories': male_categories,
        'female_categories': female_categories,
        'active_page': 'custom_categories'
    })

@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        gender = request.POST.get('gender') # Passed from hidden inputs/sidebar
        fields_json = request.POST.get('fields_json', '[]') # JSON string of fields array
        
        # Simple JSON field handling - Store as list in JSONField if using PG, or string/text if sqlite default
        # The model likely has a JSONField or similar.
        # Let's assume the model expects a Python list/dict if it's a JSONField, or string if TextField.
        # Given SQLite often stores as Text, we might need to be careful. 
        # But Django's JSONField handles serialization usually.
        # Let's import json
        import json
        try:
            fields_list = json.loads(fields_json)
        except Exception:
            fields_list = []

        Category.objects.create(
            user=request.user,
            name=name,
            gender=gender,
            icon=request.POST.get('icon', 'fa-scissors'),
            fields_json=fields_list # Django JSONField takes python object
        )
        messages.success(request, 'Category added successfully.')
        return redirect('categories')
    return redirect('categories')

@login_required
def delete_category(request, id):
    category = get_object_or_404(Category, id=id)
    if category.user != request.user:
         messages.error(request, 'Unauthorized')
         return redirect('categories')
         
    category.delete()
    messages.success(request, 'Category deleted.')
    return redirect('categories')

def _parse_json(json_str):
    import json
    try:
        return json.loads(json_str)
    except Exception:
        return {}

def _create_measurement(request, customer, category):
    measurements_data = _parse_json(request.POST.get('measurements_json', '{}'))
    remarks = request.POST.get('remarks')
    return Measurement.objects.create(
        user=request.user,
        customer=customer,
        category=category,
        measurements_json=measurements_data,
        remarks=remarks,
        date=timezone.now()
    )

def _create_order_from_items(request, customer, all_items):
    grand_total = float(request.POST.get('total_amt', 0) or 0)
    advance = float(request.POST.get('advance', 0) or 0)
    payment_status = _get_payment_status(advance, grand_total)
    
    items_json = []
    for item in all_items:
        items_json.append({
            'name': item['category_name'],
            'qty': 1,
            'price': item.get('price', 0),
            'ref_msmt_id': item.get('measurement_id')
        })
    return Order.objects.create(
        user=request.user,
        customer=customer,
        total_amt=grand_total,
        advance=advance,
        balance=grand_total - advance,
        payment_status=payment_status,
        payment_mode=request.POST.get('payment_mode'),
        work_status='Processing',
        delivery_date=request.POST.get('delivery_date'),
        items=items_json,
        notes=request.POST.get('order_notes'),
        bill_created_by=request.POST.get('created_by', 'System')
    )

def _handle_add_draft(request, customer, draft_cart):
    cat_id = request.POST.get('category_id')
    category = get_object_or_404(Category, id=cat_id)
    measurement = _create_measurement(request, customer, category)

    item_price = float(request.POST.get('item_price', 0) or 0)
    
    entry = {
        'customer_id': str(customer.id),
        'measurement_id': measurement.id,
        'category_name': category.name,
        'price': item_price,
        'remarks': measurement.remarks
    }
    
    edit_index = request.POST.get('edit_index')
    if edit_index and edit_index.isdigit():
        idx = int(edit_index)
        if 0 <= idx < len(draft_cart):
            draft_cart[idx] = entry
            request.session['draft_cart'] = draft_cart
            messages.success(request, f"Updated {category.name} in Bill Draft.")
            return redirect('add_measurement', customer_id=customer.id)
            
    draft_cart.append(entry)
    request.session['draft_cart'] = draft_cart
    messages.success(request, f"Added {category.name} to Bill Draft.")
    return redirect('add_measurement', customer_id=customer.id)

def _handle_finish_order(request, customer, draft_cart, action):
    all_items = list(draft_cart)
    if action == 'finish_order':
        cat_id = request.POST.get('category_id')
        category = get_object_or_404(Category, id=cat_id)
        measurement = _create_measurement(request, customer, category)

        current_item_price = float(request.POST.get('item_price', 0) or 0)
        entry = {
            'customer_id': str(customer.id),
            'measurement_id': measurement.id,
            'category_name': category.name,
            'price': current_item_price,
            'remarks': measurement.remarks
        }
        
        edit_index = request.POST.get('edit_index')
        if edit_index and edit_index.isdigit():
            idx = int(edit_index)
            if 0 <= idx < len(all_items):
                all_items[idx] = entry
            else:
                all_items.append(entry)
        else:
            all_items.append(entry)
    
    if not all_items:
        messages.error(request, "No items in bill to finish.")
        return redirect('add_measurement', customer_id=customer.id)

    new_order = _create_order_from_items(request, customer, all_items)
    request.session['draft_cart'] = []
    
    shop = ShopProfile.objects.filter(user=request.user).first()
    generate_invoice_pdf(new_order, shop)
    
    messages.success(request, 'Order created successfully.')
    return redirect('orders')

def _handle_save_only(request, customer):
    cat_id = request.POST.get('category_id')
    if cat_id:
        category = get_object_or_404(Category, id=cat_id)
        _create_measurement(request, customer, category)
        messages.success(request, 'Measurement saved.')
    return redirect('customer_measurement_history', id=customer.id)

@login_required
def add_measurement_view(request, customer_id):
    customer = get_object_or_404(Customer, id=customer_id, user=request.user)
    
    # Draft Cart Handling
    draft_cart = request.session.get('draft_cart', [])
    if draft_cart and str(draft_cart[0].get('customer_id')) != str(customer.id):
        draft_cart = []
        request.session['draft_cart'] = []

    # Handle optional reuse
    reuse_id = request.GET.get('reuse_id')
    reuse_measurement = Measurement.objects.filter(id=reuse_id, user=request.user).first() if reuse_id else None

    # Handle optional edit mode
    edit_index = request.GET.get('edit_index')
    edit_item = None
    if edit_index and edit_index.isdigit():
        idx = int(edit_index)
        if 0 <= idx < len(draft_cart):
            edit_item = draft_cart[idx]

    if request.method == 'POST':
        action = request.POST.get('action_type', 'save_only')
        
        if action == 'add_draft':
            return _handle_add_draft(request, customer, draft_cart)
        elif action in ['finish_order', 'finish_order_direct']:
            return _handle_finish_order(request, customer, draft_cart, action)
        else:
            return _handle_save_only(request, customer)

    # GET
    categories = Category.objects.filter(user=request.user, gender=customer.gender)
    shop = ShopProfile.objects.filter(user=request.user).first()
    
    return render(request, 'measurement.html', {
        'customer': customer,
        'categories': categories,
        'reuse_measurement': reuse_measurement,
        'edit_index': edit_index,
        'edit_item': edit_item,
        'shop': shop,
        'draft_cart': draft_cart, 
        'draft_total': sum(float(i.get('price', 0)) for i in draft_cart),
        'recent_measurements': Measurement.objects.filter(user=request.user, customer=customer).select_related('category').order_by('-date')[:5]
    })

@login_required
def reminders_view(request):
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    
    # Urgent: Due today or before, and NOT delivered
    urgent_orders = Order.objects.filter(
        user=request.user, 
        delivery_date__lte=today
    ).exclude(work_status='Delivered').select_related('customer').order_by('delivery_date')
    
    # Upcoming: Due tomorrow
    upcoming_orders = Order.objects.filter(
        user=request.user, 
        delivery_date=tomorrow
    ).exclude(work_status='Delivered').select_related('customer').order_by('delivery_date')
    
    # Pending Payments: Balance > 0
    pending_payments = Order.objects.filter(
        user=request.user,
        balance__gt=0
    ).select_related('customer').order_by('-id')
    
    return render(request, 'reminders.html', {
        'urgent_orders': urgent_orders,
        'upcoming_orders': upcoming_orders,
        'pending_payments': pending_payments,
        'active_page': 'reminders'
    })

@login_required
def search_view(request):
    query = request.GET.get('q', '')
    customers = []
    orders = []
    
    if query:
        customers = Customer.objects.filter(
            user=request.user
        ).filter(
            Q(name__icontains=query) | 
            Q(mobile__icontains=query) | 
            Q(city__icontains=query)
        )
        
        if query.isdigit():
             orders = Order.objects.filter(user=request.user, id=query)
        else:
             orders = Order.objects.filter(
                 user=request.user, 
                 customer__name__icontains=query
             ).order_by('-id')
    
    return render(request, 'search_results.html', {
        'query': query,
        'customers': customers,
        'orders': orders
    })

@login_required
def delete_measurement(request, id):
    if request.method == 'POST':
        measurement = get_object_or_404(Measurement, id=id, user=request.user)
        measurement.delete()
        return JsonResponse({'success': True, 'message': 'Measurement deleted successfully.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

@login_required
def remove_draft_item(request, index):
    draft_cart = request.session.get('draft_cart', [])
    if 0 <= index < len(draft_cart):
        item = draft_cart.pop(index)
        request.session['draft_cart'] = draft_cart
        messages.info(request, f"Removed {item.get('category_name')} from draft.")
    
    customer_id = request.GET.get('customer_id')
    if customer_id:
        return redirect('add_measurement', customer_id=customer_id)
    return redirect('dashboard')
