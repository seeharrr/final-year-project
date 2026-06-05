import joblib
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

class ContentBasedFilter:
    def __init__(self, max_features=5000):
        self.max_features = max_features
        self.vectorizer = None
        self.matrix = None
        self.index = None

    def fit(self, product_texts: pd.Series):
        logger.info(f"Fitting TF-IDF on {len(product_texts)} products...")
        self.vectorizer = TfidfVectorizer(max_features=self.max_features, stop_words='english')
        self.matrix = self.vectorizer.fit_transform(product_texts.values)
        self.index = list(product_texts.index)

    def get_similar(self, asin: str, n=20) -> list:
        if self.matrix is None or self.index is None or asin not in self.index:
            return []
            
        idx = self.index.index(asin)
        
        # Compute cosine similarity between this product and all others
        sim_scores = cosine_similarity(self.matrix[idx], self.matrix).flatten()
        
        # Pair with asins
        product_scores = list(zip(self.index, sim_scores))
        
        # Sort descending and exclude self
        product_scores.sort(key=lambda x: x[1], reverse=True)
        return [ps for ps in product_scores if ps[0] != asin][:n]

    def get_user_profile_recommendations(self, viewed_asins: list, purchased_asins: list, rated_asins: list = None, cart_asins: list = None, wishlist_asins: list = None, n=20) -> list:
        if self.matrix is None or not self.index:
            return []
            
        rated_asins = rated_asins or []
        cart_asins = cart_asins or []
        wishlist_asins = wishlist_asins or []
        
        valid_viewed = [a for a in viewed_asins if a in self.index]
        valid_purchased = [a for a in purchased_asins if a in self.index]
        valid_rated = [(a, r) for a, r in rated_asins if a in self.index]
        valid_cart = [a for a in cart_asins if a in self.index]
        valid_wishlist = [a for a in wishlist_asins if a in self.index]
        
        if not valid_viewed and not valid_purchased and not valid_rated and not valid_cart and not valid_wishlist:
            return []
            
        vectors = []
        for a in valid_viewed:
            idx = self.index.index(a)
            vectors.append(self.matrix[idx].toarray()[0]) # Weight 1.0 for views
            
        for a in valid_purchased:
            idx = self.index.index(a)
            # Weight purchased products 3x
            vectors.append(self.matrix[idx].toarray()[0] * 3.0)
            
        for a in valid_cart:
            idx = self.index.index(a)
            # Weight cart products 3x
            vectors.append(self.matrix[idx].toarray()[0] * 3.0)
            
        for a in valid_wishlist:
            idx = self.index.index(a)
            # Weight wishlist products 2.5x
            vectors.append(self.matrix[idx].toarray()[0] * 2.5)
            
        for a, r in valid_rated:
            idx = self.index.index(a)
            # High ratings (4-5) get strong positive weight
            if r >= 4.0:
                vectors.append(self.matrix[idx].toarray()[0] * 3.0)
            # Neutral ratings (3) get low weight
            elif r == 3.0:
                vectors.append(self.matrix[idx].toarray()[0] * 0.5)
            # Low ratings (1-2) get negative weight to push similar items away
            else:
                vectors.append(self.matrix[idx].toarray()[0] * -1.5)
            
        # Build user profile as mean vector
        profile_vector = np.mean(vectors, axis=0).reshape(1, -1)
        
        # Compute cosine similarity of profile against all products
        sim_scores = cosine_similarity(profile_vector, self.matrix).flatten()
        
        product_scores = list(zip(self.index, sim_scores))
        
        # Remove already viewed/purchased/rated/cart/wishlist from recommendations
        history_set = set(valid_viewed + valid_purchased + [a for a, r in valid_rated] + valid_cart + valid_wishlist)
        
        product_scores.sort(key=lambda x: x[1], reverse=True)
        return [ps for ps in product_scores if ps[0] not in history_set][:n]

    def get_recommendations_from_text(self, text_query: str, n=20) -> list:
        """
        Query the model with arbitrary text (e.g. search queries).
        Converts the user query to a vector using the same TF-IDF vectorizer
        with query expansion (synonym mapping) to handle natural language.
        Uses cosine similarity to find the most relevant products.
        """
        if self.matrix is None or self.vectorizer is None:
            return []

        # ── Query Expansion: map user phrases to richer keyword sets ──────────
        EXPANSIONS = {
            # Laptops
            'laptop':       'laptop notebook computer portable computing',
            'gaming laptop': 'gaming laptop notebook computer graphics gpu high performance',
            'notebook':     'notebook laptop computer portable',
            # Phones
            'phone':        'phone smartphone mobile cellular',
            'smartphone':   'smartphone phone mobile android ios',
            'iphone':       'iphone apple smartphone ios mobile',
            'android':      'android smartphone mobile phone',
            # Audio
            'headphones':   'headphones earphones earbuds audio listening music',
            'earbuds':      'earbuds earphones wireless in ear audio',
            'speaker':      'speaker audio sound music bluetooth portable',
            'wireless':     'wireless bluetooth wifi cordless',
            # Gaming
            'gaming':       'gaming game console controller esports',
            'console':      'console gaming xbox playstation nintendo switch',
            # TV / Display
            'tv':           'television tv display screen monitor 4k uhd',
            '4k':           '4k uhd ultra hd resolution television screen',
            # Camera
            'camera':       'camera photo photography dslr lens capture',
            'dslr':         'dslr camera photography lens professional',
            # Wearables
            'watch':        'watch smartwatch fitness tracker wearable',
            'smartwatch':   'smartwatch watch fitness tracker health wearable',
            'fitness':      'fitness tracker health watch wearable workout',
            # Storage
            'storage':      'storage hard drive ssd hdd memory card flash',
            'ssd':          'ssd solid state drive storage fast',
            'flash drive':  'flash drive usb storage portable memory',
            # Cables / Chargers
            'charger':      'charger charging cable adapter power usb',
            'cable':        'cable charging usb wire connector cord',
            'usb c':        'usb c type c cable charging fast',
            'type c':       'type c usb c cable charging fast',
            # Smart Home
            'smart home':   'smart home automation alexa google echo hub',
            'smart':        'smart intelligent home automation connected',
            # Price signals
            'cheap':        'cheap budget affordable low price',
            'budget':       'budget affordable cheap economical',
            'affordable':   'affordable cheap budget low cost',
            'premium':      'premium high end quality flagship',
            'expensive':    'premium luxury flagship high end',
            # Colors
            'black':        'black dark midnight',
            'white':        'white starlight silver light',
            'waterproof':   'waterproof water resistant ipx splash',
            'portable':     'portable compact lightweight travel',
        }

        query_lower = text_query.lower()
        # Give the original query much higher weight so it anchors the search
        expanded_parts = [text_query, text_query, text_query]

        for phrase, expansion in EXPANSIONS.items():
            if phrase in query_lower:
                expanded_parts.append(expansion)

        expanded_query = ' '.join(expanded_parts)

        # Transform the expanded query text into the TF-IDF vector space
        query_vector = self.vectorizer.transform([expanded_query])

        # Compute cosine similarity between query vector and all product vectors
        sim_scores = cosine_similarity(query_vector, self.matrix).flatten()

        product_scores = list(zip(self.index, sim_scores))
        
        # Filter out items that have zero similarity
        product_scores = [ps for ps in product_scores if ps[1] > 0.0]
        
        product_scores.sort(key=lambda x: x[1], reverse=True)

        return product_scores[:n]

    def save(self, path: str):
        if self.vectorizer is None:
            raise ValueError("Model not trained yet.")
        joblib.dump({
            'vectorizer': self.vectorizer,
            'matrix': self.matrix,
            'index': self.index,
            'trained_at': datetime.now()
        }, path)

    @classmethod
    def load(cls, path: str) -> 'ContentBasedFilter':
        data = joblib.load(path)
        instance = cls()
        instance.vectorizer = data['vectorizer']
        instance.matrix = data['matrix']
        instance.index = data['index']
        return instance
