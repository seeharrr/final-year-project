"""
Management command to re-assign products to the correct category based
on keyword rules derived from the product title.

Usage:
    python manage.py recategorize_products
    python manage.py recategorize_products --dry-run   (preview only)
"""

from django.core.management.base import BaseCommand
from products.models import Product, Category


# ---------------------------------------------------------------------------
# Category rules
# Each entry: (category_slug, must_contain_any, must_NOT_contain_any)
# Rules are evaluated in order; first match wins.
# ---------------------------------------------------------------------------
CATEGORY_RULES = [
    # ---- Laptops -----------------------------------------------------------
    (
        'laptops',
        ['laptop', 'notebook', 'chromebook', 'macbook', 'thinkpad', 'zenbook',
         'vivobook', 'ideapad', 'inspiron laptop', 'pavilion laptop', 'ultrabook'],
        ['case', 'sleeve', 'bag', 'charger', 'battery', 'skin', 'cover', 'stand', 'cooler', 'adapter', 'cable', 'backpack', 'keyboard', 'mouse', 'desk', 'lap desk', 'pad', 'hub', 'dock', 'headphone', 'speaker'],
    ),

    # ---- Printers & Scanners -----------------------------------------------
    (
        'printers-scanners',
        ['printer', 'scanner', 'inkjet', 'laserjet', 'toner', 'ink cartridge',
         'print head', 'printhead', 'multifunction printer'],
        [],
    ),

    # ---- Gaming ------------------------------------------------------------
    (
        'gaming',
        ['gaming', 'game controller', 'gamepad', 'joystick', 'playstation',
         'ps4', 'ps5', 'xbox', 'nintendo switch', 'nintendo 3ds',
         'steam deck', 'gaming mouse', 'gaming keyboard', 'gaming headset',
         'gaming monitor', 'gaming chair', 'gaming pc', 'gaming laptop',
         'console', 'game cartridge', 'video game'],
        [],
    ),

    # ---- Cameras -----------------------------------------------------------
    (
        'cameras',
        ['camera', 'camcorder', 'dslr', 'mirrorless', 'action cam',
         'gopro', 'dashcam', 'dash cam', 'webcam', 'security camera',
         'ip camera', 'surveillance camera', 'trail camera',
         'photography', 'polaroid'],
        ['case', 'bag', 'strap', 'mount', 'lens', 'tripod', 'battery', 'charger', 'film', 'flash', 'light', 'filter', 'memory card', 'sd card', 'cable', 'cover'],
    ),

    # ---- Headphones --------------------------------------------------------
    (
        'headphones',
        ['headphone', 'earphone', 'earbuds', 'earbud', 'headset',
         'in-ear', 'over-ear', 'on-ear', 'airpods', 'noise cancelling',
         'noise-cancelling', 'wireless earbuds'],
        [],
    ),

    # ---- Speakers ----------------------------------------------------------
    (
        'speakers',
        ['speaker', 'soundbar', 'subwoofer', 'bluetooth speaker',
         'portable speaker', 'home theater', 'home theatre',
         'stereo system', 'boombox', 'boom box'],
        [],
    ),

    # ---- TV & Display ------------------------------------------------------
    (
        'tv-display',
        ['television', ' tv ', 'smart tv', 'oled tv', 'qled tv', '4k tv',
         '8k tv', 'led tv', 'monitor', 'display', 'projector',
         'streaming stick', 'fire tv', 'roku', 'chromecast',
         'apple tv', 'android tv'],
        [],
    ),

    # ---- Phones ------------------------------------------------------------
    (
        'phones',
        ['smartphone', 'iphone', 'android phone', 'mobile phone',
         'cell phone', 'samsung galaxy', 'pixel phone', 'oneplus',
         'flip phone', 'feature phone', 'unlocked phone'],
        [],
    ),

    # ---- Wearables ---------------------------------------------------------
    (
        'wearables',
        ['smartwatch', 'smart watch', 'fitness tracker', 'fitness band',
         'activity tracker', 'apple watch', 'galaxy watch', 'fitbit',
         'garmin watch', 'wearable', 'smart band', 'health tracker'],
        [],
    ),

    # ---- Smart Home --------------------------------------------------------
    (
        'smart-home',
        ['smart home', 'smart bulb', 'smart plug', 'smart switch',
         'smart thermostat', 'smart lock', 'smart doorbell', 'smart speaker',
         'alexa', 'echo dot', 'echo show', 'google home', 'google nest',
         'smart hub', 'zigbee', 'z-wave', 'home automation',
         'smart sensor', 'motion sensor', 'door sensor',
         'robot vacuum', 'robotic vacuum'],
        [],
    ),

    # ---- Networking --------------------------------------------------------
    (
        'networking',
        ['router', 'modem', 'wifi extender', 'wi-fi extender',
         'network switch', 'ethernet switch', 'access point',
         'mesh network', 'range extender', 'network adapter',
         'powerline adapter', 'vpn router', 'nas ', 'nas drive',
         'ethernet cable', 'cat6', 'cat7', 'cat8', 'rj45'],
        [],
    ),

    # ---- Storage -----------------------------------------------------------
    (
        'storage',
        ['hard drive', 'solid state drive', ' ssd', 'hdd ', 'flash drive',
         'usb drive', 'thumb drive', 'memory card', 'microsd', 'micro sd',
         'sd card', 'cf card', 'compact flash', 'external drive',
         'internal drive', 'nas storage', 'portable drive',
         'optical drive', 'dvd drive', 'blu-ray drive'],
        [],
    ),

    # ---- Power & Batteries -------------------------------------------------
    (
        'power-batteries',
        ['power bank', 'powerbank', 'battery pack', 'portable charger',
         'aa battery', 'aaa battery', 'lithium battery', 'rechargeable battery',
         'ups ', 'uninterruptible power', 'surge protector', 'power strip',
         'extension cord', 'outlet', 'power conditioner'],
        [],
    ),

    # ---- Chargers & Cables -------------------------------------------------
    (
        'chargers-cables',
        ['charger', 'charging cable', 'usb cable', 'usb-c cable',
         'lightning cable', 'micro usb cable', 'thunderbolt cable',
         'hdmi cable', 'displayport cable', 'vga cable', 'dvi cable',
         'audio cable', 'aux cable', 'power cable', 'ac adapter',
         'wall charger', 'car charger', 'wireless charger',
         'fast charger', 'quick charge', 'charging dock',
         'usb hub', 'usb splitter', 'dock station', 'docking station',
         'cable organizer', 'cable tie', 'cable management',
         'hdmi adapter', 'usb adapter', 'type-c adapter',
         'lightning adapter'],
        [],
    ),

    # ---- Accessories & Other (catch-all) ----------------------------------
    (
        'accessories-other',
        [],   # no must-have keywords — this is the final fallback
        [],
    ),
]


