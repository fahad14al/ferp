from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_list, name='report_list'),
    path('purchase-summary/', views.purchase_summary_report, name='purchase_summary'),
    path('supplier-performance/', views.supplier_performance_report, name='supplier_performance'),
    path('inventory-turnover/', views.inventory_turnover_report, name='inventory_turnover'),
    path('sales-vs-purchase/', views.sales_vs_purchase_report, name='sales_vs_purchase'),
    path('financial-summary/', views.financial_summary_report, name='financial_summary'),
]
