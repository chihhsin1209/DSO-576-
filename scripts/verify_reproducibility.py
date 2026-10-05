"""Regenerate artifacts in a temporary directory and compare independently."""
import tempfile
import itertools
import pyarrow.parquet as pq
from clean_data import ROOT,run,sha,write_json

def main():
    base=ROOT/'outputs'; compared=[]
    with tempfile.TemporaryDirectory(prefix='module6-reproduce-') as folder:
        fresh=__import__('pathlib').Path(folder)/'outputs';run(fresh)
        for path in sorted(fresh.rglob('*')):
            if not path.is_file():continue
            rel=path.relative_to(fresh); original=base/rel
            if not original.exists():raise RuntimeError(f'Missing baseline {rel}')
            if path.suffix=='.parquet':
                left=pq.ParquetFile(original);right=pq.ParquetFile(path)
                if not left.schema_arrow.equals(right.schema_arrow,check_metadata=True):
                    raise RuntimeError(f"Logical schema mismatch: {rel}")
                for i,(a,b) in enumerate(itertools.zip_longest(left.iter_batches(batch_size=10000),right.iter_batches(batch_size=10000))):
                    if a is None or b is None or not a.equals(b):
                        raise RuntimeError(f"Logical table mismatch: {rel}, batch {i}")
                method='exact logical table equality, including order/dtypes/nested values'
            else:
                if sha(original)!=sha(path):raise RuntimeError(f'Exact SHA-256 mismatch: {rel}')
                method='exact SHA-256'
            compared.append({'artifact':str(rel),'method':method,'pass':True})
    report={'status':'PASS','compared':compared,'excluded':'reproducibility.json (this report), executed notebook, PDF, independent_check.json; these are downstream artifacts','isolation':'Temporary output directory; raw inputs and baseline output files untouched.'}
    write_json(base/'reports/reproducibility.json',report);print('Reproducibility PASS:',len(compared),'artifacts')
if __name__=='__main__':main()
