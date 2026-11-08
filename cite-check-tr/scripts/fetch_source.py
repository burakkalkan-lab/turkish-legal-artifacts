#!/usr/bin/env python3
"""Retrieve public legal sources; never equate extraction with legal verification."""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import http.client
import json
import os
from pathlib import Path
import re
import socket
import ssl
import sys
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import (Request, build_opener, HTTPRedirectHandler, HTTPHandler, HTTPSHandler,
                            ProxyHandler)
from urllib.error import HTTPError

MAX_BYTES = 20 * 1024 * 1024
MAX_PDF_PAGES = 500
MAX_TEXT_CHARS = 5_000_000
VERSION = '0.2.7'
AGENT = f'CiteCheckTR/{VERSION} (public legal source reader)'
from network_safety import validate_url, UnsafeURL, trusted_proxy_for, pinned_create_connection
from output_safety import ensure_safe_output, make_private_dir

# Blocks WebSocket and WebRTC in the browser engine: neither is covered by request routing.
BROWSER_HARDENING_JS = (
    "for (const n of ['WebSocket','RTCPeerConnection','webkitRTCPeerConnection','WebTransport']) {"
    "try { Object.defineProperty(window, n, {value: undefined, configurable: false}); } catch (e) {} }"
)


class SafeRedirect(HTTPRedirectHandler):
    def __init__(self, extra_domains=(), network_mode='local-dns'):
        super().__init__()
        self.extra_domains = extra_domains
        self.network_mode = network_mode

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.extra_domains, self.network_mode)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _pinned(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    # Looked up at call time so tests can substitute it; production always validates the IP.
    return pinned_create_connection(address, timeout, source_address)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _pinned


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _pinned


class _PinnedHTTPHandler(HTTPHandler):
    def http_open(self, req):
        return self.do_open(_PinnedHTTPConnection, req)


class _PinnedHTTPSHandler(HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PinnedHTTPSConnection, req, context=self._context)


def build_safe_opener(extra_domains=(), network_mode='local-dns'):
    redirect = SafeRedirect(extra_domains, network_mode)
    if network_mode == 'trusted-proxy':
        return build_opener(redirect)  # inherited, validated proxy; it must enforce IP policy
    # local-dns: direct connections only, to IPs validated at connect time. Proxy variables are ignored.
    return build_opener(ProxyHandler({}), _PinnedHTTPHandler(),
                        _PinnedHTTPSHandler(context=ssl.create_default_context()), redirect)


def http_fetch(url, timeout, extra_domains=(), network_mode='local-dns'):
    validate_url(url, extra_domains, network_mode)
    opener = build_safe_opener(extra_domains, network_mode)  # Never disable TLS checks.
    with opener.open(Request(url, headers={'User-Agent': AGENT}), timeout=timeout) as response:
        validate_url(response.url, extra_domains, network_mode)
        chunks, size, started = [], 0, time.monotonic()
        while True:
            chunk = response.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError('20 MiB indirme sınırı aşıldı.')
            if time.monotonic() - started > timeout:
                raise TimeoutError('İndirme süresi aşıldı.')
            chunks.append(chunk)
        return b''.join(chunks), response.url, response.headers.get('Content-Type', ''), response.status


def browser_fetch(url, timeout, actions, selector, extra_domains=(), network_mode='local-dns'):
    validate_url(url, extra_domains, network_mode)
    from playwright.sync_api import sync_playwright
    from urllib.request import getproxies, proxy_bypass
    options = {'headless': True}
    if os.environ.get('CITE_CHECK_BROWSER_PATH'):
        options['executable_path'] = os.environ['CITE_CHECK_BROWSER_PATH']
    proxy = None
    if network_mode == 'trusted-proxy':  # local-dns mode never inherits proxy variables
        proxy = getproxies().get(urlsplit(url).scheme)
        if proxy and not proxy_bypass(urlsplit(url).hostname):
            options['proxy'] = {'server': proxy}
    with sync_playwright() as pw:
        with pw.chromium.launch(**options) as browser:
            context = browser.new_context(user_agent=AGENT, accept_downloads=False, service_workers='block')

            # Block requests from scripts, redirects, iframes and third-party assets.
            def guard(route):
                try:
                    validate_url(route.request.url, extra_domains, network_mode)
                    if network_mode == 'trusted-proxy' and trusted_proxy_for(route.request.url) != proxy:
                        raise UnsafeURL('Tarayıcı isteği seçilmiş proxy ile eşleşmiyor.')
                except ValueError:
                    route.abort(error_code='blockedbyclient')
                else:
                    route.continue_()

            context.route('**/*', guard)
            context.add_init_script(BROWSER_HARDENING_JS)
            if hasattr(context, 'route_web_socket'):
                context.route_web_socket('**/*', lambda ws: ws.close())
            page = context.new_page()
            page.set_default_timeout(timeout * 1000)
            response = page.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)
            status = response.status if response else 0
            if status >= 400:
                raise HTTPError(url, status, 'Tarayıcı HTTP hatası', {}, None)
            initial = page.content()
            if blocked(initial):
                raise PermissionError('Erişim kontrolü / CAPTCHA sayfası; otomasyon durduruldu.')
            for action in actions:
                op = action['action']
                if op == 'fill':
                    page.locator(action['selector']).fill(action['value'])
                elif op == 'click':
                    page.locator(action['selector']).click()
                elif op == 'wait_for':
                    page.locator(action['selector']).first.wait_for(state='visible')
                elif op == 'select':
                    page.locator(action['selector']).select_option(action['value'])
            if selector:
                page.locator(selector).first.wait_for(state='visible')
            validate_url(page.url, extra_domains, network_mode)
            content = page.content().encode('utf-8')
            if blocked(content.decode('utf-8', errors='ignore')):
                raise PermissionError('Erişim kontrolü / CAPTCHA sayfası; otomasyon durduruldu.')
            if len(content) > MAX_BYTES:
                raise ValueError('20 MiB sayfa sınırı aşıldı.')
            return content, page.url, 'text/html; charset=utf-8', status


