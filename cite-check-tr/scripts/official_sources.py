#!/usr/bin/env python3
"""Restricted access to public Turkish court decision sources.

This is an optional source-access adapter, NOT an MCP server or legal verifier.
Search endpoints are based on published Yargı MCP clients and remain experimental.
All requests use verified TLS, pinned public IPs and same-host redirects only.
No local files are written and no repository/network upload is performed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, ProxyHandler, build_opener

from bs4 import BeautifulSoup
from fetch_source import AGENT, SafeRedirect, _PinnedHTTPSHandler, blocked
from network_safety import UnsafeURL, validate_url

SOURCES = {
    "yargitay": {
        "host": "karararama.yargitay.gov.tr",
        "search_page": "https://karararama.yargitay.gov.tr/",
        "search_api": "/aramadetaylist",
        "document_api": "/getDokuman",
    },
    "danistay": {
        "host": "karararama.danistay.gov.tr",
        "search_page": "https://karararama.danistay.gov.tr/",
        "search_api": "/aramalist",
        "document_api": "/getDokuman",
    },
    "aym_bireysel": {
        "host": "kararlarbilgibankasi.anayasa.gov.tr",
        "search_page": "https://kararlarbilgibankasi.anayasa.gov.tr/kbb/pages/search/BireyselBasvuru",
    },
    "aym_norm": {
        "host": "normkararlarbilgibankasi.anayasa.gov.tr",
        "search_page": "https://normkararlarbilgibankasi.anayasa.gov.tr/kbb/pages/search/NormDenetimi",
    },
}
MAX_BYTES = 2 * 1024 * 1024
MAX_EXTRACT_CHARS = 180_000
DOCUMENT_ID = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")
QUERY_LIMIT = 160


class SourceAccessError(ValueError):
    """An official source cannot safely be queried or parsed."""


class SameHostRedirect(SafeRedirect):
    """Disallow cross-host redirects, even to another otherwise official host."""

    def __init__(self, hostname):
        super().__init__(network_mode="local-dns")
        self.hostname = hostname

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if req is not None and req.get_method() == "POST":
            raise UnsafeURL("Arama POST isteğinde yönlendirme reddedildi.")
        parsed = urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname != self.hostname or parsed.port is not None:
            raise UnsafeURL("Resmî kaynak erişiminde farklı hedefe yönlendirme reddedildi.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def source_info(source):
    try:
        return SOURCES[source]
    except KeyError as exc:
        raise SourceAccessError("Desteklenmeyen resmî kaynak.") from exc


def _build_opener(host):
    # Existing fail-closed network code pins the validated IP at connect time.
    # Unlike the upstream sample, certificate verification is NEVER disabled.
    return build_opener(
        ProxyHandler({}),
        _PinnedHTTPSHandler(context=ssl.create_default_context()),
        SameHostRedirect(host),
    )


def _request(source, path, *, method="GET", payload=None, timeout=20):
    config = source_info(source)
    if method not in ("GET", "POST"):
        raise SourceAccessError("İzin verilmeyen istek yöntemi.")
    if method == "POST" and (source not in ("yargitay", "danistay")
                             or path != config["search_api"]):
        raise SourceAccessError("POST yalnızca sabit resmî arama uç noktasında kullanılabilir.")
    if not (3 <= timeout <= 30):
        raise SourceAccessError("Zaman aşımı 3–30 saniye aralığında olmalıdır.")
    if not path.startswith("/") or path.startswith("//"):
        raise SourceAccessError("Geçersiz resmî kaynak yolu.")
    url = "https://" + config["host"] + path
    if urlsplit(url).hostname != config["host"]:
        raise SourceAccessError("Resmî ana bilgisayar eşleşmiyor.")
    # In the default local-dns mode, DNS is checked here and again by the pinned connection.
    validate_url(url, network_mode="local-dns")
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"User-Agent": AGENT, "Accept": "application/json, text/html;q=0.9"}
    if data is not None:
        if len(data) > 4096:
            raise SourceAccessError("Arama isteği boyutu sınırı aşıldı.")
        headers["Content-Type"] = "application/json; charset=utf-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = Request(url, data=data, headers=headers, method=method)
    opener = _build_opener(config["host"])
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            final = urlsplit(final_url)
            if final.scheme != "https" or final.hostname != config["host"] or final.port is not None:
                raise UnsafeURL("Resmî kaynaktan farklı hedefe yönlendirme reddedildi.")
            chunks, size = [], 0
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise SourceAccessError("Resmî yanıtın 2 MiB sınırı aşıldı.")
                chunks.append(chunk)
            raw = b"".join(chunks)
            content_type = response.headers.get("Content-Type", "").lower()
            if not ("json" in content_type or "html" in content_type or
                    content_type.startswith("text/") or raw.lstrip().startswith((b"{", b"<"))):
                raise SourceAccessError("Beklenmeyen resmî yanıt içerik türü.")
            return raw, final_url, content_type
    except HTTPError as exc:
        raise SourceAccessError(f"Resmî servis HTTP {exc.code} yanıtı verdi; erişim doğrulanamadı.") from exc
    except (URLError, OSError) as exc:
        raise SourceAccessError("Resmî servise güvenli erişim sağlanamadı.") from exc


def _json(raw):
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as exc:
        raise SourceAccessError("Beklenen JSON yanıtı alınamadı; servis değişmiş olabilir.") from exc
    if not isinstance(obj, dict):
        raise SourceAccessError("Servis JSON biçimi beklenenden farklı.")
    return obj


def _safe_query(query):
    if not isinstance(query, str) or not (1 <= len(query.strip()) <= QUERY_LIMIT):
        raise SourceAccessError("Arama terimi 1–160 karakter olmalıdır.")
    if any(ord(c) < 32 for c in query):
        raise SourceAccessError("Arama teriminde kontrol karakteri olamaz.")
    return query.strip()


def _page_size(page_size):
    if type(page_size) is not int or not 1 <= page_size <= 20:
        raise SourceAccessError("En fazla 20 kayıt istenebilir.")
    return page_size


def search(source, query, *, page_size=10, timeout=20):
    """Search index only. No result is automatically 'verified'."""
    config = source_info(source)
    query = _safe_query(query)
    page_size = _page_size(page_size)
    if source.startswith("aym_"):
        # The uploaded client's legacy /Ara path is not assumed to work on
        # the current /kbb/pages/search/... site. Do not invent search results.
        return {
            "provider": source, "query": query, "search_url": config["search_page"],
            "status": "manual_search_required", "results": [],
            "legal_verification": "not_performed",
            "note": "AYM güncel arama formu manuel kullanılmalı; doğrudan bulunan karar URL'si ile document çalışır.",
        }
    if source == "yargitay":
        body = {"data": {
            "arananKelime": query, "birimYrgKurulDaire": "",
            "birimYrgHukukDaire": "", "birimYrgCezaDaire": "",
            "esasYil": "", "esasIlkSiraNo": "", "esasSonSiraNo": "",
            "kararYil": "", "kararIlkSiraNo": "", "kararSonSiraNo": "",
            "baslangicTarihi": "", "bitisTarihi": "",
            "siralama": "3", "siralamaDirection": "desc",
            "pageSize": page_size, "pageNumber": 1,
        }}
    else:
        body = {"data": {
            "andKelimeler": ['"' + query.replace('"', "") + '"'],
            "orKelimeler": [], "notAndKelimeler": [], "notOrKelimeler": [],
            "pageSize": page_size, "pageNumber": 1,
        }}
    raw, final_url, _ = _request(source, config["search_api"], method="POST",
                                 payload=body, timeout=timeout)
    obj = _json(raw)
    wrapped = obj.get("data")
    if not isinstance(wrapped, dict) or not isinstance(wrapped.get("data"), list):
        raise SourceAccessError("Karar arama yanıt şeması tanınmadı; arama tamamlanmış sayılamaz.")
    results = []
    for item in wrapped["data"][:page_size]:
        if not isinstance(item, dict):
            raise SourceAccessError("Karar arama kaydı geçersiz.")
        document_id = item.get("id")
        if not isinstance(document_id, (str, int)) or not DOCUMENT_ID.fullmatch(str(document_id)):
            raise SourceAccessError("Karar kimliği beklenenden farklı.")
        results.append({
            "id": str(document_id),
            "daire": item.get("daire") or item.get("daireKurul"),
            "esas_no": item.get("esasNo"),
            "karar_no": item.get("kararNo"),
            "karar_tarihi": item.get("kararTarihi"),
            "document_url": f"https://{config['host']}{config['document_api']}?{urlencode({'id': str(document_id)})}",
        })
    count = wrapped.get("recordsTotal")
    return {
        "provider": source, "query": query, "search_url": final_url,
        "status": "index_results_only", "results": results,
        "total_records": count if isinstance(count, int) else None,
        "legal_verification": "not_performed",
        "note": "Arama özeti veya künye hukuki iddiayı doğrulamaz; tam metin ve tarih ayrıca incelenmelidir.",
    }


def document_url(source, locator):
    config = source_info(source)
    if source in ("yargitay", "danistay"):
        if not isinstance(locator, str) or not DOCUMENT_ID.fullmatch(locator):
            raise SourceAccessError("Yargıtay/Danıştay belge kimliği geçersiz.")
        return f"https://{config['host']}{config['document_api']}?{urlencode({'id': locator})}"
    if not isinstance(locator, str) or len(locator) > 1024:
        raise SourceAccessError("AYM karar adresi geçersiz.")
    if locator.startswith("https://"):
        target = locator
    elif locator.startswith("/") and not locator.startswith("//"):
        target = urljoin("https://" + config["host"] + "/", locator)
    else:
        raise SourceAccessError("AYM için resmî tam URL veya mutlak sayfa yolu gerekir.")
    parsed = urlsplit(target)
    if (parsed.scheme != "https" or parsed.hostname != config["host"] or
            parsed.port is not None or parsed.username or parsed.password or parsed.fragment):
        raise SourceAccessError("AYM karar adresi başka bir hedefe işaret ediyor.")
    if not (parsed.path.startswith("/kbb/pages/") or
            parsed.path.startswith("/BB/") or parsed.path.startswith("/ND/")):
        raise SourceAccessError("AYM için yalnız karar bilgi bankası sayfaları kabul edilir.")
    if ".." in parsed.path or "//" in parsed.path or "\\" in parsed.path or len(parsed.query) > 512:
        raise SourceAccessError("AYM karar yolu güvenlik kontrolünden geçmedi.")
    return target


def document(source, locator, *, timeout=20):
    """Retrieve official content. 'retrieved' is NOT a legal correctness verdict."""
    url = document_url(source, locator)
    config = source_info(source)
    parsed = urlsplit(url)
    raw, final_url, kind = _request(source, parsed.path +
                                     (("?" + parsed.query) if parsed.query else ""),
                                     timeout=timeout)
    html = None
    if source == "yargitay":
        data = _json(raw).get("data")
        if not isinstance(data, str) or not data.strip():
            raise SourceAccessError("Yargıtay tam karar içeriği yanıt alanında bulunamadı.")
        html = data
    elif "html" in kind or raw.lstrip().startswith(b"<"):
        html = raw.decode("utf-8-sig", errors="replace")
    else:
        raise SourceAccessError("Karar tam metni için HTML yanıtı bekleniyordu.")
    if blocked(html):
        raise SourceAccessError("Giriş, CAPTCHA veya erişim engeli algılandı; işlem durduruldu.")
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script, style, noscript, template"):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = soup.get_text("\n", strip=True)
    if not text:
        raise SourceAccessError("Karar metni çıkarılamadı; doğrulama yapılamaz.")
    return {
        "provider": source, "document_url": final_url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "access_status": "retrieved_unverified", "legal_verification": "not_performed",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "title": title, "text": text[:MAX_EXTRACT_CHARS],
        "truncated": len(text) > MAX_EXTRACT_CHARS,
        "note": "Belge alındı, ancak kimlik/tamlık/iddia desteği/tarihsel uygunluk ayrıca kontrol edilmelidir.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=sorted(SOURCES), required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--search", metavar="QUERY")
    action.add_argument("--document", metavar="ID_OR_URL")
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        result = (search(args.source, args.search, page_size=args.page_size, timeout=args.timeout)
                  if args.search is not None else document(args.source, args.document, timeout=args.timeout))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (SourceAccessError, UnsafeURL, OSError, ValueError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
