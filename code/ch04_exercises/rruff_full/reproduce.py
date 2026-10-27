"""Run the complete full-source evaluation and save final all-usable-data models."""
import argparse
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--archive',type=Path,help='Optional pinned source ZIP; rebuild bundled features when supplied')
p.add_argument('--output',type=Path,default=HERE/'reproduced')
a=p.parse_args();out=a.output.resolve();models=out/'models'
if a.archive:
    subprocess.run([sys.executable,str(HERE/'prepare.py'),'--archive',str(a.archive.resolve())],check=True)
for script,extra in [('run.py',['--models-dir',str(models)]),('verify.py',['--models-dir',str(models)]),('export.py',[])]:
    subprocess.run([sys.executable,str(HERE/script),'--output',str(out),*extra],check=True)
print('PASS: all usable records fitted; held-out metrics independently verified; display exported.')
