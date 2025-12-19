from django.db import models
from django.core.validators import MinValueValidator
from apps.inventory.models import Product


class Customer(models.Model):
    """Customer model for managing customer information"""
    name = models.CharField(max_length=255, help_text="Customer full name or company name")
    email = models.EmailField(unique=True, blank=True, null=True, help_text="Primary email address")
    phone = models.CharField(max_length=20, blank=True, help_text="Phone number")
    address = models.TextField(blank=True, help_text="Full address")
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Business details
    tax_id = models.CharField(max_length=50, blank=True, help_text="Tax ID or VAT number")
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
        help_text="Credit limit for this customer"
    )
    payment_terms = models.CharField(
        max_length=100, blank=True,
        help_text="Payment terms (e.g., Net 30, COD)"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this customer is active")

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [self.address, self.city, self.state, self.postal_code, self.country]
        return ", ".join(filter(None, parts))


class SalesOrder(models.Model):
    """Sales order model"""
    ORDER_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    order_number = models.CharField(max_length=50, unique=True, help_text="Unique order number")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales_orders')
    order_date = models.DateField(auto_now_add=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='draft')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')

    # Financial details
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Shipping details
    shipping_address = models.TextField(blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_postal_code = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=100, blank=True)

    # Additional info
    notes = models.TextField(blank=True, help_text="Internal notes")
    customer_notes = models.TextField(blank=True, help_text="Notes visible to customer")
    payment_method = models.CharField(max_length=50, blank=True, help_text="Payment method used")
    is_active = models.BooleanField(default=True, help_text="Whether this sales order is active")

    class Meta:
        verbose_name = "Sales Order"
        verbose_name_plural = "Sales Orders"
        ordering = ['-order_date', '-id']

    def __str__(self):
        return f"SO-{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number if not provided
            from django.utils import timezone
            self.order_number = f"SO{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    @property
    def shipping_full_address(self):
        """Return formatted shipping address"""
        if self.shipping_address:
            parts = [self.shipping_address, self.shipping_city, self.shipping_state,
                    self.shipping_postal_code, self.shipping_country]
            return ", ".join(filter(None, parts))
        return self.customer.full_address

    def calculate_totals(self):
        """Calculate subtotal, tax, and total amounts"""
        from decimal import Decimal
        from apps.dashboard.models import GeneralSettings
        
        self.subtotal = sum(item.line_total for item in self.items.all())
        
        # Get tax percent from settings
        settings = GeneralSettings.get_settings()
        tax_multiplier = settings.tax_percent / Decimal('100.0')
        
        self.tax_amount = self.subtotal * tax_multiplier
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.save()


class SalesOrderItem(models.Model):
    """Individual items in a sales order"""
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True, help_text="Whether this order item is active")

    class Meta:
        verbose_name = "Sales Order Item"
        verbose_name_plural = "Sales Order Items"
        unique_together = ['sales_order', 'product']

    def __str__(self):
        return f"{self.product.name} - {self.quantity} units"

    @property
    def line_total(self):
        """Calculate line total after discount"""
        if self.unit_price is None or self.quantity is None:
            return 0
        discount_amount = (self.unit_price * self.quantity) * (self.discount_percent / 100)
        return (self.unit_price * self.quantity) - discount_amount

    def save(self, *args, **kwargs):
        # Set unit price from product if not set
        if not self.unit_price:
            self.unit_price = self.product.price
        super().save(*args, **kwargs)

        # Update order totals
        self.sales_order.calculate_totals()


class SalesInvoice(models.Model):
    """Invoice for a sales order"""
    invoice_number = models.CharField(max_length=50, unique=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='invoices')
    date_issued = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], default='draft')
    
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Sales Invoice"
        verbose_name_plural = "Sales Invoices"
        ordering = ['-date_issued']
        
    def __str__(self):
        return f"INV-{self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            from django.utils import timezone
            self.invoice_number = f"INV{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)
