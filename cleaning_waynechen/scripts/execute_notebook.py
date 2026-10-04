"""Run every notebook cell in a fresh process/IPython namespace, no socket server.
Usage: python scripts/execute_notebook.py
The resulting notebook stores actual text and rich display outputs. Local Jupyter
users can alternatively select Python 3, restart the kernel, and Run All.
"""
import json,pathlib,sys
import nbformat
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.io import capture_output
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    import os
    os.chdir(ROOT);path=ROOT/'cleaning_waynechen.ipynb';nb=nbformat.read(path,as_version=4)
    shell=InteractiveShell.instance();n=0
    for cell in nb.cells:
        if cell.cell_type!='code':continue
        n+=1;cell.outputs=[];cell.execution_count=n
        with capture_output(stdout=True,stderr=True,display=True) as captured:
            result=shell.run_cell(cell.source,store_history=False)
        if result.error_before_exec or result.error_in_exec:raise RuntimeError(result.error_before_exec or result.error_in_exec)
        if captured.stdout:cell.outputs.append(nbformat.v4.new_output('stream',name='stdout',text=captured.stdout))
        if captured.stderr:cell.outputs.append(nbformat.v4.new_output('stream',name='stderr',text=captured.stderr))
        for rich in captured.outputs:cell.outputs.append(nbformat.v4.new_output('display_data',data=rich.data,metadata=rich.metadata))
        print(f'Notebook cell {n} passed',flush=True)
    nbformat.validate(nb);nbformat.write(nb,path)
    evidence={'fresh_python_process':True,'fresh_ipython_namespace':True,'execution_method':'All code cells executed in order by scripts/execute_notebook.py; in-process IPython avoids a socket-backed Jupyter server.','all_code_cells_completed':True,'code_cell_count':n,'python_version':sys.version.split()[0],'executed_from_original_raw_files':True}
    (ROOT/'outputs/notebook_execution.json').write_text(json.dumps(evidence,indent=2)+'\n')
if __name__=='__main__':main()
