from django import forms
from django.utils import timezone
from datetime import timedelta
from apps.inventory.models import Product, Category, Supplier


class ReportFilterForm(forms.Form):
    """Base form for report filtering"""
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        initial=lambda: timezone.now().date() - timedelta(days=30)
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        initial=timezone.now().date
    )
    
    export_format = forms.ChoiceField(
        choices=[
            ('', 'View in Browser'),
            ('pdf', 'Export as PDF'),
            ('excel', 'Export as Excel'),
            ('csv', 'Export as CSV'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class PurchaseSummaryFilterForm(ReportFilterForm):
    """Filter form for purchase summary report"""
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        required=False,
        empty_label="All Suppliers",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'All Statuses'),
            ('draft', 'Draft'),
            ('approved', 'Approved'),
            ('confirmed', 'Confirmed'),
            ('processing', 'Processing'),
            ('received', 'Received'),
            ('cancelled', 'Cancelled'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class SupplierPerformanceFilterForm(ReportFilterForm):
    """Filter form for supplier performance report"""
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        required=False,
        empty_label="All Suppliers",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    min_quality_rating = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=5,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Min Quality Rating'})
    )


class InventoryTurnoverFilterForm(ReportFilterForm):
    """Filter form for inventory turnover report"""
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        required=False,
        empty_label="All Products",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    low_stock_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class SalesVsPurchaseFilterForm(ReportFilterForm):
    """Filter form for sales vs purchase analysis"""
    period = forms.ChoiceField(
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        required=False,
        initial='monthly',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class FinancialSummaryFilterForm(ReportFilterForm):
    """Filter form for financial summary report"""
    account_type = forms.ChoiceField(
        choices=[
            ('', 'All Account Types'),
            ('asset', 'Assets'),
            ('liability', 'Liabilities'),
            ('equity', 'Equity'),
            ('revenue', 'Revenue'),
            ('expense', 'Expenses'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    include_inactive = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Include Inactive Accounts'
    )


class ReportScheduleForm(forms.Form):
    """Form for scheduling automated reports"""
    report_type = forms.ChoiceField(
        choices=[
            ('purchase_summary', 'Purchase Summary'),
            ('supplier_performance', 'Supplier Performance'),
            ('inventory_turnover', 'Inventory Turnover'),
            ('sales_vs_purchase', 'Sales vs Purchase Analysis'),
            ('financial_summary', 'Financial Summary'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    frequency = forms.ChoiceField(
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    email_recipients = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter email addresses, one per line'}),
        help_text='Enter email addresses to receive the report, one per line'
    )
    
    file_format = forms.ChoiceField(
        choices=[
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
            ('csv', 'CSV'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
