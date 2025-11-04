from django.urls import path
from . import views

urlpatterns = [
    # Main POS Interface
    path('', views.pos_view, name='pos'),
    
    # Product Search & Retrieval
    path('pos/api/search-products/', views.search_products, name='search_products'),
    path('pos/api/product-barcode/', views.get_product_by_barcode, name='product_barcode'),
    path('pos/api/popular-products/', views.get_popular_products, name='popular_products'),
    
    # Customer Management
    path('pos/api/search-customers/', views.search_customers, name='search_customers'),
    
    # Sales Processing
    path('pos/api/process-sale/', views.process_sale, name='process_sale'),
    
    # M-Pesa Integration
    path('pos/api/mpesa/initiate/', views.initiate_mpesa_payment, name='initiate_mpesa'),
    path('pos/api/mpesa/status/', views.check_mpesa_status, name='check_mpesa_status'),
    path('pos/api/mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # Shift Management
    path('pos/api/shift/start/', views.start_shift, name='start_shift'),
    path('pos/api/shift/close/', views.close_shift, name='close_shift'),
]