"""Raw-input cleaning; rules and expected results are reviewable in config/."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')

def clean_text(x):
    return (x.strip() or None) if isinstance(x,str) else None

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)

def run(out):
    rules=json.loads((ROOT/'config/cleaning_rules.json').read_text())
    checks=json.loads((ROOT/'config/expected_record_checks.json').read_text())
    paths={k:ROOT/v for k,v in rules['sources'].items()}
    before={k:sha(p) for k,p in paths.items()}
    if before!=rules['source_sha256']: raise RuntimeError(f'Source hash mismatch: {before}')
    out=Path(out); data=out/'data'; reports=out/'reports'
    data.mkdir(parents=True,exist_ok=True); reports.mkdir(parents=True,exist_ok=True)
    seen={}; kept=[]; removed=[]; special={}; raw_count=0; raw_rating=0; raw_helpful=0; dup_rating=0; dup_helpful=0
    with paths['reviews'].open() as f:
        for row,line in enumerate(f,1):
            x=json.loads(line); raw_count+=1; raw_rating+=x['rating']; raw_helpful+=x['helpful_vote']
            fp=hashlib.sha256(canonical(x).encode()).hexdigest()
            if row in [1,31,28,213,6566,6567]: special[row]=x
            if fp in seen:
                removed.append({'removed_source_row':row,'retained_first_source_row':seen[fp],'fingerprint':fp})
                dup_rating+=x['rating']; dup_helpful+=x['helpful_vote']
            else:
                seen[fp]=row; x['source_review_row']=row; kept.append(x)
    reviews=pd.DataFrame(kept).rename(columns={'title':'review_title'})
    del kept,seen
    for raw,derived in [('review_title','review_title_clean'),('text','text_clean')]: reviews[derived]=reviews[raw].map(clean_text)
    reviews['rating_valid']=pd.to_numeric(reviews.rating,errors='coerce')
    reviews['rating_invalid']=~(reviews.rating_valid.between(1,5)&(reviews.rating_valid%1==0))
    reviews.loc[reviews.rating_invalid,'rating_valid']=np.nan
    reviews['helpful_vote_valid']=pd.to_numeric(reviews.helpful_vote,errors='coerce')
    reviews['helpful_vote_invalid']=~(reviews.helpful_vote_valid.ge(0)&(reviews.helpful_vote_valid%1==0))
    reviews.loc[reviews.helpful_vote_invalid,'helpful_vote_valid']=np.nan
    reviews['verified_purchase_invalid']=~reviews.verified_purchase.map(lambda x:type(x) is bool)
    reviews['verified_purchase_valid']=reviews.verified_purchase.where(~reviews.verified_purchase_invalid)
    reviews['review_time_utc']=pd.to_datetime(reviews.timestamp,unit='ms',utc=True,errors='coerce')
    reviews['timestamp_missing']=reviews.timestamp.isna()
    reviews['timestamp_failed']=reviews.timestamp.notna()&reviews.review_time_utc.isna()
    reviews['timestamp_outside_window']=reviews.review_time_utc.notna()&~reviews.review_time_utc.between(pd.Timestamp('1996-05-01',tz='UTC'),pd.Timestamp('2023-09-30 23:59:59.999',tz='UTC'))
    products=pd.read_parquet(paths['metadata']).rename(columns={'title':'product_title','images':'product_images'})
    if products.parent_asin.isna().any() or products.parent_asin.duplicated().any(): raise RuntimeError('Metadata keys must be nonnull and unique')
    products['product_title_clean']=products.product_title.map(clean_text)
    price=products.price.map(lambda x:x.strip() if isinstance(x,str) else x)
    missing=price.isna()|price.isin(['None',''])
    products['price_numeric']=pd.to_numeric(price.mask(missing),errors='coerce')
    products['price_parse_failed']=~missing&products.price_numeric.isna()
    products['price_invalid_numeric']=products.price_numeric.notna()&(~np.isfinite(products.price_numeric)|products.price_numeric.lt(0))
    products.loc[products.price_invalid_numeric,'price_numeric']=np.nan
    products['price_zero']=products.price_numeric.eq(0);products['price_over_1000']=products.price_numeric.gt(1000)
    products['store_missing']=products.store.isna()
    for c in ['features','description','categories']:
        products[c+'_text']=products[c].map(lambda a:'\n'.join(str(v) for v in a) if a is not None and len(a) else None)
        products[c+'_missing']=products[c].map(lambda a:a is None or not any(isinstance(v,str) and v.strip() for v in a))
    parsed=[]; failures=[]
    for x in products.details:
        try: parsed.append(json.loads(x) if isinstance(x,str) else x); failures.append(False)
        except (ValueError,TypeError): parsed.append(None); failures.append(True)
    products['details_parsed_json']=[canonical(x) if x is not None else None for x in parsed]
    products['details_parse_failed']=failures
    products['details_missing']=[not bool(x) for x in parsed]
    merged=reviews.merge(products,on='parent_asin',how='left',validate='many_to_one',indicator='metadata_match')
    neg=merged.rating_valid.isin([1,2]); valid=merged.rating_valid.notna()
    stats={
      'raw_reviews':raw_count,'duplicate_copies_removed':len(removed),'duplicate_groups':len({x['fingerprint'] for x in removed}),
      'retained_reviews':len(reviews),'metadata_records':len(products),'merged_rows':len(merged),'unmatched_retained_reviews':int(merged.metadata_match.eq('left_only').sum()),
      'unmatched_parent_keys':int(merged.loc[merged.metadata_match.eq('left_only'),'parent_asin'].nunique(dropna=False)),
      'extra_merge_rows':len(merged)-len(reviews),'duplicate_metadata_keys':int(products.parent_asin.duplicated().sum()),
      'metadata_without_retained_review':int((~products.parent_asin.isin(reviews.parent_asin)).sum()),
      'raw_rating_sum':raw_rating,'duplicate_rating_sum':dup_rating,'retained_rating_sum':float(merged.rating_valid.sum()),
      'raw_helpful_total':raw_helpful,'duplicate_helpful_total':dup_helpful,'retained_helpful_total':float(merged.helpful_vote_valid.sum(min_count=1)),
      'review_title_changes':int((reviews.review_title.fillna('')!=reviews.review_title_clean.fillna('')).sum()),
      'review_body_changes':int((reviews.text!=reviews.text_clean).sum()),'blank_review_bodies':int(reviews.text_clean.isna().sum()),
      'products_missing_price':int(products.price_numeric.isna().sum()),'reviews_missing_price':int(merged.price_numeric.isna().sum()),
      'price_parse_failures':int(products.price_parse_failed.sum()),'reviews_price_over_1000':int(merged.price_over_1000.sum()),
      'reviews_missing_store':int(merged.store_missing.sum()),'timestamp_failed':int(reviews.timestamp_failed.sum()),'timestamp_outside_window':int(reviews.timestamp_outside_window.sum()),
      'rating_invalid':int(reviews.rating_invalid.sum()),'helpful_vote_invalid':int(reviews.helpful_vote_invalid.sum()),'verified_purchase_invalid':int(reviews.verified_purchase_invalid.sum()),
      'details_parse_failures':int(products.details_parse_failed.sum()),'negative_reviews':int(neg.sum()),'verified_reviews':int(merged.verified_purchase_valid.eq(True).sum()),'valid_price_products':int(products.price_numeric.notna().sum())}
    stats.update({c+'_missing':int(products[c+'_missing'].sum()) for c in ['features','description','categories','details']})
    metrics={'mean_review_rating':float(merged.rating_valid.mean()),'rating_denominator':int(valid.sum()),'negative_review_rate':float(neg.sum()/valid.sum()),'verified_purchase_rate':float(merged.verified_purchase_valid.eq(True).sum()/merged.verified_purchase_valid.notna().sum()),'verified_denominator':int(merged.verified_purchase_valid.notna().sum()),'mean_available_product_price':float(products.price_numeric.mean()),'helpful_vote_denominator':int(merged.helpful_vote_valid.notna().sum())}
    mismatches={k:{'expected':v,'actual':stats[k]} for k,v in rules['expected'].items() if stats[k]!=v}
    for k,v in rules['expected_metrics'].items():
        if abs(metrics[k]-v['value'])>v['tolerance']: mismatches[k]={'expected':v,'actual':metrics[k]}
    result=[]; indexed=merged.set_index('source_review_row'); log=pd.DataFrame(removed)
    for c in checks:
        row=c['source_review_row']; actual={}; ok=False
        if c['id'] in ['A','B']:
            val=indexed.loc[row,'price_numeric']; original=indexed.loc[row,'price']; actual={'original':original,'price_numeric':None if pd.isna(val) else float(val)}
            ok=actual['price_numeric']==c['expected'] and original==c['original']
        elif c['id']=='C':
            actual={'store_missing':bool(indexed.loc[row,'store_missing']),'retained':row in indexed.index};ok=actual==c['expected']
        elif c['id']=='D':
            original=special[row]['text']; cleaned=indexed.loc[row,'text_clean']; actual={'original_length':len(original),'cleaned_length':len(cleaned),'trailing_nbsp':original.endswith('\u00a0'),'only_trailing_nbsp_removed':cleaned==original[:-1]};ok=actual==c['expected']
        else:
            raw_a=dict(special[6566]);raw_b=dict(special[6567]);raw_a.pop('source_review_row',None);raw_b.pop('source_review_row',None)
            actual={'raw_identical':canonical(raw_a)==canonical(raw_b),'removed':row not in indexed.index,'counterpart_retained':6566 in indexed.index,'logged_first_row':int(log.loc[log.removed_source_row.eq(row),'retained_first_source_row'].iloc[0])};ok=actual==c['expected']
        result.append({**c,'actual':actual,'pass':bool(ok)})
    after={k:sha(p) for k,p in paths.items()}
    if after!=before: raise RuntimeError('Raw sources changed during processing')
    audit={'status':'PASS' if not mismatches and all(x['pass'] for x in result) else 'FAIL','counts':stats,'metrics':metrics,'mismatches':mismatches,'source_sha256_before':before,'source_sha256_after':after,'timestamp_min':str(reviews.review_time_utc.min()),'timestamp_max':str(reviews.review_time_utc.max()),'record_checks_passed':sum(x['pass'] for x in result)}
    write_json(reports/'audit.json',audit);write_json(reports/'record_checks.json',result)
    if audit['status']!='PASS': raise RuntimeError(f'Validation stopped: {mismatches}; record checks: {result}')
    # Preserve raw nested columns; all metrics use validated derived fields.
    grouped=merged.groupby('parent_asin',dropna=False,sort=True).agg(review_count=('source_review_row','size'),valid_rating_count=('rating_valid','count'),rating_sum=('rating_valid',lambda s:s.sum(min_count=1)),mean_rating=('rating_valid','mean'),negative_count=('rating_valid',lambda s:int(s.isin([1,2]).sum())),valid_helpful_count=('helpful_vote_valid','count'),helpful_total=('helpful_vote_valid',lambda s:s.sum(min_count=1)),valid_verified_count=('verified_purchase_valid','count'),verified_count=('verified_purchase_valid',lambda s:int(s.eq(True).sum())))
    grouped['negative_rate']=grouped.negative_count/grouped.valid_rating_count.replace(0,np.nan);grouped['verified_rate']=grouped.verified_count/grouped.valid_verified_count.replace(0,np.nan)
    pm=products[['parent_asin','price_numeric']].merge(grouped.reset_index(),on='parent_asin',how='left',validate='one_to_one')
    assert grouped.review_count.sum()==len(merged) and grouped.rating_sum.sum()==stats['retained_rating_sum']
    merged.to_parquet(data/'beauty_cleaned.parquet',index=False);products.to_parquet(data/'products_cleaned.parquet',index=False);pm.to_parquet(data/'product_metrics.parquet',index=False)
    reasons={1:'predeclared missing price',31:'predeclared numeric price',28:'predeclared missing store',213:'predeclared trailing NBSP',6566:'retained duplicate counterpart of excluded row 6567'}
    for col in [c for c in merged if c.endswith(('_invalid','_missing','_failed','_outside_window','_over_1000','_zero'))]:
        ids=merged.loc[merged[col].eq(True),'source_review_row']
        if len(ids): reasons.setdefault(int(ids.iloc[0]),'first flag: '+col)
    remaining=merged.loc[~merged.source_review_row.isin(reasons)].sample(n=50-len(reasons),random_state=576)
    for row in remaining.source_review_row: reasons[int(row)]='deterministic random seed 576'
    sample=merged.loc[merged.source_review_row.isin(reasons)].copy();sample['selection_reason']=sample.source_review_row.map(reasons)
    assert len(sample)==50 and 6567 not in sample.source_review_row.values
    sample.to_csv(data/'cleaned_sample.csv',index=False)
    log.to_csv(reports/'removed_duplicates.csv',index=False)
    pd.concat([pd.DataFrame({'table':name,'column':df.columns,'missing_count':df.isna().sum().values,'rows':len(df)}) for name,df in [('reviews',merged),('products',products)]]).to_csv(reports/'missing_counts.csv',index=False)
    pd.concat([pd.DataFrame({'table':name,'column':df.columns,'dtype':df.dtypes.astype(str).values}) for name,df in [('reviews',merged),('products',products)]]).to_csv(reports/'cleaned_types.csv',index=False)
    write_json(reports/'source_profile.json',{'sources':rules['sources'],'sha256':before,'review_rows':raw_count,'metadata_rows':len(products),'original_review_fields':sorted(special[1].keys()-{'source_review_row'}),'metadata_columns':list(pd.read_parquet(paths['metadata']).columns),'review_grain':rules['review_grain']})
    print(json.dumps(audit,indent=2))
    return audit

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-root',type=Path,default=ROOT/'outputs');run(p.parse_args().output_root)