def classify_title(title: str) -> str:
    """Return the best-matching category slug for a given product title."""
    lower = title.lower()

    for slug, must_have, must_not in CATEGORY_RULES:
        # If must_have is empty it's the catch-all → always matches
        if must_have and not any(kw in lower for kw in must_have):
            continue
        if must_not and any(kw in lower for kw in must_not):
            continue
        return slug

    return 'accessories-other'  # ultimate fallback


class Command(BaseCommand):
    help = 'Re-assign every active product to the correct category based on title keywords.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Preview changes without saving to the database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Pre-fetch all categories into a slug → Category map
        cat_map = {c.slug: c for c in Category.objects.all()}
        missing_slugs = set()

        # Validate that every slug in our rules exists in the DB
        for slug, _, _ in CATEGORY_RULES:
            if slug not in cat_map:
                missing_slugs.add(slug)
        if missing_slugs:
            self.stderr.write(
                self.style.ERROR(
                    f'Missing categories in DB: {missing_slugs}. '
                    f'Please create them first.'
                )
            )
            return

        products = Product.objects.filter(is_active=True).select_related('category')
        total = products.count()
        self.stdout.write(f'Processing {total} active products …')

        changed = 0
        unchanged = 0
        category_counts = {slug: 0 for slug, _, _ in CATEGORY_RULES}

        bulk_update = []

        for product in products.iterator(chunk_size=500):
            new_slug = classify_title(product.title)
            new_cat = cat_map[new_slug]
            category_counts[new_slug] += 1

            if product.category_id != new_cat.pk:
                product.category = new_cat
                changed += 1
                if not dry_run:
                    bulk_update.append(product)
            else:
                unchanged += 1

            # Flush every 500 records
            if not dry_run and len(bulk_update) >= 500:
                Product.objects.bulk_update(bulk_update, ['category'])
                bulk_update = []

        # Final flush
        if not dry_run and bulk_update:
            Product.objects.bulk_update(bulk_update, ['category'])

        mode = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n{mode}Done! {changed} products re-assigned, {unchanged} already correct.'
        ))
        self.stdout.write('\nFinal category distribution:')
        for slug, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            cat_name = cat_map[slug].name
            self.stdout.write(f'  {cat_name:<30} {count:>5} products')
