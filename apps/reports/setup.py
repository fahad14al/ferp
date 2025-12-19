"""
Installation and setup script for the Reports App
Run this after installing dependencies
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ferp.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User
from apps.reports.models import DashboardMetric

def setup_reports_app():
    """Setup the reports app with initial data"""
    
    print("=" * 60)
    print("Reports App Setup")
    print("=" * 60)
    
    # Run migrations
    print("\n1. Running migrations...")
    try:
        call_command('makemigrations', 'reports')
        call_command('migrate', 'reports')
        print("✓ Migrations completed successfully")
    except Exception as e:
        print(f"✗ Migration error: {e}")
        return False
    
    # Create initial dashboard metrics
    print("\n2. Creating initial dashboard metrics...")
    metrics = [
        ('purchase_orders_today', 'Purchase Orders Today', 'count'),
        ('pending_deliveries', 'Pending Deliveries', 'count'),
        ('low_stock_alerts', 'Low Stock Alerts', 'count'),
        ('supplier_performance', 'Supplier Performance', '%'),
        ('monthly_spending', 'Monthly Spending', 'USD'),
        ('inventory_value', 'Inventory Value', 'USD'),
        ('sales_revenue', 'Sales Revenue', 'USD'),
        ('profit_margin', 'Profit Margin', '%'),
    ]
    
    created_count = 0
    for metric_type, name, unit in metrics:
        metric, created = DashboardMetric.objects.get_or_create(
            metric_type=metric_type,
            defaults={'value': 0, 'unit': unit}
        )
        if created:
            created_count += 1
    
    print(f"✓ Created {created_count} dashboard metrics")
    
    # Collect static files
    print("\n3. Collecting static files...")
    try:
        call_command('collectstatic', '--noinput', '--clear')
        print("✓ Static files collected")
    except Exception as e:
        print(f"⚠ Static files warning: {e}")
    
    print("\n" + "=" * 60)
    print("Setup completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the development server: python manage.py runserver")
    print("2. Access reports at: http://localhost:8000/reports/")
    print("3. Access admin at: http://localhost:8000/admin/")
    print("\nOptional:")
    print("- Install openpyxl for Excel export: pip install openpyxl")
    print("- Install weasyprint for PDF export: pip install weasyprint")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    success = setup_reports_app()
    sys.exit(0 if success else 1)
