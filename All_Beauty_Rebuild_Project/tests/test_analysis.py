import unittest
import pandas as pd
from src.analysis import (overview_metrics, product_summary, rank_queue,
                          rating_distribution, review_excerpts, review_excerpt_count, product_metadata)


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.reviews = pd.DataFrame({
            'parent_asin': ['a']*10 + ['b'],
            'rating_valid': [1., 2.] + [5.]*8 + [float('nan')],
            'source_review_row': list(range(11)),
            'text': [''] + ['body']*10,
            'review_time_utc': pd.to_datetime(['2024-01-01']*11, utc=True)})
        self.products = pd.DataFrame({'parent_asin': ['a','b','c'], 'product_title':['A','B','C'],
                                     'features_missing':[False,True,True],
                                     'description_missing':[False,True,True],
                                     'details_missing':[False,True,True]})

    def test_rate_and_overview(self):
        x = overview_metrics(self.reviews)
        self.assertEqual((x['negative_count'], x['valid_rating_count']), (2,10))
        self.assertAlmostEqual(x['negative_rate'], 0.2)
    def test_summary_includes_metadata_only(self):
        x = product_summary(self.reviews,self.products).set_index('parent_asin')
        self.assertEqual(x.loc['a','negative_rate'], 0.2)
        self.assertTrue(pd.isna(x.loc['b','negative_rate']))
        self.assertEqual(x.loc['c','review_count'], 0)
    def test_queue_filter_and_no_mutation(self):
        x = product_summary(self.reviews,self.products)
        before = x.copy(deep=True)
        self.assertEqual(rank_queue(x)['parent_asin'].tolist(), ['a'])
        self.assertEqual(len(rank_queue(x,1,'All three fields captured')), 1)
        self.assertEqual(len(rank_queue(x,1,'At least one field not captured')), 0)
        pd.testing.assert_frame_equal(x,before)
    def test_distribution_and_pagination(self):
        self.assertEqual(rating_distribution(self.reviews,'a').review_count.tolist(), [1,1,0,0,8])
        self.assertEqual(review_excerpt_count(self.reviews,'a'),2)
        self.assertEqual(len(review_excerpts(self.reviews,'a',page_size=1)),1)
        self.assertEqual(review_excerpts(self.reviews,'a').iloc[0]['text'],'No review body captured')
    def test_metadata(self):
        self.assertEqual(product_metadata(self.products,'unknown')['fields']['product_title']['status'], 'Not captured')
    def test_bad_metadata_keys(self):
        with self.assertRaises(ValueError):
            product_summary(self.reviews, pd.concat([self.products,self.products.iloc[:1]]))
    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            rank_queue(product_summary(self.reviews,self.products), 0)

if __name__=='__main__':
    unittest.main()
