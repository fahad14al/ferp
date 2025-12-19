from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
import json
from .models import Customer, SalesOrder, SalesOrderItem, SalesInvoice
from .forms import CustomerForm, SalesOrderForm, SalesOrderItemForm


@login_required
def customer_list(request):
    """List all customers"""
    customers = Customer.objects.filter(is_active=True).order_by('name')
    low_credit_customers = customers.filter(credit_limit__gt=0)

    context = {
        'customers': customers,
        'low_credit_count': low_credit_customers.count(),
    }
    return render(request, 'sales/customer_list.html', context)


@login_required
def customer_detail(request, pk):
    """View customer details and their sales orders"""
    customer = get_object_or_404(Customer, pk=pk)
    sales_orders = customer.sales_orders.filter(is_active=True).order_by('-order_date')[:10]

    context = {
        'customer': customer,
        'recent_orders': sales_orders,
    }
    return render(request, 'sales/customer_detail.html', context)


@login_required
def customer_create(request):
    """Create a new customer"""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f'Customer "{customer.name}" created successfully! You can add another.')
            return redirect('sales:customer_create')
    else:
        form = CustomerForm()

    context = {
        'form': form,
        'title': 'Add New Customer',
    }
    return render(request, 'sales/customer_form.html', context)


@login_required
def sales_order_list(request):
    """List all sales orders"""
    sales_orders = SalesOrder.objects.filter(is_active=True).select_related('customer').order_by('-order_date')

    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        sales_orders = sales_orders.filter(status=status_filter)

    context = {
        'sales_orders': sales_orders,
        'status_choices': SalesOrder.ORDER_STATUS_CHOICES,
        'current_status': status_filter,
    }
    return render(request, 'sales/sales_order_list.html', context)


@login_required
def sales_order_detail(request, pk):
    """View sales order details"""
    sales_order = get_object_or_404(
        SalesOrder.objects.select_related('customer'),
        pk=pk
    )
    items = sales_order.items.select_related('product').all()

    context = {
        'sales_order': sales_order,
        'items': items,
    }
    return render(request, 'sales/sales_order_detail.html', context)


@login_required
def sales_order_create(request):
    """Create a new sales order"""
    if request.method == 'POST':
        form = SalesOrderForm(request.POST)
        if form.is_valid():
            sales_order = form.save()
            messages.success(request, f'Sales order {sales_order.order_number} created successfully! You can add another.')
            return redirect('sales:sales_order_create')
    else:
        form = SalesOrderForm()

    context = {
        'form': form,
        'title': 'Create Sales Order',
    }
    return render(request, 'sales/sales_order_form.html', context)


@login_required
def sales_order_add_item(request, order_pk):
    """Add an item to a sales order"""
    sales_order = get_object_or_404(SalesOrder, pk=order_pk)

    if request.method == 'POST':
        form = SalesOrderItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.sales_order = sales_order
            item.save()
            messages.success(request, f'Item "{item.product.name}" added to order.')
            return redirect('sales:sales_order_detail', pk=sales_order.pk)
    else:
        form = SalesOrderItemForm()

    context = {
        'form': form,
        'sales_order': sales_order,
        'title': f'Add Item to {sales_order.order_number}',
    }
    return render(request, 'sales/sales_order_item_form.html', context)


@login_required
def sales_order_update_status(request, pk):
    """Update sales order status"""
    if request.method == 'POST':
        sales_order = get_object_or_404(SalesOrder, pk=pk)
        new_status = request.POST.get('status')

        if new_status in dict(SalesOrder.ORDER_STATUS_CHOICES):
            sales_order.status = new_status
            sales_order.save()
            messages.success(request, f'Order status updated to {new_status}.')

            # If order is confirmed, reduce inventory
            if new_status == 'confirmed':
                with transaction.atomic():
                    for item in sales_order.items.all():
                        product = item.product
                        if product.stock_quantity >= item.quantity:
                            product.stock_quantity -= item.quantity
                            product.save()
                            
                            # Log stock movement
                            from apps.inventory.models import StockMovement
                            StockMovement.objects.create(
                                product=product,
                                movement_type='OUT',
                                quantity=item.quantity,
                                reason='Sale',
                                notes=f"SO-{sales_order.order_number}"
                            )
                        else:
                            messages.warning(
                                request,
                                f'Insufficient stock for {product.name}. Order may need adjustment.'
                            )

        return redirect('sales:sales_order_detail', pk=pk)

    return redirect('sales:sales_order_list')


