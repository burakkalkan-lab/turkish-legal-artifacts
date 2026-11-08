"""v0.2.7 security regressions: IP pinning, exact hosts, blocklist, output guard, browser hardening."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cite-check-tr/scripts'))
import fetch_source as m
import network_safety as ns
from output_safety import ensure_safe_output, UnsafeOutput
from validate_report import validate


def dns_for(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))]


class HostPolicyTests(unittest.TestCase):
    def test_official_hosts_are_exact_not_wildcard(self):
        with patch('network_safety.socket.getaddrinfo', return_value=dns_for('8.8.8.8')):
            self.assertTrue(ns.validate_url('https://cdn.tbmm.gov.tr/x'))
            self.assertTrue(ns.validate_url('https://kararlarbilgibankasi.anayasa.gov.tr/kbb/'))
            for bad in ['https://yeni-alt.tbmm.gov.tr/', 'https://x.mevzuat.gov.tr/', 'https://evil.gov.tr/']:
                with self.subTest(url=bad), self.assertRaises(ns.UnsafeURL):
                    ns.validate_url(bad)

    def test_extra_domain_is_exact_unless_wildcard_requested(self):
        with patch('network_safety.socket.getaddrinfo', return_value=dns_for('8.8.8.8')):
            self.assertTrue(ns.validate_url('https://example.org/a', ['example.org']))
            with self.assertRaises(ns.UnsafeURL):
                ns.validate_url('https://sub.example.org/a', ['example.org'])
            self.assertTrue(ns.validate_url('https://sub.example.org/a', ['*.example.org']))

    def test_code_hosting_and_paste_services_always_blocked(self):
        with patch('network_safety.socket.getaddrinfo', return_value=dns_for('8.8.8.8')):
            for url in ['https://github.com/x/y', 'https://raw.githubusercontent.com/x', 'https://gist.github.com/x',
                        'https://gitlab.com/x', 'https://pastebin.com/raw/x', 'https://webhook.site/x']:
                for extra in ([], ['github.com', 'githubusercontent.com', '*.github.com', 'pastebin.com', 'gitlab.com', 'webhook.site']):
                    with self.subTest(url=url, extra=bool(extra)), self.assertRaises(ns.UnsafeURL) as cm:
                        ns.validate_url(url, extra)
                    if extra:
                        self.assertEqual(cm.exception.code, 'blocked_domain')

    def test_ipv4_mapped_ipv6_loopback_blocked(self):
        answers = [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::ffff:127.0.0.1', 443, 0, 0))]
        with patch('network_safety.socket.getaddrinfo', return_value=answers), self.assertRaises(ns.UnsafeURL):
            ns.resolve_global('www.mevzuat.gov.tr', 443)

    def test_validator_requires_exact_official_host_for_verified_findings(self):
        import json
        report = json.loads((ROOT / 'cite-check-tr/examples/live-report-2026-11-08.json').read_text(encoding='utf-8'))
        self.assertEqual(validate(report), [])
        report['bulgular'][1]['kaynak_url'] = report['bulgular'][1]['kaynak_url'].replace('cdn.tbmm.gov.tr', 'evil.tbmm.gov.tr')
        self.assertTrue(any('resmî ana bilgisayar' in e for e in validate(report)))


class PinnedConnectionTests(unittest.TestCase):
    def test_rebinding_blocked_at_connect_time(self):
        # Preflight sees a public IP; the connection-time lookup is answered with loopback.
        answers = iter([dns_for('8.8.8.8'), dns_for('127.0.0.1'), dns_for('127.0.0.1')])
        with patch('network_safety.socket.getaddrinfo', side_effect=lambda *a, **k: next(answers)):
            ns.validate_url('https://www.mevzuat.gov.tr/')
            with patch('network_safety.socket.create_connection') as connect, self.assertRaises(ns.UnsafeURL):
                ns.pinned_create_connection(('www.mevzuat.gov.tr', 443))
            connect.assert_not_called()

    def test_connects_only_to_validated_ip(self):
        with patch('network_safety.socket.getaddrinfo', return_value=dns_for('93.184.216.34')), \
                patch('network_safety.socket.create_connection', return_value='SOCK') as connect:
            self.assertEqual(ns.pinned_create_connection(('www.mevzuat.gov.tr', 443), 5), 'SOCK')
        self.assertEqual(connect.call_args.args[0], ('93.184.216.34', 443))

    def test_real_http_fetch_refuses_loopback_server(self):
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b'reached')
            def log_message(self, *a): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), H)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/'
            # Bypass only the URL preflight; the connection layer must still refuse loopback.
            with patch.object(m, 'validate_url', side_effect=lambda u, e=(), n='local-dns': u):
                with self.assertRaises(Exception) as cm:
                    m.http_fetch(url, 3)
            self.assertIn('UnsafeURL', repr(cm.exception) + type(cm.exception).__name__ + repr(getattr(cm.exception, 'reason', '')))
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_local_dns_mode_ignores_proxy_environment(self):
        env = {'https_proxy': 'http://proxy.example:8080', 'http_proxy': 'http://proxy.example:8080'}
        with patch.dict(os.environ, env, clear=True):
            opener = m.build_safe_opener(network_mode='local-dns')
        proxies = [h for h in opener.handlers if h.__class__.__name__ == 'ProxyHandler']
        self.assertTrue(all(h.proxies == {} for h in proxies))
        self.assertTrue(any(isinstance(h, m._PinnedHTTPSHandler) for h in opener.handlers))


class BrowserHardeningTests(unittest.TestCase):
    def test_websocket_and_webrtc_blocked_and_no_proxy_in_local_dns(self):
        playwright = MagicMock()
        browser = playwright.chromium.launch.return_value.__enter__.return_value
        context = browser.new_context.return_value
        page = context.new_page.return_value
        page.goto.return_value.status = 200
        page.content.return_value = '<html><body>' + 'Kanun metni ' * 40 + '</body></html>'
        page.url = 'https://www.mevzuat.gov.tr/'
        manager = MagicMock(); manager.__enter__.return_value = playwright
        env = {'https_proxy': 'http://proxy.example:8080'}
        with patch.dict(os.environ, env, clear=True), \
                patch('playwright.sync_api.sync_playwright', return_value=manager), \
                patch.object(m, 'validate_url', side_effect=lambda u, e=(), n='local-dns': u):
            m.browser_fetch('https://www.mevzuat.gov.tr/', 5, [], None)
        context.route_web_socket.assert_called_once()
        init_script = context.add_init_script.call_args.args[0]
        for name in ('WebSocket', 'RTCPeerConnection', 'WebTransport'):
            self.assertIn(name, init_script)
        self.assertNotIn('proxy', playwright.chromium.launch.call_args.kwargs)


class HeuristicAndLimitTests(unittest.TestCase):
    def test_long_legal_text_quoting_access_denied_is_not_blocked(self):
        html = '<title>Karar</title><main>' + ('Gerekçe metni. ' * 200) + ' "access denied" ifadesi tırnak içinde geçer.</main>'
        self.assertFalse(m.blocked(html))
        self.assertTrue(m.blocked('<title>x</title><p>Access Denied</p>'))

    def test_pdf_page_limit(self):
        from io import BytesIO
        from pypdf import PdfWriter
        writer = PdfWriter()
        for _ in range(3):
            writer.add_blank_page(width=100, height=100)
        buf = BytesIO(); writer.write(buf)
        with patch.object(m, 'MAX_PDF_PAGES', 2), self.assertRaises(ValueError):
            m.extract(buf.getvalue(), 'https://www.mevzuat.gov.tr/', 'application/pdf')


class OutputGuardTests(unittest.TestCase):
    def setUp(self):
        if not shutil.which('git'):
            self.skipTest('git yok')
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        shutil.copy(ROOT / '.gitignore', self.repo / '.gitignore')

    def tearDown(self):
        self.temp.cleanup()

    def test_refuses_non_ignored_path_inside_repo(self):
        with self.assertRaises(UnsafeOutput):
            ensure_safe_output(self.repo / 'rapor-klasoru')
        with self.assertRaises(UnsafeOutput):
            ensure_safe_output(self.repo / 'rapor.json', is_dir=False)

    def test_allows_ignored_path_and_paths_outside_repo(self):
        ensure_safe_output(self.repo / 'evidence' / 'a')
        ensure_safe_output(Path(self.temp.name) / 'disarida')

    def test_fetch_refuses_repo_output_without_any_network(self):
        with patch.object(m, 'http_fetch') as http, patch.object(m, 'browser_fetch') as browser:
            with self.assertRaises(UnsafeOutput):
                m.fetch('https://www.mevzuat.gov.tr/', self.repo / 'sonuc')
            http.assert_not_called(); browser.assert_not_called()
        self.assertFalse((self.repo / 'sonuc').exists())

    def test_attach_report_refuses_repo_output(self):
        evidence = {'attempts': []}
        with self.assertRaises(UnsafeOutput):
            m.attach_report(ROOT / 'cite-check-tr/examples/expected-offline-report.json', 'A2', evidence, self.repo / 'r.json')

    @unittest.skipIf(os.name == 'nt', 'POSIX izinleri')
    def test_evidence_dir_is_owner_only(self):
        from output_safety import make_private_dir
        d = Path(self.temp.name) / 'private-dir'
        make_private_dir(d)
        self.assertEqual(d.stat().st_mode & 0o777, 0o700)


class NoRepositoryTransferTests(unittest.TestCase):
    def test_scripts_never_push_or_talk_to_code_hosts(self):
        scripts = ROOT / 'cite-check-tr/scripts'
        for path in scripts.glob('*.py'):
            text = path.read_text(encoding='utf-8')
            for forbidden in ('git push', "'push'", '"push"', "'commit'", "'add'", "'remote'"):
                self.assertNotIn(forbidden, text, f'{path.name}: {forbidden}')
            if path.name != 'network_safety.py':  # the deny-list itself names these hosts
                for host in ('github.com', 'githubusercontent', 'gist.', 'gitlab.com'):
                    self.assertNotIn(host, text, f'{path.name}: {host}')
        guard = (scripts / 'output_safety.py').read_text(encoding='utf-8')
        self.assertEqual(guard.count('subprocess.run('), 1)
        self.assertIn('check-ignore', guard)


if __name__ == '__main__':
    unittest.main()
