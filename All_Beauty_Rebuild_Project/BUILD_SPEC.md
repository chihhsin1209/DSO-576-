# BUILD_SPEC — Amazon All Beauty Review & Captured Listing Content Prioritization

**Project:** USC Marshall DSO 576, Phase 2  
**Status:** Proposed revised team vision and build contract. The existing All Beauty cleaning outputs are from the `alex` branch; team adoption and integration into `main` are still required.

## A. Revised vision and boundary

**Primary user:** An Amazon All Beauty category/assortment manager reviewing product listings for possible customer-experience or information-quality problems.

**Recurring decision:** Which parent-ASIN listings deserve manual inspection first, based on their share and volume of low ratings, with captured listing metadata available for context.

**Why better than current practice:** Rather than manually sorting through individual reviews and disconnected listing attributes, the manager receives a repeatable, product-level screening queue and can drill into the underlying evidence.

**Important limits:** A 1–2-star rating means a negative rating, **not** a proven complaint about missing product information. Missing fields in the captured historical metadata mean **not captured in this dataset**, not missing from a current live Amazon listing. Review counts are not sales or demand, `store` is not necessarily brand, and the dataset cannot support causal claims about conversion or sales uplift. No automatic listing edits or AI-generated diagnoses are in MVP scope.

**Scope change:** This specification intentionally changes the earlier Appliances/keyword-mention vision to a **Beauty negative-review prioritization** MVP, following the actual available All Beauty cleaned-data pipeline. The team must approve this Phase 1 vision revision before final submission.

## B. Use cases (select/input → see → decide)

1. **Prioritize:** Manager sets a minimum valid-rating count (default **5**) and optionally a captured-metadata availability filter → dashboard shows ranked parent-ASIN products with negative ratings, valid-rating denominators, average rating and review volume → manager selects listings for manual review.
2. **Diagnose:** Manager selects a parent ASIN → dashboard shows rating distribution, summary counts and associated review excerpts (default: 1–2-star reviews) → manager decides whether evidence is substantial enough for deeper inspection.
3. **Check captured content:** Manager selects a product and inspects the metadata panel → dashboard shows captured title, store, numeric price where valid, features, description and details with explicit availability labels → manager decides which attributes should be checked against the *current* live listing manually.

The MVP does **not** persist investigation statuses or priorities; the decision takes place outside the app.

## C. Dashboard UI contract (Phase 3; do not build the UI in Phase 2)

**Landing view:** All Beauty overview + ranked product queue. Two major sections/tabs: **Overview & Queue** and **Product Detail** (activated by product selection).

**Overview:** Total retained review rows; number of distinct reviewed parent ASINs; valid-rated review count; total negative (1–2-star) reviews; overall negative-review rate. Metrics use the **entire canonical cleaned review table**, independent of the queue minimum-count threshold. A reviewed product means a nonnull parent ASIN with at least one retained review. Separately label a product count that includes metadata-only products, if displayed.

**Queue columns:** parent_asin, product title (fallback to ASIN if unavailable), total review count, valid rating count, negative count, negative-review rate, average valid rating, `features_missing`, `description_missing`, `details_missing`, and metadata-match indicator. A compact captured-content count may be derived as the sum of these three *missing-capture* flags; it is not a live-listing quality score.

**Queue controls:** Minimum valid-rated reviews (integer, default 5, minimum 1); metadata capture status (`All`, `At least one field not captured`, `All three fields captured`). Apply these filters to queue membership only. No subcategory filter: `categories` has no usable values in the audited All Beauty metadata (112,590/112,590 absent). Do not infer categories from titles or `store`.

**Queue sort:** negative-review rate descending, then negative count descending, valid rating count descending, parent_asin ascending. Display rates as percentages alongside numerator and denominator. A product with zero valid ratings has rate `N/A`, and is excluded under the default queue threshold.

**Product Detail:** Product identity (parent_asin, captured title and store), review count, valid-rated count, 1-star through 5-star counts, mean valid rating, negative-review count/rate, and metadata capture panel. Review excerpts default to 1–2-star reviews; a toggle switches to all retained reviews. Show rating, review title, review body, UTC timestamp if valid, helpful votes if valid, verified-purchase flag if valid, and `source_review_row` for traceability. Sort most recent valid UTC timestamp first, then `source_review_row` ascending; invalid/missing timestamps last. Show 20 rows per page. Empty review text is labeled `No review body captured`, not silently removed from rating denominators. Product selection must not alter overview totals or other queue rows.

**Empty/unavailable states:** No queue products meet the threshold → clear empty message; no relevant review excerpts → clear message; unavailable numeric rate → `N/A`; nonmatching metadata → `Not captured`; source field absent/empty → `Not captured (historical snapshot)`; invalid price → show unavailable numeric price, not fabricated zero. Never claim any captured field is missing from the current listing.