def blocked(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(' ', strip=True).casefold()
    login_gate = bool(soup.select('input[type="password"]')) and len(text) < 1200 and any(
        term in (soup.title.get_text().casefold() if soup.title else '')
        for term in ('sign in', 'log in', 'login', 'oturum aç', 'giriş'))
    def hidden(node):
        for el in [node, *node.parents]:
            if not hasattr(el, 'get'):
                continue
            classes = el.get('class', [])
            style = el.get('style', '').replace(' ', '').lower()
            if el.has_attr('hidden') or el.get('aria-hidden') == 'true' or 'display:none' in style:
                return True
            if 'modal' in classes and 'show' not in classes and 'in' not in classes:
                return True
        return False
    challenges = [node for node in soup.select('.g-recaptcha, .h-captcha, #challenge-form') if not hidden(node)]
    # Phrase heuristics apply to short pages only, so long legal texts that merely quote them pass.
    phrase_hit = len(text) < 2000 and any(
        phrase in text for phrase in ('verify you are human', 'insan olduğunuzu doğrulayın', 'access denied'))
    return login_gate or bool(challenges) or phrase_hit


def extract(data, url, content_type, selector=None):
    if data.startswith(b'%PDF') or 'application/pdf' in content_type:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise PermissionError('Şifreli PDF; otomatik açma denenmedi.')
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError(f'PDF {MAX_PDF_PAGES} sayfa sınırını aşıyor.')
        pages, total = [], 0
        for page in reader.pages:
            page_text = page.extract_text() or ''
            total += len(page_text)
            if total > MAX_TEXT_CHARS:
                raise ValueError('PDF metin çıkarma sınırı aşıldı.')
            pages.append(page_text)
        return {'title': str((reader.metadata or {}).get('/Title', '')), 'text': '\n\n'.join(
            f'[Sayfa {i+1}]\n{txt}' for i, txt in enumerate(pages)), 'links': [],
            'format': 'pdf', 'needs_ocr': not any(t.strip() for t in pages), 'blocked': False}
    if not ('html' in content_type or content_type.startswith('text/') or data.lstrip().startswith(b'<')):
        raise ValueError('Desteklenmeyen içerik türü: ' + content_type)
    from bs4 import BeautifulSoup
    encoding = re.search(r'charset=([^;\s]+)', content_type, re.I)
    soup = BeautifulSoup(data, 'html.parser', from_encoding=encoding.group(1).strip('"') if encoding else None)
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    is_blocked = blocked(str(soup))
    nodes = soup.select(selector) if selector else [soup.body or soup]
    if not nodes:
        raise ValueError('İçerik seçicisi sayfada bulunamadı: ' + selector)
    links = []
    for a in soup.select('a[href]'):
        target = urljoin(url, a['href'])
        if urlsplit(target).scheme in ('http', 'https'):
            links.append({'text': a.get_text(' ', strip=True), 'url': target})
    for tag in soup.select('script, style, noscript, template'):
        tag.decompose()
    text = '\n'.join(n.get_text('\n', strip=True) for n in nodes)
    return {'title': title, 'text': text, 'links': links, 'format': 'html', 'needs_ocr': False, 'blocked': is_blocked}


def read_actions(path):
    if not path:
        return []
    actions = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(actions, list) or len(actions) > 20:
        raise ValueError('Eylemler en fazla 20 öğelik liste olmalı.')
    for a in actions:
        if not isinstance(a, dict) or a.get('action') not in ('fill', 'click', 'wait_for', 'select'):
            raise ValueError('Desteklenmeyen tarayıcı eylemi.')
        if not isinstance(a.get('selector'), str) or not a['selector']:
            raise ValueError('Her eylem için selector gerekli.')
        if a['action'] in ('fill', 'select') and not isinstance(a.get('value'), str):
            raise ValueError('fill/select için value gerekli.')
    return actions


def fetch(url, output, engine='auto', timeout=20, selector=None, actions=None, extra_domains=(), network_mode='local-dns'):
    actions = actions or []
    output = ensure_safe_output(output, is_dir=True)  # refuses non-ignored Git work trees
    make_private_dir(output)  # Never overwrite a previous evidence bundle; owner-only permissions.
    result = {'module_version': VERSION, 'network_mode': network_mode, 'requested_url': url, 'final_url': None,
              'retrieved_at': None, 'status': 'error', 'legal_verification': 'not_performed',
              'attempts': [], 'document': None}
    try:
        validate_url(url, extra_domains, network_mode)
    except (ValueError, OSError) as exc:
        result['status'] = 'blocked'
        result['attempts'].append({'url': url, 'at': datetime.now(timezone.utc).isoformat(),
            'engine': 'preflight', 'result': 'blocked', 'http_status': None,
            'error_type': type(exc).__name__, 'error_code': getattr(exc, 'code', 'preflight_failed'),
            'detail': (str(exc) if isinstance(exc, UnsafeURL) else 'URL/DNS/proxy ön kontrolü reddedildi.') + ' HTTP isteği yapılmadı.'})
        (output / 'evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return result
    engines = ['http', 'browser'] if engine == 'auto' else [engine]
    if actions:
        engines = ['browser']
    for method in engines:
        stamp = datetime.now(timezone.utc).isoformat()
        attempt = {'url': url, 'at': stamp, 'engine': method, 'result': 'error', 'http_status': None}
        result['attempts'].append(attempt)
        try:
            data, final, content_type, status = (http_fetch(url, timeout, extra_domains, network_mode) if method == 'http'
                else browser_fetch(url, timeout, actions, selector, extra_domains, network_mode))
            validate_url(final, extra_domains, network_mode)
            attempt.update(http_status=status, final_url=final)
            doc = extract(data, final, content_type, selector)
            attempt['result'] = 'blocked' if doc['blocked'] else 'retrieved'
            result.update(final_url=final, retrieved_at=stamp)
            suffix = 'pdf' if doc['format'] == 'pdf' else 'html'
            raw_name = f'{method}-source.{suffix}'
            text_name = f'{method}-text.txt'
            (output / raw_name).write_bytes(data)
            (output / text_name).write_text(doc.pop('text'), encoding='utf-8')
            doc.update(raw_file=raw_name, text_file=text_name, sha256=hashlib.sha256(data).hexdigest())
            result['document'] = doc
            if doc['blocked']:
                result['status'] = 'blocked'
                break
            text = (output / text_name).read_text(encoding='utf-8')
            if doc['needs_ocr']:
                result['status'] = 'needs_ocr'
                break
            if not text.strip() or (method == 'http' and doc['format'] == 'html' and len(text.strip()) < 120):
                attempt['result'] = 'insufficient_content'
                result['status'] = 'insufficient_content'
                continue
            result['status'] = 'retrieved'
            break
        except Exception as exc:
            # Do not serialize exception messages that might contain proxy credentials.
            attempt['error_type'] = type(exc).__name__
            attempt['error_code'] = getattr(exc, 'code', None)
            attempt['detail'] = 'İndirme/tarayıcı/metin çıkarma tamamlanamadı; hata türüne ve HTTP koduna bakın.'
            if isinstance(exc, HTTPError):
                attempt['http_status'] = exc.code
                if exc.code in (401, 403, 429):
                    result['status'] = 'blocked'
                    break
            if isinstance(exc, (PermissionError, UnsafeURL)):
                result['status'] = 'blocked'
                break
    (output / 'evidence.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


def attach_report(report_path, finding_id, evidence, output):
    """Append real access attempts, preserving all legal judgments for human/model review."""
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    finding = next((b for b in report['bulgular'] if b['id'] == finding_id), None)
    if finding is None:
        raise ValueError('Bulgu kimliği raporda yok: ' + finding_id)
    if report['erisim_modu'] == 'cevrimdisi':
        report['erisim_modu'] = 'karma'
    for a in evidence['attempts']:
        successful = a['result'] == 'retrieved'
        finding.setdefault('erisim_kaydi', []).append({
            'url': a.get('final_url', a['url']), 'tarih': a['at'][:10],
            # Download success is deliberately not labelled tam_metin until reviewed.
            'sonuc': 'icerik_alindi' if successful else 'erisim_hatasi',
            'aciklama': f"{a['engine']}: {a['result']}; HTTP={a['http_status']}; hata={a.get('error_type', 'yok')}. "
                        'Kimlik, iddia desteği ve metin bütünlüğü ayrıca incelenmelidir.'})
    output = ensure_safe_output(output, is_dir=False)
    with Path(output).open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('url')
    p.add_argument('--output', required=True, help='Yeni kanıt klasörü (var olmamalı)')
    p.add_argument('--engine', choices=['auto', 'http', 'browser'], default='auto')
    p.add_argument('--timeout', type=int, default=20, help='İstek/eylem başına saniye')
    p.add_argument('--selector', help='İlgili metnin CSS seçicisi; tarayıcı bu öğeyi bekler')
    p.add_argument('--actions', help='Yerel JSON: fill/click/wait_for/select eylemleri')
    p.add_argument('--network-mode', choices=['local-dns', 'trusted-proxy'], default='local-dns',
                   help='trusted-proxy: yalnızca hedef DNS/IP denetimi yapan güvenilir çıkış proxy’si için; otomatik seçilmez')
    p.add_argument('--allow-domain', action='append', default=[], help='Ek izin verilen kamuya açık TAM ana bilgisayar adı; alt alan adları için "*.örnek.org" (birden fazla olabilir). Kod barındırma/yapıştırma hizmetleri her zaman engelli.')
    p.add_argument('--report', help='Erişim kaydı eklenecek JSON raporu')
    p.add_argument('--finding', help='Rapordaki bulgu kimliği, ör. A2')
    p.add_argument('--report-output', help='Yeni rapor yolu (var olmamalı)')
    args = p.parse_args()
    if not 1 <= args.timeout <= 120:
        p.error('--timeout 1–120 arasında olmalı')
    if any([args.report, args.finding, args.report_output]) and not all([args.report, args.finding, args.report_output]):
        p.error('--report, --finding ve --report-output birlikte kullanılmalı')
    if args.actions and args.engine == 'http':
        p.error('--actions için auto veya browser seçin')
    try:
        result = fetch(args.url, args.output, args.engine, args.timeout, args.selector, read_actions(args.actions), args.allow_domain, args.network_mode)
        if args.report:
            attach_report(args.report, args.finding, result, args.report_output)
        print(json.dumps({'status': result['status'], 'evidence': str(Path(args.output)/'evidence.json'),
                          'legal_verification': result['legal_verification']}, ensure_ascii=False))
        return 0 if result['status'] == 'retrieved' else 2
    except (ValueError, OSError, KeyError) as exc:
        print(f'Girdi/çıktı hatası: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
