import os,sys,tempfile
from pathlib import Path
import nbformat
from nbclient import NotebookClient
ROOT=Path(__file__).resolve().parents[1]
def main():
    path=ROOT/'Module_6_Cleaning.ipynb';nb=nbformat.read(path,as_version=4)
    with tempfile.TemporaryDirectory(prefix='module6-jupyter-') as folder:
        kernel=Path(folder)/'kernels'/'module6';kernel.mkdir(parents=True)
        (kernel/'kernel.json').write_text(__import__('json').dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],'display_name':'Module 6 project Python','language':'python'}))
        os.environ['JUPYTER_PATH']=folder+os.pathsep+os.environ.get('JUPYTER_PATH','')
        os.environ['IPYTHONDIR']=str(Path(folder)/'ipython')
        NotebookClient(nb,timeout=1800,kernel_name='module6',allow_errors=False,resources={'metadata':{'path':str(ROOT)}}).execute()
    nb.metadata['kernelspec']={'display_name':'Python 3','language':'python','name':'python3'}
    nbformat.write(nb,path);print('Notebook PASS: executed with',sys.executable)
if __name__=='__main__':main()
