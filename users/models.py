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

    def __str__(self):
        return self.username


class ShopProfile(models.Model):
    """
    Comprehensive profile for the Shop associated with a User.
    Stores business details, contact information, and system configuration.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop_profile')
    
    # Business Identity
    shop_name = models.CharField(max_length=100, blank=True, help_text="Official name of the shop")
    address = models.TextField(blank=True, help_text="Full physical address")
    pincode = models.CharField(max_length=10, blank=True, help_text="Area PIN code")
    state = models.CharField(max_length=50, blank=True, help_text="State for GST purposes")
    gst_no = models.CharField(max_length=20, blank=True, help_text="GST Identification Number")
    
    # Contact Information
    mobile = models.CharField(max_length=20, blank=True, help_text="Primary contact mobile")
    whatsapp = models.CharField(max_length=20, blank=True, help_text="WhatsApp number for communication")
    email = models.EmailField(blank=True, help_text="Official shop email address")
    
    # Financial & Legal
    upi_id = models.CharField(max_length=50, blank=True, help_text="UPI ID for digital payments")
    terms = models.TextField(blank=True, help_text="Default terms and conditions for bills")
    logo = models.CharField(max_length=200, blank=True) # Storing path as string to match legacy structure
    upi_qr = models.ImageField(upload_to='shop/qrs/', blank=True, null=True, help_text="Upload your own UPI QR Code image")
    
    # Staff & Role Management (JSON Configuration)
    bill_creators = models.JSONField(default=list, blank=True) # List of staff names
    staff_roles = models.JSONField(default=dict, blank=True) # Map of {staff_name: role}
    staff_pins = models.JSONField(default=dict, blank=True) # Map of {staff_name: pin}
    
    # Multi-tenant Configuration
    database_name = models.CharField(max_length=100, blank=True, null=True) # Track shop's isolated database
    
    # System Status
    is_active = models.BooleanField(default=True) # Shop active status
    is_approved = models.BooleanField(default=False) # Super Admin approval for registration
    created_at = models.DateTimeField(auto_now_add=True, null=True) 
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = 'users_shopprofile'
        verbose_name = 'Shop Profile'
        verbose_name_plural = 'Shop Profiles'

    def __str__(self):
        return self.shop_name or f"Shop of {self.user.username}"
