import os, sys, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recs.settings')
django.setup()

from products.models import Product, Category

# Analyze each product and determine where it SHOULD be
# Based on the categories: Accessories & Other, Wearables, Speakers, Headphones,
# TV & Display, Networking, Gaming, Phones, Printers & Scanners, Power & Batteries,
# Other Electronics, Cameras, Smart Home, Storage, Chargers & Cables, Laptops

misplaced = []
total = 0

def determine_correct_category(product):
    """Determine the correct category for a product based on its title."""
    title = product.title.lower()
    current = product.category.name
    
    # ===== PROTECTION PLANS / WARRANTIES / INSURANCE =====
    if any(kw in title for kw in ['protection plan', 'warranty', 'asurion', 'insurance', 'service plan']):
        return 'Accessories & Other'
    
    # ===== PRINTERS & SCANNERS =====
    # Ink cartridges, toner, printers, scanners, copy paper
    printer_keywords = [
        'printer', 'scanner', 'ink cartridge', 'toner', 'cartridge replacement',
        'ink bottle', 'ink tank', 'ink pack', 'imageCLASS', 'imageclass',
        'pixma', 'megatank', 'megatank', 'imageformula', 'imagepro',
        'printhead', 'print head', 'ink compatible', 'ink cartridges',
        'cli-', 'pgi-', 'pg-', 'cl-', 'pfi-', 'gi-20', 'maintenance cartridge',
        'copy paper', 'reams', 'fsc certified',
        'canon genuine', 'toner cartridge', 'ink value pack',
        'e-z ink', 'canon color ink', 'selphy', 'photo paper',
        'crg ', 'crg-',
    ]
    # Canon genuine toner/ink products
    if any(kw in title for kw in printer_keywords):
        # Exclude actual cameras that happen to mention printer compatibility
        if not any(cam in title for cam in ['camera', 'mirrorless', 'dslr', 'camcorder', 'webcam']):
            return 'Printers & Scanners'
    
    # Canon genuine numbered cartridges (like Canon Genuine 051, 054, 055, etc.)
    if 'canon genuine' in title and any(kw in title for kw in ['toner', 'cartridge', 'ink']):
        return 'Printers & Scanners'
    
    # ===== SMART HOME =====
    smart_home_keywords = [
        'smart home', 'smart plug', 'smart bulb', 'smart lock', 'thermostat',
        'echo dot', 'echo show', 'echo pop', 'alexa', 'ring video doorbell',
        'ring alarm', 'ring doorbell', 'video doorbell', 'security system',
        'home security system', 'security camera', 'indoor camera', 'outdoor camera',
        'smart speaker', 'smart display', 'nest', 'simplisafe',
        'tp-link tapo', 'tapo', 'kasa smart', 'kasa indoor',
        'wyze cam', 'wyze floodlight', 'wyze wireless',
        'arlo', 'reolink', 'lorex', 'eufy security', 'eufycam',
        'blink mini', 'blink outdoor', 'blink indoor',
        'floodlight camera', 'doorbell camera',
        'ring floodlight', 'ring spotlight', 'ring indoor',
        'feit electric', 'security camera system',
        'baby monitor', 'pet cam',
    ]
    if any(kw in title for kw in smart_home_keywords):
        # These are smart home / security products, NOT cameras
        # Unless they are actual standalone camera products (like Sony, Canon actual cameras)
        camera_brands_real = ['sony alpha', 'canon eos', 'nikon z', 'fujifilm x', 'panasonic lumix',
                             'gopro hero', 'dji', 'insta360', 'kodak pixpro']
        if not any(cb in title for cb in camera_brands_real):
            return 'Smart Home'

    # ===== CAMERAS (actual cameras, lenses, photography equipment) =====
    camera_keywords = [
        'camera', 'mirrorless', 'dslr', 'camcorder', 'webcam', 'gopro',
        'lens', 'tripod', 'gimbal', 'drone', 'instax', 'film camera',
        'action camera', 'vlog camera', 'cinema camera',
    ]
    camera_brands = ['sony alpha', 'canon eos', 'canon rf', 'canon ef', 'nikon z',
                    'nikon nikkor', 'nikon d', 'fujifilm', 'panasonic lumix',
                    'gopro', 'dji', 'insta360', 'kodak pixpro', 'sigma',
                    'tamron', 'olympus', 'polaroid']
    
    # ===== STORAGE =====
    storage_keywords = [
        'ssd', 'hard drive', 'hdd', 'usb drive', 'flash drive', 'thumb drive',
        'memory card', 'sd card', 'micro sd', 'microsd', 'sdxc', 'sdhc',
        'external drive', 'internal drive', 'nvme', 'nas ',
        'seagate', 'western digital', 'wd ', 'crucial', 'samsung evo',
        'sandisk', 'kingston', 'portable ssd',
    ]
    if any(kw in title for kw in storage_keywords):
        # SD cards and memory cards that mention "camera" should go to Storage, not Cameras
        if any(s in title for s in ['memory card', 'sd card', 'micro sd', 'sdxc', 'sdhc', 'ssd', 
                                     'hard drive', 'hdd', 'flash drive', 'sandisk', 'seagate',
                                     'kingston', 'crucial', 'western digital', 'wd ']):
            return 'Storage'
    
    # ===== POWER & BATTERIES =====
    battery_keywords = [
        'battery', 'batteries', 'alkaline', 'nimh', 'energizer', 'duracell',
        'coppertop', 'lithium coin', 'power bank', 'ups ', 'rechargeable battery',
        'rechargeable batteries', 'battery pack', 'battery charger',
        'apc ups', 'apc back-ups',
    ]
    if any(kw in title for kw in battery_keywords):
        # Exclude camera-specific batteries (they belong in Cameras)
        # Exclude UPS that are already in correct category
        # Battery chargers for AA/AAA go to Power & Batteries
        if any(cam in title for cam in ['for alpha', 'for canon', 'for nikon', 'for sony', 
                                         'camera battery', 'for gopro', 'for dslr',
                                         'lp-e', 'np-f', 'en-el', 'npfz', 'nb-']):
            return 'Cameras'
        return 'Power & Batteries'
    
    # ===== CHARGERS & CABLES =====
    charger_cable_keywords = [
        'charger', 'cable', 'adapter', 'power cord', 'usb hub', 'docking station',
        'wall charger', 'car charger', 'lightning cable', 'usb-c cable',
        'charging pad', 'charging station', 'power strip', 'surge protector',
        'extension cord', 'hdmi cable', 'displayport cable', 'ethernet cable',
        'audio cable', 'speaker cable', 'rca cable', 'toslink', 'optical cable',
        'usb cable', 'usb extension', 'cord holder', 'card reader',
        'usb-a to', 'usb-c to', 'usb adapter', 'travel adapter',
    ]
    if any(kw in title for kw in charger_cable_keywords):
        # Modems and routers are Networking
        if any(n in title for n in ['modem', 'router', 'wifi', 'wi-fi']):
            return 'Networking'
        return 'Chargers & Cables'
    
    # ===== NETWORKING =====
    networking_keywords = [
        'router', 'modem', 'wifi extender', 'wi-fi extender', 'mesh',
        'access point', 'ethernet switch', 'network switch',
        'tp-link archer', 'netgear', 'arris', 'linksys', 'asus router',
    ]
    if any(kw in title for kw in networking_keywords):
        return 'Networking'
    
    # ===== TV & DISPLAY =====
    tv_display_keywords = [
        'monitor', 'television', ' tv ', ' tv,', 'display', 'projector',
        'smart tv', 'hdtv', 'oled tv', 'qled',
    ]
    if any(kw in title for kw in tv_display_keywords):
        if 'baby monitor' not in title and 'camera monitor' not in title:
            return 'TV & Display'
    
    # ===== HEADPHONES =====
    headphone_keywords = [
        'headphone', 'earbud', 'earphone', 'airpods', 'beats', 'sennheiser',
        'sony wh-', 'galaxy buds', 'jbl tune', 'headset', 'in-ear',
        'over-ear', 'on-ear', 'noise cancelling headphone',
    ]
    if any(kw in title for kw in headphone_keywords):
        if not any(ex in title for ex in ['case', 'cover', 'stand', 'hook', 'hanger']):
            return 'Headphones'
    
    # ===== SPEAKERS =====
    speaker_keywords = [
        'speaker', 'soundbar', 'sound bar', 'home theater', 'bluetooth speaker',
        'portable speaker', 'smart speaker', 'subwoofer',
    ]
    if any(kw in title for kw in speaker_keywords):
        if 'speaker cable' not in title and 'speaker wire' not in title and 'speaker stand' not in title:
            return 'Speakers'
    
    # ===== GAMING =====
    gaming_keywords = [
        'gaming', 'ps4', 'ps5', 'playstation', 'xbox', 'nintendo',
        'dualshock', 'dualsense', 'controller', 'joystick', 'gaming mouse',
        'gaming keyboard', 'console', 'switch lite', 'game controller',
    ]
    if any(kw in title for kw in gaming_keywords):
        return 'Gaming'
    
    # ===== WEARABLES =====
    wearable_keywords = [
        'smartwatch', 'smart watch', 'fitness tracker', 'apple watch',
        'galaxy watch', 'garmin', 'fitbit', 'mi band', 'amazfit',
    ]
    if any(kw in title for kw in wearable_keywords):
        return 'Wearables'
    
    # ===== PHONES =====
    phone_keywords = [
        'iphone', 'smartphone', 'galaxy s2', 'pixel phone', 'oneplus',
        'cell phone', 'android phone',
    ]
    if any(kw in title for kw in phone_keywords):
        if not any(ex in title for ex in ['case', 'cover', 'screen protector', 'mount', 'holder', 'charger', 'cable']):
            return 'Phones'
    
    # ===== LAPTOPS =====
    laptop_keywords = [
        'laptop', 'chromebook', 'macbook', 'thinkpad', 'zenbook',
        'surface book', 'ideapad', 'vivobook',
    ]
    laptop_excludes = [
        'battery', 'charger', 'adapter', 'cable', 'case', 'skin', 'stand', 'bag',
        'sleeve', 'mouse', 'keyboard', 'speaker', 'screen protector', 'for',
        'compatible', 'backpack', 'cooling pad', 'dock', 'hub',
    ]
    if any(kw in title for kw in laptop_keywords):
        if any(ti in title for ti in ['intel', 'amd', 'core i', 'ryzen', 'gb ram', 'windows', 'macos', 'chrome os']):
            return 'Laptops'
        if not any(ex in title for ex in laptop_excludes):
            return 'Laptops'
    
    return None  # Can't determine, keep current


