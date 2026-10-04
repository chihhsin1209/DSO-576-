# Module 6 - Wayne J. Chen: All Beauty data cleaning

- Branch: `cleaning-waynechen`
- Branch URL: https://github.com/chihhsin1209/DSO-576-/tree/cleaning-waynechen
- Submitted commit ID: `PENDING_USER_PUSH`
- Source ZIP snapshot commit: `14d977ee9dc441249520bb74b17cabaa72ab874e`

## Project and source

The newer uploaded project vision uses **All Beauty**. The older branch's Appliances proposal is preserved in `docs/project-start.md` for provenance, and is superseded for this assignment. A Beauty category manager wants to prioritize listings for possible missing or unclear information mentioned repeatedly by customers. Planned main comparison: distinct review mentions of a theme per parent listing (at least two) against listing coverage. This assignment cleans and validates data, without claiming to prove information gaps.

Dataset: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023
Pinned HF revision: `2b6d039ed471f2ba5fd2acb718bf33b0a7e5598e`. Download date: 2026-10-04 (Los Angeles).

Inputs are the **full category**: `All_Beauty.jsonl` (701,528 reviews, 326,611,506 bytes) and `meta_All_Beauty.jsonl` (112,590 listings, 212,990,142 bytes). The raw metadata JSONL is used instead of the preliminary parquet. Its full row count is checked, but byte-equivalence with that parquet is not claimed. `source_manifest.json` pins source paths, byte sizes, and published SHA-256 checksums. Originals are read only; downloads are atomic and verified. No remote loading script is executed.

## Run from the package root

Python 3.12 was used. Cleaning/download/reproduction scripts use the standard library. The notebook and PDF require the listed dependencies. Allow about 3 GB of free disk for raw data, the database and its reproduction; memory is bounded by streaming plus an independent fingerprint set.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/download_data.py
python scripts/execute_notebook.py
python scripts/reproduce.py
python scripts/build_report.py
```

The downloader needs internet access; subsequent cleaning can run offline from verified originals. To run scripts without the notebook:

```bash
python scripts/clean_data.py
python scripts/verify_outputs.py
python scripts/reproduce.py
python scripts/build_report.py
```

Alternatively open `cleaning_waynechen.ipynb` in VS Code/Jupyter, select the environment, **Restart Kernel**, then **Run All**. The supplied notebook was actually executed in a new Python process/IPython namespace through `execute_notebook.py`; it did not use a socket-backed Jupyter server in this environment. Actual cell outputs and `outputs/notebook_execution.json` record the method honestly. `reproduce.py` independently reruns the full cleaner in another process and compares deterministic output hashes. Specify `--raw-dir PATH --out PATH` on the cleaner/verifier for custom locations; `reproduce.py` accepts `--raw-dir PATH --baseline PATH`.

## Expected results and files

- `701,528 - 7,275 = 694,253` retained reviews; metadata stays `112,590`.
- Many-to-one left join on `parent_asin` conserves `694,253` rows; unmatched reviews `0`; metadata with no retained reviews `25`.
- Rating sum `2,749,862`; helpful votes `641,610`; mean rating `3.960893`; negative-review rate `20.6681%`; verified-purchase rate `90.5226%`.
- Five genuine checks and all 50 sample membership/field checks pass. `11` deterministic output files match on full rerun.

`outputs/cleaned.sqlite` (generated, excluded from ZIP/Git) contains `reviews`, `metadata`, `removed_duplicates`, `repeated_review_keys`, `metadata_conflicting_keys` and `review_products`/`eligible_metadata` views. `payload` stores typed JSON including nested source columns. SQLite purchase flags are 0/1; JSON flags remain booleans. Product columns are accessed through the left-join view. Full cleaned review data need not be committed; the instructor can recreate it from pinned originals.

Committed evidence:
- `outputs/audit.json`, `column_audit.csv`: full-dataset counts, missingness, types, changes, flags, totals and join coverage.
- `outputs/removed_duplicates.csv`, `repeated_review_keys.csv`, `metadata_conflicting_keys.csv`, `unmatched_products.csv`: exact-duplicate mappings and key audits (empty tables retain headers).
- `outputs/product_metrics.csv`, `annual_metrics.csv`: complete **aggregated** metric tables, not extra review samples.
- `outputs/record_checks.json`, `verification.json`: original/expected/actual cases and independent raw-to-output checks.
- `outputs/output_checksums.json`, `reproducibility.json`, `notebook_execution.json`: deterministic result and rerun evidence.
- `outputs/samples/cleaned_sample.jsonl` and `.csv`: **50 real joined review records**. Difficult cases first, remaining slots by SHA-256(record_id). This audit sample is not representative. JSONL preserves types; CSV must load `asin`, `parent_asin`, and `user_id` as strings (see notebook).
- `docs/cleaning_rules.md`, `record_expectations.json`: rules and expectations separate from transformation code.
- `Wayne_Chen_Module_6_Report.pdf`: individual Gradescope report with all 14 checklist items, decision log and five record checks.

