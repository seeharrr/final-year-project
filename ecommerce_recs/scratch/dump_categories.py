import os, sys, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recs.settings')
django.setup()

from products.models import Product, Category

# Write to file to avoid encoding issues
with open('scratch/category_dump.txt', 'w', encoding='utf-8') as f:
    cats = Category.objects.all().order_by('name')
    for c in cats:
        products = c.products.all().order_by('title')
        f.write(f"\n{'='*80}\n")
        f.write(f"CATEGORY: {c.name} (slug: {c.slug}) -- {products.count()} products\n")
        f.write(f"{'='*80}\n")
        for p in products:
            # Replace non-ascii chars
            title = p.title[:150].encode('ascii', 'replace').decode('ascii')
            f.write(f"  [ID:{p.id}] {title}\n")

print("Done! Output saved to scratch/category_dump.txt")
