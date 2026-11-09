# Beauty Review Intelligence — Streamlit MVP

## User and decision
For beauty category managers and customer-experience analysts deciding which products need attention, comparing brands, and investigating customer feedback patterns. Review counts are **not sales**.

## App and demo links
- Streamlit app: **ADD LIVE APP URL AFTER DEPLOYMENT**
- Demo video (3–6 minutes): **ADD VIEWABLE VIDEO URL**
- GitHub repository: **ADD REPOSITORY URL**

## Run locally
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deployment
Upload `streamlit_app.py`, `requirements.txt`, and the `data/dashboard_data.json` file to the **same GitHub branch**. In Streamlit Community Cloud choose that repository and branch and set **Main file path** to `streamlit_app.py`. The app does not require login or secrets. Test in an incognito window.

## Data scope
Historical Amazon Reviews 2023 All Beauty cleaned snapshot extracted from the provided `beauty_review_intelligence_v5(1).html`: 694,253 eligible review rows, 112,565 products. Product-level summaries are complete for eligible reviews; review text is capped to 3,000 sampled negative excerpts. Not live sales or product defect evidence.

## Features
- Search and filter products, brands, price, satisfaction, issue, review volume and heuristic product type.
- Weighted KPIs, performance matrix, action queue, historical trends, brand comparison, rating-based sentiment, sample word frequencies, separate action table and review evidence.
- Top-N brand discovery and side-by-side comparison of two independently selected brands, with charts and a metrics table.
- Clear empty states and explicit caveats when source data cannot support an exact answer.

## Definitions and limitations
- Negative reviews: ratings 1–2 stars; neutral: 3; positive: 4–5. Exact three-way counts are available only for the full dataset, not filtered product subsets.
- Product type is **inferred from product names** with keyword rules, not a validated category.
- Action flags: <10 reviews → Limited evidence; otherwise rating <3.5 or negative rate >=30% → Investigate; otherwise rating <4.2 or negative rate >=15% → Monitor; else Performing well.
- Similarity Lab is excluded because actual product descriptions are not present in the source data. No score is invented.
- Word frequencies come only from a capped negative-review excerpt sample, not all reviews. Historical yearly trends, rating distribution and issue themes are full-dataset and not filtered.
- Future work: source review-level data for filtered sentiment, verified categories, full review text and description coverage.

## Demo video walkthrough (3–6 min)
1. Introduce user (beauty category manager) and decision (prioritize products).
2. Show overview KPIs, matrix and action queue; explain units and that review volume is not sales.
3. Filter by brand/type/minimum reviews; show numbers update. Compare brands.
4. Explain full-dataset rating-based sentiment pie and sampled negative-review word chart.
5. Open Product Action Table, sort and inspect review evidence.
6. Test difficult case: search for a nonexistent product; show clear no-results message and recover.
7. Compare two brands using separate selectors and explain the chart and table differences.
8. End with limitation: text sample and missing descriptions prevent full text analysis.

## Public showcase preference
**Team to select:** All members agree / Do not share publicly / Decide later.

## V7 changes
- Sidebar brand filter uses individual initials A through Z, plus # / Other, with substring search.
- Beauty Brands offers top-N brands by review volume and two independent searchable brand selectors.
- Choosing two different brands updates rating, negative-rate, review-volume charts and comparison table.
- Similarity Lab removed because source data lacks actual product descriptions; no upload is required.
- Brand comparisons are review-weighted and based on historical product summaries.