@login_required
def pos(request):
    """Point of Sale interface for quick sales"""
    from apps.inventory.models import Product, StockMovement

    # Get all active products for POS
    products = Product.objects.filter(is_active=True).order_by('name')

    # Handle adding items to cart (session-based)
    if request.method == 'POST':
        if 'add_product' in request.POST:
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1))

            try:
                product = Product.objects.get(pk=product_id, is_active=True)
                if product.stock_quantity >= quantity:
                    cart = request.session.get('pos_cart', {})
                    key = str(product_id)

                    if key in cart:
                        cart[key]['quantity'] += quantity
                    else:
                        cart[key] = {
                            'id': product.id,
                            'name': product.name,
                            'sku': product.sku,
                            'price': str(product.price),
                            'quantity': quantity
                        }

                    request.session['pos_cart'] = cart
                    messages.success(request, f'Added {quantity} x {product.name} to cart')
                else:
                    messages.error(request, f'Insufficient stock for {product.name}')
            except Product.DoesNotExist:
                messages.error(request, 'Product not found')

        elif 'remove_item' in request.POST:
            product_id = request.POST.get('product_id')
            cart = request.session.get('pos_cart', {})
            if product_id in cart:
                del cart[product_id]
                request.session['pos_cart'] = cart
                messages.success(request, 'Item removed from cart')

        elif 'clear_cart' in request.POST:
            request.session['pos_cart'] = {}
            messages.success(request, 'Cart cleared')

        elif 'complete_sale' in request.POST:
            cart = request.session.get('pos_cart', {})
            if not cart:
                messages.error(request, 'Cart is empty')
                return redirect('sales:pos')

            # Get form data
            customer_name = request.POST.get('customer_name', 'Walk-in Customer').strip()
            customer_phone = request.POST.get('customer_phone', '').strip()
            customer_address = request.POST.get('customer_address', '').strip()
            payment_method = request.POST.get('payment_method', 'cash')
            
            # Create sales order
            with transaction.atomic():
                # Resolve Customer
                customer = None
                
                # Try by Phone
                if customer_phone:
                    customer = Customer.objects.filter(phone=customer_phone).first()
                
                # Try by Name if not found and not Walk-in
                if not customer and customer_name and customer_name.lower() != 'walk-in customer':
                     customer = Customer.objects.filter(name=customer_name).first()

                # Create if not found
                if not customer:
                    # If it's just "Walk-in Customer" or empty, get/create the default
                    if not customer_name or customer_name.lower() == 'walk-in customer':
                         customer, created = Customer.objects.get_or_create(
                            name='Walk-in Customer',
                            email='walkin@temp.com',
                            defaults={'is_active': True}
                        )
                    else:
                        # Create new named customer
                        customer = Customer.objects.create(
                            name=customer_name,
                            phone=customer_phone,
                            address=customer_address,
                            is_active=True
                        )

                # Create sales order
                sales_order = SalesOrder.objects.create(
                    customer=customer,
                    status='confirmed',
                    notes=f'POS Sale - Payment: {payment_method}',
                    payment_method=payment_method,
                    shipping_address=customer.address or "",
                    shipping_city=customer.city or "",
                    shipping_state=customer.state or "",
                )

                total_amount = 0
                # Add items to order
                for item_data in cart.values():
                    product = Product.objects.select_for_update().get(pk=item_data['id'])
                    quantity = item_data['quantity']
                    unit_price = float(item_data['price'])

                    if product.stock_quantity < quantity:
                         messages.error(request, f"Insufficient stock for {product.name}")
                         return redirect('sales:pos') # Transaction rolls back

                    SalesOrderItem.objects.create(
                        sales_order=sales_order,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price
                    )

                    # Update inventory
                    product.stock_quantity -= quantity
                    product.save()

                    # Log stock movement
                    StockMovement.objects.create(
                        product=product,
                        movement_type='OUT',
                        quantity=quantity,
                        reason='POS Sale',
                        notes=f"SO-{sales_order.order_number}"
                    )

                    total_amount += unit_price * quantity

                # Update order totals
                from apps.dashboard.models import GeneralSettings
                settings = GeneralSettings.get_settings()
                tax_multiplier = float(settings.tax_percent) / 100.0

                sales_order.subtotal = total_amount
                sales_order.tax_amount = total_amount * tax_multiplier
                sales_order.total_amount = sales_order.subtotal + sales_order.tax_amount
                sales_order.save()

                # Create Invoice
                SalesInvoice.objects.create(
                    sales_order=sales_order,
                    amount_due=sales_order.total_amount,
                    amount_paid=sales_order.total_amount,
                    status='paid'
                )

                # Clear cart
                request.session['pos_cart'] = {}

                messages.success(request, f'Sale completed! Order #{sales_order.order_number}')
                return redirect('sales:sales_order_detail', pk=sales_order.pk)

        elif 'scan_barcode' in request.POST:
            barcode = request.POST.get('barcode', '').strip()
            if barcode:
                try:
                    product = Product.objects.get(sku=barcode, is_active=True)
                    if product.stock_quantity >= 1:
                        cart = request.session.get('pos_cart', {})
                        key = str(product.id)
                        
                        if key in cart:
                            # Check if adding one more exceeds stock
                            if cart[key]['quantity'] + 1 <= product.stock_quantity:
                                cart[key]['quantity'] += 1
                                messages.success(request, f'Added {product.name}')
                            else:
                                messages.error(request, f'Insufficient stock for {product.name}')
                        else:
                            cart[key] = {
                                'id': product.id,
                                'name': product.name,
                                'sku': product.sku,
                                'price': str(product.price),
                                'quantity': 1
                            }
                            messages.success(request, f'Added {product.name}')
                        
                        request.session['pos_cart'] = cart
                    else:
                        messages.error(request, f'Insufficient stock for {product.name}')
                except Product.DoesNotExist:
                    messages.error(request, f'Product not found: {barcode}')
            
            return redirect('sales:pos')

    # Calculate cart totals
    cart = request.session.get('pos_cart', {})
    cart_items = []
    subtotal = 0

    for item_data in cart.values():
        quantity = item_data['quantity']
        price = float(item_data['price'])
        line_total = quantity * price
        subtotal += line_total

        cart_items.append({
            'id': item_data['id'],
            'name': item_data['name'],
            'sku': item_data['sku'],
            'price': price,
            'quantity': quantity,
            'line_total': line_total
        })

    from apps.dashboard.models import GeneralSettings
    settings = GeneralSettings.get_settings()
    tax_percent = float(settings.tax_percent)
    tax_multiplier = tax_percent / 100.0

    tax_amount = subtotal * tax_multiplier
    total_amount = subtotal + tax_amount

    context = {
        'products': products,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'total_amount': total_amount,
        'tax_percent': tax_percent,
    }

    return render(request, 'sales/pos.html', context)


