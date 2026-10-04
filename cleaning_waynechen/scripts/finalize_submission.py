"""Add the user's real pushed code/evidence commit to README and PDF."""
import argparse,json,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--commit',required=True,help='Full 40-character commit SHA containing the code and cleaning evidence');a=p.parse_args()
if not re.fullmatch(r'[0-9a-fA-F]{40}',a.commit):p.error('Use the full 40-character Git commit SHA.')
path=ROOT/'submission_metadata.json';m=json.loads(path.read_text());m['submitted_commit']=a.commit.lower();path.write_text(json.dumps(m,indent=2)+'\n')
subprocess.run([sys.executable,str(ROOT/'scripts/build_report.py')],check=True)
print('Updated README and PDF with your supplied commit. Review before submission.')
