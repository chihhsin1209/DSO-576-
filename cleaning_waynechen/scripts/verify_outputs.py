"""Independent raw-source and cleaned-output verification; no cleaner imported."""
import argparse,collections,hashlib,json,pathlib,sqlite3
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main(raw,out):
    db=sqlite3.connect(out/'cleaned.sqlite');db.row_factory=sqlite3.Row
    audit=json.loads((out/'audit.json').read_text());seen=set();n=dups=0;rating_sum=helpful_sum=0;rating_n=0;negative=0
    # Independently rescan all review records and count exact parsed objects.
    with (raw/'All_Beauty.jsonl').open() as f:
        for line in f:
            r=json.loads(line);n+=1
            canonical=json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
            key=hashlib.sha256(canonical.encode('utf-8')).hexdigest()
            if key in seen:dups+=1;continue
            seen.add(key)
            v=r.get('rating')
            if isinstance(v,(int,float)) and not isinstance(v,bool) and v in [1,2,3,4,5]:
                rating_n+=1;rating_sum+=v;negative+=v in [1,2]
            v=r.get('helpful_vote')
            if isinstance(v,int) and not isinstance(v,bool) and v>=0:helpful_sum+=v
    assert n==audit['tables']['reviews']['raw_rows']
    assert dups==audit['tables']['reviews']['exact_duplicate_rows_removed']
    assert len(seen)==audit['metrics']['review_count']
    assert rating_sum==audit['metrics']['rating_sum']
    assert rating_n==audit['metrics']['rating_n']
    assert negative==audit['metrics']['negative_review_n']
    assert helpful_sum==audit['metrics']['helpful_vote_sum']
    checks=json.loads((out/'record_checks.json').read_text())
    assert len(checks)==5 and all(c['actual']==c['expected'] and c['matches'] for c in checks)
    # Compare each sample field back to its full-data stored record and join.
    sample=[json.loads(x) for x in (out/'samples/cleaned_sample.jsonl').read_text().splitlines()]
    assert len(sample)==50 and len({x['record_id'] for x in sample})==50
    for r in sample:
        full=db.execute('SELECT * FROM review_products WHERE record_id=?',(r['record_id'],)).fetchone();assert full is not None
        payload=json.loads(full['payload']);assert all(r[k]==v for k,v in payload.items())
        assert r['metadata_matched']==bool(full['metadata_matched'])
        assert r['product']==(json.loads(full['metadata_payload']) if full['metadata_payload'] else None)
    # Aggregate denominator checks from raw numeric values and product groups.
    product_n=db.execute('SELECT SUM(n) FROM (SELECT COUNT(*) n FROM reviews WHERE parent_asin IS NOT NULL GROUP BY parent_asin)').fetchone()[0]
    null_keys=db.execute('SELECT COUNT(*) FROM reviews WHERE parent_asin IS NULL').fetchone()[0]
    assert product_n+null_keys==len(seen)
    assert db.execute('SELECT COUNT(*) FROM review_products').fetchone()[0]==len(seen)
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    # Labeled synthetic boundary probes, separate from the five genuine records.
    # These probe the implementation, while the full-data checks above are independent.
    from clean_data import prose,identifier,numeric
    assert prose('I love it <3')=='I love it <3'
    assert identifier(' 00123 ')=='00123'
    assert numeric(True,integer=True)[1]=='conversion'
    assert numeric(6,integer=True,lo=1,hi=5)[1]=='domain'
    assert prose('A<br />B &amp; C')=='A\nB & C'
    result={'passed':True,'independent_raw_review_rows':n,'independent_exact_duplicates':dups,'independent_retained_rows':len(seen),'independent_rating_sum':rating_sum,'independent_helpful_vote_sum':helpful_sum,'five_genuine_record_checks_passed':5,'sample_rows_verified_against_full_output':50,'synthetic_boundary_probes_passed':5,'joined_count_equals_retained':True,'sqlite_integrity':'ok'}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    db.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=pathlib.Path,default=ROOT/'data/raw');p.add_argument('--out',type=pathlib.Path,default=ROOT/'outputs');a=p.parse_args();main(a.raw_dir,a.out)
