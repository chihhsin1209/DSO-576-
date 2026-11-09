# Beauty Review Intelligence — Streamlit MVP

**Course:** USC DSO-576 | Phase 3 Project MVP  
**Project:** Amazon All Beauty Customer Review Analytics

## 1. Project Overview

Beauty Review Intelligence is an interactive dashboard designed to help beauty category managers, product managers, and customer-experience analysts understand customer feedback and identify products that may need improvement.

The dashboard helps users decide which products to investigate, compare brand performance, and identify common customer complaints.

## 2. Live App & Demo Video

- **Live Dashboard:** https://beauty-review-dashboard-wreypodnm3p4ysb3kfsxql.streamlit.app/
- **Demo Video:** https://drive.google.com/file/d/1MR0jwRmgxa2hj56xh8hTgMaX5t8aS5WO/view?usp=sharing
- **Team GitHub Repository:** https://github.com/chihhsin1209/DSO-576-

## 3. Main Features

**Overview**
- Displays key metrics, including product counts, review volume, average ratings, and negative-review rates.
- Provides a Product Performance Matrix and Action Queue to identify products that may require attention.

**Beauty Brands Comparison**
- Allows users to select and compare two beauty brands.
- Compares average ratings, negative-review rates, and review volumes.
- Updates charts automatically when brand selections change.

**Sentiment & Words**
- Analyzes available negative-review excerpts and frequently occurring words.
- Helps users identify potential customer complaints and recurring issues.

**Product Action Table**
- Displays product-level performance metrics and suggested investigation priorities.
- Helps managers identify products that may need further review.

**Interactive Filters**
- Allows users to filter products by brand, product type, price, satisfaction, issue, and minimum review count.
- Updates relevant results based on user selections.
- Provides guidance when no products match the selected filters.

## 4. Data Scope

**Data Source:** Amazon Reviews 2023 — All Beauty (cleaned historical snapshot).

| Metric | Value |
|---|---|
| Eligible reviews | 694,253 |
| Products represented | 112,565 |
| Average rating | Approximately 3.96 / 5 |
| Negative-review rate (1–2 stars) | Approximately 20.7% |
| Verified-purchase share | Approximately 90.5% |

**Data Sample Disclosure**

The dashboard uses product-level summaries derived from the eligible review dataset. Text-based insights use a limited sample of up to 3,000 negative-review excerpts rather than all review texts.

Product types are inferred from product names rather than verified category labels.

Review volume represents the number of reviews, not product sales.

## 5. How to Run Locally

**Requirements:** Python and the packages listed in `requirements.txt`.

1. Clone or download the repository.
2. Navigate to the `beauty_streamlit_app` folder.
3. Ensure `data/dashboard_data.json` is available.
4. Install the required packages:

```bash
python3 -m pip install -r requirements.txt
```

5. Run the Streamlit application:

```bash
python3 -m streamlit run streamlit_app.py
```

6. Open the local address displayed in the terminal (typically `http://localhost:8501`).

## 6. Limitations & Future Improvements

- **Limited text sample:** Text insights use up to 3,000 negative-review excerpts, which may not represent all customer feedback.
- **Historical data:** The dashboard uses historical Amazon review data and does not provide real-time reviews, prices, or sales.
- **Product classification:** Product types are inferred from names and may not always be accurate.

Future improvements could include a larger review-text sample, more accurate product categorization, and regularly updated review data.

## 7. Public Showcase Preference

**Team decision:** Decide later — subject to confirmation by all team members.
