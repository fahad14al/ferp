from django.contrib import admin
from django.contrib import admin
from .models import Customer, SalesOrder, SalesOrderItem, SalesInvoice


class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 0
    fields = ['product', 'quantity', 'unit_price', 'discount_percent', 'line_total']
    readonly_fields = ['line_total']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    fields = None
    list_display = ['name', 'email', 'phone', 'city', 'country', 'is_active']
    list_filter = ['is_active', 'city', 'state', 'country']
    search_fields = ['name', 'email', 'phone', 'tax_id']
    ordering = ['name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        ('Business Details', {
            'fields': ('tax_id', 'credit_limit', 'payment_terms')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


# @admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    fields = None
    list_display = ['order_number', 'customer', 'order_date', 'status', 'total_amount', 'is_active']
    # ... (Keep definitions)


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'sales_order', 'date_issued', 'amount_due', 'status']
    list_filter = ['status', 'date_issued']
    search_fields = ['invoice_number', 'sales_order__order_number']
    readonly_fields = ['date_issued', 'order_items_preview']
    
    def order_items_preview(self, obj):
        html = '<table style="width:100%; text-align:left; border-collapse: collapse;"><thead><tr style="border-bottom: 1px solid #ccc;"><th>Product</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead><tbody>'
        for item in obj.sales_order.items.all():
            html += f'<tr style="border-bottom: 1px solid #eee;"><td>{item.product.name}</td><td>{item.quantity}</td><td>{item.unit_price}</td><td>{item.line_total}</td></tr>'
        html += '</tbody></table>'
        from django.utils.html import format_html
        return format_html(html)
    
    order_items_preview.short_description = "Ordered Items"
