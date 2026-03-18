from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ShopProfile
import datetime

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_verified', 'subscription_end_date', 'is_active', 'is_staff')
    list_filter = ('is_verified', 'is_staff', 'is_active', 'subscription_end_date')
    search_fields = ('username', 'email', 'mobile')
    ordering = ('-date_joined',)
    
    actions = ['approve_users', 'extend_subscription_1_year', 'extend_subscription_2_years']

    fieldsets = UserAdmin.fieldsets + (
        ('Custom Verification & Subscription', {'fields': ('is_verified', 'subscription_end_date', 'otp_code', 'otp_expiry')}),
        ('Role', {'fields': ('is_admin',)}),
    )

    def approve_users(self, request, queryset):
        queryset.update(is_verified=True, is_active=True)
        self.message_user(request, "Selected users have been verified.")
    approve_users.short_description = "Approve / Verify Selected Users"

    def extend_subscription_1_year(self, request, queryset):
        for user in queryset:
            # If expired or not set, start from today. Else start from current end date.
            start_date = user.subscription_end_date if user.subscription_end_date and user.subscription_end_date > datetime.date.today() else datetime.date.today()
            user.subscription_end_date = start_date + datetime.timedelta(days=365)
            user.save()
        self.message_user(request, "Subscription extended by 1 year.")
    extend_subscription_1_year.short_description = "Extend Subscription (1 Year)"

    def extend_subscription_2_years(self, request, queryset):
        for user in queryset:
            start_date = user.subscription_end_date if user.subscription_end_date and user.subscription_end_date > datetime.date.today() else datetime.date.today()
            user.subscription_end_date = start_date + datetime.timedelta(days=730)
            user.save()
        self.message_user(request, "Subscription extended by 2 years.")
    extend_subscription_2_years.short_description = "Extend Subscription (2 Years)"

admin.site.register(User, CustomUserAdmin)
admin.site.register(ShopProfile)
