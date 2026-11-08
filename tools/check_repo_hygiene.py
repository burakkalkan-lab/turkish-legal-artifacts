#!/usr/bin/env python3
"""Repository hygiene gate: blocks secrets, personal data and evidence files from being committed.

Usage:
  python tools/check_repo_hygiene.py --staged    # entire Git index (pre-commit hook)
  python tools/check_repo_hygiene.py --tracked   # committed HEAD tree (CI)
  python tools/check_repo_hygiene.py --pre-push  # hook stdin; all outgoing reachable history
  python tools/check_repo_hygiene.py --tree      # every file under the project root (no Git needed)

Findings never print the matched value, only file, line and rule. Exit code 1 on any error.
This is a safety net, not a guarantee: review `git diff --cached` before you commit.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404 - fixed read-only git listing commands
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules'}
MAX_SCAN_BYTES = 2 * 1024 * 1024

FORBIDDEN_PATHS = [
    (re.compile(r'(^|/)evidence(/|$)'), 'kanıt klasörü'),
    (re.compile(r'(^|/)(private|confidential|client-data)(/|$)'), 'özel/müvekkil klasörü'),
    (re.compile(r'(^|/)(http|browser)-(source\.(html|pdf)|text\.txt)$'), 'indirilmiş ham kaynak/metin'),
    (re.compile(r'(^|/)evidence\.json$'), 'erişim kanıt günlüğü'),
    (re.compile(r'(^|/)\.env(\..*)?$'), '.env dosyası'),
    (re.compile(r'\.(pem|key|p12|pfx|jks|keystore|sqlite3?|db)$', re.I), 'anahtar/veritabanı dosyası'),
    (re.compile(r'\.(log)$', re.I), 'günlük dosyası'),
    (re.compile(r'(^|/)(\.cite-check-tr)(/|$)'), 'kullanıcı veri klasörü'),
]
FORBIDDEN_ALLOW = {'.env.example'}

SECRET_RULES = [
    ('GitHub token', re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b')),
    ('GitHub fine-grained token', re.compile(r'\bgithub_pat_[A-Za-z0-9_]{40,}\b')),
    ('Anthropic/OpenAI tarzı anahtar', re.compile(r'\bsk-(?:ant-)?[A-Za-z0-9_-]{24,}\b')),
    ('AWS erişim anahtarı', re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('Google API anahtarı', re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b')),
    ('Slack token', re.compile(r'\bxox[baprs]-[0-9A-Za-z-]{10,}\b')),
    ('Özel anahtar bloğu', re.compile(r'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----')),
    ('URL içinde kimlik bilgisi', re.compile(r'https?://(?!user:)[^/\s:@]+:[^/\s:@]{3,}@[^/\s]+')),
    ('Bearer/Authorization değeri', re.compile(r'(?i)\bauthorization\s*[:=]\s*[\'"]?(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{16,}')),
    ('Atanmış gizli değer', re.compile(r'(?i)\b(?:api[_-]?key|secret|token|passwd|password)\b\s*[:=]\s*[\'"][A-Za-z0-9_\-./+=]{16,}[\'"]')),
    ('TR IBAN', re.compile(r'\bTR\d{2}(?:\s?\d{4}){5}\s?\d{2}\b')),
]
TCKN = re.compile(r'(?<!\d)([1-9]\d{10})(?!\d)')


def valid_tckn(value):
    d = [int(c) for c in value]
    return (len(d) == 11 and d[0] != 0 and (((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10) == d[9]
            and sum(d[:10]) % 10 == d[10])


def git_run(*args):
    git = shutil.which('git')
    if not git:
        raise OSError('git bulunamadı')
    return subprocess.run(
        [git, *args], cwd=ROOT, capture_output=True, check=True, timeout=30,
        env={**os.environ, 'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}
    ).stdout


def index_entries():
    for record in git_run('ls-files', '--stage', '-z').split(b'\0'):
        if not record:
            continue
        header, name = record.split(b'\t', 1)
        mode, oid, stage = header.decode('ascii').split()
        if stage != '0':
            raise ValueError('Çözümlenmemiş index çatışması')
        yield Path(os.fsdecode(name)), mode, oid


def commit_entries(commit):
    for record in git_run('ls-tree', '-r', '-z', '--full-tree', commit).split(b'\0'):
        if not record:
            continue
        header, name = record.split(b'\t', 1)
        mode, kind, oid = header.decode('ascii').split()
        yield Path(os.fsdecode(name)), mode, oid


def push_commits(stream):
    # Scan ALL reachable history, also on new branches and force pushes. No remote trust
    # or fetch is needed. A secret removed in a later commit still blocks publication.
    if git_run('rev-parse', '--is-shallow-repository').strip() != b'false':
        raise ValueError('Sığ depo geçmişi tamamen denetlenemiyor')
    tips = []
    for line in stream:
        fields = line.split()
        if len(fields) != 4:
            raise ValueError('Geçersiz pre-push girdisi')
        _, local_oid, _, remote_oid = fields
        if not all(re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', x) for x in (local_oid, remote_oid)):
            raise ValueError('Geçersiz Git nesne kimliği')
        if set(local_oid) == {'0'}:
            continue  # branch/tag deletion sends no content
        # Commit tags are supported; blob/tree tags fail closed.
        tips.append(git_run('rev-parse', '--verify', local_oid + '^{commit}').decode().strip())
    if not tips:
        return []
    return git_run('rev-list', *tips).decode('ascii').splitlines()


def check_object(rel, mode, oid):
    if mode not in ('100644', '100755'):
        return [f'{rel.as_posix()!r}: sembolik bağ/alt modül desteklenmiyor']
    if int(git_run('cat-file', '-s', oid)) > MAX_SCAN_BYTES:
        return [f'{rel.as_posix()!r}: içerik tarama sınırını aşıyor']
    return check_content(rel, git_run('cat-file', 'blob', oid))


def tree_files():
    return [p.relative_to(ROOT) for p in ROOT.rglob('*')
            if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS)]


def check_file(rel):
    path = ROOT / rel
    if path.is_symlink() or path.stat().st_size > MAX_SCAN_BYTES:
        return [f'{rel.as_posix()!r}: dosya güvenli biçimde taranamıyor']
    return check_content(rel, path.read_bytes())


def check_content(rel, data):
    errors = []
    posix = repr(rel.as_posix())
    if rel.name not in FORBIDDEN_ALLOW:
        for pattern, label in FORBIDDEN_PATHS:
            if pattern.search(rel.as_posix()):
                errors.append(f'{posix}: yasak dosya türü ({label})')
    try:
        text = data.decode('utf-8')
        if '\x00' in text:
            raise ValueError('binary')
    except (UnicodeDecodeError, ValueError):
        return errors + [f'{posix}: UTF-8 metin olarak taranamıyor']
    for number, line in enumerate(text.splitlines(), 1):
        for label, rule in SECRET_RULES:
            if rule.search(line):
                errors.append(f'{posix}:{number}: olası gizli bilgi ({label})')
        for match in TCKN.finditer(line):
            if valid_tckn(match.group(1)):
                errors.append(f'{posix}:{number}: geçerli TCKN biçiminde 11 haneli sayı')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--staged', action='store_true')
    group.add_argument('--tracked', action='store_true')
    group.add_argument('--tree', action='store_true')
    group.add_argument('--pre-push', action='store_true')
    args = parser.parse_args(argv)
    count = 0
    errors = []
    try:
        if args.tree:
            files = tree_files()
            count = len(files)
            errors = [e for rel in files for e in check_file(rel)]
        else:
            if args.staged:
                entries = index_entries()
            elif args.pre_push:
                entries = (entry for commit in push_commits(sys.stdin) for entry in commit_entries(commit))
            else:
                head = git_run('rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
                entries = commit_entries(head)
            seen = set()
            for rel, mode, oid in entries:
                key = (rel.as_posix(), mode, oid)
                if key in seen:
                    continue
                seen.add(key)
                count += 1
                errors.extend(check_object(rel, mode, oid))
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f'HATA: Git içeriği tamamen denetlenemedi ({type(exc).__name__}); işlem reddedildi.', file=sys.stderr)
        return 2
    if errors:
        print('HATA: depoya gönderilmemesi gereken içerik bulundu (değerler gösterilmez):', file=sys.stderr)
        for e in errors:
            print('  - ' + e, file=sys.stderr)
        print('Dosyayı sahneden çıkarın (git restore --staged <dosya>), gizli değeri döndürün/silin ve '
              'gerekiyorsa .gitignore’a ekleyin.', file=sys.stderr)
        return 1
    print(f'GEÇTİ: {count} dosya sürümünde yasak dosya türü, gizli bilgi veya geçerli TCKN bulunmadı.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
