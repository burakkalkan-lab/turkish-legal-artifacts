#!/usr/bin/env python3
"""Release integrity check; not a legal-source authenticity check."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'cite-check-tr/scripts'))
from validate_report import validate

REQUIRED = [
    'tests/test_security_v027.py',
    '.gitignore', '.github/workflows/tests.yml', 'CONTRIBUTING.md', 'tests/verify_release.py',
    'README.md', 'docs/getting-started.md', 'LICENSE', 'SECURITY.md', 'CHANGELOG.md', 'docs/testing.md', 'docs/publishing.md',
    'cite-check-tr/SKILL.md', 'cite-check-tr/PROMPT.md',
    'cite-check-tr/scripts/fetch_source.py',
    'cite-check-tr/scripts/network_safety.py',
    'cite-check-tr/scripts/validate_report.py',
    'cite-check-tr/scripts/probe_official_sources.py',
    'cite-check-tr/scripts/requirements.txt', 'cite-check-tr/scripts/README.md',
    'cite-check-tr/references/sources.md', 'cite-check-tr/references/verification.md',
    'cite-check-tr/references/privacy.md', 'cite-check-tr/assets/report-template.md',
    'cite-check-tr/assets/output-schema.json',
    'cite-check-tr/examples/synthetic-input.txt',
    'cite-check-tr/examples/expected-offline-report.json',
    'cite-check-tr/examples/live-report-2026-11-08.json',
    'tools/check_repo_hygiene.py', '.githooks/pre-commit', '.githooks/pre-push', '.gitattributes',
    '.github/dependabot.yml', '.github/PULL_REQUEST_TEMPLATE.md', '.github/ISSUE_TEMPLATE/config.yml',
    '.github/ISSUE_TEMPLATE/bug_report.yml', 'cite-check-tr/scripts/output_safety.py',
    'tests/test_security_v026.py', 'tests/test_repo_hygiene.py',
    'tests/test_fetch_source.py', 'tests/test_validate_report.py',
    'tests/test_uri_validation.py', 'tests/test_v022_regressions.py', 'tests/test_network_safety.py', 'tests/test_cli.py', 'tests/test_browser_dom.py', 'tests/test_probe_official_sources.py'
]
for name in REQUIRED:
    p = ROOT / name
    assert p.is_file(), f'Missing {name}'
    assert p.stat().st_size, f'Empty {name}'

skill = (ROOT/'cite-check-tr/SKILL.md').read_text(encoding='utf-8')
assert skill.startswith('---\nname: cite-check-tr\ndescription: ')
assert skill.count('\n---\n') >= 1
assert len(skill.splitlines()[2].removeprefix('description: ')) <= 200
schema = json.loads((ROOT/'cite-check-tr/assets/output-schema.json').read_text(encoding='utf-8'))
assert schema['properties']['rapor_surumu']['const']=='0.2.7'
assert schema['$defs']['bulgu']['properties']['durum']['enum']==[
    'dogrulandi', 'uyumsuzluk', 'dogrulanamadi', 'uzman_incelemesi'
]
from jsonschema import Draft202012Validator
Draft202012Validator.check_schema(schema)
for example in (ROOT/'cite-check-tr/examples').glob('*.json'):
    report = json.loads(example.read_text(encoding='utf-8'))
    errors = validate(report)
    assert not errors, f'{example.name}: {errors}'
    assert report['rapor_surumu']=='0.2.7'

print(f'PASS: {len(REQUIRED)} required files, frontmatter, v0.2.7 schema and example reports')
