"""Local smoke and reconciliation checks for the generated canonical parquet outputs."""
from src.analysis import load_data, overview_metrics, product_summary, rank_queue, rating_distribution, review_excerpts
import json
from pathlib import Path

reviews, products = load_data()
overview = overview_metrics(reviews)
summary = product_summary(reviews, products)
queue = rank_queue(summary)
print('FULL DATA OVERVIEW:', json.dumps(overview, indent=2))
print('PRODUCT SUMMARY ROWS:', len(summary))
print('RANKED QUEUE ROWS:', len(queue))
print('TOP 5 ASINS:', queue.parent_asin.head().tolist())
assert len(summary) >= len(products), 'Summary unexpectedly lost metadata products'
assert int(summary.review_count.sum()) <= len(reviews), 'Product summary amplified review rows'
assert int(summary.negative_count.sum()) <= overview['negative_count']
assert int(summary.valid_rating_count.sum()) <= overview['valid_rating_count']
if reviews.parent_asin.notna().all():
    assert int(summary.review_count.sum()) == len(reviews)
    assert int(summary.negative_count.sum()) == overview['negative_count']
if not queue.empty:
    asin = queue.iloc[0].parent_asin
    print('FIRST PRODUCT DISTRIBUTION:', rating_distribution(reviews, asin).to_dict('records'))
    print('FIRST PRODUCT NEGATIVE EXCERPTS:', len(review_excerpts(reviews, asin)))
reference = {'review_count': 694253}
if overview['review_count'] != reference['review_count']:
    print('WARNING: review count differs from historical reference 694253; investigate audit/source version.')
else:
    print('Historical cleaned review count matched.')
audit_path = Path('outputs/reports/audit.json')
if audit_path.exists():
    audit = json.loads(audit_path.read_text())
    print('Audit available:', audit_path)
print('Backend smoke checks PASSED.')
