"""Fail-closed URL checks for the optional public legal source reader.

Security model (v0.2.7):
* Only explicitly listed official HOSTS (not whole domains) are allowed by default.
* Code-hosting, paste and webhook services are always denied, even with --allow-domain,
  so retrieved or user material can never be routed to a repository or paste service.
* In ``local-dns`` mode the DNS answer is validated and then PINNED: the socket is opened
  to the validated IP (see ``pinned_create_connection``), which closes the DNS-rebinding
  gap between "check" and "connect" for the HTTP client. The browser engine cannot be
  pinned this way; run it without internal-network access for untrusted inputs.
"""
import ipaddress
import socket
from urllib.parse import urlsplit
from urllib.request import getproxies, proxy_bypass


class UnsafeURL(ValueError):
    """URL target violates public-source security policy."""

    def __init__(self, message, code="unsafe_url"):
        super().__init__(message)
        self.code = code


# Exact hosts. A sibling or newly created sub-domain is NOT trusted automatically.
OFFICIAL_HOSTS = frozenset({
    'mevzuat.gov.tr', 'www.mevzuat.gov.tr',
    'resmigazete.gov.tr', 'www.resmigazete.gov.tr',
    'yargitay.gov.tr', 'www.yargitay.gov.tr', 'karararama.yargitay.gov.tr',
    'danistay.gov.tr', 'www.danistay.gov.tr', 'karararama.danistay.gov.tr',
    'anayasa.gov.tr', 'www.anayasa.gov.tr',
    'kararlarbilgibankasi.anayasa.gov.tr', 'normkararlarbilgibankasi.anayasa.gov.tr',
    'kvkk.gov.tr', 'www.kvkk.gov.tr',
    'tbmm.gov.tr', 'www.tbmm.gov.tr', 'cdn.tbmm.gov.tr',
})

# Always denied (suffix match), even when passed to --allow-domain.
BLOCKED_DOMAINS = frozenset({
    'github.com', 'githubusercontent.com', 'githubassets.com', 'github.io',
    'gitlab.com', 'bitbucket.org', 'codeberg.org', 'sourcehut.org',
    'pastebin.com', 'paste.ee', 'hastebin.com', 'ghostbin.co', 'rentry.co',
    'transfer.sh', 'file.io', 'anonfiles.com', 'webhook.site', 'requestbin.com',
    'pipedream.net', 'ngrok.io', 'ngrok-free.app', 'trycloudflare.com',
    'discord.com', 'discordapp.com', 't.me', 'telegram.org',
})


def _clean_domain(value):
    if not isinstance(value, str) or not value or any(c in value for c in '/:@?\\# '):
        raise UnsafeURL('İzin verilen alan adı geçersiz.')
    try:
        host = value.rstrip('.').encode('idna').decode('ascii').lower()
    except (UnicodeError, ValueError) as exc:
        raise UnsafeURL('Geçersiz alan adı.') from exc
    if not host or '..' in host or any(not ch.isalnum() and ch != '-' for label in host.split('.') for ch in label):
        raise UnsafeURL('Geçersiz alan adı karakteri.')
    return host


def _parse_allowed(value):
    """Return (host, include_subdomains). '*.example.org' opts in to sub-domains explicitly."""
    if isinstance(value, str) and value.startswith('*.'):
        return _clean_domain(value[2:]), True
    return _clean_domain(value), False


def is_blocked_host(host):
    return any(host == d or host.endswith('.' + d) for d in BLOCKED_DOMAINS)


def is_official_host(host):
    return isinstance(host, str) and host.lower().rstrip('.') in OFFICIAL_HOSTS


def trusted_proxy_for(url):
    """Require an inherited proxy; trust must be explicitly selected by the caller.

    In this mode the deployment's trusted egress proxy, NOT this process,
    must resolve targets and reject private/reserved destinations.
    """
    parsed = urlsplit(url)
    proxy = getproxies().get(parsed.scheme)
    if not proxy or proxy_bypass(parsed.hostname) or proxy_bypass(parsed.netloc):
        raise UnsafeURL('Güvenilir proxy modu: proxy eksik veya NO_PROXY hedefi dışlıyor.', code='proxy_required')
    try:
        config = urlsplit(proxy)
        config.port
    except ValueError as exc:
        raise UnsafeURL('Geçersiz proxy yapılandırması.') from exc
    if config.scheme not in ('http', 'https') or not config.hostname or config.username or config.password:
        raise UnsafeURL('Proxy, kimlik bilgisi içermeyen HTTP(S) adresi olmalıdır.')
    if config.path not in ('', '/') or config.query or config.fragment:
        raise UnsafeURL('Proxy adresi yol, sorgu veya fragment içeremez.')
    return proxy


