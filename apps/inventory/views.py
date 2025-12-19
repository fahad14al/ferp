from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.db.models import Sum, Count, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.template.loader import get_template
from django.core.paginator import Paginator
import json
from .models import Product, Category, Supplier, StockMovement
from .forms import ProductForm, CategoryForm, SupplierForm, StockAdjustmentForm


@login_required
def inventory_dashboard(request):
    """Main inventory dashboard with key metrics and alerts."""
    # Key metrics
    total_products = Product.objects.filter(is_active=True).count()
    total_value = Product.objects.filter(is_active=True).aggregate(
        total=models.Sum(models.F('stock_quantity') * models.F('price'))
    )['total'] or 0

    low_stock_products = Product.objects.filter(
        is_active=True,
        stock_quantity__lte=models.F('reorder_level')
    )
    low_stock_count = low_stock_products.count()

    out_of_stock = Product.objects.filter(is_active=True, stock_quantity=0).count()

    # Recent movements
    recent_movements = StockMovement.objects.select_related('product').order_by('-date')[:10]

    # Top categories by product count
    category_stats = Category.objects.annotate(
        product_count=Count('product'),
        total_value=Sum(models.F('product__stock_quantity') * models.F('product__price'))
    ).filter(product_count__gt=0).order_by('-product_count')[:5]

    context = {
        'total_products': total_products,
        'total_value': total_value,
        'low_stock_count': low_stock_count,
        'out_of_stock': out_of_stock,
        'low_stock_products': low_stock_products[:5],  # Show first 5
        'recent_movements': recent_movements,
        'category_stats': category_stats,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def inventory_list(request):
    """Enhanced inventory list with filtering and search."""
    products = Product.objects.filter(is_active=True).select_related('category', 'supplier')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Category filter
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    # Stock status filter
    stock_status = request.GET.get('stock_status')
    if stock_status == 'low':
        products = products.filter(stock_quantity__lte=models.F('reorder_level'))
    elif stock_status == 'out':
        products = products.filter(stock_quantity=0)

    # Supplier filter
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        products = products.filter(supplier_id=supplier_id)

    # Pagination
    paginator = Paginator(products, 25)  # 25 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Stats for sidebar
    low_stock = Product.objects.filter(
        is_active=True,
        stock_quantity__lte=models.F('reorder_level')
    ).count()

    categories = Category.objects.all()
    suppliers = Supplier.objects.all()

    context = {
        'page_obj': page_obj,
        'products': page_obj,  # For backward compatibility
        'low_stock_count': low_stock,
        'categories': categories,
        'suppliers': suppliers,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_supplier': supplier_id,
        'selected_stock_status': stock_status,
    }
    return render(request, 'inventory/list.html', context)


@login_required
def product_detail(request, pk):
    """Enhanced product detail with full stock history."""
    product = get_object_or_404(Product, pk=pk)
    movements = StockMovement.objects.filter(product=product).order_by('-date')

    # Pagination for movements
    paginator = Paginator(movements, 20)
    page_number = request.GET.get('page')
    movements_page = paginator.get_page(page_number)

    context = {
        'product': product,
        'movements_page': movements_page,
        'total_movements': movements.count(),
    }
    return render(request, 'inventory/detail.html', context)


@login_required
def product_create(request):
    """Create new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" created successfully! You can add another.')
            return redirect('inventory:product_create')
    else:
        form = ProductForm()
    return render(request, 'inventory/create.html', {'form': form})


@login_required
def product_update(request, pk):
    """Update existing product."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = ProductForm(instance=product)
    return render(request, 'inventory/update.html', {'form': form, 'product': product})


@login_required
def product_delete(request, pk):
    """Delete product (soft delete by setting inactive)."""
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, f'Product "{product.name}" has been deactivated.')
        return redirect('inventory:inventory_list')
    return render(request, 'inventory/delete.html', {'product': product})


