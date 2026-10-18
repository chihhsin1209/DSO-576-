"""Read-only All Beauty analytics; definitions follow BUILD_SPEC.md (Phase 2)."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

VALID = [1, 2, 3, 4, 5]
CAPTURE_FILTERS = ('All', 'At least one field not captured', 'All three fields captured')
CAPTURE_COLUMNS = ('features_missing', 'description_missing', 'details_missing')


def load_data(root: str | Path = '.') -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load canonical outputs; never silently substitute samples."""
    root = Path(root)
    data = root / 'outputs' / 'data'
    required = [data / 'beauty_cleaned.parquet', data / 'products_cleaned.parquet']
    for file in required:
        if not file.is_file():
            raise FileNotFoundError(f'Missing canonical file: {file}. Run rebuild_full_dataset.py first.')
    return pd.read_parquet(required[0]), pd.read_parquet(required[1])


def _required(df: pd.DataFrame, columns: tuple[str, ...], label: str):
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f'{label} missing required columns: {sorted(missing)}')


def _ratings(reviews: pd.DataFrame) -> pd.Series:
    _required(reviews, ('rating_valid',), 'reviews')
    r = pd.to_numeric(reviews['rating_valid'], errors='coerce')
    return r.where(r.isin(VALID))


def overview_metrics(reviews: pd.DataFrame) -> dict:
    """Independent of queue filter; reviewed products exclude null identifiers."""
    _required(reviews, ('parent_asin',), 'reviews')
    ratings = _ratings(reviews)
    denom = int(ratings.notna().sum())
    neg = int(ratings.isin((1, 2)).sum())
    return {'review_count': len(reviews),
            'reviewed_product_count': int(reviews.parent_asin.nunique(dropna=True)),
            'valid_rating_count': denom,
            'negative_count': neg,
            'negative_rate': neg / denom if denom else None}


