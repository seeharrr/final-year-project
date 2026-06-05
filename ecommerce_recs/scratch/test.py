import os
import django
import sys
sys.path.append(r'c:\Users\zaina\Downloads\ecommerce_recs.1\ecommerce_recs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recs.settings')
django.setup()

from django.test import RequestFactory
from products.views import catalog
import re

request = RequestFactory().get('/catalog/?category=laptops')
response = catalog(request)
html = response.content.decode('utf-8', errors='ignore')
titles = re.findall(r'title=\"([^\"]+)\"', html)
print("LAPTOPS TITLES:")
for t in titles[:12]:
    print("-", t)

request2 = RequestFactory().get('/catalog/?category=cameras')
response2 = catalog(request2)
html2 = response2.content.decode('utf-8', errors='ignore')
titles2 = re.findall(r'title=\"([^\"]+)\"', html2)
print("CAMERAS TITLES:")
for t in titles2[:12]:
    print("-", t)
