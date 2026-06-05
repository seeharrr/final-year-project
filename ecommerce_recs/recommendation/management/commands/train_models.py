import os
import pandas as pd
import numpy as np
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.text import slugify
from recommendation.engine.preprocessing import (
    load_amazon_dataset, deduplicate_products, generate_synthetic_interactions,
    filter_sparse_data, build_product_feature_text, prepare_interaction_matrix
)
from recommendation.engine.collaborative import CollaborativeFilter
from recommendation.engine.content_based import ContentBasedFilter
from recommendation.evaluation.metrics import run_full_evaluation
from recommendation.models import ModelMetadata
from products.models import Product, Category
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Train the recommendation models on real product data and sync to database'

    def add_arguments(self, parser):
        parser.add_argument('--dataset-path', type=str, required=True,
                          help='Path to Amazon products sales CSV')
        parser.add_argument('--sync-db', action='store_true',
                          help='Sync ALL products to the Django database')
        parser.add_argument('--num-users', type=int, default=200,
                          help='Number of synthetic users to generate (default: 200)')
        parser.add_argument('--interactions-per-user', type=int, default=25,
                          help='Average interactions per user (default: 25)')
        parser.add_argument('--n-factors', type=int, default=50,
                          help='Number of SVD factors (default: 50)')

    def handle(self, *args, **options):
        dataset_path = options['dataset_path']
        sync_db = options['sync_db']
        num_users = options['num_users']
        interactions_per_user = options['interactions_per_user']
        n_factors = options['n_factors']
        
        self.stdout.write(self.style.SUCCESS(
            f"\n{'='*60}\n  AI Recommendation System — Model Training\n{'='*60}\n"
        ))
        
        # ─────────────────────────────────────────────────
        # STEP 1: Load and prepare product catalog
        # ─────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(f"[1/6] Loading product catalog from {dataset_path}..."))
        products_df = load_amazon_dataset(dataset_path)
        self.stdout.write(f"  Loaded {len(products_df)} raw rows")
        
        # Deduplicate by title
        unique_products_df = deduplicate_products(products_df)
        self.stdout.write(f"  {len(unique_products_df)} unique products after deduplication")
        self.stdout.write(f"  Categories: {unique_products_df['product_category'].nunique()}")
        
        # ─────────────────────────────────────────────────
        # STEP 2: Generate synthetic user interactions
        # ─────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f"\n[2/6] Generating synthetic interactions ({num_users} users, ~{interactions_per_user} each)..."
        ))
        interactions_df = generate_synthetic_interactions(
            unique_products_df, 
            num_users=num_users,
            avg_interactions_per_user=interactions_per_user
        )
        self.stdout.write(f"  Generated {len(interactions_df)} total interactions")
        
        # Filter sparse data
        self.stdout.write("  Filtering sparse users/products...")
        interactions_df = filter_sparse_data(interactions_df, min_user_ratings=5, min_product_ratings=3)
        self.stdout.write(f"  After filtering: {len(interactions_df)} interactions, "
                         f"{interactions_df['reviewerID'].nunique()} users, "
                         f"{interactions_df['asin'].nunique()} products")
        
        # ─────────────────────────────────────────────────
        # STEP 3: Train Collaborative Filter (SVD)
        # ─────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(f"\n[3/6] Training Collaborative Filter (SVD, {n_factors} factors)..."))
        
        matrix, user_to_idx, idx_to_user, product_to_idx, idx_to_product = prepare_interaction_matrix(interactions_df)
        
        cf = CollaborativeFilter(n_factors=n_factors)
        cf_metrics = cf.train(matrix, user_to_idx, idx_to_user, product_to_idx, idx_to_product)
        
        cf_path = os.path.join(settings.BASE_DIR, 'models', 'saved', 'cf_model.joblib')
        os.makedirs(os.path.dirname(cf_path), exist_ok=True)
        cf.save(cf_path)
        
        self.stdout.write(f"  RMSE: {cf_metrics['rmse_mean']:.4f}")
        self.stdout.write(f"  MAE:  {cf_metrics['mae_mean']:.4f}")
        self.stdout.write(f"  Variance explained: {cf_metrics.get('explained_variance', 0):.2%}")
        self.stdout.write(f"  Model saved to {cf_path}")
        
        # ─────────────────────────────────────────────────
        # STEP 4: Train Content-Based Filter (TF-IDF)
        # ─────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("\n[4/6] Training Content-Based Filter (TF-IDF)..."))
        
        cbf_products = unique_products_df.set_index('asin')
        product_texts = build_product_feature_text(cbf_products)
        
        cbf = ContentBasedFilter(max_features=5000)
        cbf.fit(product_texts)
        
        cbf_path = os.path.join(settings.BASE_DIR, 'models', 'saved', 'cbf_model.joblib')
        cbf.save(cbf_path)
        
        self.stdout.write(f"  Fitted TF-IDF on {len(product_texts)} products")
        self.stdout.write(f"  Vocabulary size: {len(cbf.vectorizer.vocabulary_)}")
        self.stdout.write(f"  Model saved to {cbf_path}")
        
        # ─────────────────────────────────────────────────
        # STEP 5: Run evaluation metrics
        # ─────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS("\n[5/6] Running evaluation metrics..."))
        
        # Build all_recs dict for evaluation
        all_recs = {}
        sample_users = list(user_to_idx.keys())[:50]  # Sample for speed
        for user_id in sample_users:
            top_n = cf.get_top_n(user_id, list(product_to_idx.keys()), n=10)
            all_recs[user_id] = [asin for asin, _ in top_n]
        
        eval_results = run_full_evaluation(
            cf_model=cf,
            cbf_model=cbf,
            interaction_matrix=matrix,
            all_recs=all_recs,
            catalog_size=len(unique_products_df)
        )
        
        self.stdout.write(f"  RMSE:          {eval_results['rmse']:.4f}")
        self.stdout.write(f"  Precision@10:  {eval_results['precision_at_10']:.4f}")
        self.stdout.write(f"  Recall@10:     {eval_results['recall_at_10']:.4f}")
        self.stdout.write(f"  Coverage:      {eval_results['coverage']:.4f}")
        self.stdout.write(f"  Diversity:     {eval_results['diversity']:.4f}")
        
        # Save metadata
        ModelMetadata.objects.create(
            model_type='svd',
            rmse=eval_results['rmse'],
            precision_at_k=eval_results['precision_at_10'],
            recall_at_k=eval_results['recall_at_10'],
            coverage=eval_results['coverage'],
            diversity=eval_results['diversity'],
            k_value=10,
            notes=f"SVD ({n_factors} factors), {num_users} synthetic users, "
                  f"{len(interactions_df)} interactions, {len(unique_products_df)} products"
        )
        ModelMetadata.objects.create(
            model_type='tfidf',
            notes=f"TF-IDF (5000 features) on {len(product_texts)} products, "
                  f"vocab size: {len(cbf.vectorizer.vocabulary_)}"
        )
        
        # ─────────────────────────────────────────────────
        # STEP 6: Sync products to database
        # ─────────────────────────────────────────────────
        if sync_db:
            self.stdout.write(self.style.SUCCESS(f"\n[6/6] Syncing {len(unique_products_df)} products to database..."))
            self._sync_products_to_db(unique_products_df)
        else:
            self.stdout.write(self.style.WARNING("\n[6/6] Skipped DB sync (use --sync-db flag to sync products)"))
        
        # ─────────────────────────────────────────────────
        # SUMMARY
        # ─────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS("  Training complete!"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
        self.stdout.write(f"  Products in catalog:  {len(unique_products_df)}")
        self.stdout.write(f"  Synthetic users:      {interactions_df['reviewerID'].nunique()}")
        self.stdout.write(f"  Total interactions:   {len(interactions_df)}")
        self.stdout.write(f"  CF RMSE:              {cf_metrics['rmse_mean']:.4f}")
        self.stdout.write(f"  CF model:             {cf_path}")
        self.stdout.write(f"  CBF model:            {cbf_path}")
        self.stdout.write("")

    def _sync_products_to_db(self, products_df: pd.DataFrame):
        """Sync all products from the dataset to the Django database."""
        synced = 0
        errors = 0
        
        for _, row in products_df.iterrows():
            try:
                asin = row['asin']
                
                # Category handling
                category_name = str(row.get('product_category', 'Uncategorized'))
                if pd.isna(category_name) or category_name == 'nan':
                    category_name = 'Uncategorized'
                category_slug = slugify(category_name)[:50] or 'uncategorized'
                
                category, _ = Category.objects.get_or_create(
                    name=category_name[:100],
                    defaults={'slug': category_slug}
                )
                
                # Price
                price = self._safe_float(row.get('discounted_price'), 
                                         fallback=self._safe_float(row.get('original_price'), fallback=0.0))
                
                # Rating
                avg_rating = self._safe_float(row.get('product_rating'), fallback=0.0)
                
                # Number of ratings/reviews
                num_ratings = int(self._safe_float(row.get('total_reviews'), fallback=0))
                
                # Brand extraction from title (e.g., first word or known brand)
                title = str(row.get('product_title', 'Unknown Product'))
                brand = self._extract_brand(title)
                
                # Image URL
                image_url = str(row.get('product_image_url', ''))
                if image_url == 'nan':
                    image_url = ''
                
                # Description (use sustainability tags + best seller status)
                desc_parts = []
                if pd.notna(row.get('sustainability_tags')) and str(row.get('sustainability_tags')) != 'nan':
                    desc_parts.append(f"Sustainability: {row['sustainability_tags']}")
                if row.get('is_best_seller') == 'Best Seller':
                    desc_parts.append("⭐ Best Seller")
                if pd.notna(row.get('has_coupon')) and row.get('has_coupon') != 'No Coupon':
                    desc_parts.append(f"💰 {row['has_coupon']}")
                description = ' | '.join(desc_parts)
                
                Product.objects.update_or_create(
                    asin=asin,
                    defaults={
                        'title': title[:500],
                        'description': description,
                        'price': price,
                        'category': category,
                        'brand': brand,
                        'avg_rating': avg_rating,
                        'num_ratings': num_ratings,
                        'image_url': image_url,
                        'is_active': True
                    }
                )
                synced += 1
                
                if synced % 500 == 0:
                    self.stdout.write(f"  Synced {synced} products...")
                    
            except Exception as e:
                errors += 1
                if errors <= 5:
                    logger.warning(f"Error syncing product: {e}")
        
        self.stdout.write(self.style.SUCCESS(f"  Successfully synced {synced} products ({errors} errors)"))
    
    def _safe_float(self, value, fallback=0.0) -> float:
        """Safely convert a value to float."""
        try:
            result = float(value)
            if pd.isna(result):
                return fallback
            return result
        except (ValueError, TypeError):
            return fallback
    
    def _extract_brand(self, title: str) -> str:
        """Extract brand name from product title (first word/known brands)."""
        known_brands = [
            'Apple', 'Samsung', 'Sony', 'LG', 'Dell', 'HP', 'Lenovo', 'Asus', 'Acer',
            'Microsoft', 'Google', 'Bose', 'JBL', 'Anker', 'Logitech', 'Corsair',
            'Razer', 'SteelSeries', 'HyperX', 'Kingston', 'SanDisk', 'Western',
            'Seagate', 'Intel', 'AMD', 'NVIDIA', 'Canon', 'Nikon', 'Fujifilm',
            'DJI', 'GoPro', 'Ring', 'Nest', 'Echo', 'Kindle', 'Fire', 'Roku',
            'TP-Link', 'Netgear', 'ASUS', 'MSI', 'Gigabyte', 'EVGA',
            'Beats', 'Sennheiser', 'Audio-Technica', 'Shure', 'Blue',
            'Epson', 'Brother', 'Panasonic', 'Philips', 'TCL', 'Hisense',
            'Fitbit', 'Garmin', 'Xiaomi', 'OnePlus', 'Motorola', 'Nokia',
            'BOYA', 'LISEN', 'UGREEN', 'Baseus', 'Spigen', 'OtterBox',
        ]
        
        title_upper = title.upper()
        for brand in known_brands:
            if brand.upper() in title_upper:
                return brand
        
        # Fallback: first word of title
        first_word = title.split()[0] if title.split() else 'Unknown'
        if len(first_word) > 2 and first_word[0].isupper():
            return first_word
        
        return 'Unknown'