# Analyze all products
products = Product.objects.select_related('category').all()
for p in products:
    total += 1
    correct = determine_correct_category(p)
    if correct and correct != p.category.name:
        misplaced.append({
            'id': p.id,
            'title': p.title[:120],
            'current': p.category.name,
            'should_be': correct,
        })

# Write report
with open('scratch/misplaced_report.txt', 'w', encoding='utf-8') as f:
    f.write(f"PRODUCT CATEGORY ANALYSIS REPORT\n")
    f.write(f"{'='*80}\n")
    f.write(f"Total products analyzed: {total}\n")
    f.write(f"Products in wrong category: {len(misplaced)}\n\n")
    
    # Group by current category
    from collections import defaultdict
    by_current = defaultdict(list)
    by_should = defaultdict(list)
    for m in misplaced:
        by_current[m['current']].append(m)
        by_should[m['should_be']].append(m)
    
    f.write(f"\n{'='*80}\n")
    f.write(f"MISPLACED PRODUCTS BY CURRENT (WRONG) CATEGORY\n")
    f.write(f"{'='*80}\n")
    for cat in sorted(by_current.keys()):
        items = by_current[cat]
        f.write(f"\n--- Currently in '{cat}' but SHOULD NOT BE ({len(items)} products) ---\n")
        for m in items:
            f.write(f"  [ID:{m['id']}] {m['title']}\n")
            f.write(f"    -> Should be: {m['should_be']}\n")
    
    f.write(f"\n{'='*80}\n")
    f.write(f"SUMMARY: MOVES NEEDED\n")
    f.write(f"{'='*80}\n")
    for cat in sorted(by_current.keys()):
        items = by_current[cat]
        moves = defaultdict(int)
        for m in items:
            moves[m['should_be']] += 1
        for dest, count in sorted(moves.items(), key=lambda x: -x[1]):
            f.write(f"  {cat} -> {dest}: {count} products\n")

print(f"Analysis complete! {len(misplaced)} misplaced products found out of {total}")
print(f"Report saved to scratch/misplaced_report.txt")
