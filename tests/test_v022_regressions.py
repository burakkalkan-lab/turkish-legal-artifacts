"""Regressions reproduced during the v0.2.1 review."""
from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'cite-check-tr/scripts'))
from validate_report import validate
from network_safety import validate_url, UnsafeURL
import fetch_source as m

SAMPLE = json.loads((ROOT/'cite-check-tr/examples/expected-offline-report.json').read_text(encoding='utf-8'))
URL = 'https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6098.pdf'
PROXY_ENV = {'https_proxy': 'http://trusted-proxy.example:8080', 'http_proxy': 'http://trusted-proxy.example:8080'}


class RegressionTests(unittest.TestCase):
    def test_malformed_nested_report_returns_errors(self):
        for field, value in [('erisim_kaydi', None), ('erisim_kaydi', [None]), ('kaynak_url', 123),
                             ('kaynak_url', 'https://[bad'), ('id', []), ('kanit_alintisi', {})]:
            with self.subTest(field=field, value=value):
                report = deepcopy(SAMPLE)
                report['bulgular'][0][field] = value
                self.assertTrue(validate(report))

    def test_malformed_report_cli_no_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            report = deepcopy(SAMPLE)
            report['bulgular'][0]['erisim_kaydi'] = None
            p = Path(d)/'invalid.json'; p.write_text(json.dumps(report))
            run = subprocess.run([sys.executable, str(ROOT/'cite-check-tr/scripts/validate_report.py'),str(p)],capture_output=True,text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn('HATA:', run.stderr)
        self.assertNotIn('Traceback', run.stderr)

    def test_dns_preflight_writes_evidence_without_network(self):
        with tempfile.TemporaryDirectory() as d, patch('network_safety.socket.getaddrinfo', side_effect=socket.gaierror()), patch.object(m,'http_fetch') as http, patch.object(m,'browser_fetch') as browser:
            result = m.fetch(URL, Path(d)/'evidence')
            saved = json.loads((Path(d)/'evidence/evidence.json').read_text(encoding='utf-8'))
            self.assertEqual(saved, result)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['attempts'][0]['engine'], 'preflight')
            self.assertEqual(result['attempts'][0]['error_code'], 'dns_resolution_failed')
            self.assertTrue(result['attempts'][0]['at'])
            http.assert_not_called(); browser.assert_not_called()
            source = Path(d)/'report.json'; source.write_text(json.dumps(SAMPLE))
            attached = Path(d)/'attached.json'
            m.attach_report(source,'A2',result,attached)
            self.assertEqual(validate(json.loads(attached.read_text(encoding='utf-8'))), [])

    def test_trusted_proxy_skips_only_local_dns(self):
        with patch.dict(os.environ, PROXY_ENV, clear=True), patch('network_safety.socket.getaddrinfo', side_effect=AssertionError('local DNS must not run')):
            self.assertEqual(validate_url(URL, network_mode='trusted-proxy'), URL)
            for bad in ['http://127.0.0.1/', 'https://localhost/', 'https://mevzuat.gov.tr.evil.org/', 'file:///etc/passwd', 'https://www.mevzuat.gov.tr:9000/']:
                with self.subTest(url=bad), self.assertRaises(UnsafeURL):
                    validate_url(bad, network_mode='trusted-proxy')

    def test_proxy_mode_is_never_implicit(self):
        with patch.dict(os.environ, PROXY_ENV, clear=True), patch('network_safety.socket.getaddrinfo', side_effect=socket.gaierror()):
            with self.assertRaises(UnsafeURL):
                validate_url(URL)

    def test_missing_proxy_and_no_proxy_reject(self):
        for env in [{}, {**PROXY_ENV,'no_proxy':'*'}, {**PROXY_ENV,'no_proxy':'.mevzuat.gov.tr'}, {'https_proxy':'http://user:secret@proxy.example:8080'}]:
            with self.subTest(env_keys=list(env)), patch.dict(os.environ,env,clear=True):
                with self.assertRaises(UnsafeURL):
                    validate_url(URL, network_mode='trusted-proxy')

    def test_port_specific_no_proxy_rejects(self):
        with patch.dict(os.environ,{**PROXY_ENV,'no_proxy':'www.mevzuat.gov.tr:443'},clear=True):
            with self.assertRaises(UnsafeURL):
                validate_url('https://www.mevzuat.gov.tr:443/doc',network_mode='trusted-proxy')

    def test_no_direct_fallback_when_proxy_missing(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{},clear=True), patch.object(m,'http_fetch') as http, patch.object(m,'browser_fetch') as browser:
            result = m.fetch(URL,Path(d)/'out',network_mode='trusted-proxy')
            self.assertEqual(result['attempts'][0]['error_code'], 'proxy_required')
            http.assert_not_called(); browser.assert_not_called()

    def test_proxy_mode_still_checks_redirects(self):
        from urllib.request import Request
        with patch.dict(os.environ,PROXY_ENV,clear=True):
            redirect=m.SafeRedirect(network_mode='trusted-proxy')
            with self.assertRaises(UnsafeURL):
                redirect.redirect_request(Request(URL),None,302,'Found',{},'http://169.254.169.254/')

    def test_fetch_propagates_proxy_mode(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,PROXY_ENV,clear=True), patch('network_safety.socket.getaddrinfo',side_effect=AssertionError('no local DNS')), patch.object(m,'http_fetch',return_value=(b'<html><body>'+b'public legal document '*20+b'</body></html>',URL,'text/html',200)) as http:
            result=m.fetch(URL,Path(d)/'out',network_mode='trusted-proxy')
            self.assertEqual(result['status'],'retrieved')
            self.assertEqual(http.call_args.args[-1],'trusted-proxy')
            self.assertEqual(result['network_mode'],'trusted-proxy')


if __name__ == '__main__':
    unittest.main()
