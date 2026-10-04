"""Full-data cleaning/auditing with bounded memory. Raw files are read only."""
import argparse, collections, csv, datetime as dt, hashlib, html, json, math, pathlib, re, sqlite3, unicodedata
from download_data import verify, sha
ROOT=pathlib.Path(__file__).resolve().parents[1]
LOW=int(dt.datetime(1996,5,1,tzinfo=dt.timezone.utc).timestamp()*1000)
HIGH=int(dt.datetime(2023,10,1,tzinfo=dt.timezone.utc).timestamp()*1000)
BR=re.compile(r'<br\s*/?\s*>',re.I)
def dumps(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def missing(x):return x is None or x=='' or x==[] or x=={}
def prose(x):
    if x is None:return None
    if not isinstance(x,str):return x
    x=unicodedata.normalize('NFC',html.unescape(BR.sub('\n',x))).strip()
    return x or None

def identifier(x):
    if not isinstance(x,str):return None
    return x.strip() or None

def numeric(x,integer=False,lo=None,hi=None):
    if x is None or x=='':return None,'missing'
    if isinstance(x,bool):return None,'conversion'
    try:y=float(x)
    except (ValueError,TypeError):return None,'conversion'
    if not math.isfinite(y) or (integer and not y.is_integer()):return None,'conversion'
    if (lo is not None and y<lo) or (hi is not None and y>hi):return None,'domain'
    return (int(y) if integer else y),None

def clean(r,kind):
    c=dict(r);flags=[];errors={}
    for k in (['asin','parent_asin','user_id'] if kind=='reviews' else ['parent_asin']):
        c[k]=identifier(r.get(k))
        if c[k] is None:flags.append('missing_'+k)
    for k in (['title','text'] if kind=='reviews' else ['main_category','title','store']):c[k]=prose(r.get(k))
    if kind=='metadata':
        for k in ['features','description']:
            v=r.get(k)
            if v is None:c[k]=[]
            elif isinstance(v,list):c[k]=[prose(x) for x in v]
            else:c[k]=[];flags.append('invalid_'+k)
        details=r.get('details')
        c['details']={k:prose(v) if isinstance(v,str) else v for k,v in details.items()} if isinstance(details,dict) else {}
        if not isinstance(details,dict):flags.append('invalid_details')
        specs={'average_rating':(False,1,5),'rating_number':(True,0,None),'price':(False,0,None)}
        if not c.get('categories'):flags.append('category_unavailable')
        if not c.get('title'):flags.append('missing_listing_title')
    else:
        specs={'rating':(True,1,5),'helpful_vote':(True,0,None),'timestamp':(True,None,None)}
        purchase=r.get('verified_purchase')
        c['verified_purchase']=purchase if isinstance(purchase,bool) else None
        if purchase is not None and not isinstance(purchase,bool):errors['verified_purchase']='conversion';flags.append('invalid_verified_purchase')
        if c.get('text') is None:flags.append('missing_review_text')
    for k,(integer,lo,hi) in specs.items():
        c[k],err=numeric(r.get(k),integer,lo,hi)
        if err in ['conversion','domain']:errors[k]=err;flags.append('invalid_'+k)
    if kind=='reviews':
        stamp=c['timestamp'];c['review_date_utc']=None;c['date_in_scope']=False
        if stamp is not None:
            try:c['review_date_utc']=dt.datetime.fromtimestamp(stamp/1000,dt.timezone.utc).isoformat(timespec='milliseconds')
            except (OverflowError,OSError,ValueError):errors['timestamp']='conversion';flags.append('invalid_date')
            c['date_in_scope']=c['review_date_utc'] is not None and LOW<=stamp<HIGH
            if c['review_date_utc'] is not None and not c['date_in_scope']:flags.append('date_outside_documented_scope')
    c['flags']=flags;return c,errors

def profile_add(counter,r):
    for k,v in r.items():
        counter['types'][k][type(v).__name__]+=1
        if missing(v):counter['missing'][k]+=1

def new_profile():return {'types':collections.defaultdict(collections.Counter),'missing':collections.Counter()}
def csv_query(db,query,path):
    cursor=db.execute(query)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow([x[0] for x in cursor.description]);w.writerows(cursor)
def main(raw_dir,out):
    out.mkdir(parents=True,exist_ok=True);manifest=json.loads((ROOT/'source_manifest.json').read_text())
    for spec in manifest['files']:verify(raw_dir/spec['filename'],spec)
    dbpath=out/'cleaned.sqlite.building'
    if dbpath.exists():dbpath.unlink()
    db=sqlite3.connect(dbpath);db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF')
    db.executescript('''
      CREATE TABLE reviews(source_line INTEGER PRIMARY KEY,record_id TEXT UNIQUE,source_hash TEXT UNIQUE,
      user_id TEXT,asin TEXT,parent_asin TEXT,rating INTEGER,helpful_vote INTEGER,verified_purchase INTEGER,
      timestamp INTEGER,review_date_utc TEXT,date_in_scope INTEGER,text_present INTEGER,payload TEXT);
      CREATE TABLE metadata(source_line INTEGER PRIMARY KEY,source_hash TEXT UNIQUE,parent_asin TEXT,
      title TEXT,store TEXT,price REAL,average_rating REAL,rating_number INTEGER,payload TEXT);
      CREATE TABLE removed_duplicates(kind TEXT,removed_line INTEGER,kept_line INTEGER);
    ''')
    evidence={'source':manifest,'tables':{},'rules_file':'docs/cleaning_rules.md'}
    for kind,spec in zip(['reviews','metadata'],manifest['files']):
        print('Processing',kind,flush=True)
        rawprof=new_profile();retprof=new_profile();cleanprof=new_profile();changed=collections.Counter();errs=collections.Counter();flagcounts=collections.Counter();n=dups=0
        rawtot=collections.Counter();duptot=collections.Counter()
        with (raw_dir/spec['filename']).open(encoding='utf-8') as f:
            for line,txt in enumerate(f,1):
                r=json.loads(txt);n+=1;profile_add(rawprof,r)
                for k in ['rating','helpful_vote'] if kind=='reviews' else ['rating_number','price']:
                    v=r.get(k)
                    if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v):rawtot[k]+=v
                fingerprint=hashlib.sha256(dumps(r).encode()).hexdigest()
                previous=db.execute(f'SELECT source_line FROM {kind} WHERE source_hash=?',(fingerprint,)).fetchone()
                if previous:
                    dups+=1;db.execute('INSERT INTO removed_duplicates VALUES (?,?,?)',(kind,line,previous[0]))
                    for k in rawtot:
                        v=r.get(k)
                        if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v):duptot[k]+=v
                    continue
                profile_add(retprof,r);c,errors=clean(r,kind);profile_add(cleanprof,{k:c.get(k) for k in r})
                for k in r:
                    if dumps(r[k])!=dumps(c.get(k)):changed[k]+=1
                for k,err in errors.items():errs[k+'_'+err]+=1
                flagcounts.update(c['flags'])
                if kind=='reviews':
                    db.execute('INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(line,f'All_Beauty:{line:07d}',fingerprint,c['user_id'],c['asin'],c['parent_asin'],c['rating'],c['helpful_vote'],c['verified_purchase'],c['timestamp'],c['review_date_utc'],int(c['date_in_scope']),int(c['text'] is not None),dumps(c)))
                else:db.execute('INSERT INTO metadata VALUES (?,?,?,?,?,?,?,?,?)',(line,fingerprint,c['parent_asin'],c['title'],c['store'],c['price'],c['average_rating'],c['rating_number'],dumps(c)))
                if n%50000==0:db.commit()
        db.commit();assert n==spec['rows'],(kind,n,spec['rows'])
        evidence['tables'][kind]={'raw_rows':n,'exact_duplicate_rows_removed':dups,'retained_rows':n-dups,'raw_profile':rawprof,'retained_before_cleaning_profile':retprof,'cleaned_profile':cleanprof,'changed_fields':changed,'errors':errs,'flags':flagcounts,'raw_numeric_totals':rawtot,'removed_duplicate_totals':duptot}
    db.executescript('''
      CREATE INDEX reviews_parent ON reviews(parent_asin);
      CREATE INDEX reviews_candidate ON reviews(user_id,asin,timestamp);
      CREATE INDEX metadata_parent ON metadata(parent_asin);
      CREATE TABLE metadata_conflicting_keys AS SELECT parent_asin,count(*) AS records FROM metadata
        WHERE parent_asin IS NOT NULL GROUP BY parent_asin HAVING count(*)>1;
      CREATE VIEW eligible_metadata AS SELECT * FROM metadata WHERE parent_asin IS NOT NULL
        AND parent_asin NOT IN (SELECT parent_asin FROM metadata_conflicting_keys);
      CREATE TABLE repeated_review_keys AS SELECT user_id,asin,timestamp,count(*) AS records FROM reviews
        WHERE user_id IS NOT NULL AND asin IS NOT NULL AND timestamp IS NOT NULL
        GROUP BY user_id,asin,timestamp HAVING count(*)>1;
      CREATE VIEW review_products AS SELECT r.*,m.source_line AS metadata_source_line,m.title AS product_title,
        m.store AS product_store,m.price AS product_price,m.average_rating AS listing_average_rating,
        m.rating_number AS listing_rating_number,m.payload AS metadata_payload,
        CASE WHEN m.source_line IS NULL THEN 0 ELSE 1 END AS metadata_matched,
        CASE WHEN EXISTS(SELECT 1 FROM repeated_review_keys k WHERE k.user_id=r.user_id AND k.asin=r.asin AND k.timestamp=r.timestamp) THEN 1 ELSE 0 END AS repeated_review_key
      FROM reviews r LEFT JOIN eligible_metadata m ON r.parent_asin=m.parent_asin;
    ''')
    def one(q):return dict(db.execute(q).fetchone())
    evidence['duplicates']={
      'raw_repeated_review_candidate_groups':db.execute('SELECT COUNT(*) FROM (SELECT user_id,asin,timestamp FROM reviews GROUP BY user_id,asin,timestamp HAVING COUNT(*)>1)').fetchone()[0],
      'retained_repeated_review_candidate_groups':db.execute('SELECT COUNT(*) FROM repeated_review_keys').fetchone()[0],
      'retained_rows_in_repeated_review_candidate_groups':db.execute('SELECT COALESCE(SUM(records),0) FROM repeated_review_keys').fetchone()[0],
      'metadata_conflicting_parent_keys':db.execute('SELECT COUNT(*) FROM metadata_conflicting_keys').fetchone()[0],
      'metadata_rows_excluded_from_join_for_conflicts':db.execute('SELECT COALESCE(SUM(records),0) FROM metadata_conflicting_keys').fetchone()[0]}
    evidence['duplicates']['repeated_review_identifiers']={}
    for field in ['user_id','asin','parent_asin']:
        row=db.execute(f'SELECT COUNT(*) AS groups,SUM(n) AS rows_in_groups,SUM(n-1) AS repeats_beyond_first FROM (SELECT COUNT(*) n FROM reviews WHERE {field} IS NOT NULL GROUP BY {field} HAVING COUNT(*)>1)').fetchone()
        evidence['duplicates']['repeated_review_identifiers'][field]=dict(row)
    evidence['duplicates']['metadata_repeated_parent_groups_after_exact_dedup']=evidence['duplicates']['metadata_conflicting_parent_keys']
    # Raw candidate multiplicities are counted from a second independent source scan.
    rawkeys=collections.Counter()
    with (raw_dir/'All_Beauty.jsonl').open() as f:
        for txt in f:
            r=json.loads(txt);rawkeys[(r.get('user_id'),r.get('asin'),r.get('timestamp'))]+=1
    evidence['duplicates']['raw_repeated_review_candidate_groups']=sum(v>1 for v in rawkeys.values())
    evidence['duplicates']['raw_rows_in_repeated_review_candidate_groups']=sum(v for v in rawkeys.values() if v>1)
    del rawkeys
    evidence['merge']=one('''SELECT COUNT(*) AS joined_rows,SUM(metadata_matched) AS matched_rows,
      SUM(1-metadata_matched) AS unmatched_review_rows,
      COUNT(DISTINCT CASE WHEN metadata_matched=0 THEN parent_asin END) AS unmatched_parent_keys,
      COUNT(DISTINCT CASE WHEN metadata_matched=1 THEN parent_asin END) AS matched_parent_keys,
      SUM(parent_asin IS NULL) AS missing_parent_key_rows FROM review_products''')
    evidence['merge']['eligible_metadata_rows']=db.execute('SELECT COUNT(*) FROM eligible_metadata').fetchone()[0]
    evidence['merge']['metadata_without_reviews']=db.execute('SELECT COUNT(*) FROM eligible_metadata m WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.parent_asin=m.parent_asin)').fetchone()[0]
    evidence['metrics']=one('''SELECT COUNT(*) AS review_count,COUNT(rating) AS rating_n,SUM(rating) AS rating_sum,
      AVG(rating) AS average_rating,SUM(CASE WHEN rating IN (1,2) THEN 1 ELSE 0 END) AS negative_review_n,
      1.0*SUM(CASE WHEN rating IN (1,2) THEN 1 ELSE 0 END)/NULLIF(COUNT(rating),0) AS negative_review_rate,
      COUNT(verified_purchase) AS purchase_n,SUM(verified_purchase) AS verified_purchase_n,
      AVG(verified_purchase) AS verified_purchase_rate,COUNT(helpful_vote) AS helpful_n,SUM(helpful_vote) AS helpful_vote_sum,
      SUM(text_present) AS review_body_n,SUM(date_in_scope) AS in_scope_date_n,
      COUNT(DISTINCT parent_asin) AS parent_product_n,COUNT(DISTINCT user_id) AS reviewer_n,
      MIN(review_date_utc) AS date_min,MAX(review_date_utc) AS date_max FROM reviews''')
    evidence['suspicious']=one('SELECT MAX(helpful_vote) AS max_helpful_vote,MIN(timestamp) AS min_timestamp,MAX(timestamp) AS max_timestamp FROM reviews')
    evidence['suspicious'].update(one('SELECT MIN(price) AS min_price,MAX(price) AS max_price,MAX(rating_number) AS max_listing_rating_count FROM metadata'))
    evidence['suspicious']['helpful_vote_p99']=db.execute('SELECT helpful_vote FROM reviews WHERE helpful_vote IS NOT NULL ORDER BY helpful_vote LIMIT 1 OFFSET ?', (int(evidence['metrics']['helpful_n']*.99),)).fetchone()[0]
    evidence['reconciliation']={}
    for k,metric in [('rating','rating_sum'),('helpful_vote','helpful_vote_sum')]:
        tab=evidence['tables']['reviews'];start=tab['raw_numeric_totals'][k];removed=tab['removed_duplicate_totals'].get(k,0);actual=evidence['metrics'][metric]
        evidence['reconciliation'][k]={'original_sum':start,'duplicate_sum_removed':removed,'cleaned_sum':actual,'difference_after_duplicate_accounting':start-removed-actual}
    evidence['reconciliation']['metadata_totals']=one('SELECT SUM(price) AS price_sum,COUNT(price) AS price_n,SUM(rating_number) AS rating_number_sum FROM metadata')
    assert evidence['merge']['joined_rows']==evidence['tables']['reviews']['retained_rows']
    assert all(x['difference_after_duplicate_accounting']==0 for k,x in evidence['reconciliation'].items() if k!='metadata_totals')
    evidence['input_integrity']={spec['filename']:sha(raw_dir/spec['filename']) for spec in manifest['files']}
    assert all(evidence['input_integrity'][s['filename']]==s['sha256'] for s in manifest['files'])
    csv_query(db,'SELECT * FROM removed_duplicates ORDER BY kind,removed_line',out/'removed_duplicates.csv')
    csv_query(db,'SELECT * FROM metadata_conflicting_keys ORDER BY parent_asin',out/'metadata_conflicting_keys.csv')
    csv_query(db,'SELECT * FROM repeated_review_keys ORDER BY user_id,asin,timestamp',out/'repeated_review_keys.csv')
    csv_query(db,'''SELECT r.parent_asin,COUNT(*) AS review_count,COUNT(r.rating) AS rating_n,
      AVG(r.rating) AS review_average_rating,SUM(r.rating IN (1,2)) AS negative_review_n,
      1.0*SUM(CASE WHEN r.rating IN (1,2) THEN 1 ELSE 0 END)/NULLIF(COUNT(r.rating),0) AS negative_review_rate,
      COUNT(r.verified_purchase) AS purchase_n,AVG(r.verified_purchase) AS verified_purchase_rate,
      SUM(r.text_present) AS review_body_n,SUM(r.helpful_vote) AS helpful_vote_sum,
      CASE WHEN m.parent_asin IS NULL THEN 0 ELSE 1 END AS metadata_matched,m.title AS product_title,m.store AS store,m.price AS price
      FROM reviews r LEFT JOIN eligible_metadata m ON r.parent_asin=m.parent_asin
      WHERE r.parent_asin IS NOT NULL GROUP BY r.parent_asin ORDER BY r.parent_asin''',out/'product_metrics.csv')
    csv_query(db,'''SELECT parent_asin,COUNT(*) AS unmatched_review_rows FROM review_products
      WHERE metadata_matched=0 GROUP BY parent_asin ORDER BY parent_asin''',out/'unmatched_products.csv')
    csv_query(db,'''SELECT substr(review_date_utc,1,4) AS year,COUNT(*) AS reviews,COUNT(rating) AS rating_n,AVG(rating) AS average_rating
      FROM reviews WHERE date_in_scope=1 GROUP BY year ORDER BY year''',out/'annual_metrics.csv')
    # Five expected values were declared before this script's first run.
    expected=json.loads((ROOT/'docs/record_expectations.json').read_text());checks=[]
    for case in expected:
        row=db.execute('SELECT * FROM review_products WHERE source_line=?',(case['source_line'],)).fetchone()
        if row is None:raise AssertionError(f"Case was unexpectedly dropped: {case['source_line']}")
        cleanreview=json.loads(row['payload']);actual={k:(row[k] if k in ['metadata_matched','product_price'] else cleanreview[k]) for k in case['expected']}
        match=actual==case['expected'];checks.append({**case,'actual':actual,'matches':match});assert match,checks[-1]
    (out/'record_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    # Select difficult cases first, then deterministic hash order for diversity.
    selected=[x['source_line'] for x in expected];reasons={x['source_line']:'Five-record check: '+x['case'] for x in expected}
    predicates=[('unmatched metadata','metadata_matched=0'),('repeated candidate review key','repeated_review_key=1'),('missing listing price','metadata_matched=1 AND product_price IS NULL'),('missing listing text',"metadata_matched=1 AND (json_array_length(json_extract(metadata_payload,'$.features'))=0 OR json_array_length(json_extract(metadata_payload,'$.description'))=0)"),('low rating','rating IN (1,2)'),('high helpful votes','helpful_vote>100')]
    for reason,pred in predicates:
        r=db.execute(f'SELECT source_line FROM review_products WHERE {pred} ORDER BY source_line LIMIT 1').fetchone()
        if r and r[0] not in selected:selected.append(r[0]);reasons[r[0]]=reason
    candidates=((hashlib.sha256(r['record_id'].encode()).hexdigest(),r['source_line']) for r in db.execute('SELECT record_id,source_line FROM reviews'))
    import heapq
    for _,line in heapq.nsmallest(80,candidates):
        if len(selected)>=50:break
        if line not in selected:selected.append(line);reasons[line]='Deterministic SHA256 rank of record_id'
    sample=[]
    for line in selected:
        row=db.execute('SELECT * FROM review_products WHERE source_line=?',(line,)).fetchone();r=json.loads(row['payload']);m=json.loads(row['metadata_payload']) if row['metadata_payload'] else None
        sample.append({'record_id':row['record_id'],'source_line':line,**r,'repeated_review_key':bool(row['repeated_review_key']),'metadata_matched':bool(row['metadata_matched']),'metadata_source_line':row['metadata_source_line'],'product':m,'sample_reason':reasons[line]})
    sample_dir=out/'samples';sample_dir.mkdir(exist_ok=True)
    (sample_dir/'cleaned_sample.jsonl').write_text(''.join(dumps(x)+'\n' for x in sample),encoding='utf-8')
    columns=['record_id','source_line','parent_asin','asin','user_id','rating','title','text','review_date_utc','helpful_vote','verified_purchase','flags','repeated_review_key','metadata_matched','metadata_source_line','product','sample_reason']
    with (sample_dir/'cleaned_sample.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for r in sample:writer.writerow({k:dumps(r[k]) if isinstance(r.get(k),(dict,list)) else r.get(k) for k in columns})
    assert len(sample)==50 and len({x['record_id'] for x in sample})==50
    evidence['sample']={'rows':50,'method':'Difficult cases first, then SHA256(record_id) ascending; no representativeness claimed.','case_source_lines':selected}
    # Missing-column report has three comparable stages.
    with (out/'column_audit.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['table','column','raw_missing','retained_preclean_missing','cleaned_missing','raw_types','cleaned_types','changed_retained_values','failed_conversion','invalid_domain'])
        for kind,t in evidence['tables'].items():
            for k in sorted(t['raw_profile']['types']):
                w.writerow([kind,k,t['raw_profile']['missing'].get(k,0),t['retained_before_cleaning_profile']['missing'].get(k,0),t['cleaned_profile']['missing'].get(k,0),dumps(t['raw_profile']['types'][k]),dumps(t['cleaned_profile']['types'][k]),t['changed_fields'].get(k,0),t['errors'].get(k+'_conversion',0),t['errors'].get(k+'_domain',0)])
    # Integrity check and deterministic logical output fingerprint independent of SQLite storage layout.
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    h=hashlib.sha256()
    for table,order in [('reviews','source_line'),('metadata','source_line'),('removed_duplicates','kind,removed_line')]:
        h.update(table.encode())
        for row in db.execute(f'SELECT * FROM {table} ORDER BY {order}'):h.update((dumps(list(row))+'\n').encode())
    evidence['logical_database_sha256']=h.hexdigest();db.commit();db.close();dbpath.replace(out/'cleaned.sqlite')
    (out/'audit.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
    generated_files=['audit.json','column_audit.csv','removed_duplicates.csv','metadata_conflicting_keys.csv','repeated_review_keys.csv','product_metrics.csv','unmatched_products.csv','annual_metrics.csv','record_checks.json','samples/cleaned_sample.jsonl','samples/cleaned_sample.csv']
    fingerprint={rel:sha(out/rel) for rel in sorted(generated_files)}
    (out/'output_checksums.json').write_text(json.dumps(fingerprint,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'reviews':evidence['tables']['reviews']['retained_rows'],'metadata':evidence['tables']['metadata']['retained_rows'],'merge':evidence['merge'],'metrics':evidence['metrics']},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=pathlib.Path,default=ROOT/'data/raw');p.add_argument('--out',type=pathlib.Path,default=ROOT/'outputs');a=p.parse_args();main(a.raw_dir,a.out)
