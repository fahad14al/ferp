from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.forms import modelformset_factory
from django.utils import timezone
from django.db.models import Sum, F, Q, Count
from django.http import JsonResponse
from .models import (
    PurchaseOrder, PurchaseOrderItem, PurchaseInvoice,
    SupplierPerformance
)
from .forms import (
    PurchaseOrderForm, PurchaseOrderItemForm, PurchaseOrderItemFormSet,
    PurchaseOrderReceiveForm, PurchaseOrderItemReceiveForm, PurchaseOrderFilterForm
)
from apps.inventory.models import Supplier, Product
from apps.account.models import Payment, Transaction, Account
from apps.reports.models import PurchaseReport, SupplierPerformanceReport


@login_required
def purchase_order_list(request):
    """List all purchase orders with advanced filtering and analytics."""
    orders = PurchaseOrder.objects.select_related('supplier', 'created_by', 'approved_by').filter(is_active=True)

    # Use filter form
    filter_form = PurchaseOrderFilterForm(request.GET)
    if filter_form.is_valid():
        status = filter_form.cleaned_data.get('status')
        supplier_id = filter_form.cleaned_data.get('supplier')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        payment_status = filter_form.cleaned_data.get('payment_status')
        priority = filter_form.cleaned_data.get('priority')

        if status:
            orders = orders.filter(status=status)
        if supplier_id:
            orders = orders.filter(supplier_id=supplier_id)
        if date_from:
            orders = orders.filter(order_date__gte=date_from)
        if date_to:
            orders = orders.filter(order_date__lte=date_to)
        if payment_status:
            orders = orders.filter(payment_status=payment_status)
        if priority:
            orders = orders.filter(priority=priority)

    # Pagination and ordering
    orders = orders.order_by('-order_date')

    # Analytics
    total_orders = orders.count()
    total_value = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    pending_orders = orders.filter(status__in=['confirmed', 'processing', 'partially_received']).count()
    today = timezone.now().date()
    overdue_orders = orders.filter(
        payment_status__in=['unpaid', 'partially_paid', 'overdue'],
        payment_due_date__lt=today
    ).count()

    suppliers = Supplier.objects.filter(is_active=True)

    context = {
        'orders': orders,
        'suppliers': suppliers,
        'filter_form': filter_form,
        'analytics': {
            'total_orders': total_orders,
            'total_value': total_value,
            'pending_orders': pending_orders,
            'overdue_orders': overdue_orders,
        }
    }
    return render(request, 'purchase/purchase_order_list.html', context)


@login_required
def purchase_order_detail(request, pk):
    """Display comprehensive purchase order details."""
    order = get_object_or_404(
        PurchaseOrder.objects.select_related('supplier', 'created_by', 'approved_by'),
        pk=pk
    )
    items = order.items.select_related('product').filter(is_active=True)

    # Related data
    invoices = order.invoices.filter(is_active=True)
    payments = Payment.objects.filter(purchase_invoice__in=invoices, is_active=True)
    transactions = Transaction.objects.filter(
        Q(purchase_order=order) | Q(purchase_invoice__in=invoices),
        is_active=True
    ).select_related('account')

    # Analytics
    total_received = sum(item.quantity_received for item in items)
    total_ordered = sum(item.quantity_ordered for item in items)
    completion_rate = (total_received / total_ordered * 100) if total_ordered > 0 else 0

    context = {
        'order': order,
        'items': items,
        'invoices': invoices,
        'payments': payments,
        'transactions': transactions,
        'analytics': {
            'completion_rate': completion_rate,
            'total_received': total_received,
            'total_ordered': total_ordered,
            'pending_quantity': total_ordered - total_received,
        }
    }
    return render(request, 'purchase/purchase_order_detail.html', context)


