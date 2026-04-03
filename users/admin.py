from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ShopProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_verified', 'is_active', 'is_staff')
    list_filter = ('is_verified', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)
    
    actions = ['approve_users']

    fieldsets = UserAdmin.fieldsets + (
        ('Custom Verification', {'fields': ('is_verified', 'otp_code', 'otp_expiry')}),
        ('Role', {'fields': ('is_admin',)}),
    )

    def approve_users(self, request, queryset):
        queryset.update(is_verified=True, is_active=True)
        self.message_user(request, "Selected users have been verified.")
    approve_users.short_description = "Approve / Verify Selected Users"

admin.site.register(User, CustomUserAdmin)

class ShopProfileAdmin(admin.ModelAdmin):
    list_display = ('shop_name', 'user', 'mobile', 'is_approved', 'is_active', 'created_at')
    list_filter = ('is_approved', 'is_active')
    search_fields = ('shop_name', 'user__username', 'mobile', 'upi_id')
    actions = ['approve_shops']

    def approve_shops(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, "Selected shops have been approved.")
    approve_shops.short_description = "Approve Selected Shops"

admin.site.register(ShopProfile, ShopProfileAdmin)
