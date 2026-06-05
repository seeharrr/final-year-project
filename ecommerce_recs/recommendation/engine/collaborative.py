import joblib
import numpy as np
from datetime import datetime
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_squared_error
import logging

logger = logging.getLogger(__name__)


class CollaborativeFilter:
    """
    Collaborative Filtering using Truncated SVD (Latent Factor Model).
    
    Uses scikit-learn's TruncatedSVD to decompose the user-item rating matrix
    into latent factors, then predicts ratings via dot product of user/item vectors.
    """
    
    def __init__(self, n_factors=50, n_epochs=20, lr_all=0.005, reg_all=0.02):
        self.n_factors = n_factors
        self.n_epochs = n_epochs  # kept for API compat, not used by TruncatedSVD
        self.lr_all = lr_all      # kept for API compat
        self.reg_all = reg_all    # kept for API compat
        self.model = None
        self.user_factors = None
        self.item_factors = None
        self.user_to_idx = None
        self.idx_to_user = None
        self.product_to_idx = None
        self.idx_to_product = None
        self.global_mean = 0.0
        self.user_means = None

    def train(self, interaction_matrix: np.ndarray, user_to_idx: dict, idx_to_user: dict,
              product_to_idx: dict, idx_to_product: dict) -> dict:
        """
        Train SVD model on the user-item interaction matrix.
        
        Args:
            interaction_matrix: numpy array of shape (n_users, n_products), values are ratings (0 = unrated)
            user_to_idx, idx_to_user, product_to_idx, idx_to_product: mapping dicts
        
        Returns:
            dict with training metrics: {rmse_mean, rmse_std, mae_mean}
        """
        self.user_to_idx = user_to_idx
        self.idx_to_user = idx_to_user
        self.product_to_idx = product_to_idx
        self.idx_to_product = idx_to_product
        
        # Store means for prediction
        rated_mask = interaction_matrix > 0
        self.global_mean = interaction_matrix[rated_mask].mean() if rated_mask.any() else 3.0
        
        # Per-user mean (for users with ratings)
        self.user_means = np.zeros(interaction_matrix.shape[0])
        for i in range(interaction_matrix.shape[0]):
            user_ratings = interaction_matrix[i][interaction_matrix[i] > 0]
            if len(user_ratings) > 0:
                self.user_means[i] = user_ratings.mean()
            else:
                self.user_means[i] = self.global_mean
        
        # Center the matrix (subtract user means from non-zero entries)
        centered_matrix = interaction_matrix.copy()
        for i in range(centered_matrix.shape[0]):
            mask = centered_matrix[i] > 0
            centered_matrix[i][mask] -= self.user_means[i]
        
        # Apply SVD
        n_components = min(self.n_factors, min(centered_matrix.shape) - 1)
        logger.info(f"Training SVD with {n_components} factors on {centered_matrix.shape} matrix...")
        
        self.model = TruncatedSVD(n_components=n_components, random_state=42)
        self.user_factors = self.model.fit_transform(centered_matrix)
        self.item_factors = self.model.components_.T  # (n_products, n_factors)
        
        # Compute training RMSE
        predicted = self.user_factors @ self.model.components_
        
        # Only evaluate on rated entries
        rmse_values = []
        mae_values = []
        for i in range(interaction_matrix.shape[0]):
            for j in range(interaction_matrix.shape[1]):
                if interaction_matrix[i, j] > 0:
                    pred_rating = predicted[i, j] + self.user_means[i]
                    pred_rating = np.clip(pred_rating, 1.0, 5.0)
                    actual = interaction_matrix[i, j]
                    rmse_values.append((pred_rating - actual) ** 2)
                    mae_values.append(abs(pred_rating - actual))
        
        rmse = np.sqrt(np.mean(rmse_values)) if rmse_values else 0.0
        mae = np.mean(mae_values) if mae_values else 0.0
        
        # Variance explained
        explained_var = self.model.explained_variance_ratio_.sum()
        
        logger.info(f"SVD Training complete — RMSE: {rmse:.4f}, MAE: {mae:.4f}, "
                     f"Variance explained: {explained_var:.2%}")
        
        return {
            'rmse_mean': float(rmse),
            'rmse_std': 0.0,
            'mae_mean': float(mae),
            'explained_variance': float(explained_var)
        }

    def predict(self, user_id: str, product_id: str) -> float:
        """Predict rating for a specific user-product pair."""
        if self.model is None or self.user_to_idx is None:
            return 0.0
        
        if user_id not in self.user_to_idx or product_id not in self.product_to_idx:
            return 0.0
        
        u_idx = self.user_to_idx[user_id]
        p_idx = self.product_to_idx[product_id]
        
        pred = np.dot(self.user_factors[u_idx], self.item_factors[p_idx])
        pred += self.user_means[u_idx]
        
        return float(np.clip(pred, 1.0, 5.0))

    def get_top_n(self, user_id: str, all_product_ids: list, n=20) -> list:
        """
        Get top-n product recommendations for a user.
        Returns list of (product_id, predicted_score) sorted descending.
        """
        if self.model is None or self.user_to_idx is None:
            return []
        
        if user_id not in self.user_to_idx:
            return []
        
        u_idx = self.user_to_idx[user_id]
        
        predictions = []
        for product_id in all_product_ids:
            if product_id not in self.product_to_idx:
                continue
            
            p_idx = self.product_to_idx[product_id]
            pred = np.dot(self.user_factors[u_idx], self.item_factors[p_idx])
            pred += self.user_means[u_idx]
            pred = float(np.clip(pred, 1.0, 5.0))
            
            predictions.append((product_id, pred))
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        return predictions[:n]

    def save(self, path: str):
        """Save the trained model to disk."""
        if self.model is None:
            raise ValueError("Model not trained yet.")
        joblib.dump({
            'model': self.model,
            'user_factors': self.user_factors,
            'item_factors': self.item_factors,
            'user_to_idx': self.user_to_idx,
            'idx_to_user': self.idx_to_user,
            'product_to_idx': self.product_to_idx,
            'idx_to_product': self.idx_to_product,
            'global_mean': self.global_mean,
            'user_means': self.user_means,
            'trained_at': datetime.now()
        }, path)
        logger.info(f"CF model saved to {path}")

    @classmethod
    def load(cls, path: str) -> 'CollaborativeFilter':
        """Load a trained model from disk."""
        data = joblib.load(path)
        instance = cls()
        instance.model = data['model']
        instance.user_factors = data['user_factors']
        instance.item_factors = data['item_factors']
        instance.user_to_idx = data['user_to_idx']
        instance.idx_to_user = data['idx_to_user']
        instance.product_to_idx = data['product_to_idx']
        instance.idx_to_product = data['idx_to_product']
        instance.global_mean = data['global_mean']
        instance.user_means = data['user_means']
        return instance
