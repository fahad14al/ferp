from django.core.management.base import BaseCommand
from apps.inventory.models import Product, StockMovement
from apps.purchase.models import PurchaseOrder, PurchaseOrderItem

class Command(BaseCommand):
    help = 'Debug stock issues'

    def handle(self, *args, **kwargs):
        def check_product(name_part):
            self.stdout.write(f"\n--- Checking {name_part} ---")
            products = Product.objects.filter(name__icontains=name_part)
            for p in products:
                self.stdout.write(f"Product: {p.name} (ID: {p.id}) | Stock: {p.stock_quantity} | Cost: {p.cost_price}")
                
                movements = StockMovement.objects.filter(product=p)
                self.stdout.write(f"  Movements: {movements.count()}")
                for m in movements:
                    self.stdout.write(f"    - {m.date.strftime('%Y-%m-%d %H:%M')} | {m.movement_type} {m.quantity} | {m.reason} | {m.notes}")
                    
                po_items = PurchaseOrderItem.objects.filter(product=p)
                self.stdout.write(f"  PO Items: {po_items.count()}")
                for pi in po_items:
                    po = pi.purchase_order
                    self.stdout.write(f"    - PO #{po.order_number} (ID: {po.id}) | Status: {po.status}")
                    self.stdout.write(f"      Ordered: {pi.quantity_ordered} | Received: {pi.quantity_received} | Pending: {pi.pending_quantity}")

        check_product('Meat')
        check_product('Mango')
