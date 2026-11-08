"""A clean installation must enforce URI/date formats, never silently skip them."""
from copy import deepcopy
from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from jsonschema import FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'cite-check-tr/scripts'))
import validate_report as module
SAMPLE = json.loads((ROOT/'cite-check-tr/examples/live-report-2026-11-08.json').read_text())


def with_source(url):
    report = deepcopy(SAMPLE)
    finding = next(f for f in report['bulgular'] if f['durum'] == 'uyumsuzluk')
    finding['kaynak_url'] = url
    for entry in finding['erisim_kaydi']:
        if entry['sonuc'] == 'tam_metin':
            entry['url'] = url
    return report


class URIValidationTests(unittest.TestCase):
    def test_required_format_checkers_installed(self):
        self.assertTrue({'uri', 'date'} <= FormatChecker().checkers.keys())

    def test_source_uri_space_rejected(self):
        self.assertTrue(module.validate(with_source('https://www.mevzuat.gov.tr/invalid path')))

    def test_access_log_uri_rejected(self):
        report = deepcopy(SAMPLE)
        report['bulgular'][0]['erisim_kaydi'][0]['url'] = 'not a URI'
        self.assertTrue(module.validate(report))

    def test_reference_uri_space_rejected(self):
        report = deepcopy(SAMPLE)
        report['bulgular'][0]['resmi_basvuru_url'] = 'https://www.mevzuat.gov.tr/invalid path'
        self.assertTrue(module.validate(report))

    def test_encoded_uri_accepted_without_claiming_authenticity(self):
        self.assertEqual(module.validate(with_source('https://www.mevzuat.gov.tr/example%20path')), [])

    def test_null_offline_sources_still_valid(self):
        report = json.loads((ROOT/'cite-check-tr/examples/expected-offline-report.json').read_text())
        self.assertEqual(module.validate(report), [])

    def test_missing_checker_stops_validation(self):
        with patch.dict(FormatChecker.checkers, {}, clear=True):
            with self.assertRaisesRegex(ImportError, 'biçim denetimi eksik'):
                module.validate(SAMPLE)

    def test_missing_checker_cli_is_installation_error(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';p.write_text(json.dumps(SAMPLE))
            stderr=StringIO()
            with patch.dict(FormatChecker.checkers, {}, clear=True), redirect_stderr(stderr):
                code=module.main([str(p)])
        self.assertEqual(code, 2)
        self.assertIn('requirements.txt',stderr.getvalue())
        self.assertNotIn('Traceback',stderr.getvalue())


if __name__=='__main__':
    unittest.main()
