import pandas as pd
import logging
import numpy as np
import random
import re

logger = logging.getLogger(__name__)


def load_amazon_dataset(filepath: str) -> pd.DataFrame:
    """Load the Amazon products sales CSV and prepare product catalog."""
    if not filepath.endswith('.csv'):
        raise ValueError("File must be .csv")
    
    df = pd.read_csv(filepath)
    logger.info(f"Loaded {len(df)} rows from {filepath}")
    
    # Standardize column names for internal use
    column_map = {
        'product_title': 'product_title',
        'product_rating': 'product_rating',
        'total_reviews': 'total_reviews',
        'purchased_last_month': 'purchased_last_month',
        'discounted_price': 'discounted_price',
        'original_price': 'original_price',
        'is_best_seller': 'is_best_seller',
        'is_sponsored': 'is_sponsored',
        'has_coupon': 'has_coupon',
        'sustainability_tags': 'sustainability_tags',
        'product_image_url': 'product_image_url',
        'product_category': 'product_category',
        'discount_percentage': 'discount_percentage',
    }
    
    for expected, mapped in column_map.items():
        if expected not in df.columns:
            logger.warning(f"Missing column: {expected}")
    
    # Drop rows with missing titles
    if 'product_title' in df.columns:
        df = df.dropna(subset=['product_title'])
    
    # Create unique product IDs (asin equivalent) based on product_title
    # Since titles can repeat (same product in multiple categories/rows),
    # we deduplicate later at the DB sync stage
    if 'asin' not in df.columns:
        df['asin'] = [f"PROD{i:06d}" for i in range(len(df))]
    
    # Fill NaN ratings with 0
    if 'product_rating' in df.columns:
        df['product_rating'] = pd.to_numeric(df['product_rating'], errors='coerce').fillna(0.0)
    
    if 'total_reviews' in df.columns:
        df['total_reviews'] = pd.to_numeric(df['total_reviews'], errors='coerce').fillna(0).astype(int)
    
    if 'discounted_price' in df.columns:
        df['discounted_price'] = pd.to_numeric(df['discounted_price'], errors='coerce')
    
    if 'original_price' in df.columns:
        df['original_price'] = pd.to_numeric(df['original_price'], errors='coerce')
    
    logger.info(f"Processed {len(df)} products after cleaning")
    return df


def deduplicate_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate products by title. Keep the row with the highest total_reviews
    for each unique product title. Reassign ASIN based on deduplication.
    """
    if 'total_reviews' in df.columns:
        df_sorted = df.sort_values('total_reviews', ascending=False)
    else:
        df_sorted = df
    
    deduped = df_sorted.drop_duplicates(subset=['product_title'], keep='first').copy()
    deduped['asin'] = [f"PROD{i:06d}" for i in range(len(deduped))]
    
    logger.info(f"Deduplicated from {len(df)} to {len(deduped)} unique products")
    return deduped


def generate_synthetic_interactions(products_df: pd.DataFrame, 
                                    num_users: int = 200, 
                                    avg_interactions_per_user: int = 25) -> pd.DataFrame:
    """
    Generate synthetic user ratings based on real product data.
    
    Uses product_rating and total_reviews to create realistic interaction patterns:
    - Popular products (high total_reviews) are more likely to be interacted with
    - Ratings cluster around the product's actual product_rating
    - Users have varying numbers of interactions (some power users, some casual)
    """
    logger.info(f"Generating synthetic interactions for {num_users} users across {len(products_df)} products...")
    
    product_ids = products_df['asin'].tolist()
    
    # Build popularity weights from total_reviews
    if 'total_reviews' in products_df.columns:
        weights = products_df['total_reviews'].fillna(1).values.astype(float)
        weights = np.clip(weights, 1, None)  # Minimum weight of 1
        weights = weights / weights.sum()
    else:
        weights = np.ones(len(product_ids)) / len(product_ids)
    
    # Build product rating lookup for generating realistic user ratings
    rating_lookup = {}
    if 'product_rating' in products_df.columns:
        for _, row in products_df.iterrows():
            rating_lookup[row['asin']] = float(row.get('product_rating', 4.0)) if pd.notna(row.get('product_rating')) else 4.0
    
    data = []
    for user_id in range(1, num_users + 1):
        # Vary interactions per user (some browse a lot, some don't)
        num_interactions = max(5, int(np.random.normal(avg_interactions_per_user, 8)))
        num_interactions = min(num_interactions, len(product_ids))
        
        # Sample products weighted by popularity
        sampled_indices = np.random.choice(
            len(product_ids), size=num_interactions, replace=False, p=weights
        )
        sampled_products = [product_ids[i] for i in sampled_indices]
        
        for pid in sampled_products:
            # Generate rating close to the product's actual rating
            base_rating = rating_lookup.get(pid, 4.0)
            # Add noise: user might rate higher or lower than average
            user_rating = base_rating + np.random.normal(0, 0.6)
            user_rating = np.clip(user_rating, 1.0, 5.0)
            user_rating = round(user_rating * 2) / 2  # Round to nearest 0.5
            
            data.append({
                'reviewerID': f"USER{user_id:04d}",
                'asin': pid,
                'overall': float(user_rating)
            })
    
    interactions_df = pd.DataFrame(data)
    logger.info(f"Generated {len(interactions_df)} synthetic interactions")
    return interactions_df


def filter_sparse_data(df: pd.DataFrame, min_user_ratings=5, min_product_ratings=3) -> pd.DataFrame:
    """Iteratively remove sparse users and products until stable."""
    if df.empty:
        return df
    
    original_size = len(df)
    iteration = 0
    while True:
        start_size = len(df)
        
        # Filter products with too few ratings
        product_counts = df['asin'].value_counts()
        valid_products = product_counts[product_counts >= min_product_ratings].index
        df = df[df['asin'].isin(valid_products)]
        
        # Filter users with too few ratings
        user_counts = df['reviewerID'].value_counts()
        valid_users = user_counts[user_counts >= min_user_ratings].index
        df = df[df['reviewerID'].isin(valid_users)]
        
        iteration += 1
        if len(df) == start_size:
            break

    removed = original_size - len(df)
    logger.info(f"Filtered from {original_size} to {len(df)} interactions ({removed} removed in {iteration} iterations)")
    logger.info(f"  Remaining: {df['reviewerID'].nunique()} users, {df['asin'].nunique()} products")
    return df


def build_user_item_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pivot table to user-item matrix, NaN -> 0."""
    return df.pivot_table(index='reviewerID', columns='asin', values='overall', fill_value=0)


