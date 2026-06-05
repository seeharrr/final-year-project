"""
Fix product categories - comprehensive recategorization script.
Moves products to the correct category based on careful keyword analysis.
"""
import os, sys, django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_recs.settings')
django.setup()

from products.models import Product, Category
from django.utils.text import slugify
from collections import defaultdict

# Ensure all categories exist
CATEGORIES = [
    'Accessories & Other', 'Wearables', 'Speakers', 'Headphones',
    'TV & Display', 'Networking', 'Gaming', 'Phones',
    'Printers & Scanners', 'Power & Batteries', 'Other Electronics',
    'Cameras', 'Smart Home', 'Storage', 'Chargers & Cables', 'Laptops'
]

cat_objs = {}
for name in CATEGORIES:
    cat, _ = Category.objects.get_or_create(name=name, defaults={'slug': slugify(name)})
    cat_objs[name] = cat


def classify_product(title_original):
    """Return the correct category name for a product, or None if unsure."""
    title = title_original.lower()
    
    # ==========================================
    # HIGHEST PRIORITY: Protection plans / warranties
    # ==========================================
    if any(kw in title for kw in ['protection plan', 'asurion', 'service plan', 'extended warranty']):
        return 'Accessories & Other'
    
    # ==========================================
    # PRINTERS & SCANNERS (ink, toner, printers, scanners, paper)
    # ==========================================
    # Direct printer/scanner products
    if any(kw in title for kw in ['printer', 'scanner', 'imageclass', 'imageformula', 'imageprog',
                                   'megatank', 'selphy', 'pixma', 'copy paper']):
        return 'Printers & Scanners'
    
    # Ink cartridges and toner (Canon, HP, Epson, E-Z Ink etc.)
    # Careful: only if they clearly indicate ink/toner for a printer
    ink_toner_patterns = [
        'ink cartridge', 'toner cartridge', 'ink bottle', 'ink tank', 'ink value pack',
        'ink pack', 'genuine ink', 'ink replacement',
        'printhead', 'print head', 'maintenance cartridge',
        'photo paper', 'color ink paper set',
    ]
    if any(kw in title for kw in ink_toner_patterns):
        return 'Printers & Scanners'
    
    # Canon CLI/PGI/PG/CL/PFI/GI ink products (very specific Canon printer consumables)
    canon_ink_prefixes = ['canon cli-', 'canon pgi-', 'canon pg-', 'canon cl-', 'canon pfi-',
                          'canon gi-', 'canon crg', 'canon genuine 0', 'canon genuine 1',
                          'canon mc-g', 'canon 045', 'canonpg-', 'canoncl-',
                          'e-z ink', 'canon color ink', 'canon toner',
                          'matte black ink 55ml']
    if any(title.startswith(kw) or kw in title for kw in canon_ink_prefixes):
        if not any(cam in title for cam in ['camera body', 'mirrorless camera', 'dslr camera']):
            return 'Printers & Scanners'
    
    # Canon RP-108, KP-108 (printer paper/ink sets)
    if any(kw in title for kw in ['rp-108', 'kp-108', 'qx20 color ink']):
        return 'Printers & Scanners'
    
    # Kodak printer products
    if any(kw in title for kw in ['kodak dock', 'kodak scanza', 'kodak phc-']):
        return 'Printers & Scanners'
    
    # ==========================================
    # SMART HOME (security cameras, smart plugs, doorbells, etc.)
    # ==========================================
    # Security cameras and home security systems
    security_brands = ['arlo', 'reolink', 'lorex', 'eufy security', 'eufycam',
                       'blink mini', 'blink outdoor', 'blink indoor', 'blink video',
                       'wyze cam', 'wyze floodlight', 'wyze wireless',
                       'simplisafe', 'ring alarm', 'ring video doorbell',
                       'ring floodlight', 'ring spotlight', 'ring indoor',
                       'ecobee smart', 'ecobee video',
                       'feit electric', 'tactacam defend']
    if any(kw in title for kw in security_brands):
        return 'Smart Home'
    
    # Security camera keywords
    if any(kw in title for kw in ['security camera', 'home security', 'doorbell camera',
                                   'floodlight camera', 'video doorbell',
                                   'baby monitor', 'pet cam', 'indoor camera',
                                   'outdoor camera for home']):
        # Exclude actual camera brands
        real_camera_brands = ['canon eos', 'sony alpha', 'nikon z', 'nikon d',
                             'fujifilm x-', 'panasonic lumix s', 'gopro hero',
                             'dji osmo', 'dji mini', 'dji air', 'dji avata',
                             'insta360 x', 'insta360 go', 'kodak pixpro']
        if not any(cb in title for cb in real_camera_brands):
            return 'Smart Home'
    
    # Tapo / Kasa smart cameras
    if any(kw in title for kw in ['tapo', 'kasa smart', 'kasa indoor']):
        return 'Smart Home'
    
    # Smart home devices (bulbs, plugs, etc.)
    if any(kw in title for kw in ['smart plug', 'smart bulb', 'smart lock', 'thermostat',
                                   'echo dot', 'echo show', 'echo pop', 'fire tv stick',
                                   'amazon echo', 'smart display']):
        return 'Smart Home'
    
    # Seagate Skyhawk (surveillance HDDs) - these are for security systems
    if 'skyhawk' in title:
        return 'Storage'
    
    # ==========================================
    # LAPTOPS
    # ==========================================
    laptop_identifiers = ['laptop', 'chromebook', 'macbook', 'thinkpad', 'zenbook',
                         'surface book', 'surface laptop', 'ideapad', 'vivobook',
                         'swift ', 'aspire ']
    laptop_tech_proof = ['intel', 'amd', 'core i', 'ryzen', 'gb ram', 'ssd', 
                        'windows', 'macos', 'chrome os', '16gb', '8gb', '32gb',
                        'i5', 'i7', 'i9', 'processor']
    laptop_excludes = ['battery', 'charger', 'adapter', 'cable', 'case', 'skin', 'stand',
                      'bag', 'sleeve', 'mouse', 'keyboard', 'speaker', 'screen protector',
                      'for laptop', 'compatible', 'backpack', 'cooling pad', 'dock', 'hub',
                      'mount', 'cover', 'replacement', 'webcam', 'fan ', 'stylus',
                      'protection plan', 'warranty', 'tote', 'holder', 'lap desk',
                      'sticker', 'decal']
    
    if any(kw in title for kw in laptop_identifiers):
        # If it has tech specs, it's likely a real laptop
        has_tech = any(t in title for t in laptop_tech_proof)
        has_excludes = any(ex in title for ex in laptop_excludes)
        
        if 'notebook' in title and not has_tech:
            pass  # Paper notebook
        elif has_tech and not has_excludes:
            return 'Laptops'
        elif not has_excludes and any(kw in title for kw in ['laptop', 'chromebook', 'macbook', 'thinkpad']):
            return 'Laptops'
    
    # ==========================================
    # PHONES (actual phones, not phone accessories)
    # ==========================================
    phone_excludes = ['case', 'cover', 'screen protector', 'mount', 'holder',
                     'charger', 'cable', 'stand', 'ring', 'wallet', 'grip',
                     'tempered glass', 'film', 'strap', 'armband', 'belt clip',
                     'pouch', 'car mount', 'cradle', 'dock', 'adapter', 'headphone',
                     'earbud', 'speaker', 'battery', 'power bank', 'tripod',
                     'selfie stick', 'gimbal', 'microphone', 'for iphone', 'for samsung',
                     'for galaxy', 'for pixel', 'compatible with', 'replacement']
    
    if any(kw in title for kw in ['iphone 1', 'iphone se', 'samsung galaxy s2', 'samsung galaxy s3',
                                   'google pixel', 'oneplus ']):
        if not any(ex in title for ex in phone_excludes):
            return 'Phones'
    
    if 'smartphone' in title or 'cell phone' in title or 'android phone' in title:
        if not any(ex in title for ex in phone_excludes):
            return 'Phones'
    
    # ==========================================
    # HEADPHONES
    # ==========================================
    headphone_keywords = ['headphone', 'earbud', 'earphone', 'airpods', 'galaxy buds',
                         'headset', 'in-ear monitor', 'beats solo', 'beats studio',
                         'beats fit', 'beats flex', 'beats powerbeats',
                         'sony wh-', 'sony wf-', 'bose quietcomfort', 
                         'sennheiser momentum', 'sennheiser hd',
                         'jbl tune', 'jbl live', 'jbl vibe',
                         'jabra elite', 'jabra evolve',
                         'skullcandy', 'audio-technica ath-']
    headphone_excludes = ['headphone case', 'headphone stand', 'headphone hook',
                         'headphone hanger', 'headphone adapter', 'headphone cable',
                         'for headphone', 'headphone holder', 'headphone rack']
    
    if any(kw in title for kw in headphone_keywords):
        if not any(ex in title for ex in headphone_excludes):
            return 'Headphones'
    
    # ==========================================
    # SPEAKERS
    # ==========================================
    speaker_keywords = ['speaker', 'soundbar', 'sound bar', 'home theater system',
                       'bluetooth speaker', 'portable speaker', 'subwoofer',
                       'party speaker', 'tower speaker',
                       'echo pop', 'homepod']
    speaker_excludes = ['speaker cable', 'speaker wire', 'speaker stand', 'speaker mount',
                       'speaker bracket', 'for speaker', 'speaker cover', 'speaker bag',
                       'speaker adapter', 'headphone', 'earphone', 'gaming speaker']
    
    if any(kw in title for kw in speaker_keywords):
        if not any(ex in title for ex in speaker_excludes):
            return 'Speakers'
    
    # ==========================================
    # GAMING
    # ==========================================
    gaming_keywords = ['gaming mouse', 'gaming keyboard', 'gaming headset',
                      'gaming controller', 'gaming chair', 'gaming monitor',
                      'playstation', 'ps4', 'ps5', 'xbox', 'nintendo switch',
                      'dualsense', 'dualshock', 'joy-con', 'joycon',
                      'razer ', 'corsair ', 'steelseries ', 'hyperx ',
                      'logitech g pro', 'logitech g502', 'logitech g305',
                      'game controller', 'gaming pad', 'fight stick',
                      'nintendo switch 2', 'switch 2']
    gaming_products = ['for streaming', 'for gaming']
    
    if any(kw in title for kw in gaming_keywords):
        return 'Gaming'
    
    # ==========================================
    # WEARABLES
    # ==========================================
    wearable_keywords = ['smartwatch', 'smart watch', 'fitness tracker',
                        'apple watch', 'galaxy watch', 'garmin ',
                        'fitbit', 'amazfit', 'mi band',
                        'fitness band']
    wearable_excludes = ['watch band', 'watch strap', 'watch charger', 'watch case',
                        'watch screen protector', 'for apple watch', 'for galaxy watch',
                        'for garmin', 'for fitbit', 'watch adapter', 'watch stand',
                        'watch dock']
    
    if any(kw in title for kw in wearable_keywords):
        if not any(ex in title for ex in wearable_excludes):
            return 'Wearables'
    
    # ==========================================
    # CAMERAS (actual cameras, lenses, photography gear)
    # ==========================================
    # NOTE: security cameras are handled above under Smart Home
    camera_brands = ['canon eos', 'sony alpha', 'nikon z5', 'nikon z6', 'nikon z7', 'nikon z8',
                    'nikon z50', 'nikon z f', 'nikon d', 'nikon coolpix',
                    'fujifilm instax', 'fujifilm x-', 'fujifilm x100',
                    'panasonic lumix', 'olympus tough',
                    'gopro hero', 'gopro max', 'gopro ', 'dji mini', 'dji air', 
                    'dji avata', 'dji fpv', 'dji neo', 'dji osmo',
                    'dji rs ', 'insta360', 'kodak pixpro', 'kodak fun', 'kodak ektar',
                    'polaroid now', 'polaroid go', 'polaroid flip',
                    'blackmagic', 'ricoh theta', 'pentax 17', 'leica d-lux']
    
    if any(kw in title for kw in camera_brands):
        return 'Cameras'
    
    # Camera lenses
    lens_brands = ['sigma ', 'tamron ', 'canon rf', 'canon ef', 'nikon nikkor',
                  'sony e ', 'sony fe ', 'sony sel', 'ttartisan', 'viltrox']
    lens_indicators = ['lens', 'f/', 'f1.', 'f2.', 'f4', 'f5.', 'mm ']
    
    if any(kw in title for kw in lens_brands) and any(li in title for li in lens_indicators):
        return 'Cameras'
    
    # Camera accessories (tripods, gimbals, flashes, bags, straps)
    camera_accessories = ['tripod', 'gimbal', 'camera strap', 'camera bag',
                         'camera backpack', 'camera case', 'camera sling',
                         'camera flash', 'speedlite', 'speedlight',
                         'camera mount', 'camera clip', 'camera wrist',
                         'godox', 'neewer', 'manfrotto', 'joby', 'sirui',
                         'peak design', 'pelican vault',
                         'gopro mount', 'gopro accessory', 'gopro handler',
                         'gopro head strap', 'gopro chest mount', 'gopro suction',
                         'gopro light mod', 'gopro media mod', 'gopro volta',
                         'gopro fetch', 'gopro bite', 'gopro floaty',
                         'gopro grab bag', 'gopro extension', 'gopro shorty',
                         'gopro protective', 'gopro performance',
                         'dslr', 'mirrorless', 'camcorder',
                         'webcam', 'logitech brio', 'logitech c270', 'logitech c920',
                         'logitech c922', 'logitech c930', 'logitech mx brio',
                         'logitech streamcam', 'logitech ptz',
                         'elgato cam link', 'elgato facecam',
                         'feelworld', 'atomos', 'bagsmart', 'mosiso camera',
                         'pgytech', 'drone', 'holy stone', 'deerc',
                         'action camera', 'vlog camera',
                         'disposable camera', 'film camera', 'instant camera',
                         'quick release plate', 'ball head',
                         'camera field monitor',
                         'binocular', 'binoculars']
    
    if any(kw in title for kw in camera_accessories):
        return 'Cameras'
    
    # Fujifilm Instax film
    if 'instax' in title or 'fujifilm' in title:
        return 'Cameras'
    
    # ==========================================
    # TV & DISPLAY  
    # ==========================================
    tv_keywords = ['monitor', 'television', ' tv ', ' tv,', 'smart tv',
                  'projector', 'hdtv', 'oled tv', 'qled', 'roku tv',
                  'fire tv', 'apple tv', 'chromecast', 'streaming stick',
                  'roku express', 'roku streaming']
    tv_excludes = ['baby monitor', 'camera monitor', 'camera field monitor',
                  'for monitor', 'monitor stand', 'monitor arm', 'monitor mount',
                  'monitor cable', 'fire tv stick']
    
    if any(kw in title for kw in tv_keywords):
        if not any(ex in title for ex in tv_excludes):
            return 'TV & Display'
    
    # Radar detectors (these had 'camera' in title)
    if any(kw in title for kw in ['radar detector', 'laser detector', 'laser/radar']):
        return 'Other Electronics'
    
    # Car stereo receivers (Pioneer, Pyle) — these are electronics
    if any(kw in title for kw in ['car stereo', 'car receiver', 'head unit', 'double din',
                                   'single din', 'pioneer avh', 'pioneer dmh', 'pyle ']):
        return 'Other Electronics'
    
    # ==========================================
    # STORAGE (SSD, HDD, memory cards, NAS, flash drives)
    # ==========================================
    storage_keywords = ['ssd', 'hard drive', 'hdd', 'usb flash drive', 'thumb drive',
                       'memory card', 'sd card', 'micro sd', 'microsd', 'sdxc', 'sdhc',
                       'external drive', 'internal drive', 'nvme', ' nas ',
                       'portable ssd', 'flash drive', 'usb drive',
                       'docking station for', 'sata to usb', 'ssd enclosure',
                       'hard drive dock', 'sata external']
    storage_brands = ['sandisk', 'seagate', 'western digital', 'wd ', 'crucial ',
                     'kingston', 'samsung evo', 'samsung pro', 'lexar',
                     'pny ', 'transcend ', 'sabrent']
    
    if any(kw in title for kw in storage_keywords):
        return 'Storage'
    
    if any(kw in title for kw in storage_brands):
        if any(s in title for s in ['memory', 'sd', 'ssd', 'drive', 'storage',
                                     'card', 'micro', 'flash', 'usb ']):
            return 'Storage'
    
    # ==========================================
    # POWER & BATTERIES
    # ==========================================
    power_keywords = ['battery pack', 'batteries', 'alkaline', 'rechargeable batter',
                     'power bank', 'ups battery', 'portable charger',
                     'energizer', 'duracell', 'coppertop',
                     'apc ups', 'apc back-ups', 'battery backup',
                     'surge protector', 'power strip',
                     'eneloop', 'nimh', 'li-ion battery',
                     'solar panel', 'solar charger']
    power_excludes = ['for alpha', 'for canon', 'for nikon', 'for sony camera',
                     'camera battery', 'for gopro', 'for dslr',
                     'lp-e', 'np-f', 'en-el', 'npfz', 'nb-', 'bp-',
                     'battery grip', 'gopro enduro']
    
    if any(kw in title for kw in power_keywords):
        if not any(ex in title for ex in power_excludes):
            return 'Power & Batteries'
    
    # ==========================================
    # CHARGERS & CABLES
    # ==========================================
    charger_cable_kw = ['charger', 'charging cable', 'charging pad', 'charging station',
                       'cable', 'adapter', 'power adapter',
                       'usb hub', 'usb-c hub', 'thunderbolt dock',
                       'docking station',
                       'hdmi cable', 'hdmi to', 'displayport cable',
                       'audio cable', 'toslink', 'optical cable',
                       'usb extension', 'usb cable', 'usb-a to', 'usb-c to',
                       'lightning cable', 'magsafe',
                       'wall charger', 'car charger', 'fast charger',
                       'wireless charger', 'qi charger',
                       'travel adapter', 'plug adapter',
                       'cord holder', 'cable management']
    charger_excludes = ['modem', 'router', 'wifi', 'wi-fi', 'mesh',
                       'speaker', 'headphone', 'earbud', 'airpod',
                       'battery charger for aa', 'battery charger for aaa',
                       'rechargeable aa', 'rechargeable aaa',
                       'nimh', 'eneloop']
    
    if any(kw in title for kw in charger_cable_kw):
        # Modems and routers are Networking
        if any(n in title for n in ['modem', 'router', 'wifi extender', 'wi-fi extender']):
            return 'Networking'
        if not any(ex in title for ex in charger_excludes):
            return 'Chargers & Cables'
    
    # ==========================================
    # NETWORKING
    # ==========================================
    networking_kw = ['router', 'modem', 'mesh wifi', 'mesh wi-fi', 'wifi extender',
                    'wi-fi extender', 'access point', 'network switch',
                    'ethernet switch', 'wifi adapter', 'wi-fi adapter',
                    'wifi card', 'wi-fi card', 'pcie wifi',
                    'range extender', 'signal booster',
                    'tp-link archer', 'netgear nighthawk', 'netgear orbi',
                    'arris ', 'linksys', 'asus router',
                    'ubiquiti', 'unifi']
    
    if any(kw in title for kw in networking_kw):
        return 'Networking'
    
    return None  # Can't confidently determine


