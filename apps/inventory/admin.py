from django.contrib import admin
from .models import Category, Supplier, Product, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_email', 'contact_phone')
    search_fields = ('name', 'contact_email')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'stock_quantity', 'price', 'is_low_stock')
    list_filter = ('category', 'supplier', 'is_active')
    search_fields = ('name', 'sku')
    readonly_fields = ('stock_quantity',)  # Updated via StockMovement

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('category', 'supplier')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):  # Use standard admin for movements
    list_display = ('product', 'movement_type', 'quantity', 'reason', 'date')
    list_filter = ('movement_type', 'date', 'product')
    search_fields = ('product__name', 'reason')
    date_hierarchy = 'date'
