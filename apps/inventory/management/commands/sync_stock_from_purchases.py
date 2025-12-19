from django.core.management.base import BaseCommand
from apps.purchase.models import PurchaseOrder
from apps.inventory.models import StockMovement

class Command(BaseCommand):
    help = 'Syncs inventory stock with received purchase orders'

    def handle(self, *args, **kwargs):
        received_orders = PurchaseOrder.objects.filter(status='received')
        updated_count = 0
        
        for order in received_orders:
            # Check if movements exist for this order
            po_note = f"PO-{order.order_number}"
            
            for item in order.items.filter(is_active=True):
                # Check 1: If item has received qty but no movement (Missing Movement)
                movement_exists = StockMovement.objects.filter(
                    product=item.product,
                    notes__contains=order.order_number
                ).exists()
                
                if item.quantity_received > 0 and not movement_exists:
                    self.stdout.write(f"Backfilling MISSING StockMovement for {item.product.name} from {order.order_number}")
                    StockMovement.objects.create(
                        product=item.product,
                        movement_type='IN',
                        quantity=item.quantity_received,
                        reason='Purchase Sync',
                        notes=po_note
                    )
                    # Force cost update
                    if item.unit_price > 0:
                        item.product.cost_price = item.unit_price
                        item.product.save()
                    updated_count += 1
                
                # Check 2: If Order is Received but Item is NOT (Inconsistent State)
                elif item.quantity_received == 0:
                     self.stdout.write(f"Fixing UNRECEIVED item {item.product.name} in Received Order #{order.order_number}")
                     # This will trigger receive_item() which updates stock AND quantity_received
                     item.receive_item(quantity=item.quantity_ordered)
                     updated_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully synced {updated_count} items.'))
