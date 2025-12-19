from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.inventory.models import Product, Supplier
from django.contrib.auth.models import User
from django.db.models import Sum


class PurchaseOrder(models.Model):
    """Purchase order model for managing supplier orders."""
    ORDER_STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending_approval', _('Pending Approval')),
        ('approved', _('Approved')),
        ('confirmed', _('Confirmed')),
        ('processing', _('Processing')),
        ('partially_received', _('Partially Received')),
        ('received', _('Received')),
        ('cancelled', _('Cancelled')),
        ('closed', _('Closed')),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', _('Unpaid')),
        ('partially_paid', _('Partially Paid')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
    ]

    # Basic Information
    order_number = models.CharField(_("Order Number"), max_length=50, unique=True, help_text=_("Unique purchase order number"))
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders', verbose_name=_("Supplier"))
    order_date = models.DateField(_("Order Date"), default=timezone.now)
    expected_delivery_date = models.DateField(_("Expected Delivery Date"), null=True, blank=True)
    actual_delivery_date = models.DateField(_("Actual Delivery Date"), null=True, blank=True)

    # Status and Workflow
    status = models.CharField(_("Status"), max_length=20, choices=ORDER_STATUS_CHOICES, default='draft')
    payment_status = models.CharField(_("Payment Status"), max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')

    # Financial Details
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(_("Tax Rate (%)"), max_digits=5, decimal_places=2, default=15.00, validators=[MinValueValidator(0)])
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    discount_amount = models.DecimalField(_("Discount Amount"), max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    shipping_cost = models.DecimalField(_("Shipping Cost"), max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(_("Total Amount"), max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Payment Information
    payment_terms = models.CharField(_("Payment Terms"), max_length=100, blank=True, help_text=_("Payment terms (e.g., Net 30, COD)"))
    payment_due_date = models.DateField(_("Payment Due Date"), null=True, blank=True)

    # Additional Information
    notes = models.TextField(_("Internal Notes"), blank=True, null=True, help_text=_("Internal notes"))
    supplier_notes = models.TextField(_("Supplier Notes"), blank=True, null=True, help_text=_("Notes for supplier"))
    terms_conditions = models.TextField(_("Terms & Conditions"), blank=True, null=True)

    # Approval Workflow
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_purchase_orders', verbose_name=_("Created By"))
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchase_orders', verbose_name=_("Approved By"))
    approved_date = models.DateTimeField(_("Approved Date"), null=True, blank=True)

    # Tracking
    priority = models.CharField(_("Priority"), max_length=20, choices=[
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ], default='medium')

    is_active = models.BooleanField(_("Active"), default=True, help_text=_("Whether this purchase order is active"))

    class Meta:
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")
        ordering = ['-order_date', '-id']
        permissions = [
            ("can_approve_purchase_order", "Can approve purchase orders"),
            ("can_create_purchase_order", "Can create purchase orders"),
        ]

    def __str__(self):
        return f"PO-{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number if not provided
            self.order_number = f"PO{timezone.now().strftime('%Y%m%d%H%M%S')}"

        # Calculate payment due date based on payment terms
        if self.payment_terms and not self.payment_due_date:
            self.calculate_payment_due_date()

        super().save(*args, **kwargs)

    def calculate_totals(self):
        """Calculate subtotal, tax, and total amounts"""
        self.subtotal = sum(item.line_total for item in self.items.filter(is_active=True))
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
        self.save()

    def calculate_payment_due_date(self):
        """Calculate payment due date based on payment terms"""
        if 'net' in self.payment_terms.lower():
            try:
                days = int(''.join(filter(str.isdigit, self.payment_terms)))
                self.payment_due_date = self.order_date + timezone.timedelta(days=days)
            except (ValueError, TypeError):
                pass

    def receive_order(self):
        """Update order status based on received items (No stock movement side effects)"""
        # Determine status based on item progress
        active_items = self.items.filter(is_active=True)
        if not active_items.exists():
            return

        all_received = all(item.is_fully_received for item in active_items)
        any_received = any(item.quantity_received > 0 for item in active_items)

        new_status = self.status
        if all_received:
            new_status = 'received'
        elif any_received:
            new_status = 'partially_received'
        
        # Update dates if finishing
        if new_status == 'received' and not self.actual_delivery_date:
            self.actual_delivery_date = timezone.now().date()
            
        if self.status != new_status:
            self.status = new_status
            self.save()

    def complete_order(self):
        """Force complete the order: Receive all pending items and update stock"""
        with transaction.atomic():
            for item in self.items.filter(is_active=True):
                if item.pending_quantity > 0:
                    item.receive_item() # Receives pending amount
            
            # Update final status
            self.receive_order()

    def approve_order(self, user):
        """Approve the purchase order"""
        if self.status == 'pending_approval':
            self.status = 'approved'
            self.approved_by = user
            self.approved_date = timezone.now()
            self.save()

    @property
    def days_overdue(self):
        """Calculate days overdue for payment"""
        if self.payment_due_date and self.payment_status != 'paid':
            today = timezone.now().date()
            if today > self.payment_due_date:
                return (today - self.payment_due_date).days
        return 0

    @property
    def total_received_quantity(self):
        """Total quantity received across all items"""
        return sum(item.quantity_received for item in self.items.filter(is_active=True))

    @property
    def total_ordered_quantity(self):
        """Total quantity ordered across all items"""
        return sum(item.quantity_ordered for item in self.items.filter(is_active=True))


class PurchaseOrderItem(models.Model):
    """Individual items in a purchase order."""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items', verbose_name=_("Purchase Order"))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Product"))

    # Quantities
    quantity_ordered = models.PositiveIntegerField(_("Quantity Ordered"), validators=[MinValueValidator(1)])
    quantity_received = models.PositiveIntegerField(_("Quantity Received"), default=0, validators=[MinValueValidator(0)])
    quantity_rejected = models.PositiveIntegerField(_("Quantity Rejected"), default=0, validators=[MinValueValidator(0)])

    # Pricing
    unit_price = models.DecimalField(_("Unit Price"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_percent = models.DecimalField(_("Discount Percent"), max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Tracking
    received_date = models.DateTimeField(_("Received Date"), null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True, null=True)
    is_active = models.BooleanField(_("Active"), default=True, help_text=_("Whether this order item is active"))

    class Meta:
        verbose_name = _("Purchase Order Item")
        verbose_name_plural = _("Purchase Order Items")
        unique_together = ['purchase_order', 'product']

    def __str__(self):
        return f"{self.product.name} - {self.quantity_ordered} units"

    @property
    def line_total(self):
        """Calculate line total after discount"""
        if self.unit_price is None or self.quantity_ordered is None:
            return 0
        discount_amount = (self.unit_price * self.quantity_ordered) * (self.discount_percent / 100)
        return (self.unit_price * self.quantity_ordered) - discount_amount

    @property
    def is_fully_received(self):
        """Check if item is fully received"""
        return self.quantity_received >= self.quantity_ordered

    @property
    def pending_quantity(self):
        """Quantity still pending to be received"""
        return max(0, self.quantity_ordered - self.quantity_received)

    @property
    def acceptance_rate(self):
        """Calculate acceptance rate (received / ordered)"""
        if self.quantity_ordered > 0:
            return (self.quantity_received / self.quantity_ordered) * 100
        return 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update order totals
        if self.purchase_order:
            self.purchase_order.calculate_totals()

    def receive_item(self, quantity=None, received_date=None):
        """Receive quantity of this item and update inventory"""
        if quantity is None:
            quantity = self.pending_quantity
        elif quantity > self.pending_quantity:
            raise ValueError(_("Cannot receive more than pending quantity"))

        self.quantity_received += quantity
        if received_date:
            self.received_date = received_date
        elif not self.received_date:
            self.received_date = timezone.now()
        self.save()

        # Update product stock
        from apps.inventory.models import StockMovement
        StockMovement.objects.create(
            product=self.product,
            movement_type='IN',
            quantity=quantity,
            reason='Purchase',
            notes=f"PO-{self.purchase_order.order_number}"
        )
        
        # Update product cost price to latest purchase price
        if self.unit_price > 0:
            self.product.cost_price = self.unit_price
            self.product.save()


class PurchaseInvoice(models.Model):
    """Purchase invoice for tracking supplier invoices."""
    INVOICE_STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('sent', _('Sent')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
        ('cancelled', _('Cancelled')),
    ]

    invoice_number = models.CharField(_("Invoice Number"), max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='invoices', verbose_name=_("Purchase Order"))
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='invoices', verbose_name=_("Supplier"))

    invoice_date = models.DateField(_("Invoice Date"), default=timezone.now)
    due_date = models.DateField(_("Due Date"))
    status = models.CharField(_("Status"), max_length=20, choices=INVOICE_STATUS_CHOICES, default='draft')

    # Financial details
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(_("Total Amount"), max_digits=12, decimal_places=2, default=0)

    # Payment tracking
    amount_paid = models.DecimalField(_("Amount Paid"), max_digits=12, decimal_places=2, default=0)
    payment_date = models.DateField(_("Payment Date"), null=True, blank=True)

    notes = models.TextField(_("Notes"), blank=True, null=True)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Purchase Invoice")
        verbose_name_plural = _("Purchase Invoices")
        ordering = ['-invoice_date']

    def __str__(self):
        return f"INV-{self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        """Calculate remaining balance"""
        return self.total_amount - self.amount_paid

    @property
    def is_overdue(self):
        """Check if invoice is overdue"""
        return self.due_date < timezone.now().date() and self.status != 'paid'


class SupplierPerformance(models.Model):
    """Track supplier performance metrics."""
    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE, related_name='performance', verbose_name=_("Supplier"))

    # Performance metrics
    total_orders = models.PositiveIntegerField(_("Total Orders"), default=0)
    on_time_deliveries = models.PositiveIntegerField(_("On-Time Deliveries"), default=0)
    quality_rating = models.DecimalField(_("Quality Rating"), max_digits=3, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    average_delivery_days = models.PositiveIntegerField(_("Average Delivery Days"), default=0)

    # Financial metrics
    total_spent = models.DecimalField(_("Total Spent"), max_digits=12, decimal_places=2, default=0)
    average_order_value = models.DecimalField(_("Average Order Value"), max_digits=10, decimal_places=2, default=0)

    last_updated = models.DateTimeField(_("Last Updated"), auto_now=True)

    class Meta:
        verbose_name = _("Supplier Performance")
        verbose_name_plural = _("Supplier Performance")

    def __str__(self):
        return f"Performance - {self.supplier.name}"

    @property
    def on_time_delivery_rate(self):
        """Calculate on-time delivery rate"""
        if self.total_orders > 0:
            return (self.on_time_deliveries / self.total_orders) * 100
        return 0

    def update_metrics(self):
        """Update performance metrics based on purchase orders"""
        orders = self.supplier.purchase_orders.filter(status__in=['received', 'closed'])

        self.total_orders = orders.count()
        self.total_spent = orders.aggregate(total=Sum('total_amount'))['total'] or 0

        if self.total_orders > 0:
            self.average_order_value = self.total_spent / self.total_orders

        # Calculate delivery performance
        on_time_count = 0
        total_delivery_days = 0

        for order in orders:
            if order.expected_delivery_date and order.actual_delivery_date:
                delivery_days = (order.actual_delivery_date - order.expected_delivery_date).days
                total_delivery_days += delivery_days
                if delivery_days <= 0:  # On time or early
                    on_time_count += 1

        self.on_time_deliveries = on_time_count
        if orders.count() > 0:
            self.average_delivery_days = total_delivery_days // orders.count()

        self.save()
