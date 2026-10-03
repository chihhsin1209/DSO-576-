# Amazon Appliances Review Data Cleaning

## Project purpose
This project cleans Amazon Appliances review data to support product-listing quality analysis. It identifies reviews that may mention missing or unclear listing information, helping Amazon teams prioritize listings for improvement.

## Data source
McAuley Lab Amazon Reviews 2023 — Appliances category
https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023

The cleaning script downloads the first 300 review records from the official Appliances review file and creates a cleaned 50-row sample.

## Repository contents
- src/clean_appliances.py — reproducible cleaning script
- data_cleaning_joshya_gupta.ipynb — notebook with project documentation and five validation checks
- data/sample/appliances_reviews_cleaned_sample.csv — cleaned 50-row sample
- requirements.txt — Python dependencies
- .gitignore — prevents the raw downloaded data and virtual environment from being committed

## How to run
From the repository root, run this command in the terminal:
.venv/bin/python src/clean_appliances.py

This recreates:
data/sample/appliances_reviews_cleaned_sample.csv

## Cleaning rules
- Trim and standardize whitespace in titles and review text.
- Convert ratings and helpful-vote counts to numeric values.
- Change invalid ratings and negative helpful-vote counts to missing values.
- Convert millisecond timestamps to UTC datetimes.
- Remove duplicates based on user ID, product ID, timestamp, and review text.
- Create a stable hashed review ID called review_uid.
- Flag possible listing-information keywords with issue_mentioned.

## Results from the documented run
- 300 reviews loaded
- 0 duplicate reviews removed
- 0 invalid ratings
- 0 negative helpful votes
- 0 missing review texts
- 12 reviews flagged as possible listing-information issues
- 50 cleaned sample rows saved

## Validation
The notebook checks:
1. The cleaned sample has 50 rows.
2. review_uid has no duplicates.
3. Ratings are within 1–5.
4. Review text is not missing.
5. issue_mentioned is a valid True/False field for every row.

## Limitation
The keyword flag is a screening tool, not proof that a listing is incomplete. The next project phase should compare flagged reviews with product metadata using parent_asin.

## Git information
- Branch: cleaning-joshyagupta
- Repository: https://github.com/chihhsin1209/DSO-576-
- Final commit ID: add after the final commit and push