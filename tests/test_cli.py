"""Command-line validation behavior without external network or AI tools."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'cite-check-tr/scripts/validate_report.py'
SAMPLE=ROOT/'cite-check-tr/examples/expected-offline-report.json'


class CLITests(unittest.TestCase):
    def test_valid_example_cli_success(self):
        result=subprocess.run([sys.executable,str(SCRIPT),str(SAMPLE)],text=True,capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('GEÇTİ',result.stdout)

    def test_invalid_claim_cli_failure(self):
        report=json.loads(SAMPLE.read_text(encoding='utf-8'))
        report['bulgular'][0]['durum']='dogrulandi'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.json'
            p.write_text(json.dumps(report,ensure_ascii=False),encoding='utf-8')
            result=subprocess.run([sys.executable,str(SCRIPT),str(p)],text=True,capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode, 1)
        self.assertIn('HATA',result.stderr)


if __name__ == '__main__':
    unittest.main()
