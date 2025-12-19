from apps.inventory.models import Product, StockMovement
from apps.purchase.models import PurchaseOrder, PurchaseOrderItem

def check_product(name_part):
    print(f"\n--- Checking {name_part} ---")
    products = Product.objects.filter(name__icontains=name_part)
    for p in products:
        print(f"Product: {p.name} (ID: {p.id}) | Stock: {p.stock_quantity} | Cost: {p.cost_price}")
        
        movements = StockMovement.objects.filter(product=p)
        print(f"  Movements: {movements.count()}")
        for m in movements:
            print(f"    - {m.date.strftime('%Y-%m-%d %H:%M')} | {m.movement_type} {m.quantity} | {m.reason} | {m.notes}")
            
        po_items = PurchaseOrderItem.objects.filter(product=p)
        print(f"  PO Items: {po_items.count()}")
        for pi in po_items:
            po = pi.purchase_order
            print(f"    - PO #{po.order_number} (ID: {po.id}) | Status: {po.status}")
            print(f"      Ordered: {pi.quantity_ordered} | Received: {pi.quantity_received} | Pending: {pi.pending_quantity}")

check_product('Meat')
check_product('Mango')
