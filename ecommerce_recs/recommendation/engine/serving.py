import os
from django.conf import settings
from products.models import Product
from recommendation.models import Recommendation, BrowsingHistory, PurchaseHistory, SearchHistory, UserRating
from recommendation.engine.content_based import ContentBasedFilter
import random

# Simple In-Memory Cache for CBF model
_CBF_MODEL_CACHE = {
    'model': None,
    'last_loaded': None
}

def _get_cbf_model():
    """Returns the loaded ContentBasedFilter, with caching."""
    global _CBF_MODEL_CACHE
    cbf_path = os.path.join(settings.BASE_DIR, 'models', 'saved', 'cbf_model.joblib')
    
    if not os.path.exists(cbf_path):
        return None
        
    # Check if we need to load or reload
    try:
        mtime = os.path.getmtime(cbf_path)
        if _CBF_MODEL_CACHE['model'] is None or _CBF_MODEL_CACHE['last_loaded'] < mtime:
            _CBF_MODEL_CACHE['model'] = ContentBasedFilter.load(cbf_path)
            _CBF_MODEL_CACHE['last_loaded'] = mtime
    except Exception:
        return None
            
    return _CBF_MODEL_CACHE['model']

def get_recommendations_for_user(user, n=10):
    """
    Primary serving function with Real-time Blending.
    Always blends pre-computed recommendations with real-time history for freshness.
    """
    # 1. Get pre-computed recommendations
    precomputed = list(Recommendation.objects.filter(user=user).select_related('product', 'product__category').order_by('-score')[:n])
    
    # 2. Get real-time recommendations based on latest activity
    realtime = get_real_time_user_recommendations(user, n)
    
    # 3. Blend them
    # If no precomputed, just use realtime
    if not precomputed:
        return realtime[:n]
        
    # Blending strategy: Interleave them, prioritizing real-time for the first slots to feel "fast"
    blended = []
    seen_asins = set()
    
    # Convert precomputed to dict format if needed (template compatibility)
    # Actually precomputed are Recommendation objects, realtime are dicts
    
    rt_ptr = 0
    pc_ptr = 0
    
    while len(blended) < n:
        added = False
        # Try to add from real-time first for top slots
        if rt_ptr < len(realtime):
            item = realtime[rt_ptr]
            asin = item['product'].asin
            if asin not in seen_asins:
                blended.append(item)
                seen_asins.add(asin)
                added = True
            rt_ptr += 1
            
        if len(blended) == n: break
        
        # Then add from precomputed
        if pc_ptr < len(precomputed):
            item = precomputed[pc_ptr]
            asin = item.product.asin
            if asin not in seen_asins:
                # Keep as Recommendation object
                blended.append(item)
                seen_asins.add(asin)
                added = True
            pc_ptr += 1
            
        if not added and rt_ptr >= len(realtime) and pc_ptr >= len(precomputed):
            break
            
    return blended[:n]

