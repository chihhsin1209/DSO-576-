# Amazon Appliances Data Cleaning

## Project purpose
This project cleans Amazon Appliances review and metadata for product listing quality analysis.

## Data source
McAuley Lab Amazon Reviews 2023 - Appliances category.

Original files:
- Appliances.jsonl
- meta_Appliances.jsonl

Link: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023 

## Files
- cleaning_yulim.ipynb - data cleaning and validation notebook
- src/clean_appliances.py - reproducible cleaning script
- data/sample/appliances_cleaned_sample_yulim.csv - cleaned 50-row sample
- requirements.txt - Python dependency

## How to run
From the project folder, run:

python3 src/clean_appliances.py

The script creates:

data/sample/appliances_cleaned_sample_yulim.csv

## Expected output
- Final review rows: 2,105,949
- Final metadata rows: 94,327
- Merged rows: 2,105,949
- Sample rows: 50

## GitHub submission
Branch: [add branch name]
Branch URL: [add branch URL]
Commit ID: [add commit ID]