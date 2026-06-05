import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recs.settings')
django.setup()

from products.models import Product, Category

def test_phone_ranking():
    category_slug = 'phones'
    products = Product.objects.filter(is_active=True, category__slug=category_slug)
    
    product_list = list(products)
    category_name = 'Phones'
    hero_keywords = ['phone']
    
    def is_hero(p):
        title = p.title.lower()
        if any(kw in title for kw in hero_keywords):
            universal_excludes = ['case', 'bag', 'sleeve', 'paper', 'ink', 'cartridge', 'tripod', 'lens', 'mount', 'strap', 'cable', 'charger', 'battery', 'adapter']
            if any(ex in title for ex in universal_excludes):
                return False
            if category_name == 'Phones':
                phone_excludes = ['holder', 'stand', 'protector', 'pencil', 'pen', 'stylus', 'memory card', 'tool', 'kit', 'headset', 'headphones', 'earbuds', 'mount', 'shield', 'skin', 'wrap', 'airtag', 'drive', 'microphone', 'monitor', 'keyboard', 'gimbal', 'stabilizer', 'watch', 'dji']
                if any(ex in title for ex in phone_excludes):
                    return False
            return True
        return False

    hero_products = [p for p in product_list if is_hero(p)]
    other_products = [p for p in product_list if not is_hero(p)]
    final_list = hero_products + other_products
    
    print("Top 10 Ranked Products for Phones:")
    for p in final_list[:10]:
        print(f"- {p.title}")

if __name__ == "__main__":
    test_phone_ranking()
