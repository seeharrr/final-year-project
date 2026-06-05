import pandas as pd
from django.test import TestCase
from recommendation.engine.preprocessing import (
    load_amazon_dataset,
    filter_sparse_data,
    build_user_item_matrix,
    build_product_feature_text,
    encode_users_products,
    prepare_interaction_matrix
)
import numpy as np

class PreprocessingTests(TestCase):
    
    def setUp(self):
        # Synthetic DataFrame
        self.df = pd.DataFrame({
            'reviewerID': ['u1', 'u1', 'u1', 'u2', 'u3', 'u4', 'u5', 'u1', 'u1', 'u1'],
            'asin': ['p1', 'p2', 'p3', 'p1', 'p1', 'p2', 'p3', 'p4', 'p5', 'p6'],
            'overall': [5.0, 4.0, 3.0, 4.0, 5.0, 2.0, 1.0, 5.0, 4.0, 3.0],
            'product_title': ['T1', 'T2', 'T3', 'T1', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6'],
            'product_category': ['C1', 'C2', 'C3', 'C1', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6'],
            'sustainability_tags': ['D1', 'D2', 'D3', 'D1', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6'],
            'is_best_seller': ['No Badge']*10
        })

    def test_filter_sparse_data(self):
        filtered_df = filter_sparse_data(self.df, min_user_ratings=2, min_product_ratings=2)
        self.assertEqual(len(filtered_df), 0)
        
        filtered_df2 = filter_sparse_data(self.df, min_user_ratings=1, min_product_ratings=1)
        self.assertEqual(len(filtered_df2), 10)

    def test_build_user_item_matrix(self):
        matrix = build_user_item_matrix(self.df)
        self.assertEqual(matrix.shape, (5, 6)) # 5 users, 6 products
        self.assertEqual(matrix.loc['u1', 'p1'], 5.0)
        self.assertEqual(matrix.loc['u2', 'p1'], 4.0)
        self.assertEqual(matrix.loc['u3', 'p3'], 0.0) # NaN filled with 0
        
    def test_build_product_feature_text(self):
        products_df = self.df.drop_duplicates(subset=['asin']).set_index('asin')
        texts = build_product_feature_text(products_df)
        self.assertEqual(len(texts), 6)
        self.assertTrue('t1' in texts['p1'])
        self.assertTrue('c1' in texts['p1'])
        
    def test_encode_users_products(self):
        u2i, i2u, p2i, i2p = encode_users_products(self.df)
        self.assertEqual(len(u2i), 5)
        self.assertEqual(len(p2i), 6)
        self.assertEqual(u2i['u1'], 0)
        self.assertEqual(p2i['p1'], 0)
        
    def test_prepare_interaction_matrix(self):
        matrix, u2i, i2u, p2i, i2p = prepare_interaction_matrix(self.df)
        self.assertEqual(matrix.shape, (5, 6))
        self.assertIsInstance(matrix, np.ndarray)
        self.assertEqual(matrix[u2i['u1'], p2i['p1']], 5.0)
