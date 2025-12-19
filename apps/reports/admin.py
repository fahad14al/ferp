from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ReportTemplate, GeneratedReport, PurchaseReport,
    SupplierPerformanceReport, InventoryTurnoverReport,
    SalesVsPurchaseAnalysis, DashboardMetric
)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'is_active', 'created_by', 'date_range_required']
    list_filter = ['report_type', 'is_active', 'date_range_required']
    search_fields = ['name', 'description']
    readonly_fields = ['created_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'report_type', 'description', 'is_active')
        }),
        ('Filters', {
            'fields': ('date_range_required', 'supplier_filter', 'product_filter', 'category_filter')
        }),
        ('Template Settings', {
            'fields': ('template_file', 'default_parameters')
        }),
        ('Tracking', {
            'fields': ('created_by',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ['template', 'status', 'file_format', 'generated_at', 'generated_by', 'status_badge']
    list_filter = ['status', 'file_format', 'generated_at', 'is_active']
    search_fields = ['template__name', 'generated_by__username']
    readonly_fields = ['generated_at', 'generated_by', 'processing_time']
    date_hierarchy = 'generated_at'
    
    fieldsets = (
        ('Report Information', {
            'fields': ('template', 'status', 'file_format')
        }),
        ('Parameters', {
            'fields': ('parameters', 'start_date', 'end_date')
        }),
        ('Generated File', {
            'fields': ('report_file', 'generated_at', 'processing_time')
        }),
        ('Tracking', {
            'fields': ('generated_by', 'error_message', 'is_active')
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'gray',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(PurchaseReport)
class PurchaseReportAdmin(admin.ModelAdmin):
    list_display = ['report_date', 'period', 'total_orders', 'total_order_value', 'average_order_value', 'on_time_delivery_rate']
    list_filter = ['period', 'report_date']
    search_fields = ['report_date']
    date_hierarchy = 'report_date'
    
    fieldsets = (
        ('Report Period', {
            'fields': ('report_date', 'period')
        }),
        ('Purchase Metrics', {
            'fields': ('total_orders', 'total_order_value', 'average_order_value')
        }),
        ('Supplier Metrics', {
            'fields': ('total_suppliers', 'active_suppliers')
        }),
        ('Product Metrics', {
            'fields': ('total_products_purchased', 'top_product')
        }),
        ('Performance Metrics', {
            'fields': ('on_time_delivery_rate', 'order_accuracy_rate')
        }),
        ('Financial Metrics', {
            'fields': ('total_spent', 'average_cost_per_unit')
        }),
    )


@admin.register(SupplierPerformanceReport)
class SupplierPerformanceReportAdmin(admin.ModelAdmin):
    list_display = ['supplier', 'report_date', 'period', 'total_orders', 'on_time_delivery_rate_display', 'quality_rating']
    list_filter = ['period', 'report_date', 'supplier']
    search_fields = ['supplier__name']
    date_hierarchy = 'report_date'
    
    fieldsets = (
        ('Report Information', {
            'fields': ('supplier', 'report_date', 'period')
        }),
        ('Order Metrics', {
            'fields': ('total_orders', 'completed_orders', 'cancelled_orders')
        }),
        ('Delivery Metrics', {
            'fields': ('on_time_deliveries', 'late_deliveries', 'average_delivery_days')
        }),
        ('Quality Metrics', {
            'fields': ('quality_rating', 'return_rate')
        }),
        ('Financial Metrics', {
            'fields': ('total_order_value', 'average_order_value', 'payment_terms_compliance')
        }),
    )
    
    def on_time_delivery_rate_display(self, obj):
        return f"{obj.on_time_delivery_rate:.1f}%"
    on_time_delivery_rate_display.short_description = 'On-Time Delivery Rate'


@admin.register(InventoryTurnoverReport)
class InventoryTurnoverReportAdmin(admin.ModelAdmin):
    list_display = ['product', 'report_date', 'period', 'inventory_turnover_ratio', 'days_inventory_outstanding']
    list_filter = ['period', 'report_date', 'product__category']
    search_fields = ['product__name', 'product__sku']
    date_hierarchy = 'report_date'
    
    fieldsets = (
        ('Report Information', {
            'fields': ('product', 'report_date', 'period')
        }),
        ('Inventory Metrics', {
            'fields': ('beginning_inventory', 'ending_inventory', 'average_inventory')
        }),
        ('Sales/Purchase Metrics', {
            'fields': ('units_sold', 'units_purchased', 'cost_of_goods_sold')
        }),
        ('Turnover Calculations', {
            'fields': ('inventory_turnover_ratio', 'days_inventory_outstanding')
        }),
    )


@admin.register(SalesVsPurchaseAnalysis)
class SalesVsPurchaseAnalysisAdmin(admin.ModelAdmin):
    list_display = ['report_date', 'period', 'total_sales', 'total_purchases', 'gross_margin', 'gross_margin_percentage']
    list_filter = ['period', 'report_date']
    date_hierarchy = 'report_date'
    
    fieldsets = (
        ('Report Period', {
            'fields': ('report_date', 'period')
        }),
        ('Sales Metrics', {
            'fields': ('total_sales', 'sales_orders_count', 'average_sale_price')
        }),
        ('Purchase Metrics', {
            'fields': ('total_purchases', 'purchase_orders_count', 'average_purchase_price')
        }),
        ('Profitability Metrics', {
            'fields': ('gross_margin', 'gross_margin_percentage')
        }),
        ('Product Performance', {
            'fields': ('top_selling_product', 'top_purchased_product')
        }),
    )


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_type', 'value', 'unit', 'last_updated']
    list_filter = ['metric_type', 'last_updated']
    search_fields = ['metric_type']
    readonly_fields = ['last_updated']
    
    fieldsets = (
        ('Metric Information', {
            'fields': ('metric_type', 'value', 'unit')
        }),
        ('Additional Data', {
            'fields': ('metadata', 'last_updated')
        }),
    )