@login_required
def purchase_order_create(request):
    """Create a new purchase order with enhanced validation."""
    if request.method == 'POST':
        order_form = PurchaseOrderForm(request.POST)
        item_formset = PurchaseOrderItemFormSet(request.POST, queryset=PurchaseOrderItem.objects.none())

        if order_form.is_valid() and item_formset.is_valid():
            try:
                with transaction.atomic():
                    order = order_form.save(commit=False)
                    order.created_by = request.user
                    order.save()

                    # Save items
                    items = item_formset.save(commit=False)
                    for item in items:
                        item.purchase_order = order
                        item.save()

                    if not items:
                        raise ValueError("At least one item is required")

                    # Calculate totals
                    order.calculate_totals()

                    # Trigger stock update if created as 'received'
                    if order.status == 'received':
                        order.complete_order()
                        messages.success(request, f'Purchase order {order.order_number} created and inventory updated.')
                    else:
                        messages.success(request, f'Purchase order {order.order_number} created successfully! You can add another.')
                        
                    return redirect('purchase:purchase_order_create')

            except Exception as e:
                messages.error(request, f'Error creating purchase order: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        order_form = PurchaseOrderForm()
        item_formset = PurchaseOrderItemFormSet(queryset=PurchaseOrderItem.objects.none())

    context = {
        'order_form': order_form,
        'item_formset': item_formset,
        'products': Product.objects.filter(is_active=True),
    }
    return render(request, 'purchase/purchase_order_form.html', context)


@login_required
def purchase_order_update(request, pk):
    """Update an existing purchase order."""
    order = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == 'POST':
        order_form = PurchaseOrderForm(request.POST, instance=order)
        item_formset = PurchaseOrderItemFormSet(request.POST, queryset=order.items.filter(is_active=True))

        if order_form.is_valid() and item_formset.is_valid():
            try:
                with transaction.atomic():
                    # Capture original status to detect changes
                    original_status = PurchaseOrder.objects.get(pk=pk).status
                    
                    order = order_form.save()

                    # Delete removed items
                    for form in item_formset.deleted_forms:
                        if form.instance.pk:
                            form.instance.is_active = False
                            form.instance.save()

                    # Save updated/new items
                    items = item_formset.save(commit=False)
                    for item in items:
                        item.purchase_order = order
                        item.save()

                    # Recalculate totals
                    order.calculate_totals()
                    
                    # Force completion (stock update) if status is 'received'
                    # We do this regardless of original status to allow "retry" if previous stock update failed
                    if order.status == 'received':
                        order.complete_order()
                        messages.success(request, f'Purchase order {order.order_number} marked as received and inventory updated.')
                    else:
                        messages.success(request, f'Purchase order {order.order_number} updated successfully.')

                    return redirect('purchase:purchase_order_detail', pk=order.pk)

            except Exception as e:
                messages.error(request, f'Error updating purchase order: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        order_form = PurchaseOrderForm(instance=order)
        item_formset = PurchaseOrderItemFormSet(queryset=order.items.filter(is_active=True))

    context = {
        'order': order,
        'order_form': order_form,
        'item_formset': item_formset,
        'products': Product.objects.filter(is_active=True),
    }
    return render(request, 'purchase/purchase_order_form.html', context)


@login_required
def purchase_order_delete(request, pk):
    """Delete a purchase order."""
    order = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == 'POST':
        order_number = order.order_number
        order.is_active = False
        order.save()  # Soft delete
        messages.success(request, f'Purchase order {order_number} deleted successfully.')
        return redirect('purchase:purchase_order_list')

    context = {
        'order': order,
    }
    return render(request, 'purchase/purchase_order_confirm_delete.html', context)


@login_required
def purchase_order_receive(request, pk):
    """Receive items for a purchase order with enhanced tracking."""
    order = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == 'POST':
        receive_form = PurchaseOrderReceiveForm(request.POST)

        if receive_form.is_valid():
            try:
                with transaction.atomic():
                    # Update order delivery date
                    if receive_form.cleaned_data.get('actual_delivery_date'):
                        order.actual_delivery_date = receive_form.cleaned_data['actual_delivery_date']
                        order.save()

                    # Handle receiving quantities from POST data
                    item_ids = request.POST.getlist('item_id[]')
                    receive_quantities = request.POST.getlist('receive_quantity[]')
                    rejected_quantities = request.POST.getlist('rejected_quantity[]')

                    for i, item_id in enumerate(item_ids):
                        if item_id and receive_quantities[i]:
                            item = get_object_or_404(PurchaseOrderItem, pk=item_id, purchase_order=order)
                            quantity = int(receive_quantities[i])
                            rejected = int(rejected_quantities[i]) if rejected_quantities[i] else 0

                            item.quantity_rejected = rejected
                            item.receive_item(quantity)

                    # Update order status
                    order.receive_order()

                    # Update supplier performance
                    performance, created = SupplierPerformance.objects.get_or_create(supplier=order.supplier)
                    performance.update_metrics()

                    messages.success(request, f'Items received for purchase order {order.order_number}.')
                    return redirect('purchase:purchase_order_detail', pk=order.pk)

            except Exception as e:
                messages.error(request, f'Error receiving items: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        receive_form = PurchaseOrderReceiveForm()

    # GET request - show receive form
    items = order.items.select_related('product').filter(
        is_active=True,
        quantity_received__lt=F('quantity_ordered')
    )

    context = {
        'order': order,
        'items': items,
        'receive_form': receive_form,
    }
    return render(request, 'purchase/purchase_order_receive.html', context)


@login_required
def purchase_order_approve(request, pk):
    """Approve a purchase order."""
    order = get_object_or_404(PurchaseOrder, pk=pk)

    if order.status == 'pending_approval':
        order.approve_order(request.user)
        messages.success(request, f'Purchase order {order.order_number} approved successfully.')
    else:
        messages.error(request, 'Purchase order is not pending approval.')

    return redirect('purchase:purchase_order_detail', pk=order.pk)


@login_required
def supplier_performance(request):
    """Display supplier performance metrics."""
    performances = SupplierPerformance.objects.select_related('supplier').filter(
        supplier__is_active=True
    ).order_by('-total_spent')

    # Generate reports if needed
    for performance in performances:
        if performance.last_updated.date() < timezone.now().date():
            performance.update_metrics()

    context = {
        'performances': performances,
    }
    return render(request, 'purchase/supplier_performance.html', context)


@login_required
def purchase_reports(request):
    """Purchase analytics and reporting dashboard."""
    # Date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if not date_from:
        date_from = timezone.now().date().replace(day=1)  # First day of current month
    else:
        date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()

    if not date_to:
        date_to = timezone.now().date()
    else:
        date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()

    # Purchase analytics
    orders = PurchaseOrder.objects.filter(
        is_active=True,
        order_date__gte=date_from,
        order_date__lte=date_to
    )

    total_orders = orders.count()
    total_value = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    avg_order_value = total_value / total_orders if total_orders > 0 else 0

    # Status breakdown
    status_breakdown = orders.values('status').annotate(
        count=Count('id'),
        total_value=Sum('total_amount')
    ).order_by('status')

    # Top suppliers
    top_suppliers = orders.values('supplier__name').annotate(
        order_count=Count('id'),
        total_value=Sum('total_amount')
    ).order_by('-total_value')[:10]

    # Top products
    top_products = PurchaseOrderItem.objects.filter(
        purchase_order__in=orders,
        is_active=True
    ).values('product__name').annotate(
        total_quantity=Sum('quantity_ordered'),
        total_value=Sum(F('quantity_ordered') * F('unit_price'))
    ).order_by('-total_value')[:10]

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'analytics': {
            'total_orders': total_orders,
            'total_value': total_value,
            'avg_order_value': avg_order_value,
        },
        'status_breakdown': status_breakdown,
        'top_suppliers': top_suppliers,
        'top_products': top_products,
    }
    return render(request, 'purchase/purchase_reports.html', context)


@login_required
def supplier_list(request):
    """List all suppliers with performance metrics."""
    suppliers = Supplier.objects.filter(is_active=True).prefetch_related('performance')

    # Ensure performance data is up to date
    for supplier in suppliers:
        performance, created = SupplierPerformance.objects.get_or_create(supplier=supplier)
        if performance.last_updated.date() < timezone.now().date():
            performance.update_metrics()

    context = {
        'suppliers': suppliers,
    }
    return render(request, 'purchase/supplier_list.html', context)


@login_required
def purchase_order_api(request):
    """API endpoint for purchase order operations."""
    if request.method == 'GET':
        action = request.GET.get('action')

        if action == 'get_product_price':
            product_id = request.GET.get('product_id')
            if product_id:
                try:
                    product = Product.objects.get(pk=product_id, is_active=True)
                    return JsonResponse({
                        'success': True,
                        'cost_price': float(product.cost_price),
                        'price': float(product.price),
                    })
                except Product.DoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Product not found'})

    return JsonResponse({'success': False, 'error': 'Invalid request'})
