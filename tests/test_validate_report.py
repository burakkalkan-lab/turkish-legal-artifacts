"""Fail-closed schema AND cross-field evidence tests."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cite-check-tr/scripts'))
from validate_report import validate

SAMPLE=json.loads((ROOT/'cite-check-tr/examples/expected-offline-report.json').read_text(encoding='utf-8'))


def live_report():
    result=deepcopy(SAMPLE)
    result['erisim_modu']='karma'
    finding=result['bulgular'][0]
    finding.update(durum='dogrulandi', kimlik_duzeyi='tam_metin',
                   kaynak_url='https://karararama.yargitay.gov.tr/karar/123',
                   kaynak_erisim_tarihi='2026-11-08', kanit_konumu='Paragraf 5',
                   kanit_alintisi='Kısa, sentetik örnek kanıt ibaresi')
    finding['erisim_kaydi'].append({'url':finding['kaynak_url'], 'tarih':'2026-11-08',
                                  'sonuc':'tam_metin','aciklama':'Sentetik tam metin karşılaştırma örneği'})
    return result


class ReportValidationTests(unittest.TestCase):
    def test_human_review_cannot_be_disabled(self):
        report=deepcopy(SAMPLE)
        report["uzman_onayi_gerekli"]=False
        self.assertTrue(validate(report))

    def test_offline_sample_valid(self):
        self.assertEqual(validate(SAMPLE), [])

    def test_live_sample_valid(self):
        report=json.loads((ROOT/'cite-check-tr/examples/live-report-2026-11-08.json').read_text())
        self.assertEqual(validate(report), [])

    def test_intentional_synthetic_positive_valid_structurally(self):
        self.assertEqual(validate(live_report()), [])

    def test_error_only_log_cannot_be_verified(self):
        report=live_report()
        report['bulgular'][0]['erisim_kaydi'][-1]['sonuc']='erisim_hatasi'
        self.assertTrue(validate(report))

    def test_download_only_log_cannot_be_verified(self):
        report=live_report()
        report['bulgular'][0]['erisim_kaydi'][-1]['sonuc']='icerik_alindi'
        self.assertTrue(validate(report))

    def test_mismatched_source_url_cannot_be_verified(self):
        report=live_report()
        report['bulgular'][0]['kaynak_url']='https://karararama.yargitay.gov.tr/karar/other'
        self.assertTrue(validate(report))

    def test_mismatched_date_cannot_be_verified(self):
        report=live_report()
        report['bulgular'][0]['kaynak_erisim_tarihi']='2026-11-07'
        self.assertTrue(validate(report))

    def test_missing_quote_rejected(self):
        report=live_report()
        report['bulgular'][0]['kanit_alintisi']=None
        self.assertTrue(validate(report))

    def test_inconsistent_mode_rejected(self):
        report=live_report()
        report['erisim_modu']='erisim_basarisiz'
        self.assertTrue(validate(report))

    def test_duplicate_finding_ids_rejected(self):
        report=live_report()
        report['bulgular'][1]['id']=report['bulgular'][0]['id']
        self.assertTrue(validate(report))

    def test_inaccurate_offline_verification_rejected(self):
        report=live_report()
        report['erisim_modu']='cevrimdisi'
        self.assertTrue(validate(report))

    def test_mismatch_requires_reliable_text(self):
        report=live_report()
        report['bulgular'][0]['durum']='uyumsuzluk'
        report['bulgular'][0]['erisim_kaydi'][-1]['sonuc']='erisim_hatasi'
        self.assertTrue(validate(report))


if __name__ == '__main__':
    unittest.main()