# API VIEWS FOR POS SYSTEM

@login_required
@require_GET
def api_scan_barcode(request):
    """API endpoint to scan barcode (SKU)"""
    barcode = request.GET.get('barcode', '').strip()
    if not barcode:
        return JsonResponse({'error': 'No barcode provided'}, status=400)

    from apps.inventory.models import Product
    try:
        product = Product.objects.get(sku=barcode, is_active=True)
        return JsonResponse({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'price': str(product.price),
            'stock_quantity': product.stock_quantity
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': f'Product not found for barcode: {barcode}'}, status=404)


@login_required
@require_GET
def api_search_product(request):
    """API endpoint to search products by name or SKU"""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)

    from apps.inventory.models import Product
    from django.db.models import Q

    products = Product.objects.filter(
        Q(name__icontains=q) | Q(sku__icontains=q),
        is_active=True
    ).values('id', 'name', 'sku', 'price', 'stock_quantity')[:20]  # Limit results

    return JsonResponse(list(products), safe=False)

@login_required
@require_GET
def api_products(request):
    """API endpoint to get all active products for POS"""
    from apps.inventory.models import Product
    products = Product.objects.filter(is_active=True).values(
        'id', 'name', 'sku', 'price', 'stock_quantity'
    )
    return JsonResponse(list(products), safe=False)


@login_required
@require_POST
@csrf_exempt
def api_cart_add(request):
    """API endpoint to add product to cart"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity') or 1)

        from apps.inventory.models import Product
        product = Product.objects.get(id=product_id, is_active=True)

        # Get or create cart in session
        cart = request.session.get('pos_cart', {})
        
        current_in_cart = 0
        if str(product_id) in cart:
            current_in_cart = cart[str(product_id)]['quantity']
            
        total_requested = current_in_cart + quantity

        if product.stock_quantity < total_requested:
            return JsonResponse({'error': f'Insufficient stock for {product.name}. Available: {product.stock_quantity}, In Cart: {current_in_cart}'}, status=400)

        if str(product_id) in cart:
            cart[str(product_id)]['quantity'] += quantity
        else:
            cart[str(product_id)] = {
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': str(product.price),
                'quantity': quantity
            }

        request.session['pos_cart'] = cart
        return JsonResponse({'success': True})

    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_GET
def api_cart(request):
    """API endpoint to get current cart"""
    cart = request.session.get('pos_cart', {})
    items = []

    for item_data in cart.values():
        items.append({
            'id': item_data['id'],
            'name': item_data['name'],
            'sku': item_data['sku'],
            'price': item_data['price'],
            'quantity': item_data['quantity']
        })

    return JsonResponse({'items': items})


@login_required
@require_POST
@csrf_exempt
def api_cart_update(request):
    """API endpoint to update cart item quantity"""
    try:
        data = json.loads(request.body)
        product_id = str(data.get('product_id'))
        quantity = data.get('quantity', 1)

        cart = request.session.get('pos_cart', {})

        if product_id in cart:
            cart[product_id]['quantity'] = quantity
            request.session['pos_cart'] = cart
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Item not in cart'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def api_cart_remove(request):
    """API endpoint to remove item from cart"""
    try:
        data = json.loads(request.body)
        product_id = str(data.get('product_id'))

        cart = request.session.get('pos_cart', {})

        if product_id in cart:
            del cart[product_id]
            request.session['pos_cart'] = cart
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Item not in cart'}, status=404)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def api_cart_clear(request):
    """API endpoint to clear cart"""
    request.session['pos_cart'] = {}
    return JsonResponse({'success': True})


@login_required
@require_GET
def api_customers(request):
    """API endpoint to get all active customers for POS"""
    customers = Customer.objects.filter(is_active=True).values(
        'id', 'name', 'email'
    ).order_by('name')
    return JsonResponse(list(customers), safe=False)


@login_required
@require_POST
@csrf_exempt
def api_checkout(request):
    """API endpoint to complete checkout with customer, payment, and discount support"""
    cart = request.session.get('pos_cart', {})

    if not cart:
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    try:
        data = json.loads(request.body)
        # Old ID support (optional)
        customer_id = data.get('customer_id')
        
        # New direct fields
        customer_name = data.get('customer_name', 'Walk-in Customer').strip()
        customer_phone = data.get('customer_phone', '').strip()
        customer_address = data.get('customer_address', '').strip()
        
        payment_method = data.get('payment_method')
        discount_percent = data.get('discount_percent', 0)

        with transaction.atomic():
            # RESOLVE CUSTOMER
            customer = None
            
            # 1. Try by ID (legacy/explicit)
            if customer_id:
                customer = Customer.objects.filter(id=customer_id).first()

            # 2. Try by Phone (if provided)
            # IMPORTANT: Don't match empty strings for phone
            if not customer and customer_phone:
                customer = Customer.objects.filter(phone=customer_phone).first()
                # If found, maybe update address? For now, just use it.
                if not customer:
                    # Create new customer with Phone
                    customer = Customer.objects.create(
                        name=customer_name if customer_name else "Customer",
                        phone=customer_phone,
                        address=customer_address
                    )

            # 3. Try by Name (if specific name provided, not Walk-in)
            if not customer and customer_name and customer_name.lower() != 'walk-in customer':
                # Create new customer by Name (to allow duplicates or distinct simple entries)
                customer = Customer.objects.create(
                    name=customer_name,
                    phone=customer_phone,
                    address=customer_address
                )

            # 4. Fallback to Walk-in
            if not customer:
                customer, created = Customer.objects.get_or_create(
                    name='Walk-in Customer',
                    email='walkin@temp.com',
                    defaults={'is_active': True}
                )

            # Create sales order
            sales_order = SalesOrder.objects.create(
                customer=customer,
                status='confirmed',
                notes=f'POS Sale - Payment: {payment_method}',
                payment_method=payment_method,
                shipping_address=customer.address if customer.address else "",
                shipping_city=customer.city if customer.city else "",
                shipping_state=customer.state if customer.state else "",
                shipping_postal_code=customer.postal_code if customer.postal_code else "",
                shipping_country=customer.country if customer.country else ""
            )

            total_amount = 0
            # Add items to order
            # Add items to order
            for item_data in cart.values():
                from apps.inventory.models import Product
                # Use select_for_update to lock rows and prevent race conditions
                product = Product.objects.select_for_update().get(pk=item_data['id'])
                quantity = item_data['quantity']
                unit_price = float(item_data['price'])

                if product.stock_quantity < quantity:
                     raise ValueError(f"Insufficient stock for {product.name}")

                SalesOrderItem.objects.create(
                    sales_order=sales_order,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price
                )

                # Update inventory
                product.stock_quantity -= quantity
                product.save()
                
                total_amount += (quantity * unit_price)

            # Calculate discount and totals
            from apps.dashboard.models import GeneralSettings
            settings = GeneralSettings.get_settings()
            tax_rate = float(settings.tax_percent) / 100.0

            # Note: iterate over items gave us total_amount (subtotal)
            discount_amount = total_amount * (discount_percent / 100)
            discounted_subtotal = total_amount - discount_amount
            tax_amount = discounted_subtotal * tax_rate
            final_total = discounted_subtotal + tax_amount

            # Update order totals
            sales_order.subtotal = total_amount
            sales_order.tax_amount = tax_amount
            sales_order.discount_amount = discount_amount
            sales_order.total_amount = final_total
            sales_order.save()

            # Create Invoice automatically for POS sales
            from .models import SalesInvoice
            invoice = SalesInvoice.objects.create(
                sales_order=sales_order,
                amount_due=final_total,
                amount_paid=final_total,
                status='paid',
                notes=sales_order.notes
            )

            # Clear cart
            request.session['pos_cart'] = {}

            # Prepare response with customer details for receipt
            return JsonResponse({
                'success': True,
                'order_number': sales_order.order_number,
                'order_id': sales_order.id,
                'invoice_id': invoice.id,
                'total_amount': final_total,
                'customer_name': customer.name,
                'customer_phone': customer.phone,
                'customer_address': customer.address
            })

    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Customer not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def invoice_list(request):
    """List all sales invoices"""
    invoices = SalesInvoice.objects.all().order_by('-date_issued', '-id')
    
    context = {
        'invoices': invoices,
        'title': 'Sales Invoices',
        'active_menu': 'invoices'
    }
    return render(request, 'sales/invoice_list.html', context)


@login_required
def invoice_detail(request, pk):
    """View invoice details (Printable)"""
    invoice = get_object_or_404(SalesInvoice, pk=pk)
    
    context = {
        'invoice': invoice,
        'sales_order': invoice.sales_order,
        'company_name': 'My ERP Company', # Placeholder
        'title': f'Invoice {invoice.invoice_number}',
    }
    return render(request, 'sales/invoice_detail.html', context)
