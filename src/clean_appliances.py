import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REVIEW_PATH = ROOT / "data" / "raw" / "Appliances.jsonl"
META_PATH = ROOT / "data" / "raw" / "meta_Appliances.jsonl"
OUTPUT_PATH = ROOT / "data" / "sample" / "appliances_cleaned_sample_yulim.csv"

print("Loading data...")

reviews = pd.read_json(REVIEW_PATH, lines=True)
meta = pd.read_json(META_PATH, lines=True)

print("Original review rows:", len(reviews))
print("Original metadata rows:", len(meta))

for col in ["title", "text"]:
    reviews[col] = reviews[col].str.strip()

for col in ["title", "store"]:
    meta[col] = meta[col].str.strip()

review_cols = [
    "rating",
    "title",
    "text",
    "asin",
    "parent_asin",
    "user_id",
    "timestamp",
    "helpful_vote",
    "verified_purchase"
]

reviews = reviews.drop_duplicates(
    subset=review_cols,
    keep="first"
).copy()

merged = reviews.merge(
    meta,
    on="parent_asin",
    how="left",
    suffixes=("_review", "_meta"),
    validate="many_to_one"
)

sample = pd.concat([
    merged[merged["price"].isna()].head(10),
    merged[merged["price"].notna()].head(40)
]).head(50)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

sample.to_csv(
    OUTPUT_PATH,
    index=False
)

print("Final review rows:", len(reviews))
print("Final metadata rows:", len(meta))
print("Merged rows:", len(merged))
print("Saved sample rows:", len(sample))
print("Output file:", OUTPUT_PATH)