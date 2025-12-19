from django.urls import path
from . import views

app_name = 'account'

urlpatterns = [
    # Authentication
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Dashboard
    path("", views.accounting_dashboard, name="dashboard"),

    # Accounts
    path("accounts/", views.account_list, name="account_list"),
    path("accounts/<int:pk>/", views.account_detail, name="account_detail"),

    # Transactions
    path("transactions/", views.transaction_list, name="transaction_list"),

    # Payments
    path("payments/", views.payment_list, name="payment_list"),

    # Budgets
    path("budgets/", views.budget_list, name="budget_list"),

    # Tax Rates
    path("tax-rates/", views.tax_rate_list, name="tax_rate_list"),
]