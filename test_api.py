import os
import django
import json
from django.test import RequestFactory
from django.conf import settings
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ferp.settings')
django.setup()

from apps.inventory.views import api_product_search
from apps.inventory.models import Product

User = get_user_model()

def test_api():
    # Ensure active products exist
    count = Product.objects.filter(is_active=True).count()
    print(f"Active Products in DB: {count}")

    # Create dummy user
    user = User.objects.first()
    if not user:
        print("No user found to mimic login.")
        return

    # Create request
    factory = RequestFactory()
    request = factory.get('/inventory/api/product-search/')
    request.user = user  # Mimic login

    # Call view
    response = api_product_search(request)
    
    print(f"Status Code: {response.status_code}")
    content = json.loads(response.content)
    print(f"Result Count: {len(content.get('results', []))}")
    if len(content.get('results', [])) > 0:
        print("Sample:", content['results'][0]['name'])
    else:
        print("No results returned.")

if __name__ == "__main__":
    test_api()
