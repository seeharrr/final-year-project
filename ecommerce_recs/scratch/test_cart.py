import os
import django
import sys
sys.path.append(r'c:\Users\zaina\Downloads\ecommerce_recs.1\ecommerce_recs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recs.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from products.models import Product, Cart, CartItem

User = get_user_model()
user = User.objects.get(username='saher')

client = Client()
client.force_login(user)

cart, _ = Cart.objects.get_or_create(user=user)
product = Product.objects.first()
cart_item, _ = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': 1})

# Test update
response = client.post(f'/products/cart/update/{cart_item.id}/', {'action': 'increase'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print("UPDATE RESPONSE:", response.status_code, response.content)

# Test remove
response = client.post(f'/products/cart/remove/{cart_item.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
print("REMOVE RESPONSE:", response.status_code, response.content)
