"""
Management command to retrain ONLY the Content-Based Filter (TF-IDF) model
directly from the Django database. This is faster than full retraining and
ensures the model is built from clean, rich DB data including brand, category,
description, and price — all fields the user search queries rely on.
"""
import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from products.models import Product
from recommendation.engine.content_based import ContentBasedFilter
from recommendation.engine.preprocessing import build_product_feature_text
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retrain the TF-IDF Content-Based Filter model from the database products'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n  Retraining CBF (TF-IDF + Cosine Similarity) from DB\n{'='*60}\n"
        ))

        # Load all active products from the database
        self.stdout.write("Loading products from database...")
        qs = Product.objects.filter(is_active=True).select_related('category')
        if not qs.exists():
            self.stdout.write(self.style.ERROR("No active products found in the database!"))
            return

        # Build a DataFrame with all rich fields
        rows = []
        for p in qs:
            rows.append({
                'asin': p.asin,
                'product_title': p.title,
                'product_category': p.category.name if p.category else '',
                'brand': p.brand or '',
                'description': p.description or '',
                'price': float(p.price) if p.price else 0.0,
                'discounted_price': float(p.price) if p.price else 0.0,
                'original_price': float(p.price) if p.price else 0.0,
                'sustainability_tags': '',
                'is_best_seller': '',
            })

        products_df = pd.DataFrame(rows).set_index('asin')
        self.stdout.write(f"  Loaded {len(products_df)} products from DB")
        self.stdout.write(f"  Categories: {products_df['product_category'].nunique()} unique")
        self.stdout.write(f"  Brands: {products_df['brand'].nunique()} unique")

        # Build enriched feature text
        self.stdout.write("\nBuilding enriched product feature text (title + brand + category + description + price + colors + features)...")
        product_texts = build_product_feature_text(products_df)

        # Sample output for verification
        first_asin = product_texts.index[0]
        self.stdout.write(f"\n  Sample feature text for '{products_df.loc[first_asin, 'product_title'][:60]}':")
        self.stdout.write(f"  > {product_texts.iloc[0][:200]}...")

        # Fit TF-IDF with increased features for richer vocabulary
        self.stdout.write("\nFitting TF-IDF vectorizer (max_features=8000)...")
        cbf = ContentBasedFilter(max_features=8000)
        cbf.fit(product_texts)

        vocab_size = len(cbf.vectorizer.vocabulary_)
        self.stdout.write(f"  Vocabulary size: {vocab_size}")
        self.stdout.write(f"  Matrix shape: {cbf.matrix.shape}")

        # Save model
        cbf_path = os.path.join(settings.BASE_DIR, 'models', 'saved', 'cbf_model.joblib')
        os.makedirs(os.path.dirname(cbf_path), exist_ok=True)
        cbf.save(cbf_path)
        self.stdout.write(self.style.SUCCESS(f"  Model saved to {cbf_path}"))

        # Quick quality test
        self.stdout.write(self.style.SUCCESS("\n--- Quick Quality Test ---"))
        test_queries = [
            "gaming laptop with good graphics",
            "cheap wireless headphones",
            "bluetooth speaker portable",
            "smartwatch fitness tracker",
            "usb charging cable type c",
        ]
        for q in test_queries:
            recs = cbf.get_recommendations_from_text(q, n=3)
            self.stdout.write(f"\nQuery: '{q}'")
            for asin, score in recs:
                try:
                    p = qs.get(asin=asin)
                    self.stdout.write(f"  [{score:.3f}] {p.title[:70]} ({p.category.name})")
                except Product.DoesNotExist:
                    self.stdout.write(f"  [{score:.3f}] {asin}")

        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("  CBF Retraining complete!"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))
