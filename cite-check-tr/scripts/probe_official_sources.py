#!/usr/bin/env python3
"""Opt-in, one-request-per-site availability probe; NEVER legal citation verification."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from fetch_source import fetch
from output_safety import DEFAULT_EVIDENCE_DIR, ensure_safe_output

SOURCES = {
    'mevzuat': 'https://www.mevzuat.gov.tr/',
    'yargitay': 'https://karararama.yargitay.gov.tr/',
    'danistay': 'https://karararama.danistay.gov.tr/',
}


def probe(selection, output, timeout=8, network_mode='local-dns'):
    """Fetch only selected official starting pages; store attempts separately."""
    output = ensure_safe_output(output, is_dir=True)  # never inside a non-ignored Git work tree
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    results = []
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    for name in selection:
        target = output / (f'{stamp}-{name}')
        try:
            evidence = fetch(SOURCES[name], target, engine='http', timeout=timeout, network_mode=network_mode)
            results.append({'source':name,'url':SOURCES[name],
                            'status':evidence['status'],
                            'legal_verification':'not_performed',
                            'evidence':str(target/'evidence.json')})
        except (ValueError, OSError) as exc:
            # Never expose detailed URL errors from an outbound proxy.
            results.append({'source':name,'url':SOURCES[name], 'status':'error',
                            'legal_verification':'not_performed',
                            'error_type':type(exc).__name__})
    return results


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-live', action='store_true', help='Canlı resmî sitelere istek göndermeyi açıkça onayla')
    parser.add_argument('--source', action='append', choices=tuple(SOURCES), help='Belirtilmezse üçü de kontrol edilir')
    parser.add_argument('--output', default=str(DEFAULT_EVIDENCE_DIR), help='Yeni kanıt alt klasörleri oluşturulacak dizin (varsayılan: depo dışı kullanıcı klasörü)')
    parser.add_argument('--network-mode', choices=['local-dns', 'trusted-proxy'], default='local-dns')
    parser.add_argument('--timeout', type=int, default=8)
    args=parser.parse_args(argv)
    if not args.confirm_live:
        parser.error('Canlı ağ isteği için --confirm-live zorunludur.')
    if args.timeout < 1 or args.timeout > 30:
        parser.error('--timeout 1–30 arasında olmalı.')
    try:
        result=probe(list(dict.fromkeys(args.source or SOURCES.keys())), args.output, args.timeout, args.network_mode)
    except (ValueError, OSError) as exc:
        print(f'Girdi/çıktı hatası: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if all(a['status']=='retrieved' for a in result) else 2


if __name__=='__main__':
    sys.exit(main())
