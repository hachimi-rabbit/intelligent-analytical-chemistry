"""Regression tests: corrupt temporary copies and require verification to fail."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

from export_interactive import build_payload, render_script

HERE = Path(__file__).resolve().parent


class VerificationRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="g04 verify ")
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "results"
        self.output.mkdir()
        for source in (HERE / "outputs").iterdir():
            if source.suffix in (".csv", ".json") and source.name != "spectra.csv":
                shutil.copy2(source, self.output / source.name)
        self.target = self.output / "ch04-results.js"
        self.target.write_text(render_script(build_payload(self.output)), encoding="utf-8")

    def verify(self):
        env = os.environ.copy()
        env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", PYTHONUTF8="1")
        return subprocess.run([
            sys.executable, str(HERE / "verify.py"), "--output", str(self.output),
            "--interactive-data", str(self.target)
        ], capture_output=True, text=True, encoding="utf-8", env=env)

    def test_complete_results_pass(self):
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_stale_browser_export_fails(self):
        self.target.write_text(self.target.read_text(encoding="utf-8").replace('"seed":2026', '"seed":9999', 1), encoding="utf-8")
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("browser export matches Python results", result.stderr)

    def test_missing_panel_group_fails(self):
        path = self.output / "panel_sample_predictions.csv"
        frame = pd.read_csv(path)
        frame = frame[~((frame.seed == 1101) & (frame.model == "Dummy") & (frame.instrument == "B"))]
        frame.to_csv(path, index=False)
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("complete panel prediction coverage", result.stderr)

    def test_duplicate_specimen_fails(self):
        path = self.output / "panel_sample_predictions.csv"
        frame = pd.read_csv(path)
        pd.concat([frame, frame.iloc[:1]], ignore_index=True).to_csv(path, index=False)
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unique panel specimen predictions", result.stderr)

    def test_missing_cv_model_fails(self):
        path = self.output / "model_comparison.csv"
        frame = pd.read_csv(path)
        frame.iloc[1:].to_csv(path, index=False)
        result = self.verify()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("complete CV coverage comparison", result.stderr)


if __name__ == "__main__":
    unittest.main()
