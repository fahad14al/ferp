from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User
from apps.purchase.models import PurchaseOrder, PurchaseInvoice
from apps.sales.models import SalesOrder
from apps.inventory.models import Supplier, Product


class Account(models.Model):
    """Chart of accounts for financial tracking."""
    ACCOUNT_TYPE_CHOICES = [
        ('asset', _('Asset')),
        ('liability', _('Liability')),
        ('equity', _('Equity')),
        ('revenue', _('Revenue')),
        ('expense', _('Expense')),
    ]

    account_number = models.CharField(_("Account Number"), max_length=20, unique=True)
    name = models.CharField(_("Account Name"), max_length=100)
    account_type = models.CharField(_("Account Type"), max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    description = models.TextField(_("Description"), blank=True)
    parent_account = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_accounts', verbose_name=_("Parent Account"))
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ['account_number']

    def __str__(self):
        return f"{self.account_number} - {self.name}"

    @property
    def balance(self):
        """Calculate current balance"""
        debits = self.transactions.filter(transaction_type='debit').aggregate(total=models.Sum('amount'))['total'] or 0
        credits = self.transactions.filter(transaction_type='credit').aggregate(total=models.Sum('amount'))['total'] or 0

        if self.account_type in ['asset', 'expense']:
            return debits - credits
        else:
            return credits - debits


class Transaction(models.Model):
    """Financial transactions."""
    TRANSACTION_TYPE_CHOICES = [
        ('debit', _('Debit')),
        ('credit', _('Credit')),
    ]

    transaction_date = models.DateField(_("Transaction Date"), default=timezone.now)
    description = models.CharField(_("Description"), max_length=255)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    transaction_type = models.CharField(_("Transaction Type"), max_length=10, choices=TRANSACTION_TYPE_CHOICES)

    # Related entities
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions', verbose_name=_("Account"))
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_("Purchase Order"))
    purchase_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_("Purchase Invoice"))
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name=_("Sales Order"))

    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_transactions', verbose_name=_("Created By"))
    reference_number = models.CharField(_("Reference Number"), max_length=50, blank=True, help_text=_("External reference number"))
    notes = models.TextField(_("Notes"), blank=True)

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        ordering = ['-transaction_date', '-id']

    def __str__(self):
        return f"{self.transaction_date} - {self.description} - {self.amount}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = f"TXN{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Payment records for purchases and sales."""
    PAYMENT_METHOD_CHOICES = [
        ('cash', _('Cash')),
        ('bank_transfer', _('Bank Transfer')),
        ('check', _('Check')),
        ('credit_card', _('Credit Card')),
        ('debit_card', _('Debit Card')),
        ('online_payment', _('Online Payment')),
    ]

    PAYMENT_TYPE_CHOICES = [
        ('purchase', _('Purchase Payment')),
        ('sales', _('Sales Receipt')),
        ('expense', _('Expense Payment')),
        ('other', _('Other')),
    ]

    payment_date = models.DateField(_("Payment Date"), default=timezone.now)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_method = models.CharField(_("Payment Method"), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_type = models.CharField(_("Payment Type"), max_length=20, choices=PAYMENT_TYPE_CHOICES)
    reference_number = models.CharField(_("Reference Number"), max_length=50, blank=True)

    # Related entities
    purchase_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments', verbose_name=_("Purchase Invoice"))
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments', verbose_name=_("Sales Order"))
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments', verbose_name=_("Supplier"))

    # Bank details
    bank_name = models.CharField(_("Bank Name"), max_length=100, blank=True)
    account_number = models.CharField(_("Account Number"), max_length=50, blank=True)
    check_number = models.CharField(_("Check Number"), max_length=50, blank=True)

    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payments', verbose_name=_("Created By"))
    notes = models.TextField(_("Notes"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.payment_date} - {self.amount} - {self.get_payment_type_display()}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = f"PMT{timezone.now().strftime('%Y%m%d%H%M%S')}"

        # Create corresponding transaction
        self.create_transaction()
        super().save(*args, **kwargs)

    def create_transaction(self):
        """Create accounting transaction for this payment"""
        if self.payment_type == 'purchase':
            # Debit expense/cash, credit accounts payable
            Transaction.objects.create(
                transaction_date=self.payment_date,
                description=f"Payment for {self.purchase_invoice.invoice_number if self.purchase_invoice else 'Purchase'}",
                amount=self.amount,
                transaction_type='debit',
                account=Account.objects.filter(account_type='expense').first(),  # Should be configured
                purchase_invoice=self.purchase_invoice,
                created_by=self.created_by,
                notes=self.notes
            )
        elif self.payment_type == 'sales':
            # Debit cash, credit revenue
            Transaction.objects.create(
                transaction_date=self.payment_date,
                description=f"Receipt from {self.sales_order.order_number if self.sales_order else 'Sales'}",
                amount=self.amount,
                transaction_type='credit',
                account=Account.objects.filter(account_type='revenue').first(),  # Should be configured
                sales_order=self.sales_order,
                created_by=self.created_by,
                notes=self.notes
            )


class Budget(models.Model):
    """Budget tracking for departments and categories."""
    BUDGET_TYPE_CHOICES = [
        ('annual', _('Annual')),
        ('quarterly', _('Quarterly')),
        ('monthly', _('Monthly')),
    ]

    name = models.CharField(_("Budget Name"), max_length=100)
    budget_type = models.CharField(_("Budget Type"), max_length=20, choices=BUDGET_TYPE_CHOICES, default='annual')
    year = models.PositiveIntegerField(_("Year"), default=timezone.now().year)
    quarter = models.PositiveIntegerField(_("Quarter"), null=True, blank=True, choices=[(1, 'Q1'), (2, 'Q2'), (3, 'Q3'), (4, 'Q4')])
    month = models.PositiveIntegerField(_("Month"), null=True, blank=True, choices=[(i, f"{i:02d}") for i in range(1, 13)])

    # Budget amounts
    total_budget = models.DecimalField(_("Total Budget"), max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    spent_amount = models.DecimalField(_("Spent Amount"), max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    # Categories
    category = models.CharField(_("Category"), max_length=100, blank=True, help_text=_("Budget category (e.g., Supplies, Equipment)"))
    department = models.CharField(_("Department"), max_length=100, blank=True)

    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_budgets', verbose_name=_("Created By"))
    notes = models.TextField(_("Notes"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Budget")
        verbose_name_plural = _("Budgets")
        ordering = ['-year', '-month']

    def __str__(self):
        period = f"{self.year}"
        if self.month:
            period += f"-{self.month:02d}"
        elif self.quarter:
            period += f"-Q{self.quarter}"
        return f"{self.name} - {period}"

    @property
    def remaining_budget(self):
        """Calculate remaining budget"""
        return self.total_budget - self.spent_amount

    @property
    def budget_utilization_percent(self):
        """Calculate budget utilization percentage"""
        if self.total_budget > 0:
            return (self.spent_amount / self.total_budget) * 100
        return 0

    def update_spent_amount(self):
        """Update spent amount based on related transactions"""
        # This would be implemented based on specific business rules
        # For now, it's a placeholder
        pass


class TaxRate(models.Model):
    """Tax rates for different categories."""
    TAX_TYPE_CHOICES = [
        ('vat', _('VAT')),
        ('sales_tax', _('Sales Tax')),
        ('income_tax', _('Income Tax')),
        ('other', _('Other')),
    ]

    name = models.CharField(_("Tax Name"), max_length=100)
    tax_type = models.CharField(_("Tax Type"), max_length=20, choices=TAX_TYPE_CHOICES)
    rate = models.DecimalField(_("Rate (%)"), max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField(_("Description"), blank=True)

    # Applicability
    applicable_to_purchases = models.BooleanField(_("Applicable to Purchases"), default=True)
    applicable_to_sales = models.BooleanField(_("Applicable to Sales"), default=True)

    # Validity period
    effective_date = models.DateField(_("Effective Date"), default=timezone.now)
    expiry_date = models.DateField(_("Expiry Date"), null=True, blank=True)

    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Tax Rate")
        verbose_name_plural = _("Tax Rates")
        ordering = ['-effective_date']

    def __str__(self):
        return f"{self.name} - {self.rate}%"

    @property
    def is_current(self):
        """Check if tax rate is currently effective"""
        today = timezone.now().date()
        return self.effective_date <= today and (not self.expiry_date or self.expiry_date >= today)

