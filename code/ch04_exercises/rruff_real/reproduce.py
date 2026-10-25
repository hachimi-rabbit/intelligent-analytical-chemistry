"""Recompute the bundled measured subset, optionally restoring it from DTU."""
import argparse
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--redownload',action='store_true',help='Restore subset from the checksum-pinned 129 MiB DTU archive')
p.add_argument('--output',type=Path,default=HERE/'outputs')
a=p.parse_args()
if a.redownload:subprocess.run([sys.executable,str(HERE/'prepare_data.py')],check=True)
for script in ['run.py','verify.py']:
    print('Running',script,flush=True)
    subprocess.run([sys.executable,str(HERE/script),'--output',str(a.output.resolve())],check=True)
print('PASS: measured-data experiment reproduced and verified.')
