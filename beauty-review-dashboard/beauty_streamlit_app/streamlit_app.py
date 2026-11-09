"""Beauty Review Intelligence: historical Amazon All Beauty analytics MVP."""
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Beauty Review Intelligence", page_icon="✦", layout="wide")
st.markdown("""<style>
.stApp {background:#f6f7fb;color:#1b2540}
[data-testid="stMetric"] {background:white;padding:16px;border:1px solid #e8ebf3;border-radius:14px}
h1,h2,h3 {color:#202b45}div[data-testid="stTabs"] button {font-weight:650}
</style>""", unsafe_allow_html=True)

DATA_PATH = Path(__file__).parent / "data" / "dashboard_data.json"
@st.cache_data(show_spinner="Loading product summaries...")
def load_data():
    with DATA_PATH.open(encoding="utf-8") as f:
        raw=json.load(f)
    return raw, pd.DataFrame(raw["products"]), pd.DataFrame(raw["review_examples"])

try:
    raw, products, examples=load_data()
except (OSError, ValueError, KeyError) as exc:
    st.error(f"Data could not be loaded: {exc}. Check data/dashboard_data.json in GitHub.")
    st.stop()

for col in ["brand","product","main_issue","product_id"]:
    products[col]=products[col].fillna("").astype(str)
products["brand"]=products["brand"].replace("", "Unknown brand")

def category(name):
    s=str(name).lower()
    patterns=[("Haircare",r"shampoo|conditioner|hair|wig|scalp|curl|braid"),
              ("Makeup",r"lipstick|lip gloss|mascara|foundation|eyeshadow|eyeliner|makeup|blush|concealer"),
              ("Fragrance",r"perfume|fragrance|cologne|body spray"),
              ("Skincare",r"skin|face|facial|moisturiz|serum|acne|lotion|cleanser|sunscreen"),
              ("Nails",r"nail|manicure|polish|cuticle"),
              ("Tools & accessories",r"brush|mirror|tweezer|razor|sponge|comb|towel")]
    for label,pattern in patterns:
        if re.search(pattern,s):return label
    return "Other / unclassified"

@st.cache_data(show_spinner=False)
def categorize(names):
    return pd.Series(names).map(category).tolist()
products["product_type"]=categorize(tuple(products["product"].tolist()))

def action(row):
    if row.review_count<10:return "Limited evidence"
    if row.avg_rating<3.5 or row.negative_rate>=0.30:return "Investigate"
    if row.avg_rating<4.2 or row.negative_rate>=0.15:return "Monitor"
    return "Performing well"

@st.cache_data(show_spinner=False)
def action_labels(counts,ratings,negatives):
    return ["Limited evidence" if n<10 else "Investigate" if a<3.5 or b>=.30 else "Monitor" if a<4.2 or b>=.15 else "Performing well" for n,a,b in zip(counts,ratings,negatives)]
products["action"]=action_labels(tuple(products.review_count),tuple(products.avg_rating),tuple(products.negative_rate))

st.title("✦ Beauty Review Intelligence")
st.caption("Customer feedback analytics · Amazon All Beauty · Historical snapshot (not live sales)")
st.info("Source: Amazon Reviews 2023 All Beauty cleaned snapshot. 694,253 eligible reviews across 112,565 products. Product summaries cover the eligible dataset; text insights use only the available capped sample of 3,000 negative-review excerpts. Product types are inferred from names, not verified categories.")

