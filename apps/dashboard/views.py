from django.shortcuts import render
from django.db.models import Sum, Count, F, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from apps.inventory.models import Product, Supplier, Category, StockMovement
from apps.sales.models import SalesOrder, SalesOrderItem, Customer
from apps.purchase.models import PurchaseOrder, PurchaseOrderItem, PurchaseInvoice, SupplierPerformance
from apps.account.models import Transaction, Payment, Budget
from apps.reports.models import DashboardMetric, PurchaseReport, SupplierPerformanceReport


@login_required
def index(request):
    """Enhanced dashboard view with comprehensive metrics from all apps."""
    today = timezone.now().date()
    this_month = today.replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)

    # Inventory metrics
    total_products = Product.objects.filter(is_active=True).count()
    low_stock_products = Product.objects.filter(is_active=True, stock_quantity__lte=F('reorder_level')).count()
    out_of_stock_products = Product.objects.filter(is_active=True, stock_quantity=0).count()
    total_inventory_value = Product.objects.filter(is_active=True).aggregate(
        total=Sum(F('stock_quantity') * F('cost_price'))
    )['total'] or 0

    # Supplier metrics
    total_suppliers = Supplier.objects.filter(is_active=True).count()
    active_suppliers = Supplier.objects.filter(
        is_active=True,
        purchase_orders__status__in=['confirmed', 'processing', 'received']
    ).distinct().count()

    # Sales metrics
    total_sales_orders = SalesOrder.objects.filter(is_active=True).count()
    pending_sales_orders = SalesOrder.objects.filter(
        is_active=True,
        status__in=['draft', 'confirmed', 'processing']
    ).count()
    delivered_sales_orders = SalesOrder.objects.filter(
        is_active=True,
        status='delivered'
    ).count()
    total_sales_revenue = SalesOrder.objects.filter(
        is_active=True,
        status='delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Monthly sales comparison
    this_month_sales = SalesOrder.objects.filter(
        is_active=True,
        status='delivered',
        order_date__gte=this_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    last_month_sales = SalesOrder.objects.filter(
        is_active=True,
        status='delivered',
        order_date__gte=last_month,
        order_date__lt=this_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Purchase metrics
    total_purchase_orders = PurchaseOrder.objects.filter(is_active=True).count()
    pending_purchase_orders = PurchaseOrder.objects.filter(
        is_active=True,
        status__in=['confirmed', 'processing', 'partially_received']
    ).count()
    received_purchase_orders = PurchaseOrder.objects.filter(
        is_active=True,
        status__in=['received', 'closed']
    ).count()
    total_purchase_value = PurchaseOrder.objects.filter(
        is_active=True,
        status__in=['received', 'closed']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Monthly purchase comparison
    this_month_purchases = PurchaseOrder.objects.filter(
        is_active=True,
        status__in=['received', 'closed'],
        order_date__gte=this_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Pending deliveries
    pending_deliveries = PurchaseOrderItem.objects.filter(
        purchase_order__is_active=True,
        purchase_order__status__in=['confirmed', 'processing', 'partially_received'],
        quantity_received__lt=F('quantity_ordered')
    ).aggregate(total=Sum(F('quantity_ordered') - F('quantity_received')))['total'] or 0

    # Financial metrics
    total_accounts_receivable = SalesOrder.objects.filter(
        is_active=True,
        status__in=['confirmed', 'processing', 'delivered'],
        payment_status__in=['unpaid', 'partially_paid', 'overdue']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    total_accounts_payable = PurchaseOrder.objects.filter(
        is_active=True,
        status__in=['confirmed', 'processing', 'received', 'partially_received'],
        payment_status__in=['unpaid', 'partially_paid', 'overdue']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Recent transactions
    recent_transactions = Transaction.objects.filter(
        is_active=True
    ).select_related('account').order_by('-transaction_date')[:10]

    # Top products by sales
    top_selling_products = SalesOrderItem.objects.filter(
        sales_order__is_active=True,
        sales_order__status='delivered'
    ).values('product__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('unit_price'))
    ).order_by('-total_revenue')[:5]

    # Top products by purchase value
    top_purchased_products = PurchaseOrderItem.objects.filter(
        purchase_order__is_active=True,
        purchase_order__status__in=['received', 'closed']
    ).values('product__name').annotate(
        total_quantity=Sum('quantity_ordered'),
        total_cost=Sum(F('quantity_ordered') * F('unit_price'))
    ).order_by('-total_cost')[:5]

    # Supplier performance
    supplier_performance = SupplierPerformance.objects.filter(
        supplier__is_active=True
    ).select_related('supplier').order_by('-total_spent')[:5]

    # Recent activities
    recent_purchase_orders = PurchaseOrder.objects.filter(
        is_active=True
    ).select_related('supplier').order_by('-order_date')[:5]

    recent_sales_orders = SalesOrder.objects.filter(
        is_active=True
    ).select_related('customer').order_by('-order_date')[:5]

    # Stock movements today
    today_stock_movements = StockMovement.objects.filter(
        date__date=today
    ).order_by('-date')[:10]

    # Budget utilization
    budgets = Budget.objects.filter(
        is_active=True,
        year=today.year
    ).annotate(
        utilization_percent=(F('spent_amount') / F('total_budget')) * 100
    ).order_by('-utilization_percent')[:5]

    # Calculate growth rates
    sales_growth = 0
    if last_month_sales > 0:
        sales_growth = ((this_month_sales - last_month_sales) / last_month_sales) * 100

    purchase_growth = 0
    if this_month_purchases > 0:
        # Compare with last month purchases
        last_month_purchases = PurchaseOrder.objects.filter(
            is_active=True,
            status__in=['received', 'closed'],
            order_date__gte=last_month,
            order_date__lt=this_month
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        if last_month_purchases > 0:
            purchase_growth = ((this_month_purchases - last_month_purchases) / last_month_purchases) * 100

    context = {
        # Inventory
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'total_inventory_value': total_inventory_value,

        # Suppliers
        'total_suppliers': total_suppliers,
        'active_suppliers': active_suppliers,

        # Sales
        'total_sales_orders': total_sales_orders,
        'pending_sales_orders': pending_sales_orders,
        'delivered_sales_orders': delivered_sales_orders,
        'total_sales_revenue': total_sales_revenue,
        'this_month_sales': this_month_sales,
        'sales_growth': sales_growth,

        # Purchases
        'total_purchase_orders': total_purchase_orders,
        'pending_purchase_orders': pending_purchase_orders,
        'received_purchase_orders': received_purchase_orders,
        'total_purchase_value': total_purchase_value,
        'this_month_purchases': this_month_purchases,
        'purchase_growth': purchase_growth,
        'pending_deliveries': pending_deliveries,

        # Financial
        'total_accounts_receivable': total_accounts_receivable,
        'total_accounts_payable': total_accounts_payable,

        # Recent data
        'recent_transactions': recent_transactions,
        'top_selling_products': top_selling_products,
        'top_purchased_products': top_purchased_products,
        'supplier_performance': supplier_performance,
        'recent_purchase_orders': recent_purchase_orders,
        'recent_sales_orders': recent_sales_orders,
        'today_stock_movements': today_stock_movements,
        'budgets': budgets,

        # Dates for context
        'today': today,
        'this_month': this_month,
    }

    return render(request, 'dashboard_index.html', context)


def dashboard_api(request):
    """API endpoint for real-time dashboard metrics."""
    from django.http import JsonResponse

    # Update dashboard metrics
    metrics = {}

    # Purchase orders today
    today_orders = PurchaseOrder.objects.filter(
        order_date=timezone.now().date(),
        is_active=True
    ).count()
    metrics['purchase_orders_today'] = {'value': today_orders, 'unit': 'count'}

    # Pending deliveries
    pending_qty = PurchaseOrderItem.objects.filter(
        purchase_order__is_active=True,
        purchase_order__status__in=['confirmed', 'processing', 'partially_received'],
        quantity_received__lt=F('quantity_ordered')
    ).aggregate(total=Sum(F('quantity_ordered') - F('quantity_received')))['total'] or 0
    metrics['pending_deliveries'] = {'value': pending_qty, 'unit': 'units'}

    # Low stock alerts
    low_stock = Product.objects.filter(
        is_active=True,
        stock_quantity__lte=F('reorder_level')
    ).count()
    metrics['low_stock_alerts'] = {'value': low_stock, 'unit': 'products'}

    # Monthly spending
    this_month = timezone.now().date().replace(day=1)
    monthly_spend = PurchaseOrder.objects.filter(
        is_active=True,
        status__in=['received', 'closed'],
        order_date__gte=this_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    metrics['monthly_spending'] = {'value': monthly_spend, 'unit': 'USD'}

    # Inventory value
    inventory_value = Product.objects.filter(is_active=True).aggregate(
        total=Sum(F('stock_quantity') * F('cost_price'))
    )['total'] or 0
    metrics['inventory_value'] = {'value': inventory_value, 'unit': 'USD'}

    # Sales revenue
    monthly_revenue = SalesOrder.objects.filter(
        is_active=True,
        status='delivered',
        order_date__gte=this_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    metrics['sales_revenue'] = {'value': monthly_revenue, 'unit': 'USD'}

    # Profit margin
    profit_margin = 0
    if monthly_revenue > 0 and monthly_spend > 0:
        profit_margin = ((monthly_revenue - monthly_spend) / monthly_revenue) * 100
    metrics['profit_margin'] = {'value': profit_margin, 'unit': '%'}

    # Update database metrics
    for metric_type, data in metrics.items():
        DashboardMetric.objects.update_or_create(
            metric_type=metric_type,
            defaults={
                'value': data['value'],
                'unit': data['unit']
            }
        )

    return JsonResponse(metrics)