## D. Data and metric contracts

**Canonical sources:** `data/raw/All_Beauty.jsonl` (reviews) and `data/raw/full-00000-of-00001 (1).parquet` (metadata), as specified in `config/cleaning_rules.json`. These raw files are excluded from Git and **not included in the supplied ZIP**. Existing hash checks are source-version-specific: use the recorded hashes for those exact files; do not silently weaken checks or claim a fresh run without the files.

**Cleaning authority:** Preserve the behavior of the existing `scripts/clean_data.py` and `config/cleaning_rules.json` unless the team explicitly agrees on a change. Deduplicate only **identical whole raw records** using a canonical sorted-key JSON fingerprint, retaining first occurrence; never assume `(user_id,parent_asin,timestamp)` uniquely identifies reviews. Preserve raw identifiers/fields; derive `text_clean`, `review_title_clean`, `rating_valid`, `helpful_vote_valid`, `verified_purchase_valid`, UTC time and validity flags; retain invalid cases with documented flags. Metadata `parent_asin` must be non-null and unique. Left-join reviews to metadata with `validate='many_to_one'`; no review-row multiplication. Product-level metadata metrics are computed at unique product grain, not review grain.

**Artifacts already defined in the alex implementation:** `outputs/data/beauty_cleaned.parquet` (retained reviews joined to metadata), `outputs/data/products_cleaned.parquet` (metadata products), `outputs/data/product_metrics.parquet` (products including those without reviews), and `outputs/reports/audit.json`. These complete Parquet outputs are generated locally and Git-ignored; their absence from the ZIP must not be mistaken for a completed shared-main dataset.

| Metric | Numerator / calculation | Denominator / grain | Notes |
|---|---|---|---|
| Retained review count | Count rows | Review grain in `beauty_cleaned` | After exact-duplicate removal |
| Reviewed product count | Distinct nonnull `parent_asin` in reviews | Parent product | Different from total metadata products |
| Valid-rated reviews | Count non-null `rating_valid` | Review grain | Valid integer ratings 1–5 |
| Negative reviews | Count `rating_valid` in {1,2} | Review/product | No text keyword assumption |
| Negative-review rate | Negative reviews / valid-rated reviews | Entire dataset or per parent ASIN | Undefined for zero valid ratings |
| Average rating | Mean `rating_valid` | Per product, or across retained reviews for overall | Excludes invalid ratings |
| Five-star distribution | Counts of valid ratings 1,2,3,4,5 | Product | Invalid ratings excluded |
| Captured-content availability | `features_missing`, `description_missing`, `details_missing` | Unique metadata product | Snapshot availability, not omission |
| Numeric price | `price_numeric` when valid | Unique metadata product | Not revenue, never sum prices across reviews |

**No unsupported category logic:** The audited `categories_missing` count equals the full 112,590 metadata records. `main_category` is available in the source schema but must not be treated as usable differentiated subcategories without new inspection.

**Filter precedence:** Compute product metrics from *all retained reviews*, then apply queue minimum count and metadata availability filters. Never calculate the negative-review denominator using only negative or nonblank-text reviews. The detail-review toggle affects excerpts only, not product KPI values. The overall overview is not recomputed from the filtered queue.

## E. Modular architecture and function contracts

```
data/raw/All_Beauty.jsonl + data/raw/full-00000-of-00001 (1).parquet
     → scripts/clean_data.py (existing canonical validation + cleaning)
     → outputs/data/{beauty_cleaned,products_cleaned,product_metrics}.parquet
         + outputs/reports/audit.json
     → src/analysis.py (new: reusable read-only aggregations/query functions)
     → Phase 3 Streamlit UI (presentation only)
```

**`src/analysis.py` required callable contracts (names suggested; implement consistently):**

- `overview_metrics(reviews: pd.DataFrame) -> dict`: return reviewed product count, review count, valid-rated count, negative count and negative rate; never depend on queue filters.
- `product_summary(reviews: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame`: one row per metadata product plus any unmatched review parent ASINs; return identifiers, counts, rates, average valid rating and captured-metadata flags. Preserve metadata-only products with zero reviews, and `N/A`/null rates, rather than inventing review evidence.
- `rank_queue(summary: pd.DataFrame, min_valid_reviews: int = 5, capture_filter: str = 'All') -> pd.DataFrame`: implement queue inclusion and documented sort; validate thresholds/filter choices; return a DataFrame without modifying inputs.
- `rating_distribution(reviews: pd.DataFrame, parent_asin: str) -> pd.DataFrame`: exactly five rating bins, including zero-count bins.
- `review_excerpts(reviews: pd.DataFrame, parent_asin: str, negative_only: bool = True, page: int = 1, page_size: int = 20) -> pd.DataFrame`: return deterministically ordered and paged evidence; total matching review count should also be available for pagination (e.g., companion result or distinct count function).
- `product_metadata(products: pd.DataFrame, parent_asin: str) -> dict`: return captured fields and explicit field-availability statuses; never imply current live-listing state.

