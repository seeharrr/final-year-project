import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


def compute_rmse(predictions: list) -> float:
    """
    Compute RMSE from a list of (actual, predicted) tuples.
    """
    if not predictions:
        return 0.0
    
    squared_errors = [(actual - pred) ** 2 for actual, pred in predictions]
    return float(np.sqrt(np.mean(squared_errors)))


def precision_at_k(recommended: list, relevant: list, k: int) -> float:
    """
    recommended: list of product ASINs in ranked order
    relevant: list of product ASINs the user actually interacted with
    Returns proportion of top-k recommended items that are relevant.
    """
    if not recommended or not relevant or k <= 0:
        return 0.0
        
    top_k = recommended[:k]
    relevant_set = set(relevant)
    
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / k


def recall_at_k(recommended: list, relevant: list, k: int) -> float:
    """
    Returns proportion of relevant items found in top-k recommendations.
    """
    if not recommended or not relevant or k <= 0:
        return 0.0
        
    top_k = recommended[:k]
    relevant_set = set(relevant)
    
    hits = sum(1 for item in top_k if item in relevant_set)
    return hits / len(relevant_set)


def coverage(all_recommendations: dict, catalog_size: int) -> float:
    """
    all_recommendations: {user_id: [asin, ...]} dict
    Returns fraction of catalog that appears in at least one recommendation list.
    """
    if catalog_size <= 0 or not all_recommendations:
        return 0.0
        
    unique_recommended_items = set()
    for rec_list in all_recommendations.values():
        unique_recommended_items.update(rec_list)
        
    return len(unique_recommended_items) / catalog_size


def diversity(all_recommendations: dict, cbf) -> float:
    """
    For each user's list, compute mean pairwise (1 - cosine_similarity) between recommended items.
    Average across all users.
    High diversity = varied recommendations.
    """
    if not all_recommendations or not cbf or cbf.matrix is None:
        return 0.0
        
    user_diversities = []
    
    for user_id, rec_list in all_recommendations.items():
        if len(rec_list) < 2:
            continue
            
        vectors = []
        for asin in rec_list:
            if asin in cbf.index:
                idx = cbf.index.index(asin)
                vectors.append(cbf.matrix[idx].toarray()[0])
                
        if len(vectors) < 2:
            continue
            
        sim_matrix = cosine_similarity(vectors)
        
        # Get upper triangle, excluding diagonal
        n = len(vectors)
        upper_tri = sim_matrix[np.triu_indices(n, k=1)]
        
        # Diversity is 1 - similarity
        div = 1.0 - np.mean(upper_tri)
        user_diversities.append(div)
        
    if not user_diversities:
        return 0.0
        
    return float(np.mean(user_diversities))


def run_full_evaluation(cf_model, cbf_model, interaction_matrix, all_recs, catalog_size) -> dict:
    """
    Run all metrics and return results dict.
    
    Args:
        cf_model: trained CollaborativeFilter instance
        cbf_model: trained ContentBasedFilter instance
        interaction_matrix: numpy array (users x products)
        all_recs: {user_id: [asin, ...]}
        catalog_size: total number of products in catalog
    """
    logger.info("Running full evaluation suite...")
    
    # Compute RMSE from the CF model on known ratings
    rmse_val = 0.0
    predictions = []
    if cf_model and cf_model.model is not None and interaction_matrix is not None:
        for i in range(interaction_matrix.shape[0]):
            for j in range(interaction_matrix.shape[1]):
                if interaction_matrix[i, j] > 0:
                    user_id = cf_model.idx_to_user.get(i)
                    product_id = cf_model.idx_to_product.get(j)
                    if user_id and product_id:
                        pred = cf_model.predict(user_id, product_id)
                        predictions.append((interaction_matrix[i, j], pred))
        
        # Sample for efficiency if too many predictions
        if len(predictions) > 5000:
            predictions = [predictions[i] for i in np.random.choice(len(predictions), 5000, replace=False)]
        
        rmse_val = compute_rmse(predictions)
    
    # Compute precision and recall (using known interactions as ground truth)
    precision_vals = []
    recall_vals = []
    if cf_model and cf_model.idx_to_user and all_recs:
        for user_id, rec_list in all_recs.items():
            # Get the user's actual interactions as "relevant" items
            if user_id in cf_model.user_to_idx:
                u_idx = cf_model.user_to_idx[user_id]
                if interaction_matrix is not None:
                    relevant = [cf_model.idx_to_product[j] 
                               for j in range(interaction_matrix.shape[1])
                               if interaction_matrix[u_idx, j] >= 4.0 and j in cf_model.idx_to_product]
                    if relevant and rec_list:
                        precision_vals.append(precision_at_k(rec_list, relevant, 10))
                        recall_vals.append(recall_at_k(rec_list, relevant, 10))
    
    avg_precision = float(np.mean(precision_vals)) if precision_vals else 0.0
    avg_recall = float(np.mean(recall_vals)) if recall_vals else 0.0
    
    cov = coverage(all_recs, catalog_size)
    div = diversity(all_recs, cbf_model)
    
    results = {
        'rmse': rmse_val,
        'precision_at_10': avg_precision,
        'recall_at_10': avg_recall,
        'coverage': cov,
        'diversity': div
    }
    
    logger.info(f"Evaluation results: {results}")
    return results