def build_product_feature_text(products_df: pd.DataFrame) -> pd.Series:
    """
    Combine rich text features for content-based filtering.
    Includes title, brand (boosted 3x), category (boosted 2x), description,
    price range label, and extracted color/feature keywords from the title.
    This makes the TF-IDF model respond well to descriptive natural language queries.
    """
    # Price range label mapping
    def _price_label(price):
        try:
            p = float(price)
            if p < 25:    return 'very cheap budget affordable'
            if p < 75:    return 'cheap budget affordable'
            if p < 150:   return 'budget affordable mid range'
            if p < 300:   return 'mid range moderate'
            if p < 600:   return 'upper mid range premium'
            if p < 1000:  return 'premium high end expensive'
            return 'luxury high end flagship expensive'
        except (ValueError, TypeError):
            return ''

    # Color keywords to extract from titles
    COLORS = ['black', 'white', 'silver', 'gold', 'blue', 'red', 'green',
              'pink', 'purple', 'gray', 'grey', 'rose', 'midnight', 'starlight']

    # Connectivity/feature keywords to extract from titles
    FEATURES = ['wireless', 'bluetooth', 'wifi', 'usb', 'type-c', 'typec',
                'waterproof', 'portable', 'rechargeable', 'noise canceling',
                'noise cancelling', 'active noise', 'gaming', 'mechanical',
                'rgb', 'led', 'hd', '4k', '8k', 'fullhd', 'uhd', 'oled',
                'amoled', 'fast charging', 'quick charge', 'solar', 'smart',
                'touchscreen', 'fingerprint', 'dual', 'triple', 'quad',
                'foldable', 'slim', 'thin', 'lightweight', 'heavy duty',
                'rugged', 'magnetic', 'true wireless', 'in ear', 'over ear',
                'on ear', 'open back', 'closed back']

    def _combine(row):
        title = str(row.get('product_title', ''))
        category = str(row.get('product_category', ''))
        brand = str(row.get('brand', ''))
        description = str(row.get('description', ''))
        sustainability = str(row.get('sustainability_tags', ''))
        best_seller = str(row.get('is_best_seller', ''))
        price = row.get('discounted_price') or row.get('original_price') or row.get('price') or 0

        title_lower = title.lower()

        # Extract colors mentioned in the title
        found_colors = [c for c in COLORS if c in title_lower]

        # Extract feature keywords from the title
        found_features = [f for f in FEATURES if f in title_lower]

        # Price range label
        price_label = _price_label(price)

        # Build enriched text:
        # - brand repeated 3x so it has high TF-IDF weight
        # - category repeated 2x for category-based queries
        # - title + description for natural language matching
        # - color + feature keywords boosted separately
        parts = [
            title,                           # product title (core signal)
            title,                           # repeated for extra weight
            f"{brand} {brand} {brand}",      # brand boosted 3x
            f"{category} {category}",        # category boosted 2x
            description[:500],               # description (truncated)
            ' '.join(found_colors * 2),      # colors boosted 2x
            ' '.join(found_features),        # feature keywords
            price_label,                     # price range label
            sustainability,
            best_seller,
        ]

        text = ' '.join(parts).lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        # Remove 'nan' strings from missing data
        text = re.sub(r'\bnan\b', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    return products_df.apply(_combine, axis=1)


def encode_users_products(df: pd.DataFrame) -> tuple:
    """Return mappings for integer encoding."""
    unique_users = df['reviewerID'].unique()
    unique_products = df['asin'].unique()
    
    user_to_idx = {u: i for i, u in enumerate(unique_users)}
    idx_to_user = {i: u for u, i in user_to_idx.items()}
    
    product_to_idx = {p: i for i, p in enumerate(unique_products)}
    idx_to_product = {i: p for p, i in product_to_idx.items()}
    
    return user_to_idx, idx_to_user, product_to_idx, idx_to_product


def prepare_interaction_matrix(df: pd.DataFrame) -> tuple:
    """
    Prepare the user-item interaction matrix for SVD decomposition.
    Returns: (matrix as numpy array, user_to_idx, idx_to_user, product_to_idx, idx_to_product)
    """
    user_to_idx, idx_to_user, product_to_idx, idx_to_product = encode_users_products(df)
    
    n_users = len(user_to_idx)
    n_products = len(product_to_idx)
    
    matrix = np.zeros((n_users, n_products))
    for _, row in df.iterrows():
        u_idx = user_to_idx[row['reviewerID']]
        p_idx = product_to_idx[row['asin']]
        matrix[u_idx, p_idx] = row['overall']
    
    logger.info(f"Built interaction matrix: {n_users} users x {n_products} products, "
                f"density: {(matrix > 0).sum() / matrix.size:.4f}")
    
    return matrix, user_to_idx, idx_to_user, product_to_idx, idx_to_product
