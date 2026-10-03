from pathlib import Path
import hashlib
import json
import re

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "original" / "appliances_reviews_raw_300.csv"
OUTPUT_PATH = ROOT / "data" / "sample" / "appliances_reviews_cleaned_sample.csv"

DATA_URL = (
    "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/"
    "resolve/main/raw/review_categories/Appliances.jsonl"
)

ISSUE_WORDS = (
    r"missing|unclear|not listed|doesn't say|does not say|no information|"
    r"description|specification|dimension|compatib|warranty|voltage|capacity|noise"
)


def clean_text(value):
    if pd.isna(value):
        return pd.NA
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value if value else pd.NA


def download_first_300_reviews():
    print("Downloading 300 Appliances reviews...", flush=True)

    response = requests.get(DATA_URL, stream=True, timeout=(20, 120))
    response.raise_for_status()

    records = []
    for line in response.iter_lines(decode_unicode=True):
        if line:
            records.append(json.loads(line))
        if len(records) == 300:
            break

    response.close()
    return pd.DataFrame(records)


def main():
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    raw = download_first_300_reviews()
    raw.to_csv(RAW_PATH, index=False)

    df = raw.copy()

    for column in ["title", "text", "parent_asin", "user_id"]:
        df[column] = df[column].map(clean_text)

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    invalid_ratings = (~df["rating"].between(1, 5)) & df["rating"].notna()
    df.loc[invalid_ratings, "rating"] = pd.NA

    df["helpful_vote"] = pd.to_numeric(df["helpful_vote"], errors="coerce")
    negative_votes = df["helpful_vote"] < 0
    df.loc[negative_votes, "helpful_vote"] = pd.NA

    df["review_datetime"] = pd.to_datetime(
        df["timestamp"], unit="ms", errors="coerce", utc=True
    )

    before = len(df)
    df = df.drop_duplicates(subset=["user_id", "parent_asin", "timestamp", "text"]).copy()
    duplicates_removed = before - len(df)

    df["review_uid"] = df.apply(
        lambda row: hashlib.sha256(
            "|".join(
                str(row[x])
                for x in ["user_id", "parent_asin", "timestamp", "text"]
            ).encode()
        ).hexdigest()[:16],
        axis=1,
    )

    combined_text = df["title"].fillna("") + " " + df["text"].fillna("")
    df["issue_mentioned"] = combined_text.str.contains(
        ISSUE_WORDS, case=False, regex=True, na=False
    )

    flagged = df[df["issue_mentioned"]]
    not_flagged = df[~df["issue_mentioned"]]
    sample = pd.concat(
        [flagged.head(50), not_flagged.head(max(0, 50 - len(flagged)))]
    )

    sample = sample[
        [
            "review_uid",
            "parent_asin",
            "rating",
            "title",
            "text",
            "review_datetime",
            "helpful_vote",
            "verified_purchase",
            "issue_mentioned",
        ]
    ]
    sample.to_csv(OUTPUT_PATH, index=False)

    print("\nCLEANING CHECKS")
    print(f"Rows loaded: {len(raw)}")
    print(f"Exact duplicates removed: {duplicates_removed}")
    print(f"Invalid ratings changed to missing: {invalid_ratings.sum()}")
    print(f"Negative helpful votes changed to missing: {negative_votes.sum()}")
    print(f"Reviews missing text: {df['text'].isna().sum()}")
    print(f"Reviews mentioning listing-information issues: {df['issue_mentioned'].sum()}")
    print(f"Cleaned sample rows saved: {len(sample)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()