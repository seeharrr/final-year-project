from django.test import TestCase
from recommendation.evaluation.metrics import precision_at_k, recall_at_k, coverage


class TestPrecisionAtK(TestCase):
    def test_perfect_precision(self):
        recommended = ['p1', 'p2', 'p3', 'p4', 'p5']
        relevant = ['p1', 'p2', 'p3', 'p4', 'p5']
        self.assertEqual(precision_at_k(recommended, relevant, 5), 1.0)

    def test_zero_precision(self):
        recommended = ['p6', 'p7', 'p8', 'p9', 'p10']
        relevant = ['p1', 'p2', 'p3', 'p4', 'p5']
        self.assertEqual(precision_at_k(recommended, relevant, 5), 0.0)

    def test_partial_precision(self):
        recommended = ['p1', 'p6', 'p2', 'p7', 'p3']
        relevant = ['p1', 'p2', 'p3']
        self.assertEqual(precision_at_k(recommended, relevant, 5), 3 / 5)

    def test_k_less_than_list(self):
        recommended = ['p1', 'p2', 'p3', 'p4', 'p5']
        relevant = ['p1', 'p2']
        self.assertEqual(precision_at_k(recommended, relevant, 2), 1.0)

    def test_empty_recommended(self):
        self.assertEqual(precision_at_k([], ['p1'], 5), 0.0)

    def test_empty_relevant(self):
        self.assertEqual(precision_at_k(['p1'], [], 5), 0.0)


class TestRecallAtK(TestCase):
    def test_perfect_recall(self):
        recommended = ['p1', 'p2', 'p3']
        relevant = ['p1', 'p2', 'p3']
        self.assertEqual(recall_at_k(recommended, relevant, 3), 1.0)

    def test_zero_recall(self):
        recommended = ['p4', 'p5', 'p6']
        relevant = ['p1', 'p2', 'p3']
        self.assertEqual(recall_at_k(recommended, relevant, 3), 0.0)

    def test_partial_recall(self):
        recommended = ['p1', 'p4', 'p5']
        relevant = ['p1', 'p2', 'p3']
        self.assertAlmostEqual(recall_at_k(recommended, relevant, 3), 1 / 3)

    def test_empty_recommended(self):
        self.assertEqual(recall_at_k([], ['p1'], 5), 0.0)

    def test_empty_relevant(self):
        self.assertEqual(recall_at_k(['p1'], [], 5), 0.0)


class TestCoverage(TestCase):
    def test_full_coverage(self):
        all_recs = {
            'u1': ['p1', 'p2'],
            'u2': ['p3', 'p4'],
            'u3': ['p5']
        }
        self.assertEqual(coverage(all_recs, 5), 1.0)

    def test_partial_coverage(self):
        all_recs = {
            'u1': ['p1', 'p2'],
            'u2': ['p1', 'p3']
        }
        self.assertEqual(coverage(all_recs, 6), 0.5)

    def test_zero_coverage(self):
        self.assertEqual(coverage({}, 10), 0.0)

    def test_zero_catalog(self):
        self.assertEqual(coverage({'u1': ['p1']}, 0), 0.0)
