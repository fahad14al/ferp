from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('', views.inventory_dashboard, name='inventory_dashboard'),
    path('list/', views.inventory_list, name='inventory_list'),

    # Product management
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('product/create/', views.product_create, name='product_create'),
    path('product/<int:pk>/update/', views.product_update, name='product_update'),
    path('product/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('product/<int:pk>/adjust-stock/', views.stock_adjustment, name='stock_adjustment'),
    path('product/<int:pk>/barcode/', views.generate_barcode, name='generate_barcode'),

    # Category management
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/update/', views.category_update, name='category_update'),

    # Supplier management
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/create/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/update/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # API endpoints
    path('api/product-search/', views.api_product_search, name='api_product_search'),
    path('api/stock-alerts/', views.api_stock_alerts, name='api_stock_alerts'),
    path('api/product-create/', views.api_product_create, name='api_product_create'),
]
