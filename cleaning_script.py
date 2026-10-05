import pandas as pd
from pathlib import Path

SOURCE_URL = (
    "https://huggingface.co/datasets/debolut/"
    "amazon-reviews-2023-sampled-all-beauty/resolve/main/"
    "data/train-00000-of-00001.parquet"
)

TEXT_COLUMNS = [
    "review_title",
    "review_text",
    "product_title",
    "product_description",
    "product_brand",
    "product_categories",
    "image_url",
]


def load_source_data():
    """Load the original source without changing it."""
    return pd.read_parquet(SOURCE_URL)


def clean_data(df_original):
    """Apply the cleaning rules and return a cleaned copy."""
    df = df_original.copy()

    # 1. Remove exact duplicate rows and keep the first occurrence.
    df = df.drop_duplicates(keep="first").copy()

    # 2. Convert Unix milliseconds to datetime.
    df["timestamp"] = pd.to_datetime(
        df["timestamp"], unit="ms", errors="coerce"
    )

    # 3. Convert verified purchase from 0/1 to Boolean.
    df["verified_purchase"] = df["verified_purchase"].astype(bool)

    # 4. Strip surrounding whitespace from text fields.
    for col in TEXT_COLUMNS:
        df[col] = df[col].astype("string").str.strip()

    # 5. Replace HTML line breaks in review text with spaces.
    df["review_text"] = (
        df["review_text"]
        .str.replace(r"<br\s*/?>", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )

    # 6. Add review length as a derived field.
    df["review_length"] = df["review_text"].str.len()

    return df


def validate_data(df_original, df):
    """Create basic validation results for the cleaning decisions."""
    converted = pd.to_datetime(
        df_original["timestamp"], unit="ms", errors="coerce"
    )

    validation = {
        "starting_rows": len(df_original),
        "starting_columns": len(df_original.columns),
        "exact_duplicates": int(df_original.duplicated().sum()),
        "final_rows": len(df),
        "missing_values_original": int(df_original.isna().sum().sum()),
        "missing_values_after": int(df.isna().sum().sum()),
        "invalid_ratings": int((~df["rating"].isin([1, 2, 3, 4, 5])).sum()),
        "negative_helpful_votes": int((df["helpful_vote"] < 0).sum()),
        "negative_prices": int((df["product_price"] < 0).sum()),
        "timestamp_conversion_failures": int(converted.isna().sum()),
        "html_breaks_original": int(
            df_original["review_text"].str.contains("<br", regex=False, na=False).sum()
        ),
    }
    return validation


def make_record_checks(df_original, df):
    """Create five deterministic record checks from the original and cleaned data."""
    checks = []

    # 1. Timestamp conversion
    row = df_original.iloc[0]
    mask = (
        df["user_id"].eq(row["user_id"])
        & df["parent_asin"].eq(row["parent_asin"])
        & df["rating"].eq(row["rating"])
        & df["review_title"].eq(row["review_title"])
    )
    actual = df.loc[mask, "timestamp"].iloc[0]
    expected = pd.to_datetime(row["timestamp"], unit="ms")
    checks.append({
        "check": "1 - timestamp conversion",
        "original": str(row["timestamp"]),
        "expected": str(expected),
        "actual": str(actual),
        "matches": str(expected) == str(actual),
    })

    # 2. Verified purchase conversion
    row = df_original[df_original["verified_purchase"].isin([0, 1])].iloc[0]
    mask = (
        df["user_id"].eq(row["user_id"])
        & df["parent_asin"].eq(row["parent_asin"])
        & df["rating"].eq(row["rating"])
        & df["review_title"].eq(row["review_title"])
    )
    expected = bool(row["verified_purchase"])
    actual = df.loc[mask, "verified_purchase"].iloc[0]
    checks.append({
        "check": "2 - verified purchase conversion",
        "original": str(row["verified_purchase"]),
        "expected": str(expected),
        "actual": str(actual),
        "matches": expected == actual,
    })

    # 3. Review length calculation
    row = df_original.iloc[1]
    clean_text = str(row["review_text"])
    clean_text = pd.Series([clean_text]).str.replace(
        r"<br\s*/?>", " ", regex=True
    ).str.replace(r"\s+", " ", regex=True).str.strip().iloc[0]
    mask = (
        df["user_id"].eq(row["user_id"])
        & df["parent_asin"].eq(row["parent_asin"])
        & df["rating"].eq(row["rating"])
        & df["review_title"].eq(row["review_title"])
    )
    actual = df.loc[mask, "review_length"].iloc[0]
    expected = len(clean_text)
    checks.append({
        "check": "3 - review length calculation",
        "original": str(len(str(row["review_text"]))) + " original characters",
        "expected": str(expected),
        "actual": str(actual),
        "matches": expected == actual,
    })

    # 4. Blank review text is retained rather than invented.
    blank_rows = df_original[
        df_original["review_text"].fillna("").astype(str).str.strip().eq("")
    ]
    if len(blank_rows):
        row = blank_rows.iloc[0]
        mask = (
            df["user_id"].eq(row["user_id"])
            & df["parent_asin"].eq(row["parent_asin"])
            & df["rating"].eq(row["rating"])
            & df["review_title"].eq(row["review_title"])
        )
        actual_text = df.loc[mask, "review_text"].iloc[0]
        actual_len = df.loc[mask, "review_length"].iloc[0]
        checks.append({
            "check": "4 - blank review text handling",
            "original": "Blank review text",
            "expected": "Keep blank and review_length = 0",
            "actual": f"Blank review text and review_length = {actual_len}",
            "matches": str(actual_text) in ["", "<NA>"] and actual_len == 0,
        })

    # 5. Exact duplicate handling
    checks.append({
        "check": "5 - exact duplicate handling",
        "original": f"{int(df_original.duplicated().sum())} duplicate rows in source",
        "expected": "Remove duplicate copies and keep first occurrence",
        "actual": f"{len(df_original) - len(df)} rows removed; {len(df)} rows remain",
        "matches": len(df_original) - len(df) == int(df_original.duplicated().sum()),
    })

    return pd.DataFrame(checks)


def save_outputs(df_original, df, output_dir="outputs"):
    """Save cleaned data and verification files."""
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    validation = validate_data(df_original, df)
    pd.DataFrame([validation]).to_csv(out / "validation_summary.csv", index=False)

    df.to_csv(out / "cleaned_all_beauty_sample.csv", index=False)
    df.head(50).to_csv(out / "cleaned_sample_50_rows.csv", index=False)

    metrics = pd.DataFrame({
        "metric": [
            "average_rating",
            "rating_count",
            "verified_purchase_count",
            "unverified_purchase_count",
            "average_helpful_votes",
            "average_review_length",
        ],
        "value": [
            df["rating"].mean(),
            len(df["rating"]),
            int(df["verified_purchase"].sum()),
            int((~df["verified_purchase"]).sum()),
            df["helpful_vote"].mean(),
            df["review_length"].mean(),
        ],
    })
    metrics.to_csv(out / "metrics.csv", index=False)

    comparison = (
        df.groupby("verified_purchase", dropna=False)
        .agg(
            records=("rating", "size"),
            average_rating=("rating", "mean"),
            average_helpful_votes=("helpful_vote", "mean"),
            average_review_length=("review_length", "mean"),
        )
        .reset_index())
    comparison.to_csv(out / "verified_purchase_comparison.csv", index=False)

    make_record_checks(df_original, df).to_csv(
        out / "five_record_checks.csv", index=False)

    return out


def main():
    df_original = load_source_data()
    df = clean_data(df_original)
    out = save_outputs(df_original, df)

    print("Cleaning complete.")
    print(f"Starting rows: {len(df_original)}")
    print(f"Exact duplicates: {df_original.duplicated().sum()}")
    print(f"Final rows: {len(df)}")
    print(f"Outputs written to: {out.resolve()}")


if __name__ == "__main__":
    main()
