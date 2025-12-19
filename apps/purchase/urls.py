from django.urls import path
from . import views

app_name = 'purchase'

urlpatterns = [
    # Purchase Orders
    path('', views.purchase_order_list, name='purchase_order_list'),
    path('create/', views.purchase_order_create, name='purchase_order_create'),
    path('<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('<int:pk>/update/', views.purchase_order_update, name='purchase_order_update'),
    path('<int:pk>/delete/', views.purchase_order_delete, name='purchase_order_delete'),
    path('<int:pk>/receive/', views.purchase_order_receive, name='purchase_order_receive'),
    path('<int:pk>/approve/', views.purchase_order_approve, name='purchase_order_approve'),

    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),

    # Analytics and Reports
    path('reports/', views.purchase_reports, name='purchase_reports'),
    path('supplier-performance/', views.supplier_performance, name='supplier_performance'),

    # API endpoints
    path('api/', views.purchase_order_api, name='purchase_order_api'),
]
