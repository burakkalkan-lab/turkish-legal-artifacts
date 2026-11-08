"""Tests for tools/check_repo_hygiene.py. Fake secrets are assembled at runtime so this file stays clean."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import check_repo_hygiene as h


def make_tckn(first9='123456789'):
    d = [int(c) for c in first9]
    d10 = (((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10)
    d.append(d10)
    d.append(sum(d) % 10)
    return ''.join(map(str, d))


class HygieneTests(unittest.TestCase):
    def run_on(self, name, content):
        with tempfile.TemporaryDirectory() as d, patch.object(h, 'ROOT', Path(d)):
            path = Path(d) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return h.check_file(Path(name))

    def test_clean_file_passes(self):
        self.assertEqual(self.run_on('docs/a.md', 'Sentetik metin. Madde 24.\n'), [])

    def test_forbidden_paths_blocked(self):
        for name in ['evidence/x/evidence.json', 'a/private/b.txt', 'http-source.html', '.env', 'k.pem', 'run.log', 'client-data/a.txt']:
            with self.subTest(name=name):
                self.assertTrue(self.run_on(name, 'x'), name)
        self.assertEqual(self.run_on('.env.example', 'KEY=\n'), [])

    def test_secrets_detected_without_echoing_value(self):
        token = 'gh' + 'p_' + 'A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8'
        errors = self.run_on('a.py', f'x = "{token}"\n')
        self.assertTrue(errors)
        self.assertNotIn(token, ' '.join(errors))
        key = 'sk' + '-ant-' + 'abcdefghijklmnopqrstuvwx1234'
        self.assertTrue(self.run_on('b.txt', f'ANTHROPIC={key}\n'))
        self.assertTrue(self.run_on('c.txt', 'password = "' + 'x9Y8z7W6v5U4t3S2r1' + '"\n'))
        self.assertTrue(self.run_on('d.txt', '-----BEGIN ' + 'PRIVATE KEY-----\n'))

    def test_valid_tckn_detected_random_number_not(self):
        self.assertTrue(h.valid_tckn(make_tckn()))
        self.assertTrue(self.run_on('t.txt', f'Müvekkil no {make_tckn()}\n'))
        self.assertEqual(self.run_on('t.txt', 'Dosya 12345678901 ve 2024/123 E.\n'), [])

    def test_whole_repository_is_clean(self):
        files = h.tree_files()
        self.assertTrue(files)
        errors = [e for rel in files for e in h.check_file(rel)]
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