# ==========================================
# RUN THE FIX
# ==========================================
products = Product.objects.select_related('category').all()
total = 0
updated = 0
moves = defaultdict(lambda: defaultdict(int))
details = []

for p in products:
    total += 1
    correct_cat_name = classify_product(p.title)
    
    if correct_cat_name and correct_cat_name != p.category.name:
        old_cat = p.category.name
        new_cat = cat_objs[correct_cat_name]
        p.category = new_cat
        p.save(update_fields=['category'])
        updated += 1
        moves[old_cat][correct_cat_name] += 1
        details.append(f"  [{p.id}] {p.title[:100]}")
        details.append(f"    {old_cat} -> {correct_cat_name}")

# Write results
with open('scratch/fix_results.txt', 'w', encoding='utf-8') as f:
    f.write(f"CATEGORY FIX RESULTS\n")
    f.write(f"{'='*80}\n")
    f.write(f"Total products: {total}\n")
    f.write(f"Products moved: {updated}\n\n")
    
    f.write(f"SUMMARY OF MOVES:\n")
    f.write(f"{'-'*80}\n")
    for old_cat in sorted(moves.keys()):
        for new_cat, count in sorted(moves[old_cat].items(), key=lambda x: -x[1]):
            f.write(f"  {old_cat} -> {new_cat}: {count}\n")
    
    f.write(f"\n{'='*80}\n")
    f.write(f"DETAIL:\n")
    f.write(f"{'='*80}\n")
    for line in details:
        f.write(line + "\n")

# Print category counts after fix
f2 = open('scratch/category_counts_after.txt', 'w', encoding='utf-8')
f2.write("CATEGORY COUNTS AFTER FIX\n")
f2.write("="*50 + "\n")
for c in Category.objects.all().order_by('name'):
    count = c.products.count()
    f2.write(f"  {c.name}: {count} products\n")
    print(f"  {c.name}: {count} products")
f2.close()

print(f"\nDone! Moved {updated} products out of {total} total.")
print(f"Results saved to scratch/fix_results.txt")
