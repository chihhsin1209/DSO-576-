"""Download pinned sources atomically; never overwrite an existing raw file."""
import argparse, hashlib, json, pathlib, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def verify(path, spec):
    assert path.stat().st_size == spec['size'], f'Wrong size: {path}'
    assert sha(path) == spec['sha256'], f'Wrong SHA256: {path}'
def main():
    p=argparse.ArgumentParser();p.add_argument('--raw-dir',type=pathlib.Path,default=ROOT/'data/raw');a=p.parse_args()
    manifest=json.loads((ROOT/'source_manifest.json').read_text());a.raw_dir.mkdir(parents=True,exist_ok=True)
    for spec in manifest['files']:
        path=a.raw_dir/spec['filename']
        if path.exists(): verify(path,spec);print('Verified existing',path);continue
        temp=path.with_suffix(path.suffix+'.part')
        url=f"https://huggingface.co/datasets/{manifest['dataset']}/resolve/{manifest['revision']}/{spec['path']}?download=true"
        with urllib.request.urlopen(url,timeout=120) as response,temp.open('wb') as out:
            while chunk:=response.read(1024*1024):out.write(chunk)
        verify(temp,spec);temp.replace(path);print('Downloaded and verified',path)
if __name__=='__main__':main()
