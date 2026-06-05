import pandas as pd
from products.models import Product, Category
from recommendation.engine.preprocessing import load_amazon_dataset

def load_products_to_db(filepath: str):
    """Bulk creates Product objects from Amazon dataset."""
    df = load_amazon_dataset(filepath)
    
    # Calculate average rating per ASIN
    avg_ratings = df.groupby('asin')['overall'].mean()
    num_ratings = df.groupby('asin')['overall'].count()
    
    # We might have metadata in a separate file, but the prompt says 
    # expected columns include reviewText, summary, and that load_products_to_db
    # reads the Amazon dataset and maps asin, title, avg_rating. 
    # If title is missing, we use the ASIN as title.
    
    # We need a default category
    default_category, _ = Category.objects.get_or_create(
        name='General', slug='general'
    )
    
    products_to_create = []
    
    # Group by ASIN to get unique products
    # We only take the first row per ASIN to get any static info
    unique_products_df = df.drop_duplicates(subset=['asin'])
    
    for _, row in unique_products_df.iterrows():
        asin = row['asin']
        title = row.get('title', f"Product {asin}")
        if pd.isna(title):
            title = f"Product {asin}"
            
        products_to_create.append(Product(
            asin=asin,
            title=str(title)[:500],
            avg_rating=avg_ratings.get(asin, 0.0),
            num_ratings=num_ratings.get(asin, 0),
            category=default_category
        ))
        
        # Batching insert if list is getting large
        if len(products_to_create) >= 500:
            Product.objects.bulk_create(products_to_create, ignore_conflicts=True)
            products_to_create = []
            
    # Insert remaining
    if products_to_create:
        Product.objects.bulk_create(products_to_create, ignore_conflicts=True)
