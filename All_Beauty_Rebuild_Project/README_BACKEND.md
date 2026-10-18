# All Beauty — Phase 2 Backend Analysis

This package adds the reusable, read-only analysis backend required by `BUILD_SPEC.md` Section E. **It does not build the Phase 3 dashboard.**

## Installation in your existing project

Copy this package's `src/` and `tests/` directories into the ROOT of `All_Beauty_Rebuild_Project` (beside `BUILD_SPEC.md` and `rebuild_full_dataset.py`). Do not overwrite your existing cleaning scripts or canonical Parquet outputs.

With the project's `.venv` activated:

```bash
python -m unittest discover -s tests -v
python verify_backend.py
```

`verify_backend.py` expects local outputs from `rebuild_full_dataset.py` in `outputs/data/`. All functions are importable from `src.analysis`; the dashboard must use these instead of recalculating metrics.

**Functions:** `load_data`, `overview_metrics`, `product_summary`, `rank_queue`, `rating_distribution`, `review_excerpts`, `review_excerpt_count`, `product_metadata`.

## Semantics

- 1–2-star **valid ratings** are negative; denominator is all valid 1–5 ratings (NOT nonblank review text).
- Filtered queue does not affect overview counts or underlying product rates.
- Metadata-only products are retained in `product_summary` with zero reviews and undefined rating rates.
- Only use unique, non-null metadata `parent_asin` keys. Unmatched review product keys remain as product summary rows.
- Null review parent identifiers cannot be grouped to a specific product; they remain in global review totals.
- Captured metadata is a historical snapshot. Flags indicate captured-field availability, not live listing omission.

## Full-data verification

The independent unit tests use synthetic records; passing tests **does not prove** the full dataset agrees with the historical audit. Run `verify_backend.py` on your Mac with the full rebuilt local Parquet files. Save its printed counts and output as Phase 2 evidence. Validate the reported counts and reconcile any differences rather than silently changing definitions.

## Phase 2 work still outside this package

Team approval of the move from Appliances to All Beauty; documenting branch cleaning disagreements; main-branch integration; complete original-file audit and fresh-agent test.
