"""Recreate outputs in a new Python process, compare, verify, record evidence."""
import argparse,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=pathlib.Path,default=ROOT/'data/raw');p.add_argument('--baseline',type=pathlib.Path,default=ROOT/'outputs');a=p.parse_args()
    replica=a.baseline/'reproduced'
    subprocess.run([sys.executable,str(ROOT/'scripts/clean_data.py'),'--raw-dir',str(a.raw_dir),'--out',str(replica)],check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/verify_outputs.py'),'--raw-dir',str(a.raw_dir),'--out',str(replica)],check=True)
    base=json.loads((a.baseline/'output_checksums.json').read_text());new=json.loads((replica/'output_checksums.json').read_text());assert base==new
    mismatches=[]
    for rel,expected in base.items():
        with (replica/rel).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=expected:mismatches.append(rel)
    assert not mismatches,mismatches
    assert (a.baseline/'verification.json').read_bytes()==(replica/'verification.json').read_bytes()
    result={'passed':True,'fresh_python_process':True,'compared_artifact_count':len(base),'all_csv_json_jsonl_sha256_match':True,'independent_verification_matches':True,'logical_database_sha256':json.loads((replica/'audit.json').read_text())['logical_database_sha256'],'notebook_execution':'See outputs/notebook_execution.json; separate fresh Python/IPython namespace.'}
    (a.baseline/'reproducibility.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
