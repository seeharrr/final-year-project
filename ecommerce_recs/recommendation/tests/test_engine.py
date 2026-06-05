import pandas as pd
from unittest.mock import MagicMock, patch
from django.test import TestCase
from recommendation.engine.collaborative import CollaborativeFilter
from recommendation.engine.content_based import ContentBasedFilter
from recommendation.engine.hybrid import HybridRecommender

class TestCollaborativeFilter(TestCase):
    def test_init(self):
        cf = CollaborativeFilter(n_factors=50, n_epochs=10)
        self.assertEqual(cf.n_factors, 50)
        self.assertEqual(cf.n_epochs, 10)
        self.assertIsNone(cf.model)

    def test_predict_without_training(self):
        cf = CollaborativeFilter()
        result = cf.predict('user1', 'product1')
        self.assertEqual(result, 0.0)

    def test_get_top_n_without_training(self):
        cf = CollaborativeFilter()
        result = cf.get_top_n('user1', ['p1', 'p2', 'p3'], n=5)
        self.assertEqual(result, [])

    def test_save_without_training_raises(self):
        cf = CollaborativeFilter()
        with self.assertRaises(ValueError):
            cf.save('/tmp/test_model.joblib')


class TestContentBasedFilter(TestCase):
    def setUp(self):
        self.product_texts = pd.Series({
            'p1': 'wireless bluetooth headphones noise cancelling',
            'p2': 'bluetooth earbuds wireless in-ear headphones',
            'p3': 'laptop computer gaming nvidia graphics card',
            'p4': 'mechanical keyboard rgb backlit gaming',
            'p5': 'wireless mouse ergonomic bluetooth optical',
            'p6': 'usb flash drive storage portable 64gb',
            'p7': 'smartphone android 5g camera display',
            'p8': 'tablet 10 inch screen android wifi',
            'p9': 'portable charger power bank 20000mah',
            'p10': 'hdmi cable 4k high speed adapter'
        })
        self.cbf = ContentBasedFilter(max_features=100)
        self.cbf.fit(self.product_texts)

    def test_fit_creates_matrix(self):
        self.assertIsNotNone(self.cbf.matrix)
        self.assertEqual(self.cbf.matrix.shape[0], 10)

    def test_get_similar_returns_list_of_tuples(self):
        results = self.cbf.get_similar('p1', n=5)
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 5)
        for item in results:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)

    def test_get_similar_excludes_self(self):
        results = self.cbf.get_similar('p1', n=10)
        asins = [asin for asin, _ in results]
        self.assertNotIn('p1', asins)

    def test_get_similar_unknown_asin(self):
        results = self.cbf.get_similar('unknown_asin', n=5)
        self.assertEqual(results, [])

    def test_user_profile_recommendations(self):
        results = self.cbf.get_user_profile_recommendations(['p1'], ['p3'], n=5)
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 5)

    def test_save_without_training_raises(self):
        cbf = ContentBasedFilter()
        with self.assertRaises(ValueError):
            cbf.save('/tmp/test_cbf.joblib')


class TestHybridRecommender(TestCase):
    def setUp(self):
        self.cf = MagicMock(spec=CollaborativeFilter)
        self.cbf = MagicMock(spec=ContentBasedFilter)
        self.hybrid = HybridRecommender(self.cf, self.cbf)

    def test_compute_alpha_zero_ratings(self):
        self.assertEqual(self.hybrid.compute_alpha(0), 0.0)

    def test_compute_alpha_ten_ratings(self):
        self.assertEqual(self.hybrid.compute_alpha(10), 0.5)

    def test_compute_alpha_twenty_five_ratings(self):
        self.assertEqual(self.hybrid.compute_alpha(25), 1.0)

    def test_compute_alpha_twenty_ratings(self):
        self.assertEqual(self.hybrid.compute_alpha(20), 1.0)

    def test_recommend_returns_list_of_dicts(self):
        self.cf.get_top_n.return_value = [('p1', 4.5), ('p2', 4.0), ('p3', 3.5)]
        self.cbf.get_user_profile_recommendations.return_value = [('p2', 0.9), ('p4', 0.8), ('p5', 0.7)]

        results = self.hybrid.recommend(
            user_id='u1',
            user_django_id=1,
            viewed_asins=['p1'],
            purchased_asins=['p2'],
            all_product_ids=['p1', 'p2', 'p3', 'p4', 'p5'],
            n=5,
            user_rating_count=10
        )

        self.assertIsInstance(results, list)
        for rec in results:
            self.assertIn('asin', rec)
            self.assertIn('hybrid_score', rec)
            self.assertIn('cf_score', rec)
            self.assertIn('cbf_score', rec)
            self.assertIn('alpha', rec)
            self.assertIn('source', rec)
            self.assertIn('explanation', rec)

    def test_recommend_cold_start(self):
        self.cbf.get_user_profile_recommendations.return_value = [('p1', 0.9), ('p2', 0.8)]
        results = self.hybrid.recommend_cold_start(['p3'], n=5)

        self.assertIsInstance(results, list)
        for rec in results:
            self.assertEqual(rec['cf_score'], 0.0)
            self.assertEqual(rec['alpha'], 0.0)
            self.assertEqual(rec['source'], 'content')
