#!/usr/bin/env python3
"""Structural + cross-field checks for Cite Check TR reports.

IMPORTANT: This verifies internal consistency only. It cannot prove that a citation,
URL, legal proposition or copied quotation is authentic or legally correct.
"""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from network_safety import is_official_host

SCHEMA = Path(__file__).resolve().parents[1] / 'assets' / 'output-schema.json'


def semantic_errors(report):
    errors = []
    findings = report.get('bulgular', [])
    if any(not isinstance(f, dict) for f in findings):
        return ['bulgular içindeki her öğe nesne olmalıdır.']
    all_attempts = [a for f in findings for a in f.get('erisim_kaydi', []) if isinstance(a,dict)]
    statuses = {a.get('sonuc') for a in all_attempts}
    mode = report.get('erisim_modu')

    if mode == 'cevrimdisi' and any(a.get('sonuc') != 'cevrimdisi_test' for a in all_attempts):
        errors.append('cevrimdisi modunda gerçek erişim kaydı bulunamaz.')
    if mode != 'cevrimdisi' and statuses == {'cevrimdisi_test'}:
        errors.append('Canlı raporda yalnızca çevrimdışı test kayıtları bulunuyor.')
    if mode == 'resmi_tam_metin' and any(not any(a.get('sonuc') == 'tam_metin' for a in f.get('erisim_kaydi', [])) for f in findings):
        errors.append('resmi_tam_metin modunda tüm bulgularda tam metin erişimi kaydı gerekir.')
    if mode in ('yalnizca_kunye', 'erisim_basarisiz') and ('tam_metin' in statuses or 'icerik_alindi' in statuses):
        errors.append(f'{mode} modunda tam metin veya işlenmemiş içerik bulundu.')
    if mode == 'erisim_basarisiz' and not statuses.intersection({'erisim_hatasi', 'arac_yok', 'sonuc_yok'}):
        errors.append('erisim_basarisiz modunda bir erişim başarısızlığı kaydı gerekir.')

    seen = set()
    for finding in findings:
        fid = finding.get('id', '?')
        if fid in seen:
            errors.append(f'{fid}: tekrarlanan bulgu kimliği.')
        seen.add(fid)
        state = finding.get('durum')
        direct_url = finding.get('kaynak_url')
        date = finding.get('kaynak_erisim_tarihi')
        entries = finding.get('erisim_kaydi', [])
        if state in ('dogrulandi', 'uyumsuzluk'):
            try:
                host = (urlsplit(direct_url).hostname or '').lower() if isinstance(direct_url,str) else ''
            except ValueError:
                host = ''
            if not is_official_host(host):
                errors.append(f'{fid}: doğrulandı/uyumsuzluk birincil kaynak için izin listesindeki resmî ana bilgisayarlardan biri gerekir.')
            matches = [a for a in entries if a.get('sonuc') == 'tam_metin'
                       and a.get('url') == direct_url and a.get('tarih') == date]
            if not matches:
                errors.append(f'{fid}: tam metin erişim kaydının URL ve tarihi, sunulan kanıtla eşleşmiyor.')
            if not finding.get('kanit_alintisi') or not finding.get('kanit_konumu'):
                errors.append(f'{fid}: doğrudan alıntı ve metin içi kanıt konumu gerekir.')
            if mode == 'cevrimdisi':
                errors.append(f'{fid}: çevrimdışı bulgu doğrulanmış veya uyumsuz olarak işaretlenemez.')
        for source_name, link in [('kaynak_url',direct_url), ('resmi_basvuru_url',finding.get('resmi_basvuru_url'))]:
            if link is not None:
                try:
                    parsed = urlsplit(link)
                    parsed.port
                except ValueError:
                    errors.append(f'{fid}: {source_name} URL biçimi geçersiz.')
                    continue
                if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
                    errors.append(f'{fid}: {source_name} geçerli kimlik bilgisiz HTTP(S) URL olmalıdır.')
        if direct_url is not None and not date:
            errors.append(f'{fid}: kaynak_url var ama kaynak_erisim_tarihi yok.')
        if date and direct_url is None:
            errors.append(f'{fid}: kaynak_erisim_tarihi var ama kaynak_url yok.')
    return errors


def validate(report):
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads(SCHEMA.read_text(encoding='utf-8'))
    checker = FormatChecker()
    missing = {'uri', 'date'} - checker.checkers.keys()
    if missing:
        raise ImportError(
            'Zorunlu biçim denetimi eksik: ' + ', '.join(sorted(missing)) +
            '. python -m pip install -r cite-check-tr/scripts/requirements.txt komutunu çalıştırın.'
        )
    validator = Draft202012Validator(schema, format_checker=checker)
    structural = [f'{"/".join(map(str,e.absolute_path)) or "root"}: {e.message}'
                  for e in sorted(validator.iter_errors(report), key=lambda e: str(e.absolute_path))]
    # A malformed root should not crash the semantic validator.
    if structural:
        return structural
    if not isinstance(report, dict) or not isinstance(report.get('bulgular'), list):
        return structural
    return structural + semantic_errors(report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', help='Rapor JSON dosyası')
    args = parser.parse_args(argv)
    try:
        report = json.loads(Path(args.report).read_text(encoding='utf-8'))
        errors = validate(report)
    except (OSError, json.JSONDecodeError, ImportError) as exc:
        print(f'HATA: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2
    if errors:
        for err in errors:
            print('HATA: '+err, file=sys.stderr)
        return 1
    print('GEÇTİ: Şema ve çapraz alan tutarlılığı geçerli; gerçek hukuki doğruluk ayrıca denetlenmelidir.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
