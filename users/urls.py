from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('staff-login/', views.staff_login_view, name='staff_login'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/update-profile/', views.update_shop_profile, name='update_shop_profile'),
    path('settings/export/', views.export_custom_data, name='export_custom_data'),
    path('settings/backup/', views.download_backup, name='download_backup'),
    path('settings/reset/', views.reset_data, name='reset_data'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('admin/delete-user/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    path('settings/staff/delete/<str:staff_name>/', views.delete_staff, name='delete_staff'),
    path('profile/update/', views.update_shop_profile, name='update_shop_profile'),
]
