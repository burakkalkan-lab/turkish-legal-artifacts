"""Local integration tests; no legal service availability is assumed."""
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'cite-check-tr/scripts'))
spec = importlib.util.spec_from_file_location('fetch_source', ROOT/'cite-check-tr/scripts/fetch_source.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
TEXT = 'Synthetic legal source, article 24. ' * 10


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/denied':
            self.send_response(403); self.end_headers(); return
        if self.path == '/redirect-private':
            self.send_response(302); self.send_header('Location', 'http://169.254.169.254/latest/'); self.end_headers(); return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        if self.path == '/js':
            self.wfile.write(("<html><body><div id='result'></div><script>setTimeout(()=>{document.querySelector('#result').textContent="+json.dumps(TEXT)+"},100)</script></body></html>").encode())
        elif self.path == '/form':
            self.wfile.write(("<input id='query'><button onclick=\"document.querySelector('#result').textContent=document.querySelector('#query').value\">Search</button><div id='result'></div>").encode())
        elif self.path == '/captcha':
            self.wfile.write(b'<form class="g-recaptcha">Verify you are human</form>')
        else:
            self.wfile.write(('<html><title>Kanun</title><body><main>'+TEXT+'</main><a href="/doc.pdf">PDF</a><script>do_not_extract()</script></body></html>').encode())
    def log_message(self, *args):
        pass


class FetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def setUp(self):
        # The test server deliberately runs on loopback. Bypass URL validation ONLY
        # within this fixture; production URL policy remains fail-closed.
        self.url_patch = patch.object(m, 'validate_url', side_effect=lambda url, extra_domains=(), network_mode='local-dns': url)
        self.url_patch.start()
        # Same for IP pinning: the fixture server is on loopback; production pinning stays fail-closed
        # (see tests/test_security_v026.py).
        self.pin_patch = patch.object(m, '_pinned', side_effect=lambda address, timeout=None, source_address=None:
                                      socket.create_connection(address, timeout))
        self.pin_patch.start()
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name)/'evidence'

    def tearDown(self):
        self.pin_patch.stop()
        self.url_patch.stop()
        self.temp.cleanup()

    def test_http_extraction_and_hash(self):
        result = m.fetch(self.base, self.out, engine='http')
        self.assertEqual(result['status'], 'retrieved')
        self.assertEqual(result['legal_verification'], 'not_performed')
        self.assertEqual(len(result['document']['sha256']), 64)
        text = (self.out/result['document']['text_file']).read_text()
        self.assertIn(TEXT.strip(), text)
        self.assertNotIn('do_not_extract', text)
        self.assertEqual(result['document']['links'][0]['url'], self.base+'/doc.pdf')

    def test_private_redirect_blocked_without_browser_fallback(self):
        from network_safety import validate_url as real_validate
        def local_only(url, extra_domains=(), network_mode='local-dns'):
            if url.startswith(self.base):
                return url
            return real_validate(url, extra_domains)
        with patch.object(m, 'validate_url', side_effect=local_only), patch.object(m, 'browser_fetch', side_effect=AssertionError('no browser fallback')):
            result = m.fetch(self.base+'/redirect-private', self.out)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['attempts'][0]['error_type'], 'UnsafeURL')

    def test_access_denial_does_not_retry_browser(self):
        with patch.object(m, 'browser_fetch', side_effect=AssertionError('must not bypass')):
            result = m.fetch(self.base+'/denied', self.out)
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['attempts'][0]['http_status'], 403)

    def test_captcha_not_legal_text(self):
        result = m.fetch(self.base+'/captcha', self.out)
        self.assertEqual(result['status'], 'blocked')

    def test_optional_login_does_not_block_public_content(self):
        html = '<title>Mevzuat Bilgi Sistemi</title><main>' + TEXT + '</main><div hidden><input type="password"></div>'
        self.assertFalse(m.blocked(html))
        self.assertFalse(m.blocked(html + '<div class="modal fade"><div class="g-recaptcha"></div></div>'))
        self.assertTrue(m.blocked('<title>Oturum Aç</title><input type="password">'))

    def test_timeout_is_logged_and_fallback_retains_attempt(self):
        with patch.object(m, 'http_fetch', side_effect=TimeoutError), patch.object(m, 'browser_fetch', return_value=(('<body>'+TEXT+'</body>').encode(), self.base, 'text/html', 200)):
            result = m.fetch(self.base, self.out)
        self.assertEqual(result['status'], 'retrieved')
        self.assertEqual(result['attempts'][0]['error_type'], 'TimeoutError')
        self.assertEqual(len(result['attempts']), 2)

    def test_report_attachment_keeps_legal_result(self):
        result = m.fetch(self.base, self.out, engine='http')
        output = Path(self.temp.name)/'report.json'
        m.attach_report(ROOT/'cite-check-tr/examples/expected-offline-report.json', 'A2', result, output)
        report = json.loads(output.read_text())
        from jsonschema import Draft202012Validator, FormatChecker
        from validate_report import validate
        schema = json.loads((ROOT/'cite-check-tr/assets/output-schema.json').read_text())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(report)
        self.assertEqual(validate(report), [])
        finding = report['bulgular'][1]
        self.assertEqual(finding['durum'], 'dogrulanamadi')
        self.assertIsNone(finding['kaynak_url'])
        self.assertEqual(finding['erisim_kaydi'][-1]['sonuc'], 'icerik_alindi')

    def test_image_only_pdf_needs_ocr(self):
        from pypdf import PdfWriter
        w = PdfWriter(); w.add_blank_page(width=200, height=200)
        buf = BytesIO(); w.write(buf)
        with patch.object(m, 'http_fetch', return_value=(buf.getvalue(), self.base, 'application/pdf', 200)):
            result = m.fetch(self.base, self.out, engine='http')
        self.assertEqual(result['status'], 'needs_ocr')

    def test_pdf_text_extraction(self):
        # Minimal self-contained PDF with a text stream; no reportlab dependency.
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        w = PdfWriter(); page = w.add_blank_page(width=300, height=300)
        font = DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):w._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 10 200 Td (Article 24 test) Tj ET')
        page[NameObject('/Contents')] = w._add_object(stream)
        buf=BytesIO();w.write(buf)
        doc=m.extract(buf.getvalue(), self.base, 'application/pdf')
        self.assertIn('Article 24 test', doc['text'])
        self.assertFalse(doc['needs_ocr'])

    def test_existing_evidence_not_overwritten(self):
        self.out.mkdir()
        with self.assertRaises(FileExistsError):
            m.fetch(self.base, self.out)

    @unittest.skipUnless(os.environ.get('CITE_CHECK_TEST_BROWSER') == '1', 'Set CITE_CHECK_TEST_BROWSER=1 for real browser integration')
    def test_real_browser_javascript_fallback(self):
        result = m.fetch(self.base+'/js', self.out, selector='#result')
        self.assertEqual(result['status'], 'retrieved')
        self.assertEqual([a['engine'] for a in result['attempts']], ['http', 'browser'])
        self.assertIn(TEXT.strip(), (self.out/result['document']['text_file']).read_text())

    @unittest.skipUnless(os.environ.get('CITE_CHECK_TEST_BROWSER') == '1', 'Set CITE_CHECK_TEST_BROWSER=1 for real browser integration')
    def test_real_browser_search_form(self):
        result = m.fetch(self.base+'/form', self.out, selector='#result', actions=[
            {'action':'fill','selector':'#query','value':TEXT},
            {'action':'click','selector':'button'},
            {'action':'wait_for','selector':'#result'}])
        self.assertEqual(result['status'], 'retrieved')
        self.assertIn(TEXT.strip(), (self.out/result['document']['text_file']).read_text())


if __name__ == '__main__':
    unittest.main()