Functions must return values/DataFrames, not only print. Each must have unit tests, null/zero handling, deterministic results, documented inputs and outputs. The UI must not independently recompute business metrics. Keep data loading, analytics and rendering separate to limit changes from rippling through unrelated components.

## F. Technical choices

Python, pandas, numpy, pyarrow and Parquet; existing pinned dependencies in `requirements.txt`. Streamlit is proposed for **Phase 3 only**. Reading the cleaned Parquet artifacts is preferable to reparsing JSONL on every UI interaction. Cache immutable aggregated summaries by source artifact revision (e.g., content hash or file version) plus relevant filter inputs; invalidate on data changes. Paginate review evidence; avoid rendering hundreds of thousands of rows. Profile local memory and execution time on the full files before setting performance targets. Preserve Git-ignore rules for raw files, full outputs, caches, environments and secrets. Include reproducible input-file placement and execution instructions in README.

## G. Build order and Phase boundary

**Complete during Phase 2:**

1. Obtain team approval of the All Beauty vision change (the team `project-start.md` currently names Appliances).
2. Compare individual Module 6 cleaning approaches; document why the selected All Beauty exact-duplicate and metadata-join rules become canonical, and record disagreements/decisions. Do **not** describe Appliances code as if it cleaned Beauty.
3. Re-run/verify the canonical All Beauty pipeline using the required original local source files; reconcile output and audit against code and document source hashes. Share the reproducible cleaned artifacts or documented access/rebuild procedure with the team.
4. Add/test `src/analysis.py` against the canonical clean tables and edge cases; ensure the dashboard's required aggregates are available without UI code.
5. Put the agreed `BUILD_SPEC.md`, pipeline, analysis module, tests and documentation on **main** through your normal review/merge process. Avoid pushing raw/full files to Git.
6. Give a fresh agent the repository and this spec; record questions/guesses and revise the spec or backend contract until major behavior is unambiguous.

**Only in Phase 3:** build Streamlit overview, queue and product detail, interactive controls and review pagination; test UI performance and user workflow. Dashboard polish or a completed interface is not a Phase 2 requirement.

## H. Acceptance checks

1. The existing documented reference run reports **701,528** raw reviews, **7,275** identical duplicate copies removed, **694,253** retained/merged review rows, **112,590** metadata records, **0** extra join rows, and **0** unmatched retained reviews; the audit status is `PASS`. These are historical audited results in the supplied branch, **not** a claim that full source data was rerun from the uploaded ZIP.
2. Metadata duplicate/non-null key validation fails clearly instead of arbitrarily selecting a record; a many-to-one join cannot multiply review rows.
3. `negative_count = 2`, `valid_rating_count = 10` gives negative-review rate **20%**, even if only some review bodies are nonblank. Zero valid ratings gives `N/A`, not 0%.
4. Rating values other than valid integer 1–5 do not enter counts, denominators or averages. Product-level metrics reconcile with the canonical audit and/or existing `product_metrics.parquet`.
5. Sorting is deterministic for ties; minimum valid-rated count changes queue membership but never overview or product metric denominators.
6. Products with no review rows remain representable in the metadata-inclusive product summary, with review count zero and undefined review-based rates; the default queue excludes them.
7. Review evidence toggles and pagination change only displayed excerpts, not KPIs. Source row identifies evidence unambiguously after cleaning.
8. No category/subcategory control depends on the entirely empty `categories` field. Captured-content absences are always labeled as **not captured** rather than live-listing omissions.
9. A fresh coding agent can identify required files, function interfaces, all relevant metrics, interactions and empty states without making consequential product/data assumptions; discovered gaps are fixed before submitting.

## I. Explicit remaining approvals / dependencies

- **Team decision:** Sign off on changing the team project from *Appliances keyword specification mentions* to *All Beauty negative-review prioritization*. The earlier proposal cannot be treated as automatically approved.
- **Original files:** The uploaded repository ZIP lacks the complete `All_Beauty.jsonl` and metadata Parquet, and the full generated Parquet outputs; reproduce the existing audit on the team's actual source files before calling `main` canonical.
- **Repository work:** The provided `main` ZIP does not show the `alex` pipeline or a dashboard-specific `src/analysis.py`. Merge/adapt and test them rather than claiming completion from this spec alone.
- **Team cleaning reconciliation:** Document the cross-branch differences, noting that other teammates' Appliances scripts target a different dataset.
- **New default choices:** Minimum valid-rated-review count 5 and captured-content filter are proposed UI decisions requiring team signoff, not historical cleaning outcomes.

