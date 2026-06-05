from .collaborative import CollaborativeFilter
from .content_based import ContentBasedFilter

class HybridRecommender:
    def __init__(self, cf: CollaborativeFilter, cbf: ContentBasedFilter):
        self.cf = cf
        self.cbf = cbf

    def compute_alpha(self, num_ratings: int) -> float:
        """Dynamic weight for collaborative filtering."""
        return min(1.0, num_ratings / 20.0)

    def recommend(self, user_id: str, user_django_id: int, 
                  viewed_asins: list, purchased_asins: list, 
                  all_product_ids: list, n=10, user_rating_count=0,
                  rated_asins: list = None, search_queries: list = None) -> list:
        
        alpha = self.compute_alpha(user_rating_count)
        
        # Get CF Top 20
        cf_recs = self.cf.get_top_n(user_id, all_product_ids, n=20)
        cf_dict = {asin: score for asin, score in cf_recs}
        
        # Get CBF Top 20
        cbf_recs = self.cbf.get_user_profile_recommendations(viewed_asins, purchased_asins, rated_asins=rated_asins, n=30)
        
        # Boost CBF with search queries
        if search_queries:
            search_boosted = {}
            for asin, score in cbf_recs:
                search_boosted[asin] = score
                
            for q in search_queries:
                search_matches = self.cbf.get_recommendations_from_text(q, n=10)
                for asin, score in search_matches:
                    search_boosted[asin] = search_boosted.get(asin, 0) + (score * 1.5)
            
            cbf_recs = sorted(search_boosted.items(), key=lambda x: x[1], reverse=True)[:20]
            
        cbf_dict = {asin: score for asin, score in cbf_recs}
        
        # Min-Max Scaling helper
        def min_max_scale(val_dict):
            if not val_dict:
                return {}
            min_val = min(val_dict.values())
            max_val = max(val_dict.values())
            if max_val == min_val:
                return {k: 1.0 for k in val_dict.keys()}
            return {k: (v - min_val) / (max_val - min_val) for k, v in val_dict.items()}
            
        cf_norm = min_max_scale(cf_dict)
        cbf_norm = min_max_scale(cbf_dict)
        
        all_candidate_asins = set(cf_dict.keys()).union(set(cbf_dict.keys()))
        
        results = []
        for asin in all_candidate_asins:
            cf_score = cf_norm.get(asin, 0.0)
            cbf_score = cbf_norm.get(asin, 0.0)
            
            hybrid_score = (alpha * cf_score) + ((1.0 - alpha) * cbf_score)
            
            if alpha < 0.3:
                explanation = "Based on products you browsed"
                source = "content"
            elif alpha > 0.7:
                explanation = "Users like you also bought this"
                source = "collaborative"
            else:
                explanation = "Recommended based on your history and similar users"
                source = "hybrid"
                
            results.append({
                'asin': asin,
                'hybrid_score': hybrid_score,
                'cf_score': cf_score,
                'cbf_score': cbf_score,
                'alpha': alpha,
                'source': source,
                'explanation': explanation
            })
            
        results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return results[:n]

    def recommend_cold_start(self, viewed_asins: list, n=10) -> list:
        """For anonymous / zero-rating users. Pure content-based only."""
        results = self.cbf.get_user_profile_recommendations(viewed_asins, [], n=n)
        return [{
            'asin': a,
            'hybrid_score': s,
            'cf_score': 0.0,
            'cbf_score': s,
            'alpha': 0.0,
            'source': 'content',
            'explanation': 'Based on products you recently viewed'
        } for a, s in results]