def _is_global(ip_text):
    ip = ipaddress.ip_address(ip_text.split('%', 1)[0])
    mapped = getattr(ip, 'ipv4_mapped', None)
    if mapped is not None:
        ip = mapped
    return ip.is_global


def resolve_global(host, port):
    """Resolve once; every A/AAAA answer must be globally routable. Returns the IP list."""
    try:
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise UnsafeURL('Alan adı güvenli biçimde çözümlenemedi.', code='dns_resolution_failed') from exc
    ips = []
    for answer in answers:
        ip = answer[4][0]
        if not _is_global(ip):
            raise UnsafeURL('Özel, yerel veya genel internete yönlendirilemeyen DNS adresi engellendi.')
        if ip not in ips:
            ips.append(ip)
    if not ips:
        raise UnsafeURL('Alan adı için adres bulunamadı.', code='dns_resolution_failed')
    return ips


def pinned_create_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
    """Drop-in for socket.create_connection that connects ONLY to validated global IPs.

    Resolution and validation happen here, immediately before connecting, so a hostile DNS
    server cannot answer "public" for the check and "private" for the connection.
    TLS still verifies the certificate against the original host name (SNI is unchanged).
    """
    host, port = address
    last_error = None
    for ip in resolve_global(host, port):
        try:
            return socket.create_connection((ip, port), timeout, source_address)
        except OSError as exc:
            last_error = exc
    raise last_error or OSError('Bağlantı kurulamadı.')


def validate_url(url, extra_domains=(), network_mode='local-dns'):
    """Require HTTP(S), an official/explicitly allowed host and global DNS answers.

    local-dns checks all A/AAAA records; any non-global answer rejects.
    trusted-proxy delegates resolution/IP enforcement to an explicitly trusted proxy.
    Only conventional web ports are allowed (80 and 443).
    ``extra_domains`` entries match one exact host; use '*.example.org' for sub-domains.
    """
    if network_mode not in ('local-dns', 'trusted-proxy'):
        raise UnsafeURL('Bilinmeyen ağ modu.')
    if not isinstance(url, str) or any(ord(c) < 32 for c in url):
        raise UnsafeURL('Geçersiz URL.')
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURL('Geçersiz URL alanı veya port.') from exc
    if parsed.scheme not in ('http', 'https') or not hostname or parsed.username or parsed.password:
        raise UnsafeURL('Yalnızca kimlik bilgisi içermeyen HTTP(S) URL kullanın.')
    if port is not None and port not in (80, 443):
        raise UnsafeURL('Güvenlik nedeniyle yalnızca 80 ve 443 portları kullanılabilir.')
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        host = _clean_domain(hostname)
    else:
        raise UnsafeURL('Doğrudan IP adresine istek kabul edilmez.')
    if host.endswith(('.localhost', '.local', '.internal', '.onion', '.test', '.invalid')) or host in ('localhost', 'local'):
        raise UnsafeURL('Yerel veya dahili alan adları engellendi.')
    if is_blocked_host(host):
        raise UnsafeURL('Kod barındırma, yapıştırma ve webhook hizmetleri her zaman engellidir.', code='blocked_domain')
    allowed = is_official_host(host)
    if not allowed:
        for entry in extra_domains:
            domain, include_sub = _parse_allowed(entry)
            if is_blocked_host(domain):
                raise UnsafeURL('Kod barındırma, yapıştırma ve webhook hizmetleri her zaman engellidir.', code='blocked_domain')
            if host == domain or (include_sub and host.endswith('.' + domain)):
                allowed = True
    if not allowed:
        raise UnsafeURL('Alan adı izin listesinde değil. Kamuya açık farklı bir kaynak için --allow-domain '
                        'ile tam ana bilgisayar adını verin (alt alan adları için "*.örnek.org").')
    if network_mode == 'trusted-proxy':
        trusted_proxy_for(url)
        return url
    resolve_global(host, port or (443 if parsed.scheme == 'https' else 80))
    return url
