import os
import sys
import django

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recs.settings')
django.setup()

from products.models import Product, Category
from django.utils.text import slugify

def cleanup_categories():
    print("Starting category cleanup...")
    
def cleanup_categories():
    print("Starting comprehensive category cleanup...")
    
    # Define mapping: Category Name -> [Keywords]
    mapping = {
        'Laptops': ['laptop', 'chromebook', 'macbook', 'thinkpad', 'zenbook', 'surface book', 'ideapad', 'pavilion', 'hp envy', 'dell xps', 'alienware', 'inspiron', 'latitude', 'vostro', 'precision', 'vivobook', 'swift', 'aspire', 'notebook'],
        'Phones': ['phone', 'iphone', 'smartphone', 'galaxy s', 'pixel', 'oneplus', 'xiaomi', 'redmi', 'oppo', 'vivo', 'android phone', 'cell phone'],
        'Headphones': ['headphone', 'earbud', 'earphone', 'airpods', 'beats', 'sennheiser', 'sony wh', 'galaxy buds', 'jbl tune', 'headset'],
        'Power & Batteries': ['battery', 'batteries', 'alkaline', 'nimh', 'energizer', 'duracell', 'coppertop', 'lithium coin', 'power bank', 'ups', 'rechargeable'],
        'Gaming': ['gaming', 'ps4', 'ps5', 'playstation', 'xbox', 'nintendo', 'dualshock', 'controller', 'joystick', 'gaming mouse', 'gaming keyboard', 'console', 'switch lite'],
        'Wearables': ['watch', 'fitbit', 'smartwatch', 'fitness tracker', 'apple watch', 'galaxy watch', 'garmin', 'band 7', 'mi band'],
        'Smart Home': ['smart home', 'bulb', 'plug', 'socket', 'thermostat', 'ring video', 'security camera', 'alexa', 'echo dot', 'echo show', 'smart lock', 'tp-link tapo'],
        'Printers & Scanners': ['printer', 'scanner', 'ink cartridge', 'toner', 'copy paper', 'reams', 'fsc certified', 'epson eco'],
        'Chargers & Cables': ['charger', 'cable', 'adapter', 'power cord', 'usb hub', 'docking station', 'wall charger', 'car charger', 'lightning cable', 'usb-c'],
        'Storage': ['ssd', 'hard drive', 'hdd', 'usb drive', 'flash drive', 'memory card', 'sd card', 'micro sd', 'external drive', 'crucial p3'],
        'Cameras': ['camera', 'dslr', 'mirrorless', 'camcorder', 'webcam', 'gopro', 'instax', 'photography', 'lens', 'tripod'],
        'Speakers': ['speaker', 'soundbar', 'home theater', 'bluetooth speaker', 'echo pop'],
        'TV & Display': ['monitor', 'television', 'tv', 'display', 'screen', 'projector', 'hdmi'],
        'Networking': ['router', 'modem', 'wifi', 'access point', 'switch', 'ethernet', 'tp-link archer'],
    }
    
    # Exclude keywords for Laptops to avoid accessories
    laptop_excludes = [
        'battery', 'charger', 'adapter', 'cable', 'case', 'skin', 'stand', 'bag', 'sleeve', 
        'mouse', 'keyboard', 'speaker', 'earbud', 'headphone', 'microphone', 'screen protector',
        'replacement', 'part', 'ram', 'memory', 'hard drive', 'ssd', 'cord', 'power supply', 'plug',
        'for', 'compatible', 'backpack', 'webcam', 'fan', 'stylus', 'cooling pad', 'paper', 'notebook',
        'stationery', 'journal', 'hardcover', 'pages', 'college ruled', 'toolkit', 'repair kit',
        'protection plan', 'warranty', 'insurance', 'service plan', 'tote', 'dock', 'hub', 'mounting',
        'adapter', 'converter', 'power cord'
    ]
    
    # Tech indicators for "notebook" products to differentiate from paper notebooks
    laptop_tech_indicators = ['intel', 'amd', 'core i', 'ryzen', 'gb ram', 'ssd storage', 'windows', 'macos', 'chrome os', 'graphics']
    
    # Create or get categories
    cat_objs = {}
    for name in mapping:
        cat, created = Category.objects.get_or_create(
            name=name,
            defaults={'slug': slugify(name)}
        )
        cat_objs[name] = cat
        
    # Get or create an "Accessories" category
    accessories_cat, _ = Category.objects.get_or_create(
        name='Accessories & Other',
        defaults={'slug': 'accessories-other'}
    )
    
    products = Product.objects.all()
    count = 0
    updated = 0
    
    for product in products:
        title_lower = product.title.lower()
        new_cat = None
        
        # Priority mapping for specific terms
        if any(kw in title_lower for kw in ['protection plan', 'warranty', 'asurion']):
            new_cat = accessories_cat
        elif 'battery' in title_lower or 'batteries' in title_lower:
            new_cat = cat_objs['Power & Batteries']
        elif 'printer' in title_lower or 'ink' in title_lower or 'cartridge' in title_lower:
            new_cat = cat_objs['Printers & Scanners']
        elif 'watch' in title_lower or 'fitbit' in title_lower:
            new_cat = cat_objs['Wearables']
        elif 'controller' in title_lower or 'ps4' in title_lower or 'ps5' in title_lower or 'xbox' in title_lower:
            new_cat = cat_objs['Gaming']
        elif any(kw in title_lower for kw in ['bluetooth adapter', 'usb adapter']):
            new_cat = accessories_cat
        else:
            # General keyword mapping
            for name, keywords in mapping.items():
                if any(kw in title_lower for kw in keywords):
                    # Special logic for Laptops
                    if name == 'Laptops':
                        is_real_laptop = False
                        if any(kw in title_lower for kw in ['laptop', 'chromebook', 'macbook', 'thinkpad', 'zenbook', 'surface book', 'vivobook']):
                            is_real_laptop = True
                        elif 'notebook' in title_lower and any(ti in title_lower for ti in laptop_tech_indicators):
                            is_real_laptop = True
                        
                        if is_real_laptop and any(ex in title_lower for ex in laptop_excludes):
                            is_real_laptop = False
                            
                        if not is_real_laptop:
                            continue
                            
                    # Special logic for Headphones
                    if name == 'Headphones' and any(ex in title_lower for ex in ['case', 'cover', 'adapter', 'cable']):
                        continue

                    # Special logic for Phones
                    if name == 'Phones' and any(ex in title_lower for ex in ['case', 'cover', 'screen protector', 'mount', 'holder', 'charger', 'cable']):
                        continue
                            
                    new_cat = cat_objs[name]
                    break
        
        if not new_cat:
            # Fallback for "Other Electronics" keyword
            if 'electronics' in title_lower or 'gadget' in title_lower:
                new_cat = Category.objects.get_or_create(name='Other Electronics', defaults={'slug': 'other-electronics'})[0]
            else:
                new_cat = accessories_cat
            
        if product.category != new_cat:
            product.category = new_cat
            product.save()
            updated += 1
            
        count += 1
        if count % 500 == 0:
            print(f"Processed {count} products...")
            
    print(f"Cleanup complete! Processed {count} products, updated {updated} categories.")

if __name__ == "__main__":
    cleanup_categories()
