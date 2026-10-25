"""Reject broken source identity, changed measurements and stale web exports."""
import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest
import pandas as pd
from run import HERE, load_data
from verify import verify

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        shutil.copytree(HERE/'data',self.root/'data')
        shutil.copytree(HERE/'outputs',self.root/'outputs')
    def test_original_passes(self):
        with contextlib.redirect_stdout(io.StringIO()):verify(self.root/'outputs')
    def test_duplicated_spectrum_rejected(self):
        p=self.root/'data/manifest.csv';m=pd.read_csv(p);pd.concat([m,m.iloc[:1]]).to_csv(p,index=False)
        with self.assertRaisesRegex(ValueError,'duplicated'):load_data(self.root/'data')
    def test_modified_measurement_hash_rejected(self):
        p=self.root/'data/manifest.csv';m=pd.read_csv(p);m.loc[0,'numeric_sha256']='0'*64;m.to_csv(p,index=False)
        with self.assertRaisesRegex(ValueError,'checksum'):load_data(self.root/'data')
    def test_false_specimen_fold_rejected(self):
        p=self.root/'outputs/row_predictions.csv';m=pd.read_csv(p);m.loc[0,'fold']=999;m.to_csv(p,index=False)
        with self.assertRaisesRegex(AssertionError,'held-out specimen'):verify(self.root/'outputs')
    def test_stale_browser_rejected(self):
        p=self.root/'outputs/browser-data.js';p.write_text(p.read_text().replace('"n_spectra":52','"n_spectra":53',1))
        with self.assertRaisesRegex(AssertionError,'browser metrics'):verify(self.root/'outputs')

if __name__=='__main__':unittest.main()
