from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Customer URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),

    # Sales Order URLs
    path('orders/', views.sales_order_list, name='sales_order_list'),
    path('orders/create/', views.sales_order_create, name='sales_order_create'),
    path('orders/<int:pk>/', views.sales_order_detail, name='sales_order_detail'),
    path('orders/<int:order_pk>/add-item/', views.sales_order_add_item, name='sales_order_add_item'),
    path('orders/<int:pk>/update-status/', views.sales_order_update_status, name='sales_order_update_status'),

    # Invoice URLs
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoice/<int:pk>/', views.invoice_detail, name='invoice_detail'),

    # POS URLs
    path('pos/', views.pos, name='pos'),

    # POS API URLs
    path('api/scan-barcode/', views.api_scan_barcode, name='api_scan_barcode'),
    path('api/search-product/', views.api_search_product, name='api_search_product'),
    path('api/products/', views.api_products, name='api_products'),
    path('api/customers/', views.api_customers, name='api_customers'),
    path('api/cart/', views.api_cart, name='api_cart'),
    path('api/cart/add/', views.api_cart_add, name='api_cart_add'),
    path('api/cart/update/', views.api_cart_update, name='api_cart_update'),
    path('api/cart/remove/', views.api_cart_remove, name='api_cart_remove'),
    path('api/cart/clear/', views.api_cart_clear, name='api_cart_clear'),
    path('api/checkout/', views.api_checkout, name='api_checkout'),

    # Legacy URLs (for backward compatibility)
    path('', views.sales_order_list, name='sales_list'),
]