def product_summary(reviews: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Metadata-inclusive per-parent-ASIN summary; null review IDs cannot be attached to a product."""
    _required(reviews, ('parent_asin', 'rating_valid'), 'reviews')
    _required(products, ('parent_asin',), 'products')
    if products.parent_asin.isna().any() or products.parent_asin.duplicated().any():
        raise ValueError('Metadata parent_asin must be nonnull and unique (many-to-one join).')
    r = reviews.loc[reviews.parent_asin.notna(), ['parent_asin']].copy()
    r['valid_rating'] = _ratings(reviews.loc[reviews.parent_asin.notna()])
    r['is_negative'] = r['valid_rating'].isin((1, 2)).astype('int64')
    grouped = r.groupby('parent_asin', sort=False).agg(
        review_count=('valid_rating', 'size'),
        valid_rating_count=('valid_rating', 'count'),
        negative_count=('is_negative', 'sum'),
        average_rating=('valid_rating', 'mean')).reset_index()
    summary = products.merge(grouped, on='parent_asin', how='outer', validate='one_to_one', indicator='_metadata_join')
    summary['metadata_match'] = summary['_metadata_join'].map({'both': 'both', 'left_only': 'left_only', 'right_only': 'right_only'}).astype('object')
    summary = summary.drop(columns=['_metadata_join'])
    for col in ('review_count', 'valid_rating_count', 'negative_count'):
        summary[col] = summary[col].fillna(0).astype('int64')
    summary['negative_rate'] = summary.negative_count.div(summary.valid_rating_count.where(summary.valid_rating_count.ne(0)))
    for col in CAPTURE_COLUMNS:
        if col not in summary:
            summary[col] = True
        summary[col] = summary[col].fillna(True).astype(bool)
    summary['captured_content_count'] = 3 - summary[list(CAPTURE_COLUMNS)].sum(axis=1)
    return summary


def rank_queue(summary: pd.DataFrame, min_valid_reviews: int = 5,
               capture_filter: str = 'All') -> pd.DataFrame:
    if isinstance(min_valid_reviews, bool) or not isinstance(min_valid_reviews, int) or min_valid_reviews < 1:
        raise ValueError('min_valid_reviews must be a positive integer (>=1).')
    if capture_filter not in CAPTURE_FILTERS:
        raise ValueError(f'capture_filter must be one of {CAPTURE_FILTERS}.')
    _required(summary, ('parent_asin','valid_rating_count','negative_count','negative_rate',*CAPTURE_COLUMNS), 'summary')
    q = summary.loc[summary.valid_rating_count >= min_valid_reviews].copy()
    absent = q[list(CAPTURE_COLUMNS)].fillna(True).astype(bool).sum(axis=1)
    if capture_filter == 'At least one field not captured':
        q = q.loc[absent > 0]
    elif capture_filter == 'All three fields captured':
        q = q.loc[absent == 0]
    return q.sort_values(['negative_rate', 'negative_count', 'valid_rating_count', 'parent_asin'],
                         ascending=[False, False, False, True], kind='stable').reset_index(drop=True)


def rating_distribution(reviews: pd.DataFrame, parent_asin: str) -> pd.DataFrame:
    _required(reviews, ('parent_asin','rating_valid'), 'reviews')
    ratings = _ratings(reviews.loc[reviews.parent_asin.eq(parent_asin)])
    counts = ratings.value_counts().reindex(VALID, fill_value=0)
    return pd.DataFrame({'rating': VALID, 'review_count': counts.astype(int).to_numpy()})


def review_excerpts(reviews: pd.DataFrame, parent_asin: str,
                    negative_only: bool = True, page: int = 1,
                    page_size: int = 20) -> pd.DataFrame:
    """Returns one page of evidence; use review_excerpt_count for pagination totals."""
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError('page must be a positive integer')
    if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
        raise ValueError('page_size must be a positive integer')
    _required(reviews, ('parent_asin','rating_valid','source_review_row'), 'reviews')
    rows = reviews.loc[reviews.parent_asin.eq(parent_asin)].copy()
    if negative_only:
        rows = rows.loc[_ratings(rows).isin((1, 2))]
    if 'review_time_utc' in rows:
        rows['_time'] = pd.to_datetime(rows.review_time_utc, errors='coerce', utc=True)
    else:
        rows['_time'] = pd.NaT
    rows = rows.sort_values(['_time', 'source_review_row'], ascending=[False, True],
                            na_position='last', kind='stable')
    rows = rows.iloc[(page - 1) * page_size:page * page_size].drop(columns=['_time'])
    if 'text' in rows:
        rows['text'] = rows['text'].fillna('').astype(str).map(lambda x: x if x.strip() else 'No review body captured')
    return rows.reset_index(drop=True)


def review_excerpt_count(reviews: pd.DataFrame, parent_asin: str,
                         negative_only: bool = True) -> int:
    _required(reviews, ('parent_asin','rating_valid'), 'reviews')
    subset = reviews.loc[reviews.parent_asin.eq(parent_asin)]
    return int(_ratings(subset).isin((1, 2)).sum()) if negative_only else len(subset)


def _captured(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    if hasattr(value, 'size') and not isinstance(value, (str, bytes)):
        return bool(value.size)
    try:
        if bool(pd.isna(value)):
            return False
    except (ValueError, TypeError):
        pass
    return bool(str(value).strip())


def product_metadata(products: pd.DataFrame, parent_asin: str) -> dict:
    _required(products, ('parent_asin',), 'products')
    found = products.loc[products.parent_asin.eq(parent_asin)]
    if len(found) > 1:
        raise ValueError(f'Duplicate metadata for parent_asin={parent_asin}')
    fields = ('product_title', 'store', 'price_numeric', 'features', 'description', 'details')
    if found.empty:
        return {'parent_asin': parent_asin, 'metadata_match': False,
                'fields': {field: {'value': None, 'status': 'Not captured'} for field in fields}}
    row = found.iloc[0]
    result = {}
    for field in fields:
        value = row.get(field)
        available = _captured(value)
        if field == 'price_numeric':
            try:
                available = available and float(value) > 0 and pd.notna(float(value))
            except (TypeError, ValueError):
                available = False
        result[field] = {'value': value if available else None,
                         'status': 'Captured (historical snapshot)' if available else 'Not captured (historical snapshot)'}
    return {'parent_asin': parent_asin, 'metadata_match': True, 'fields': result}
