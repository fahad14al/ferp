from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Product categories for organization."""
    name = models.CharField(_("Name"), max_length=100, unique=True)
    description = models.TextField(_("Description"), blank=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Suppliers for products."""
    name = models.CharField(_("Name"), max_length=100, unique=True)
    contact_email = models.EmailField(_("Contact Email"), blank=True)
    contact_phone = models.CharField(_("Contact Phone"), max_length=20, blank=True)
    address = models.TextField(_("Address"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")

    def __str__(self):
        return self.name


class Product(models.Model):
    """Inventory products."""
    name = models.CharField(_("Name"), max_length=200)
    sku = models.CharField(_("SKU"), max_length=50, unique=True, help_text=_("Stock Keeping Unit"))
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Category"))
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Supplier"))
    description = models.TextField(_("Description"), blank=True)
    cost_price = models.DecimalField(_("Cost Price"), max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(_("Selling Price"), max_digits=10, decimal_places=2, default=0.00)
    image = models.ImageField(_("Image"), upload_to='products/', blank=True, null=True)
    stock_quantity = models.IntegerField(_("Stock Quantity"), default=0)
    reorder_level = models.PositiveIntegerField(_("Reorder Level"), default=10, help_text=_("Minimum stock before reorder"))
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def is_low_stock(self):
        return self.stock_quantity <= self.reorder_level

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def is_low_stock(self):
        return self.stock_quantity <= self.reorder_level


class StockMovement(models.Model):
    """Records stock movements (in/out)."""
    MOVEMENT_TYPES = [
        ('IN', _('Stock In')),
        ('OUT', _('Stock Out')),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Product"))
    movement_type = models.CharField(_("Movement Type"), max_length=3, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField(_("Quantity"))  # Positive for in, negative for out
    reason = models.CharField(_("Reason"), max_length=100, blank=True, help_text=_("e.g., Sale, Purchase, Adjustment"))
    date = models.DateTimeField(_("Date"), auto_now_add=True)
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Stock Movement")
        verbose_name_plural = _("Stock Movements")
        ordering = ['-date']

    def __str__(self):
        return f"{self.product.name} - {self.movement_type} {self.quantity}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update product stock
        if self.movement_type == 'IN':
            self.product.stock_quantity += self.quantity
        elif self.movement_type == 'OUT':
            self.product.stock_quantity -= abs(self.quantity)
        self.product.save()
