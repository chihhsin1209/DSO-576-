# Amazon Beauty Product Reviews

**Student:** Lame Wadipeba  
**Project:** Amazon Beauty Product Reviews  
**Branch:** cleaning-lamewadipeba  
**Branch URL:** https://github.com/chihhsin1209/DSO-576-/commits/cleaning-lamewadipeba/ 
**Commit ID:** ad75f33847b0324a57ecd74546eb5507d3ce7a2f

## Project vision

Understand customer satisfaction with beauty products by analyzing Amazon review ratings and review characteristics to identify patterns in positive and negative customer experiences.

## Business question

How do review characteristics, such as verified purchase status and helpful votes, relate to customer ratings for beauty products?

## Main metrics

- Average rating
- Rating distribution
- Verified vs. unverified purchase ratings
- Helpful votes
- Review length

## Data source

I used the `debolut/amazon-reviews-2023-sampled-all-beauty` Parquet sample on Hugging Face.

Source:
https://huggingface.co/datasets/debolut/amazon-reviews-2023-sampled-all-beauty

The original sample has 4,687 rows and 14 columns. I keep the original data in `df_original` and clean a copy.

## Cleaning decisions

I made the following cleaning decisions:

1. Removed exact duplicate rows and kept the first copy.
2. Converted `timestamp` from Unix milliseconds to datetime.
3. Converted `verified_purchase` from 0/1 to Boolean.
4. Removed extra whitespace from text fields.
5. Replaced HTML line-break tags in `review_text` with spaces.
6. Kept blank product metadata instead of filling it with made-up information.
7. Kept repeated users because one customer can review multiple products.

## Evidence

The notebook has an **Evidence & Verification** section that prints the main checks used in the PDF. This includes row counts, missing values, duplicates, data types, rating checks, verified purchase counts, helpful votes, timestamp checks, prices, and the final metrics.

## Run instructions

From the project directory:

```bash
pip install -r requirements.txt
python cleaning_script.py
```

Or open `cleaning_lamewadipeba.ipynb`, restart the kernel, and run all cells from the beginning.

## Expected output files

The script creates an `outputs/` folder with:

- `cleaned_all_beauty_sample.csv`
- `cleaned_sample_50_rows.csv`
- `validation_summary.csv`
- `metrics.csv`
- `verified_purchase_comparison.csv`
- `five_record_checks.csv`

Expected row counts:

- Original: 4,687
- Exact duplicates: 122
- Final cleaned rows: 4,565

## Codex check

I used Codex to help write some of the cleaning code. I independently checked one of its cleaning decisions by running `df.duplicated().sum()` on the original data. It returned 122, so I then checked that the duplicate-removal step reduced the dataset from 4,687 to 4,565 rows.

## Limitations

This is a sample of the All_Beauty review data, not the full population. Product brand and category information are blank in this sample, so I did not use those fields for analysis. Helpful votes show review engagement, but they are not the same thing as customer satisfaction.
