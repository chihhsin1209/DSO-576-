# DSO 576 Module 6: All Beauty review cleaning

Question: Which parent listings have a high share of negative (1-2 star) reviews, and how much captured listing content is absent? Review counts are not sales; store is not necessarily brand. Product metadata is a snapshot, not historical transaction data. Missing captured content does not prove the live listing lacks it.

## Sources and environment

Amazon Reviews 2023, McAuley Lab, All_Beauty: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023

Place the original `All_Beauty.jsonl` and `full-00000-of-00001 (1).parquet` in `data/raw/`. The pipeline verifies the exact SHA-256 hashes in `config/cleaning_rules.json` before and after processing. Original upstream download revision/date is unknown. The existing merged parquet is not an input. Raw sources remain unchanged.

Validated local interpreter: Python 3.9.6 in `/Users/hcx/dso576/.venv`. From this repository root:

```sh
source ../.venv/bin/activate
python -m pip install -r requirements.txt
python scripts/clean_data.py
python scripts/verify_reproducibility.py
python scripts/run_notebook.py
python scripts/build_report.py
```

For another machine, create a local Python virtual environment and install requirements there. Notebook execution uses the invoking Python interpreter. PDF generation uses ReportLab.

## Methodology and evidence

`config/cleaning_rules.json` records the supplied methodology and expected validations; `config/expected_record_checks.json` predeclares five cases. Originals and structured nested fields are retained. Only complete raw duplicate copies are removed, using canonical JSON fingerprints including images. IDs are never normalized. Derived text strips only outer whitespace; blank text becomes null. Numeric price, rating, helpfulness, boolean and UTC time validations create flags rather than speculative corrections. Empty captured listing arrays/dictionaries are absent content. The metadata merge is many-to-one and preserves retained reviews. Metrics report valid denominators; price averages use unique products. Product metrics retain all metadata products, including those without reviews.

Expected reconciliation: 701,528 raw reviews - 7,275 copies = 694,253 retained; 6,138 duplicate groups. Rating total: 2,778,223 - 28,361 = 2,749,862. Helpful total: 647,923 - 6,313 = 641,610. All detailed counts and rounded metric checks must pass before dataset exports.

Full review/product tables and product metrics are in `outputs/data/` and ignored by Git. The 50-row CSV includes retained predefined cases, row 6566 as counterpart evidence for excluded row 6567, first observed flags, and deterministic sampling with seed 576; `selection_reason` explains each choice. Small CSV/JSON evidence is in `outputs/reports/`. The executed notebook explains and calls the same implementation. The report is `outputs/reports/Module_6_Report.pdf` and contains the completed personal review; submission metadata remains to be finalized.

Reproducibility regenerates all cleaning artifacts in an isolated temporary directory: exact logical equality for Parquet, exact SHA-256 for deterministic JSON/CSV. The reproducibility report, notebook and PDF are downstream artifacts excluded from that comparison.

## Submission workflow

Current personal branch: `alex`; configured remote: `https://github.com/chihhsin1209/DSO-576-`. No push or commit has been performed by the reconstruction workflow. Verify instructor access manually.

`config/submission.json` stores `branch_name`, `branch_url`, `analysis_commit_id`, `submitted_commit_id`, `remote_url`, and `status`. Unknown URLs/commit IDs are JSON null. The branch URL must be verified after an authorized push. The analysis commit identifies the code/results revision; the final submitted commit identifies the revision actually handed in. A committed file cannot contain its own final commit hash. Following the starter instructions, record the analysis commit in a later documentation commit and put the actual final submitted commit in the PDF; regenerate the submission PDF after the final repository commit, without pretending its embedded hash identifies itself. Confirm this convention with the instructor if only one unspecified commit field is required.

The completed personal review is stored in `config/independent_review.json` and mirrored in `outputs/reports/independent_check.json`; report generation reads the config file. Before committing: review the notebook/report and complete submission metadata when knowable, and ensure raw/full datasets are ignored. Commit README, requirements, scripts, config, executed notebook, audit evidence and only the 50-row cleaned sample. Do not push to main/master. Do not upload a dataset ZIP. Push the personal branch only when explicitly authorized, verify its URL and instructor access, then submit the individual PDF with final commit details.
