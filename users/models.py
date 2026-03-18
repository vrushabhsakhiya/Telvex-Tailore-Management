from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    """
    Custom User model extending AbstractUser.
    Adds fields for OTP verification and specific app roles.
    """
    email = models.EmailField(unique=True, db_index=True)
    
    # 2FA / OTP Fields
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expiry = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    # Security / Locking
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(blank=True, null=True)
    
    # Role (distinct from is_staff/is_superuser)
    is_admin = models.BooleanField(default=False)
    
    # created_at handled by date_joined in AbstractUser
    
    # Subscription
    subscription_end_date = models.DateField(blank=True, null=True)

    def is_subscription_active(self):
        """
        Returns True if subscription is active (or user is admin/superuser).
        Active means end_date is in the future.
        """
        if self.is_superuser or self.is_staff:
            return True
        if not self.subscription_end_date:
            return False # No date set = Expired/Not Active
        return self.subscription_end_date >= timezone.now().date()

    def __str__(self):
        return self.username


class ShopProfile(models.Model):
    """
    Profile for the Shop associated with a User.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop_profile')
    shop_name = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    gst_no = models.CharField(max_length=20, blank=True)
    terms = models.TextField(blank=True)
    upi_id = models.CharField(max_length=50, blank=True)
    logo = models.CharField(max_length=200, blank=True) # Storing path as string to match legacy
    bill_creators = models.JSONField(default=list, blank=True) # List of staff names
    staff_roles = models.JSONField(default=dict, blank=True) # Map of {staff_name: role}
    staff_pins = models.JSONField(default=dict, blank=True) # Map of {staff_name: pin}
    database_name = models.CharField(max_length=100, blank=True, null=True) # Track shop's database
    is_active = models.BooleanField(default=True) # Shop status
    created_at = models.DateTimeField(auto_now_add=True, null=True) # Allow null for existing data
    updated_at = models.DateTimeField(auto_now=True, null=True) # Allow null for existing data

    def __str__(self):
        return self.shop_name or f"Shop of {self.user.username}"