with st.sidebar:
    st.header("Explore products")
    search=st.text_input("Product, brand, or product ID",placeholder="Search...")
    # One letter per choice avoids ambiguous alphabetical ranges.
    group=st.selectbox("Brand initial",["All"]+list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")+["# / Other"])
    brands=products.brand.drop_duplicates().sort_values()
    if group!="All":
        if group=="# / Other":
            brands=brands[~brands.str[0].str.upper().str.match(r"[A-Z]",na=False)]
        else:
            brands=brands[brands.str[0].str.upper().eq(group)]
    brand_query=st.text_input("Find brand",placeholder="Type part of brand name")
    if brand_query:brands=brands[brands.str.contains(brand_query,case=False,regex=False)]
    st.caption(f"{len(brands):,} brands match your search")
    brand_options=brands.tolist()[:150]
    if len(brands)>150:
        st.info("Showing the first 150 matching brands. Type more letters to narrow the list.")
    brand=st.selectbox("Brand / store",["All brands"]+brand_options)
    st.caption("Tip: search by product ID for an exact product; use brand search to narrow the list.")
    types=st.multiselect("Product types (name-based)",sorted(products.product_type.unique()))
    price=st.selectbox("Price",["All","Under $25","$25–$50","$50–$100","$100+","Unavailable"])
    satisfaction=st.selectbox("Satisfaction",["All","Strong (4.5+)","Moderate (3.5–4.49)","At risk (<3.5)","Negative rate 30%+"])
    issues=st.multiselect("Main issue",sorted(products.main_issue.unique()))
    min_reviews=st.selectbox("Minimum reviews",[0,5,10,25,100,250,500],index=0)
    st.caption("Filters affect product-level views. Historical annual trends and overall rating mix describe the full dataset.")

mask=pd.Series(True,index=products.index)
if search:
    mask &= (products["product"].str.contains(search,case=False,regex=False)|products["brand"].str.contains(search,case=False,regex=False)|products["product_id"].str.contains(search,case=False,regex=False))
if brand!="All brands":mask &= products.brand.eq(brand)
if types:mask &= products.product_type.isin(types)
if issues:mask &= products.main_issue.isin(issues)
mask &= products.review_count.ge(min_reviews)
if price=="Under $25":mask &= products.price.lt(25)
elif price=="$25–$50":mask &= products.price.ge(25)&products.price.lt(50)
elif price=="$50–$100":mask &= products.price.ge(50)&products.price.lt(100)
elif price=="$100+":mask &= products.price.ge(100)
elif price=="Unavailable":mask &= products.price.isna()
if satisfaction=="Strong (4.5+)":mask &= products.avg_rating.ge(4.5)
elif satisfaction=="Moderate (3.5–4.49)":mask &= products.avg_rating.ge(3.5)&products.avg_rating.lt(4.5)
elif satisfaction=="At risk (<3.5)":mask &= products.avg_rating.lt(3.5)
elif satisfaction=="Negative rate 30%+":mask &= products.negative_rate.ge(.3)
filtered=products.loc[mask].copy()
st.caption(f"{len(filtered):,} matching products · Filters apply to product-level metrics and charts")
if filtered.empty:
    st.warning("No products match these filters. Remove a restriction or choose a lower minimum review count.")
    st.stop()

n=int(filtered.review_count.sum())
avg=(filtered.avg_rating*filtered.review_count).sum()/n if n else 0
negative=(filtered.negative_rate*filtered.review_count).sum()/n if n else 0
verified=(filtered.verified_rate*filtered.review_count).sum()/n if n else 0
c=st.columns(5)
for col,label,value in zip(c,["Products","Review volume","Average rating","Negative reviews (1–2★)","Verified purchases"],[f"{len(filtered):,}",f"{n:,}",f"{avg:.2f} / 5",f"{negative:.1%}",f"{verified:.1%}"]):
    col.metric(label,value)
st.caption("Review-weighted metrics from product summaries; minor rounding may occur. Review volume is not sales volume.")

tab1,tab2,tab3,tab4=st.tabs(["Overview","Beauty Brands","Sentiment & Words","Product Action Table"])
with tab1:
    left,right=st.columns([1.8,1])
    with left:
        st.subheader("Product performance matrix")
        st.caption("Highest-review-volume 1,500 matching products. Bubble size = review count; color = negative-review rate.")
        scatter=filtered.nlargest(1500,"review_count").copy()
        fig=px.scatter(scatter,x="avg_rating",y="review_count",size="review_count",color="negative_rate",hover_name="product",hover_data=["brand","product_id"],color_continuous_scale="RdYlGn_r",labels={"avg_rating":"Average rating (stars)","review_count":"Review count","negative_rate":"Negative review rate"})
        fig.update_layout(height=440)
        st.plotly_chart(fig,use_container_width=True)
    with right:
        st.subheader("Action queue")
        counts=filtered.action.value_counts()
        for k in ["Investigate","Monitor","Performing well","Limited evidence"]:
            st.metric(k,f"{counts.get(k,0):,} products")
        st.caption("Rule-based flags for screening, not proof of product defects.")
    a,b=st.columns(2)
    with a:
        st.subheader("Historical annual review trend")
        yr=pd.DataFrame(raw["yearly"])
        fig=go.Figure()
        fig.add_bar(x=yr.year,y=yr.reviews,name="Reviews")
        fig.add_scatter(x=yr.year,y=yr.avg_rating,name="Avg rating",mode="lines+markers",yaxis="y2")
        fig.update_layout(yaxis=dict(title="Reviews"),yaxis2=dict(title="Stars",overlaying="y",side="right",range=[1,5]),height=330)
        st.plotly_chart(fig,use_container_width=True)
        st.caption("Full historical dataset; not filtered.")
    with b:
        st.subheader("Overall rating distribution")
        rating=pd.DataFrame(raw["rating_distribution"])
        st.plotly_chart(px.bar(rating,x="rating",y="reviews",labels={"rating":"Stars","reviews":"Reviews"}),use_container_width=True)
        st.caption("Full historical dataset; not filtered.")
    st.subheader("Negative feedback themes")
    st.plotly_chart(px.bar(pd.DataFrame(raw["issues"]).sort_values("reviews"),x="reviews",y="issue",orientation="h"),use_container_width=True)
    st.caption("Full historical dataset; rule-based keyword themes, one category per negative review.")

with tab2:
    st.subheader("Beauty brands · discover and compare")
    st.caption("Explore the most-reviewed brands or choose any two brands to compare side by side. Counts reflect reviews, not sales.")
    tmp=filtered.assign(weighted_rating=filtered.avg_rating*filtered.review_count, weighted_negative=filtered.negative_rate*filtered.review_count)
    brand_stats=tmp.groupby("brand",as_index=False).agg(reviews=("review_count","sum"),products=("product_id","nunique"),rating_total=("weighted_rating","sum"),negative_total=("weighted_negative","sum"))
    brand_stats=brand_stats[brand_stats.reviews.gt(0)].copy()
    brand_stats["avg_rating"]=brand_stats.rating_total/brand_stats.reviews
    brand_stats["negative_rate"]=brand_stats.negative_total/brand_stats.reviews
    st.markdown("#### Discover top brands")
    top_n=st.slider("Number of brands to display",5,30,10,5)
    top_brands=brand_stats.nlargest(top_n,"reviews").sort_values("reviews")
    st.plotly_chart(px.bar(top_brands,x="reviews",y="brand",orientation="h",color="avg_rating",color_continuous_scale="Viridis",labels={"reviews":"Review count","brand":"Brand","avg_rating":"Average rating"}),use_container_width=True)
    st.caption("Top brands ranked by review count in the current filtered view. A high count does not imply better quality.")
    st.markdown("#### Compare two brands")
    st.caption("The two selections below update the comparison charts and table automatically. Start typing in either dropdown to find a brand.")
    names=brand_stats.sort_values("brand").brand.tolist()
    ranked=brand_stats.nlargest(2,"reviews").brand.tolist()
    if len(names)<2:
        st.info("At least two brands are needed for comparison. Clear the sidebar brand filter or broaden other filters.")
    else:
        left,right=st.columns(2)
        with left:
            first=st.selectbox("Brand A",names,index=names.index(ranked[0]),key="brand_a")
        with right:
            second=st.selectbox("Brand B",names,index=names.index(ranked[1]),key="brand_b")
        if first==second:
            st.warning("Choose two different brands to compare.")
        else:
            comp=brand_stats[brand_stats.brand.isin([first,second])].copy()
            comp["Negative review rate (%)"]=(comp.negative_rate*100).round(1)
            comp["Average rating (out of 5)"]=comp.avg_rating.round(2)
            c1,c2=st.columns(2)
            with c1:
                st.plotly_chart(px.bar(comp,x="brand",y="Average rating (out of 5)",color="brand",range_y=[0,5],text_auto=".2f",labels={"brand":"Brand"},title="Average rating"),use_container_width=True)
            with c2:
                st.plotly_chart(px.bar(comp,x="brand",y="Negative review rate (%)",color="brand",range_y=[0,100],text_auto=".1f",labels={"brand":"Brand"},title="Negative review rate (1–2 stars)"),use_container_width=True)
            st.plotly_chart(px.bar(comp,x="brand",y="reviews",color="brand",text_auto=True,labels={"brand":"Brand","reviews":"Review count"},title="Review volume"),use_container_width=True)
            table=comp[["brand","products","reviews","Average rating (out of 5)","Negative review rate (%)"]].rename(columns={"brand":"Brand","products":"Products","reviews":"Reviews"})
            st.dataframe(table,hide_index=True,use_container_width=True)
            st.caption("Average rating and negative rate are weighted by review counts. Comparisons are descriptive and may be influenced by different product mixes and sample sizes.")

with tab3:
    st.subheader("Rating-based sentiment")
    st.caption("Positive = 4–5 stars; neutral = 3 stars; negative = 1–2 stars. This is a rating proxy, not text-based sentiment classification.")
    # The original product summary has avg_rating and negative_rate, but not a 3-way per-product rating breakdown.
    # Use the actual rating distribution only when the current selection represents the complete dataset.
    if bool(mask.all()):
        r=pd.DataFrame(raw["rating_distribution"])
        vals={"Positive (4–5★)":int(r.loc[r.rating>=4,"reviews"].sum()),"Neutral (3★)":int(r.loc[r.rating==3,"reviews"].sum()),"Negative (1–2★)":int(r.loc[r.rating<=2,"reviews"].sum())}
        st.plotly_chart(px.pie(names=list(vals),values=list(vals.values()),hole=.35,title="Full-dataset sentiment mix"),use_container_width=True)
    else:
        st.info("A precise 3-way sentiment pie chart is not available for filtered products: the embedded product summaries contain negative rate and mean rating, but not counts for each star. The negative rate below is exact to the source aggregate; the full-dataset pie appears when all filters are cleared.")
        st.metric("Filtered negative-review rate (1–2 stars)",f"{negative:.1%}")
    st.subheader("Most common words in available review excerpts")
    st.caption("All available text excerpts are negative-review examples; positive/neutral word comparisons cannot be computed from this dataset.")
    ids=set(filtered.product_id)
    subset=examples[examples.product_id.isin(ids)]
    st.caption(f"{len(subset):,} matching excerpts out of 3,000 sampled negative reviews. Not representative of all reviews or positive sentiment.")
    STOP=set("the and for with this that have from were they them your about would there their what when just very more than really like does dont didnt product amazon good great bad use used using its you are was but not all can had has one two out get got she her his him our who why how did too its also these those into over after before because been much only will could should some any off even still made make well look looks work works bought purchase item review reviews stars star".split())
    def words(texts):
        return Counter(w for t in texts.fillna("").astype(str) for w in re.findall(r"[a-z]{3,}",t.lower()) if w not in STOP)
    min_word_frequency=st.slider("Minimum word frequency",1,20,2,key="word_frequency")
    if subset.empty:st.warning("No review excerpts for the selected products. Widen the filters to view text evidence.")
    else:
        top=[(w,c) for w,c in words(subset.review_text).most_common(200) if c>=min_word_frequency][:20]
        if not top:
            st.info("No words meet this frequency. Lower the minimum word frequency.")
        st.plotly_chart(px.bar(pd.DataFrame(top,columns=["word","count"]).sort_values("count"),x="count",y="word",orientation="h"),use_container_width=True)
        st.caption("Counts are word occurrences in the capped negative-review excerpt sample, not all reviews.")
        st.dataframe(subset[["product","rating","review_title","review_text"]].head(15),hide_index=True,use_container_width=True)

with tab4:
    st.subheader("Product action table")
    st.caption("Suggested actions are investigative next steps based on rule-based issue tags, not confirmed defects.")
    st.caption("A separate workspace for product-level follow-up decisions. Select a product below to inspect available negative-review evidence.")
    order=st.selectbox("Sort products",["Action priority","Most reviews","Lowest rating","Highest rating","Highest negative rate"])
    x=filtered.copy()
    if order=="Action priority":
        x["priority"]=x.action.map({"Investigate":0,"Monitor":1,"Limited evidence":2,"Performing well":3})
        x=x.sort_values(["priority","review_count"],ascending=[True,False])
    elif order=="Most reviews":x=x.sort_values("review_count",ascending=False)
    elif order=="Lowest rating":x=x.sort_values("avg_rating")
    elif order=="Highest rating":x=x.sort_values("avg_rating",ascending=False)
    else:x=x.sort_values("negative_rate",ascending=False)
    issue_actions={"Packaging":"Review packaging complaints and inspect packaging quality.","Quality":"Investigate quality-related complaints and request product checks.","Scent":"Review fragrance and scent feedback with the product team.","Price":"Review perceived value and pricing feedback.","Shipping":"Investigate shipping and delivery complaints.","Other":"Read negative reviews to identify recurring concerns."}
    def recommendation(row):
        if row.action=="Limited evidence":return "Collect more customer feedback before prioritizing."
        if row.action=="Performing well":return "Maintain performance and monitor future reviews."
        issue=str(row.main_issue)
        return issue_actions.get(issue,"Review negative feedback for recurring issues.")
    x["recommended_action"]=x.apply(recommendation,axis=1)
    page_size=50
    pages=max(1,(len(x)+page_size-1)//page_size)
    page=st.number_input(f"Page (1–{pages:,}; 50 rows per page)",min_value=1,max_value=pages,value=1)
    view=x.iloc[(page-1)*page_size:page*page_size]
    st.dataframe(view[["product","brand","product_type","price","avg_rating","review_count","negative_rate","main_issue","action","recommended_action","product_id"]],hide_index=True,use_container_width=True)
    options=view.product_id.tolist()
    selected=st.selectbox("Inspect product in this page",options,format_func=lambda v: f"{x.loc[x.product_id.eq(v),'product'].iloc[0][:85]} ({v})")
    detail=x[x.product_id.eq(selected)].iloc[0]
    st.markdown(f"**{detail['product']}** — {detail['brand']}")
    st.write(f"Rating: {detail.avg_rating:.2f}/5 · Reviews: {detail.review_count:,} · Negative: {detail.negative_rate:.1%} · Action: {detail.action}")
    st.success(f"Suggested next step: {detail.recommended_action}")
    ev=examples[examples.product_id.eq(selected)]
    if ev.empty:st.info("No negative review excerpts for this product in the capped evidence sample. This does not mean the product has no negative reviews.")
    else:
        for _,r in ev.head(3).iterrows():
            st.markdown(f"**{r.get('review_title') or 'Review'}** ({r.get('rating')}★)")
            st.write(str(r.get('review_text') or '')[:1800])

with st.expander("Data scope, methodology, and limitations"):
    st.markdown("""- **Source:** Amazon Reviews 2023 All Beauty cleaned historical snapshot, embedded in the supplied HTML. The file is not a live feed.\n- **Coverage:** 694,253 eligible review rows, 112,565 products. Text evidence is limited to 3,000 sampled negative-review excerpts.\n- **Sentiment:** Star-based labels, not a machine-learning sentiment classifier. Filtered three-way counts are unavailable in the source summary and are intentionally not estimated.\n- **Categories:** Heuristic classification from product names; errors and 'Other' are expected.\n- **Similarity:** Removed from this MVP because product descriptions were not included in the supplied data; the app does not fabricate scores.\n- **Decision signals:** Action labels are transparent screening rules, not proof of product defects. No causal inference.\n- **Filters:** Product-level KPIs, matrix, brands, table and sampled word analysis update. Full-dataset historical charts do not change and are labeled accordingly.\n- **Future improvements:** Complete review-level sentiment counts, verified categories, full text corpus, and improved keyword modeling.\n""")
