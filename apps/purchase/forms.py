from django import forms
from django.forms import modelformset_factory
from .models import PurchaseOrder, PurchaseOrderItem, PurchaseInvoice
from apps.inventory.models import Product, Supplier


class PurchaseOrderForm(forms.ModelForm):
    """Form for creating and updating purchase orders."""
    order_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    expected_delivery_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    tax_rate = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        initial=15.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=False
    )
    shipping_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        initial=0.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=False
    )
    discount_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        initial=0.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        required=False
    )

    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'order_date', 'expected_delivery_date', 'status', 'payment_terms',
            'tax_rate', 'shipping_cost', 'discount_amount', 'priority',
            'notes', 'supplier_notes', 'terms_conditions'
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Net 30'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Internal notes'}),
            'supplier_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes for supplier'}),
            'terms_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Terms and conditions'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.all()


class PurchaseOrderItemForm(forms.ModelForm):
    """Form for purchase order items."""
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control item-product'}),
        required=True
    )
    quantity_ordered = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control item-quantity', 'min': '1'}),
        required=True
    )
    unit_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control item-price', 'step': '0.01'}),
        required=True
    )
    discount_percent = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control item-discount', 'step': '0.01'}),
        required=False
    )

    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity_ordered', 'unit_price', 'discount_percent']
        widgets = {
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# Formset for purchase order items
PurchaseOrderItemFormSet = modelformset_factory(
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=0,
    can_delete=True
)


class PurchaseOrderReceiveForm(forms.Form):
    """Form for receiving purchase order items."""
    actual_delivery_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )


class PurchaseOrderItemReceiveForm(forms.Form):
    """Form for receiving individual items."""
    item_id = forms.IntegerField(widget=forms.HiddenInput())
    receive_quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control receive-quantity'}),
        required=True
    )
    rejected_quantity = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control rejected-quantity'}),
        required=False
    )


class PurchaseInvoiceForm(forms.ModelForm):
    """Form for purchase invoices."""
    invoice_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )

    class Meta:
        model = PurchaseInvoice
        fields = [
            'purchase_order', 'invoice_date', 'due_date',
            'subtotal', 'tax_amount', 'total_amount', 'notes'
        ]
        widgets = {
            'purchase_order': forms.Select(attrs={'class': 'form-control'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tax_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PurchaseOrderFilterForm(forms.Form):
    """Form for filtering purchase orders."""
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + PurchaseOrder.ORDER_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        required=False,
        empty_label="All Suppliers",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    payment_status = forms.ChoiceField(
        choices=[('', 'All Payment Status')] + PurchaseOrder.PAYMENT_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    priority = forms.ChoiceField(
        choices=[('', 'All Priorities')] + PurchaseOrder._meta.get_field('priority').choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )