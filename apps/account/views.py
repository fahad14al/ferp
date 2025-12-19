
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.paginator import Paginator
from .forms import SignUpForm
from .models import Account, Transaction, Payment, Budget, TaxRate


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto-login after registration
            auth_login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('/')
    else:
        form = SignUpForm()

    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, 'You have been logged in.')
            return redirect('/')
        else:
            messages.error(request, 'Invalid username or password')

    return render(request, 'login.html')


def logout_view(request):
    auth_logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('/account/login/')


@login_required
def account_list(request):
    """List all accounts with filtering and search."""
    accounts = Account.objects.filter(is_active=True)

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        accounts = accounts.filter(
            Q(name__icontains=search_query) |
            Q(account_number__icontains=search_query)
        )

    # Account type filter
    account_type = request.GET.get('account_type')
    if account_type:
        accounts = accounts.filter(account_type=account_type)

    # Pagination
    paginator = Paginator(accounts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'accounts': page_obj,
        'account_types': Account.ACCOUNT_TYPE_CHOICES,
        'current_type': account_type,
    }
    return render(request, 'account/account_list.html', context)


@login_required
def account_detail(request, pk):
    """View account details with transactions."""
    account = Account.objects.get(pk=pk)
    transactions = account.transactions.filter(is_active=True).order_by('-transaction_date')[:50]

    context = {
        'account': account,
        'recent_transactions': transactions,
    }
    return render(request, 'account/account_detail.html', context)


@login_required
def transaction_list(request):
    """List all transactions with filtering."""
    transactions = Transaction.objects.filter(is_active=True).select_related('account', 'created_by')

    # Filters
    account_id = request.GET.get('account')
    transaction_type = request.GET.get('type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if account_id:
        transactions = transactions.filter(account_id=account_id)
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    if start_date:
        transactions = transactions.filter(transaction_date__gte=start_date)
    if end_date:
        transactions = transactions.filter(transaction_date__lte=end_date)

    transactions = transactions.order_by('-transaction_date', '-id')

    # Pagination
    paginator = Paginator(transactions, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    accounts = Account.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'transactions': page_obj,
        'accounts': accounts,
        'transaction_types': Transaction.TRANSACTION_TYPE_CHOICES,
    }
    return render(request, 'account/transaction_list.html', context)


@login_required
def payment_list(request):
    """List all payments."""
    payments = Payment.objects.filter(is_active=True).select_related('created_by').order_by('-payment_date')

    # Filters
    payment_type = request.GET.get('type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if payment_type:
        payments = payments.filter(payment_type=payment_type)
    if start_date:
        payments = payments.filter(payment_date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__lte=end_date)

    # Pagination
    paginator = Paginator(payments, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'payments': page_obj,
        'payment_types': Payment.PAYMENT_TYPE_CHOICES,
    }
    return render(request, 'account/payment_list.html', context)


@login_required
def budget_list(request):
    """List all budgets."""
    budgets = Budget.objects.filter(is_active=True).order_by('-year', '-month')

    # Filters
    year = request.GET.get('year')
    budget_type = request.GET.get('type')

    if year:
        budgets = budgets.filter(year=year)
    if budget_type:
        budgets = budgets.filter(budget_type=budget_type)

    context = {
        'budgets': budgets,
        'budget_types': Budget.BUDGET_TYPE_CHOICES,
        'years': range(timezone.now().year - 5, timezone.now().year + 6),
    }
    return render(request, 'account/budget_list.html', context)


@login_required
def tax_rate_list(request):
    """List all tax rates."""
    tax_rates = TaxRate.objects.filter(is_active=True).order_by('-effective_date')

    context = {
        'tax_rates': tax_rates,
    }
    return render(request, 'account/tax_rate_list.html', context)


@login_required
def accounting_dashboard(request):
    """Accounting dashboard with key financial metrics."""
    today = timezone.now().date()
    this_month = today.replace(day=1)
    last_month = (this_month - timezone.timedelta(days=1)).replace(day=1)

    # Account balances
    asset_accounts = Account.objects.filter(account_type='asset', is_active=True)
    liability_accounts = Account.objects.filter(account_type='liability', is_active=True)
    equity_accounts = Account.objects.filter(account_type='equity', is_active=True)
    revenue_accounts = Account.objects.filter(account_type='revenue', is_active=True)
    expense_accounts = Account.objects.filter(account_type='expense', is_active=True)

    total_assets = sum(account.balance for account in asset_accounts)
    total_liabilities = sum(account.balance for account in liability_accounts)
    total_equity = sum(account.balance for account in equity_accounts)
    total_revenue = sum(account.balance for account in revenue_accounts)
    total_expenses = sum(account.balance for account in expense_accounts)

    # Recent transactions
    recent_transactions = Transaction.objects.filter(is_active=True).select_related('account').order_by('-transaction_date')[:10]

    # Monthly comparison
    this_month_revenue = Transaction.objects.filter(
        is_active=True,
        account__account_type='revenue',
        transaction_date__gte=this_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    last_month_revenue = Transaction.objects.filter(
        is_active=True,
        account__account_type='revenue',
        transaction_date__gte=last_month,
        transaction_date__lt=this_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    this_month_expenses = Transaction.objects.filter(
        is_active=True,
        account__account_type='expense',
        transaction_date__gte=this_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    last_month_expenses = Transaction.objects.filter(
        is_active=True,
        account__account_type='expense',
        transaction_date__gte=last_month,
        transaction_date__lt=this_month
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_income': total_revenue - total_expenses,
        'recent_transactions': recent_transactions,
        'this_month_revenue': this_month_revenue,
        'last_month_revenue': last_month_revenue,
        'this_month_expenses': this_month_expenses,
        'last_month_expenses': last_month_expenses,
    }
    return render(request, 'account/dashboard.html', context)