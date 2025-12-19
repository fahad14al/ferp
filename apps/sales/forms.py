from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Field
from .models import Customer, SalesOrder, SalesOrderItem


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter customer name'}),
            'phone': forms.TextInput(attrs={'placeholder': ''}),  # No placeholder as requested
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Street address'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='col-md-6'),
                Column('phone', css_class='col-md-6'),
            ),
            'address',
            Submit('submit', 'Save Customer', css_class='btn btn-primary')
        )


class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = [
            'customer', 'expected_delivery_date', 'status',
            'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_postal_code', 'shipping_country',
            'discount_amount', 'notes', 'customer_notes'
        ]
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'shipping_address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Shipping address'}),
            'shipping_city': forms.TextInput(attrs={'placeholder': 'City'}),
            'shipping_state': forms.TextInput(attrs={'placeholder': 'State/Province'}),
            'shipping_postal_code': forms.TextInput(attrs={'placeholder': 'Postal/ZIP code'}),
            'shipping_country': forms.TextInput(attrs={'placeholder': 'Country'}),
            'discount_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Internal notes'}),
            'customer_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes visible to customer'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('customer', css_class='col-md-6'),
                Column('expected_delivery_date', css_class='col-md-6'),
            ),
            Row(
                Column('status', css_class='col-md-6'),
                Column('discount_amount', css_class='col-md-6'),
            ),
            Row(
                Column('shipping_address', css_class='col-md-12'),
            ),
            Row(
                Column('shipping_city', css_class='col-md-4'),
                Column('shipping_state', css_class='col-md-4'),
                Column('shipping_postal_code', css_class='col-md-4'),
            ),
            'shipping_country',
            'notes',
            'customer_notes',
            Submit('submit', 'Save Sales Order', css_class='btn btn-primary')
        )


class SalesOrderItemForm(forms.ModelForm):
    class Meta:
        model = SalesOrderItem
        fields = ['product', 'quantity', 'unit_price', 'discount_percent']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'discount_percent': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('product', css_class='col-md-6'),
                Column('quantity', css_class='col-md-6'),
            ),
            Row(
                Column('unit_price', css_class='col-md-6'),
                Column('discount_percent', css_class='col-md-6'),
            ),
            Submit('submit', 'Add Item', css_class='btn btn-success')
        )

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')

        if product and quantity:
            if quantity > product.stock_quantity:
                raise forms.ValidationError(
                    f"Insufficient stock. Only {product.stock_quantity} units available."
                )

        return cleaned_data