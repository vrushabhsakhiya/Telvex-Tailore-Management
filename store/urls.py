from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('orders/', views.orders_list, name='orders'),
    path('orders/update/', views.orders_update_details, name='orders_update_details'),
    path('orders/delete/<int:id>/', views.delete_order, name='delete_order'),
    path('measurements/', views.measurements_list, name='measurements'),
    path('measurements/customer/<int:id>/', views.customer_measurement_history, name='customer_measurement_history'),
    path('bills/', views.bills_list, name='bills'),
    path('bills/update/', views.bills_update, name='bills_update'),
    path('invoice/<int:id>/', views.view_invoice, name='view_invoice'),
    path('invoice/save/<int:id>/', views.save_pdf_copy, name='save_pdf_copy'),
    path('categories/', views.categories_list, name='categories'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/delete/<int:id>/', views.delete_category, name='delete_category'),
    path('measurement/add/<int:customer_id>/', views.add_measurement_view, name='add_measurement'),
    path('measurement/delete/<int:id>/', views.delete_measurement, name='delete_measurement'),
    path('measurement/remove-draft/<int:index>/', views.remove_draft_item, name='remove_draft_item'),
    path('reminders/', views.reminders_view, name='reminders'),
    path('search/', views.search_view, name='search'),
]
