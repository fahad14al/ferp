// Initial State
let products = [];
let cart = [];
let selectedCustomer = { id: null, name: 'Walk-in Customer', email: 'walkin@temp.com' };
let selectedPaymentMethod = null;
let discountPercent = 0;
let discountAmount = 0;

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
        document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;
}

// STATUS NOTIFICATION
function showStatus(message, type = 'success') {
    const notification = document.getElementById('statusNotification');
    notification.textContent = message;
    notification.className = `pos-status ${type}`;
    notification.style.display = 'block';

    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// LOAD PRODUCTS (Initial Grid)
async function loadProducts() {
    try {
        const response = await fetch(`/inventory/api/product-search/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            const data = await response.json();
            products = data.results;
            renderProducts();
        } else {
            throw new Error(`Server returned ${response.status}`);
        }
    } catch (error) {
        console.error('Error loading products:', error);
        document.getElementById('productGrid').innerHTML = `
            <div class="text-center py-5 text-danger">
                <i class="fas fa-exclamation-circle"></i> 
                <p>Failed to load products (${error.message}).</p>
                <button class="btn btn-sm btn-outline-primary mt-2" onclick="loadProducts()">Try Again</button>
            </div>
        `;
        showStatus('Failed to load product catalog', 'error');
    }
}

// CUSTOMER MANAGEMENT
// Simplified for direct entry
function getCustomerDetails() {
    return {
        name: document.getElementById('customerName').value || 'Walk-in Customer',
        phone: document.getElementById('customerPhone').value || '',
        address: document.getElementById('customerAddress').value || ''
    };
}

// QUICK FUNCTIONS
function quickQuantity(qty) {
    // This will be used when adding products
    window.quickQty = qty;
    showStatus(`Quick quantity set to ${qty}`);
}

function applyDiscount(percent) {
    discountPercent = percent;
    calculateTotals();
    document.getElementById('discountSection').style.display = 'block';
    document.getElementById('discountAmount').textContent = `${percent}%`;
    showStatus(`Discount of ${percent}% applied`);
}

function removeDiscount() {
    discountPercent = 0;
    calculateTotals();
    document.getElementById('discountSection').style.display = 'none';
    showStatus('Discount removed');
}

// PAYMENT METHODS
function selectPayment(method) {
    selectedPaymentMethod = method;

    // Update UI
    document.querySelectorAll('.payment-method').forEach(el => {
        el.classList.remove('selected');
    });
    document.querySelector(`[data-method="${method}"]`).classList.add('selected');

    // Enable checkout button
    document.getElementById('checkout').disabled = false;
    showStatus(`Payment method: ${method}`);
}

// ADD PRODUCT TO CART VIA AJAX
// ADD PRODUCT TO CART (FORM SUBMISSION)
function addToCart(productId, quantity = 1) {
    if (window.quickQty) {
        quantity = window.quickQty;
        window.quickQty = null;
    }

    // Set hidden inputs
    document.getElementById('cart_product_id').value = productId;
    document.getElementById('cart_quantity').value = quantity;

    // Add a temp hidden input to identify the action
    const form = document.getElementById('posForm');
    const actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.name = 'add_product'; // Matches views.py
    actionInput.value = '1';
    form.appendChild(actionInput);

    form.submit();
}

// LOAD CART FROM DJANGO SESSION
async function loadCart() {
    try {
        const response = await fetch('/sales/api/cart/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            const cartData = await response.json();
            cart = cartData.items || [];
            renderCart();
        }
    } catch (error) {
        console.error('Error loading cart:', error);
    }
}

// UPDATE CART ITEM QUANTITY
async function updateCartItem(productId, quantity) {
    try {
        const response = await fetch('/sales/api/cart/update/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_id: productId,
                quantity: parseInt(quantity)
            })
        });

        if (response.ok) {
            loadCart();
        }
    } catch (error) {
        console.error('Error updating cart:', error);
    }
}

// REMOVE ITEM FROM CART
async function removeFromCart(productId) {
    try {
        const response = await fetch('/sales/api/cart/remove/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                product_id: productId
            })
        });

        if (response.ok) {
            loadCart();
            showStatus('Item removed from cart');
        }
    } catch (error) {
        console.error('Error removing from cart:', error);
    }
}

// CLEAR CART
async function clearCart() {
    if (!confirm('Clear entire cart?')) return;

    try {
        const response = await fetch('/sales/api/cart/clear/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            loadCart();
            showStatus('Cart cleared');
        }
    } catch (error) {
        console.error('Error clearing cart:', error);
    }
}

// CALCULATE TOTALS
function calculateTotals() {
    let subtotal = 0;

    cart.forEach(item => {
        subtotal += parseFloat(item.price) * parseInt(item.quantity);
    });

    discountAmount = subtotal * (discountPercent / 100);
    const discountedSubtotal = subtotal - discountAmount;
    const tax = discountedSubtotal * 0.15;
    const total = discountedSubtotal + tax;

    return { subtotal, discountAmount, tax, total };
}

// RENDER PRODUCTS
// RENDER PRODUCTS
function renderProducts(isClear = false) {
    const productGrid = document.getElementById('productGrid');

    // If clearing or no results
    if (isClear || products.length === 0) {
        productGrid.innerHTML = `
            <div class="text-center py-5">
                <p class="text-muted">Type to search or scan a barcode</p>
            </div>
        `;
        return;
    }

    productGrid.innerHTML = products.map(p => `
        <div class="product">
            <div class="prod-top">
                <div class="thumb">${p.name[0].toUpperCase()}</div>
                <div>
                    <div class="name">${p.name}</div>
                    <div class="price">$${parseFloat(p.price).toFixed(2)}</div>
                    <div class="tags small">SKU: ${p.sku} | Stock: ${p.stock_quantity}</div>
                </div>
            </div>
            <div class="add-row">
                <input type="number" min="1" value="1" class="qty" id="qty-${p.id}" />
                <button class="btn" onclick="addToCart(${p.id}, document.getElementById('qty-${p.id}').value)">Add</button>
            </div>
        </div>
    `).join('');
}

// RENDER CART
function renderCart() {
    const cartItems = document.getElementById('cartItems');

    if (cart.length === 0) {
        cartItems.innerHTML = `
            <div class="text-center py-3">
                <p class="text-muted small">Cart is empty</p>
            </div>
        `;
        updateTotalsDisplay(0, 0, 0, 0);
        return;
    }

    cartItems.innerHTML = cart.map(item => `
        <div class="cart-item">
            <div class="ci-thumb">${item.name[0].toUpperCase()}</div>
            <div class="ci-meta">
                <div class="ci-name">${item.name}</div>
                <div class="ci-sub">$${parseFloat(item.price).toFixed(2)} × ${item.quantity}</div>
            </div>
            <div class="ci-actions">
                <input type="number" min="1" value="${item.quantity}" onchange="updateCartItem(${item.id}, this.value)" />
            </div>
            <button class="btn clear" onclick="removeFromCart(${item.id})">×</button>
        </div>
    `).join('');

    const totals = calculateTotals();
    updateTotalsDisplay(totals.subtotal, totals.discountAmount, totals.tax, totals.total);
}

function updateTotalsDisplay(subtotal, discountAmount, tax, total) {
    document.getElementById("subtotal").textContent = `$${subtotal.toFixed(2)}`;
    document.getElementById("discountTotal").textContent = `-$${discountAmount.toFixed(2)}`;
    document.getElementById("tax").textContent = `$${tax.toFixed(2)}`;
    document.getElementById("total").textContent = `$${total.toFixed(2)}`;
}

// CHECKOUT
/*
async function checkout() {
    // Legacy checkout - Removed in favor of Django Form POST
    if (cart.length === 0) {
        showStatus('Cart is empty', 'error');
        return;
    }
    // ... code ...
}
*/

// RECEIPT SYSTEM
function showReceipt(orderData) {
    const modal = document.getElementById('receiptModal');
    const now = new Date();

    document.getElementById('receiptDate').textContent = now.toLocaleDateString() + ' ' + now.toLocaleTimeString();
    document.getElementById('receiptOrderNumber').textContent = `Order: ${orderData.order_number}`;

    // Add customer details to receipt
    // Add customer details to receipt (Clear previous if any)
    const existingCustomerInfo = document.querySelector('.receipt-customer');
    if (existingCustomerInfo) {
        existingCustomerInfo.remove();
    }

    const customerHtml = `
        <div class="receipt-customer" style="margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 10px;">
            <div><strong>Customer:</strong> ${orderData.customer_name}</div>
            ${orderData.customer_phone ? `<div>Phone: ${orderData.customer_phone}</div>` : ''}
            ${orderData.customer_address ? `<div>Address: ${orderData.customer_address}</div>` : ''}
        </div>
    `;
    document.getElementById('receiptOrderNumber').insertAdjacentHTML('afterend', customerHtml);

    let itemsHtml = '';
    cart.forEach(item => {
        const itemTotal = parseFloat(item.price) * parseInt(item.quantity);
        itemsHtml += `
            <div class="receipt-item">
                <span>${item.name} × ${item.quantity}</span>
                <span>$${itemTotal.toFixed(2)}</span>
            </div>
        `;
    });

    document.getElementById('receiptItems').innerHTML = itemsHtml;
    document.getElementById('receiptTotal').textContent = `$${orderData.total_amount}`;
    document.getElementById('receiptPaymentMethod').textContent = `Paid by: ${selectedPaymentMethod.toUpperCase()}`;

    modal.style.display = 'flex';
}

function closeReceipt() {
    document.getElementById('receiptModal').style.display = 'none';
}

function printReceipt() {
    window.print();
}

function resetPOS() {
    document.getElementById('customerName').value = 'Walk-in Customer';
    document.getElementById('customerPhone').value = '';
    document.getElementById('customerAddress').value = '';
    selectedPaymentMethod = null;
    discountPercent = 0;
    discountAmount = 0;

    // updateCustomerDisplay(); // Removed
    document.querySelectorAll('.payment-method').forEach(el => el.classList.remove('selected'));
    document.getElementById('checkout').disabled = true;
    document.getElementById('discountSection').style.display = 'none';
    // document.getElementById('search').value = ''; // Removed
    document.getElementById('barcode').value = '';

    showStatus('POS reset for new sale');
}

// [Removed] searchProducts function
// [Removed] sort functions

// BARCODE SCANNING HANDLER (Server-Side)
document.getElementById('barcode').addEventListener('keypress', async function (e) {
    if (e.key === 'Enter') {
        e.preventDefault(); // Prevent form submission

        const barcode = this.value.trim();
        if (!barcode) return;

        try {
            // Call API to scan barcode
            const response = await fetch(`/sales/api/scan-barcode/?barcode=${encodeURIComponent(barcode)}`, {
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'Content-Type': 'application/json',
                }
            });
            const data = await response.json();

            if (response.ok && data.product) {
                // Add to cart directly
                addToCart(data.product.id, 1);
                this.value = '';
                showStatus(`Scanned: ${data.product.name}`);
            } else {
                showStatus(data.error || `Product not found: ${barcode}`, 'error');
                this.select();
            }
        } catch (error) {
            console.error('Barcode scan error:', error);
            showStatus('Error scanning barcode', 'error');
        }

        // Keep focus
        this.focus();
    }
});

// EVENT LISTENERS
// [Removed] Sort and Search listeners
// document.getElementById("clearCart").addEventListener("click", clearCart); // Handled by form submit
// document.getElementById("checkout").addEventListener("click", checkout); // Handled by form submit
// document.getElementById("refreshCart").addEventListener("click", loadCart); // Removed

// No search listener

// INITIAL LOAD
document.addEventListener("DOMContentLoaded", function () {
    // Load initial product catalog
    // loadProducts(); // Removed: Now Server-Side Rendered by Django!
    // loadCart(); // Removed: Rendered by Django template loop!

    // Focus barcode on start
    const barcodeInput = document.getElementById('barcode');
    if (barcodeInput) barcodeInput.focus();
});