def get_real_time_user_recommendations(user, n=10):
    """
    Generates recommendations on-the-fly based on recent browsing, search, and purchase history.
    """
    # 1. Fetch Histories
    viewed_asins = list(BrowsingHistory.objects.filter(user=user).order_by('-viewed_at').values_list('product__asin', flat=True)[:20])
    purchased_asins = list(PurchaseHistory.objects.filter(user=user).order_by('-purchased_at').values_list('product__asin', flat=True)[:10])
    search_queries = list(SearchHistory.objects.filter(user=user).order_by('-searched_at').values_list('query', flat=True)[:10])
    user_ratings = list(UserRating.objects.filter(user=user).values_list('product__asin', 'rating'))
    
    cart_asins = []
    wishlist_asins = []
    try:
        from products.models import Cart, Wishlist
        cart = Cart.objects.filter(user=user).first()
        if cart:
            cart_asins = list(cart.items.values_list('product__asin', flat=True))
        wishlist = Wishlist.objects.filter(user=user).first()
        if wishlist:
            wishlist_asins = list(wishlist.products.values_list('asin', flat=True))
    except Exception:
        pass
    
    if not viewed_asins and not purchased_asins and not search_queries and not user_ratings and not cart_asins and not wishlist_asins:
        return list(get_trending_products(n))
        
    cbf = _get_cbf_model()
    if not cbf:
        return list(get_trending_products(n))
        
    try:
        # Get recommendations from views/purchases/ratings/cart/wishlist
        profile_recs = cbf.get_user_profile_recommendations(
            viewed_asins=viewed_asins, 
            purchased_asins=purchased_asins, 
            rated_asins=user_ratings,
            cart_asins=cart_asins,
            wishlist_asins=wishlist_asins,
            n=n*2
        )
        
        # Get recommendations from searches
        search_recs = []
        for q in search_queries:
            # Search matches get a significant influence
            search_recs.extend(cbf.get_recommendations_from_text(q, n=10))
            
        # Combine and score
        combined_scores = {}
        for asin, score in profile_recs:
            combined_scores[asin] = combined_scores.get(asin, 0) + score
            
        for asin, score in search_recs:
            # Search matches get a strong boost (1.5x)
            combined_scores[asin] = combined_scores.get(asin, 0) + (score * 1.5)
            
        # Sort by score
        sorted_asins = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Convert to product objects with explanations
        results = []
        for asin, _ in sorted_asins:
            try:
                prod = Product.objects.select_related('category').get(asin=asin)
                # Determine explanation
                explanation = "Based on your recent interest"
                if any(asin == a for a in viewed_asins): continue # Skip if already in history
                if any(asin == a for a in purchased_asins): continue 
                if any(asin == a for a, r in user_ratings): continue
                if any(asin == a for a in cart_asins): continue
                if any(asin == a for a in wishlist_asins): continue
                
                results.append({
                    'product': prod,
                    'source': 'realtime',
                    'explanation': explanation
                })
                if len(results) == n * 2: break
            except Product.DoesNotExist:
                continue
                
        if not results:
            return list(get_trending_products(n))
            
        return results
    except Exception as e:
        print(f"Error in real-time recs: {e}")
        return list(get_trending_products(n))

def get_trending_products(n=10):
    """Returns top-n products by num_ratings as a fallback."""
    return Product.objects.filter(is_active=True).order_by('-num_ratings')[:n]

def get_session_recommendations(session_key: str, n=10):
    """For anonymous users."""
    viewed_asins = list(BrowsingHistory.objects.filter(session_key=session_key).order_by('-viewed_at').values_list('product__asin', flat=True)[:20])
    search_queries = list(SearchHistory.objects.filter(session_key=session_key).order_by('-searched_at').values_list('query', flat=True)[:5])
    
    if not viewed_asins and not search_queries:
        return list(get_trending_products(n))
        
    cbf = _get_cbf_model()
    if not cbf:
        return list(get_trending_products(n))
        
    profile_recs = cbf.get_user_profile_recommendations(viewed_asins, [], n=n*2)
    search_recs = []
    for q in search_queries:
        search_recs.extend(cbf.get_recommendations_from_text(q, n=5))
        
    combined_scores = {}
    for asin, score in profile_recs: combined_scores[asin] = combined_scores.get(asin, 0) + score
    for asin, score in search_recs: combined_scores[asin] = combined_scores.get(asin, 0) + score
    
    sorted_asins = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    
    products = []
    for asin, _ in sorted_asins:
        try:
            prod = Product.objects.select_related('category').get(asin=asin)
            products.append(prod)
            if len(products) == n: break
        except Product.DoesNotExist:
            continue
            
    if not products:
        return list(get_trending_products(n))
    return products

def record_product_view(user_or_none, product, session_key: str):
    """Records a product view."""
    BrowsingHistory.objects.create(
        user=user_or_none if user_or_none and user_or_none.is_authenticated else None,
        product=product,
        session_key=session_key if not (user_or_none and user_or_none.is_authenticated) else ''
    )

def record_search(user_or_none, query, session_key: str):
    """Records a search query."""
    if not query: return
    SearchHistory.objects.create(
        user=user_or_none if user_or_none and user_or_none.is_authenticated else None,
        query=query[:255],
        session_key=session_key if not (user_or_none and user_or_none.is_authenticated) else ''
    )
