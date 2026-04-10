from django.db import models
from django.conf import settings
from django.utils import timezone
from customers.models import Customer

class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories', null=True, blank=True, db_constraint=False)
    name = models.CharField(max_length=50)
    gender = models.CharField(max_length=10) # 'male', 'female'
    is_custom = models.BooleanField(default=False)
    fields_json = models.JSONField(default=list) 
    icon = models.CharField(max_length=50, default='fa-scissors')

    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders', null=True, db_constraint=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    items = models.JSONField() # List of dicts
    
    start_date = models.DateField(blank=True, null=True)
    delivery_date = models.DateField(blank=True, null=True)
    
    work_status = models.CharField(max_length=20, default='Working')
    payment_status = models.CharField(max_length=20, default='Pending')
    
    total_amt = models.FloatField(default=0.0)
    advance = models.FloatField(default=0.0)
    balance = models.FloatField(default=0.0)
    payment_mode = models.CharField(max_length=50, blank=True)
    bill_created_by = models.CharField(max_length=100, blank=True)
    bill_number = models.PositiveIntegerField(blank=True, null=True) # Shop specific sequence
    
    trial_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.delivery_date and self.delivery_date < self.start_date:
            raise ValidationError("Delivery date cannot be before the start date.")
        if self.total_amt < 0:
            raise ValidationError("Total amount cannot be negative.")
        if self.advance < 0:
            raise ValidationError("Advance payment cannot be negative.")

    def save(self, *args, **kwargs):
        self.clean()
        # Automatically calculate balance
        self.balance = round(float(self.total_amt or 0) - float(self.advance or 0), 2)
        
        if not self.bill_number and self.user:
            # Generate next bill number for this user
            last_bill = Order.objects.filter(user=self.user).aggregate(models.Max('bill_number'))['bill_number__max']
            self.bill_number = (last_bill or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} for {self.customer.name}"

class Measurement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='measurements', null=True, db_constraint=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='measurements')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='measurements')
    date = models.DateTimeField(default=timezone.now)
    measurements_json = models.JSONField() # Key-Value pairs
    remarks = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Msmt {self.category.name} for {self.customer.name}"

class Reminder(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reminders', null=True, db_constraint=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reminders', null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='reminders', null=True, blank=True)
    type = models.CharField(max_length=50) # 'measurement', 'delivery', 'payment'
    due_date = models.DateField(blank=True, null=True)
    due_time = models.TimeField(blank=True, null=True)
    message = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Reminder: {self.type} - {self.status}"