@login_required
def stock_adjustment(request, pk):
    """Adjust stock levels manually."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            adjustment = form.cleaned_data['adjustment']
            reason = form.cleaned_data['reason']
            notes = form.cleaned_data['notes']

            with transaction.atomic():
                # Create stock movement record
                movement_type = 'IN' if adjustment > 0 else 'OUT'
                StockMovement.objects.create(
                    product=product,
                    movement_type=movement_type,
                    quantity=abs(adjustment),
                    reason=reason,
                    notes=notes
                )

                # Update product stock (this is handled by StockMovement.save())
                messages.success(request, f'Stock adjusted by {adjustment} units.')
                return redirect('inventory:product_detail', pk=product.pk)
    else:
        form = StockAdjustmentForm()

    return render(request, 'inventory/stock_adjustment.html', {
        'form': form,
        'product': product
    })


@login_required
def generate_barcode(request, pk):
    """Generate barcode for product."""
    product = get_object_or_404(Product, pk=pk)

    # For now, just return the SKU as barcode data
    # In a real implementation, you'd generate actual barcode images
    barcode_data = product.sku

    context = {
        'product': product,
        'barcode_data': barcode_data,
    }
    return render(request, 'inventory/barcode.html', context)


# CATEGORY MANAGEMENT
@login_required
def category_list(request):
    """List all categories."""
    categories = Category.objects.all().order_by('name')
    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    """Create new category."""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully! You can add another.')
            return redirect('inventory:category_create')
    else:
        form = CategoryForm()
    return render(request, 'inventory/category_create.html', {'form': form})


@login_required
def category_update(request, pk):
    """Update category."""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('inventory:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'inventory/category_update.html', {'form': form, 'category': category})


# SUPPLIER MANAGEMENT
@login_required
def supplier_list(request):
    """List all suppliers."""
    suppliers = Supplier.objects.all().order_by('name')
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_create(request):
    """Create new supplier."""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier "{supplier.name}" created successfully! You can add another.')
            return redirect('inventory:supplier_create')
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_create.html', {'form': form})


@login_required
def supplier_update(request, pk):
    """Update supplier."""
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f'Supplier "{supplier.name}" updated successfully.')
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_update.html', {'form': form, 'supplier': supplier})


@login_required
def supplier_detail(request, pk):
    """View supplier details and their products."""
    supplier = get_object_or_404(Supplier, pk=pk)
    products = Product.objects.filter(supplier=supplier, is_active=True).select_related('category')

    # Calculate statistics
    total_value = products.aggregate(
        total=models.Sum(models.F('stock_quantity') * models.F('price'))
    )['total'] or 0

    active_products = products.count()
    low_stock_products = products.filter(stock_quantity__lte=models.F('reorder_level')).count()

    # Recent stock movements for products from this supplier
    recent_movements = StockMovement.objects.filter(
        product__supplier=supplier
    ).select_related('product').order_by('-date')[:5]

    context = {
        'supplier': supplier,
        'products': products,
        'total_value': total_value,
        'active_products': active_products,
        'low_stock_products': low_stock_products,
        'recent_movements': recent_movements,
    }
    return render(request, 'inventory/supplier_detail.html', context)


@login_required
def supplier_delete(request, pk):
    """Delete supplier."""
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f'Supplier "{supplier_name}" deleted successfully.')
        return redirect('inventory:supplier_list')

    return render(request, 'inventory/supplier_delete.html', {'supplier': supplier})


# API ENDPOINTS
@login_required
def api_product_search(request):
    """API endpoint for product search (AJAX)."""
    query = request.GET.get('q', '')
    
    products_queryset = Product.objects.filter(is_active=True)
    
    if query:
        products_queryset = products_queryset.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        )
    
    # Limit results (e.g. 50 items for grid)
    products_queryset = products_queryset[:50]

    # Limit to 10 results
    products_list = []
    for product in products_queryset[:10]:
        products_list.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'stock_quantity': product.stock_quantity,
            'price': product.price
        })

    return JsonResponse({'results': products_list})


@login_required
def api_stock_alerts(request):
    """API endpoint for stock alerts."""
    low_stock = Product.objects.filter(
        is_active=True,
        stock_quantity__lte=models.F('reorder_level')
    ).values('id', 'name', 'sku', 'stock_quantity', 'reorder_level')

    out_of_stock = Product.objects.filter(
        is_active=True,
        stock_quantity=0
    ).values('id', 'name', 'sku')

    return JsonResponse({
        'low_stock': list(low_stock),
        'out_of_stock': list(out_of_stock)
    })


@login_required
def api_product_create(request):
    """API endpoint to create a product on-the-fly."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Basic validation
            if not data.get('name') or not data.get('sku'):
                return JsonResponse({'error': 'Name and SKU are required'}, status=400)
            
            if Product.objects.filter(sku=data['sku']).exists():
                return JsonResponse({'error': 'Product with this SKU already exists'}, status=400)
            
            # Create product
            product = Product.objects.create(
                name=data['name'],
                sku=data['sku'],
                cost_price=data.get('cost_price', 0),
                price=data.get('price', 0),
                stock_quantity=data.get('stock_quantity', 0),
                description=data.get('description', ''),
            )
            
            return JsonResponse({
                'success': True,
                'product': {
                    'id': product.id,
                    'name': product.name,
                    'sku': product.sku,
                    'price': product.price
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)