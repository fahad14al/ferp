from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import Account, Transaction, Payment, Budget, TaxRate


class SignUpForm(UserCreationForm):
    """
    Extended user registration form that includes additional fields
    not present in the default UserCreationForm.
    """
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email address'),
            'autocomplete': 'email'
        }),
        help_text=_('Required. A valid email address.')
    )
    
    first_name = forms.CharField(
        required=True,
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('First name')
        }),
        help_text=_('Required. 30 characters or fewer.')
    )
    
    last_name = forms.CharField(
        required=True,
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Last name')
        }),
        help_text=_('Required. 30 characters or fewer.')
    )
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Username'),
            'autocomplete': 'username'
        }),
        help_text=_(
            'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        )
    )
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Password'),
            'autocomplete': 'new-password'
        }),
        help_text=_(
            'Your password must contain at least 8 characters.'
        )
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm password'),
            'autocomplete': 'new-password'
        }),
        help_text=_('Enter the same password as before, for verification.')
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "password1", "password2"]
    
    def __init__(self, *args, **kwargs):
        """
        Initialize form with custom settings.
        """
        super().__init__(*args, **kwargs)
        # Set required attribute for all fields except those explicitly set to required=False
        for field_name in self.fields:
            if field_name not in ['email', 'first_name', 'last_name']:
                # These are already set in field definitions above
                continue
            self.fields[field_name].required = True
    
    def clean_email(self):
        """
        Validate that the email is unique across all users.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                _('A user with that email already exists.'),
                code='duplicate_email'
            )
        return email
    
    def clean(self):
        """
        Add additional form-level validation if needed.
        """
        cleaned_data = super().clean()
        
        # Example: Ensure first and last name are different (remove if not needed)
        first_name = cleaned_data.get('first_name', '').strip().lower()
        last_name = cleaned_data.get('last_name', '').strip().lower()
        
        if first_name and last_name and first_name == last_name:
            self.add_error(
                'last_name',
                _('First name and last name should be different.')
            )
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Save the user instance with additional fields.
        
        Args:
            commit (bool): Whether to commit the user to the database immediately
            
        Returns:
            User: The created user instance
        """
        user = super().save(commit=False)
        
        # Ensure email is saved (handled by clean_email, but explicit here)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        # Set the user as inactive initially if email verification is required
        # user.is_active = False
        
        if commit:
            user.save()
            # If using signals or additional profile creation, it could be triggered here
            # create_user_profile.send(sender=self.__class__, user=user)
        
        return user


class AccountForm(forms.ModelForm):
    """Form for creating and updating accounts."""
    class Meta:
        model = Account
        fields = ['account_number', 'name', 'account_type', 'description', 'parent_account', 'is_active']
        widgets = {
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 1001'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account name'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'parent_account': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TransactionForm(forms.ModelForm):
    """Form for creating transactions."""
    transaction_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )

    class Meta:
        model = Transaction
        fields = ['transaction_date', 'description', 'amount', 'transaction_type', 'account', 'reference_number', 'notes']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction description'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'}),
        }


class PaymentForm(forms.ModelForm):
    """Form for creating payments."""
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )

    class Meta:
        model = Payment
        fields = ['payment_date', 'amount', 'payment_method', 'payment_type', 'reference_number', 'bank_name', 'account_number', 'check_number', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'payment_type': forms.Select(attrs={'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reference number'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Bank name'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Account number'}),
            'check_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Check number'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes'}),
        }


class BudgetForm(forms.ModelForm):
    """Form for creating budgets."""
    class Meta:
        model = Budget
        fields = ['name', 'budget_type', 'year', 'quarter', 'month', 'total_budget', 'category', 'department', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Budget name'}),
            'budget_type': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '2020', 'max': '2030'}),
            'quarter': forms.Select(attrs={'class': 'form-control'}),
            'month': forms.Select(attrs={'class': 'form-control'}),
            'total_budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Budget category'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes'}),
        }


class TaxRateForm(forms.ModelForm):
    """Form for creating tax rates."""
    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=True
    )
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    class Meta:
        model = TaxRate
        fields = ['name', 'tax_type', 'rate', 'description', 'applicable_to_purchases', 'applicable_to_sales', 'effective_date', 'expiry_date']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tax name'}),
            'tax_type': forms.Select(attrs={'class': 'form-control'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
            'applicable_to_purchases': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'applicable_to_sales': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }