from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q, Avg
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import timedelta
from apps.inventory.models import Product, Category, Supplier
from apps.sales.models import SalesOrder, Customer
from apps.purchase.models import PurchaseOrder, SupplierPerformance
from apps.account.models import Transaction, Account
from .models import PurchaseReport, SupplierPerformanceReport, InventoryTurnoverReport, SalesVsPurchaseAnalysis
from .forms import (
    PurchaseSummaryFilterForm, SupplierPerformanceFilterForm,
    InventoryTurnoverFilterForm, SalesVsPurchaseFilterForm,
    FinancialSummaryFilterForm
)
from .utils import (
    export_to_csv, export_to_excel, export_to_pdf,
    format_currency, prepare_chart_data, generate_color_palette
)


@login_required
def report_list(request):
    """List all available reports."""
    context = {
        'reports': [
            {
                'name': 'Purchase Summary',
                'description': 'Overview of purchase orders, suppliers, and spending',
                'url': 'purchase_summary',
            },
            {
                'name': 'Supplier Performance',
                'description': 'Supplier delivery times, quality ratings, and performance metrics',
                'url': 'supplier_performance',
            },
            {
                'name': 'Inventory Turnover',
                'description': 'Product turnover rates and inventory efficiency',
                'url': 'inventory_turnover',
            },
            {
                'name': 'Sales vs Purchase Analysis',
                'description': 'Comparison of sales and purchase performance',
                'url': 'sales_vs_purchase',
            },
            {
                'name': 'Financial Summary',
                'description': 'Revenue, expenses, and profit analysis',
                'url': 'financial_summary',
            },
        ]
    }
    return render(request, 'reports/report_list.html', context)


@login_required
def purchase_summary_report(request):
    """Purchase summary report with export capabilities."""
    form = PurchaseSummaryFilterForm(request.GET or None)
    
    # Date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export_format = request.GET.get('export_format', '')

    if not start_date:
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()

    # Purchase metrics
    orders = PurchaseOrder.objects.filter(
        order_date__gte=start_date,
        order_date__lte=end_date,
        is_active=True
    )
    
    # Apply additional filters
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        orders = orders.filter(supplier_id=supplier_id)
    
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)

    total_orders = orders.count()
    total_value = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    average_order_value = total_value / total_orders if total_orders > 0 else 0

    suppliers_count = orders.values('supplier').distinct().count()
    completed_orders = orders.filter(status='received').count()
    pending_orders = orders.exclude(status__in=['received', 'cancelled']).count()

    # Top suppliers by value
    top_suppliers = orders.values('supplier__name').annotate(
        total_value=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('-total_value')[:10]

    # Monthly trend
    monthly_data = []
    monthly_labels = []
    monthly_values = []
    current_date = start_date
    while current_date <= end_date:
        month_orders = orders.filter(order_date__year=current_date.year, order_date__month=current_date.month)
        month_value = month_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        month_label = current_date.strftime('%B %Y')
        
        monthly_data.append({
            'month': month_label,
            'orders': month_orders.count(),
            'value': month_value,
        })
        monthly_labels.append(month_label)
        monthly_values.append(float(month_value))
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    # Prepare chart data
    chart_data = prepare_chart_data(
        labels=monthly_labels,
        datasets=[{
            'label': 'Purchase Value',
            'data': monthly_values,
            'backgroundColor': 'rgba(78, 115, 223, 0.5)',
            'borderColor': 'rgba(78, 115, 223, 1)',
            'borderWidth': 2
        }]
    )

    context = {
        'form': form,
        'report_title': 'Purchase Summary Report',
        'start_date': start_date,
        'end_date': end_date,
        'total_orders': total_orders,
        'total_value': total_value,
        'average_order_value': average_order_value,
        'suppliers_count': suppliers_count,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
        'top_suppliers': top_suppliers,
        'monthly_data': monthly_data,
        'chart_data': chart_data,
    }
    
    # Handle export
    if export_format == 'csv':
        headers = ['Supplier', 'Orders', 'Total Value']
        data = [[s['supplier__name'], s['order_count'], s['total_value']] for s in top_suppliers]
        return export_to_csv(data, f'purchase_summary_{start_date}_{end_date}.csv', headers)
    
    elif export_format == 'excel':
        headers = ['Supplier', 'Orders', 'Total Value']
        data = [[s['supplier__name'], s['order_count'], float(s['total_value'])] for s in top_suppliers]
        return export_to_excel(data, f'purchase_summary_{start_date}_{end_date}.xlsx', headers)
    
    elif export_format == 'pdf':
        html_content = render_to_string('reports/purchase_summary_pdf.html', context)
        return export_to_pdf(html_content, f'purchase_summary_{start_date}_{end_date}.pdf')
    
    return render(request, 'reports/purchase_summary.html', context)


@login_required
def supplier_performance_report(request):
    """Supplier performance report."""
    suppliers = Supplier.objects.filter(is_active=True)

    supplier_data = []
    for supplier in suppliers:
        performance = supplier.performance
        orders = supplier.purchase_orders.filter(is_active=True)

        if orders.exists():
            supplier_data.append({
                'supplier': supplier,
                'total_orders': performance.total_orders if performance else orders.count(),
                'on_time_delivery_rate': performance.on_time_delivery_rate if performance else 0,
                'average_delivery_days': performance.average_delivery_days if performance else 0,
                'total_spent': performance.total_spent if performance else orders.aggregate(total=Sum('total_amount'))['total'] or 0,
                'quality_rating': performance.quality_rating if performance else 0,
            })

    context = {
        'report_title': 'Supplier Performance Report',
        'supplier_data': supplier_data,
    }
    return render(request, 'reports/supplier_performance.html', context)


@login_required
def inventory_turnover_report(request):
    """Inventory turnover report."""
    products = Product.objects.filter(is_active=True).select_related('category')

    product_data = []
    for product in products:
        # Calculate turnover (simplified - in reality would need time-based data)
        turnover = 0
        if product.stock_quantity > 0:
            # This is a simplified calculation - real turnover would use sales data over time
            turnover = 1  # Placeholder

        product_data.append({
            'product': product,
            'turnover_ratio': turnover,
            'stock_value': product.stock_quantity * product.cost_price,
        })

    context = {
        'report_title': 'Inventory Turnover Report',
        'product_data': product_data,
    }
    return render(request, 'reports/inventory_turnover.html', context)


@login_required
def sales_vs_purchase_report(request):
    """Sales vs Purchase analysis."""
    # Date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date:
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()

    # Sales data
    sales_orders = SalesOrder.objects.filter(
        order_date__gte=start_date,
        order_date__lte=end_date,
        is_active=True,
        status='delivered'
    )
    total_sales = sales_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    sales_count = sales_orders.count()

    # Purchase data
    purchase_orders = PurchaseOrder.objects.filter(
        order_date__gte=start_date,
        order_date__lte=end_date,
        is_active=True,
        status='received'
    )
    total_purchases = purchase_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    purchase_count = purchase_orders.count()

    # Profitability
    gross_margin = total_sales - total_purchases
    gross_margin_percentage = (gross_margin / total_sales * 100) if total_sales > 0 else 0

    context = {
        'report_title': 'Sales vs Purchase Analysis',
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': total_sales,
        'sales_count': sales_count,
        'total_purchases': total_purchases,
        'purchase_count': purchase_count,
        'gross_margin': gross_margin,
        'gross_margin_percentage': gross_margin_percentage,
    }
    return render(request, 'reports/sales_vs_purchase.html', context)


@login_required
def financial_summary_report(request):
    """Financial summary report."""
    # Date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date:
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()

    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()

    # Revenue transactions
    revenue_transactions = Transaction.objects.filter(
        is_active=True,
        account__account_type='revenue',
        transaction_date__gte=start_date,
        transaction_date__lte=end_date
    )
    total_revenue = revenue_transactions.aggregate(total=Sum('amount'))['total'] or 0

    # Expense transactions
    expense_transactions = Transaction.objects.filter(
        is_active=True,
        account__account_type='expense',
        transaction_date__gte=start_date,
        transaction_date__lte=end_date
    )
    total_expenses = expense_transactions.aggregate(total=Sum('amount'))['total'] or 0

    # Account balances
    asset_accounts = Account.objects.filter(account_type='asset', is_active=True)
    liability_accounts = Account.objects.filter(account_type='liability', is_active=True)
    equity_accounts = Account.objects.filter(account_type='equity', is_active=True)

    total_assets = sum(account.balance for account in asset_accounts)
    total_liabilities = sum(account.balance for account in liability_accounts)
    total_equity = sum(account.balance for account in equity_accounts)

    context = {
        'report_title': 'Financial Summary Report',
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_income': total_revenue - total_expenses,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
    }
    return render(request, 'reports/financial_summary.html', context)
