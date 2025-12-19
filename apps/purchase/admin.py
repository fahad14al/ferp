from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    readonly_fields = ['line_total']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'supplier', 'order_date', 'status', 'total_amount']
    list_filter = ['status', 'order_date', 'supplier']
    search_fields = ['order_number', 'supplier__name']
    readonly_fields = ['order_number', 'subtotal', 'tax_amount', 'total_amount']
    inlines = [PurchaseOrderItemInline]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'supplier', 'order_date', 'expected_delivery_date', 'status')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'supplier_notes', 'payment_terms', 'is_active'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'product', 'quantity_ordered', 'quantity_received', 'unit_price', 'line_total']
    list_filter = ['purchase_order__status', 'product__category']
    search_fields = ['purchase_order__order_number', 'product__name']
    readonly_fields = ['line_total']

    fieldsets = (
        ('Order Details', {
            'fields': ('purchase_order', 'product')
        }),
        ('Quantities', {
            'fields': ('quantity_ordered', 'quantity_received')
        }),
        ('Pricing', {
            'fields': ('unit_price', 'discount_percent')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
