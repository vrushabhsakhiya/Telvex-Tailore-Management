from django.urls import path
from . import views

urlpatterns = [
    path('', views.customer_list, name='customers'),
    path('save/', views.customer_save, name='customer_save'),

    path('delete/<int:id>/', views.delete_customer, name='delete_customer'),
    path('api/profile/<int:id>/', views.api_customer_details, name='api_customer_details'),
]
