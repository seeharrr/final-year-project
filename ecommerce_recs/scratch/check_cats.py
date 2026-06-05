import os
import sys
import django

# Add the project root to sys.path
sys.path.append(r'c:\Users\zaina\Downloads\ecommerce_recs.1\ecommerce_recs')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recs.settings')
django.setup()

from products.models import Product, Category

def check_categories():
    categories = Category.objects.all()
    print(f"{'Category Name':<25} | {'Product Count':<15} | {'Slug':<20}")
    print("-" * 65)
    for cat in categories:
        count = cat.products.count()
        print(f"{cat.name:<25} | {count:<15} | {cat.slug:<20}")

if __name__ == "__main__":
    check_categories()
