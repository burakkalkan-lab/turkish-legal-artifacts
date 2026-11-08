"""Real Git regressions for immutable scans and tracked-output protection."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'cite-check-tr/scripts')]
import check_repo_hygiene as h
from output_safety import ensure_safe_output, UnsafeOutput


@unittest.skipUnless(shutil.which('git'), 'git required')
class GitSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.secret = 'gh' + 'p_' + 'A' * 36

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                              capture_output=True).stdout.decode().strip()

    def write(self, text, name='sample.txt'):
        p = self.repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def scan(self, mode, stdin=''):
        output = io.StringIO()
        with patch.object(h, 'ROOT', self.repo), patch('sys.stdin', io.StringIO(stdin)), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = h.main([mode])
        self.assertNotIn(self.secret, output.getvalue())
        return result

    def commit(self, text):
        self.write(text)
        self.git('add', '.')
        self.git('commit', '-qm', 'Synthetic fixture')
        return self.git('rev-parse', 'HEAD')

    def push_input(self, oid, old=None):
        return f'refs/heads/main {oid} refs/heads/main {old or "0" * 40}\n'

    def test_staged_secret_cannot_hide_behind_clean_worktree(self):
        self.write(self.secret)
        self.git('add', 'sample.txt')
        self.write('clean')
        self.assertEqual(self.scan('--staged'), 1)

    def test_staged_secret_cannot_hide_behind_deleted_worktree(self):
        self.write(self.secret)
        self.git('add', 'sample.txt')
        (self.repo / 'sample.txt').unlink()
        self.assertEqual(self.scan('--staged'), 1)

    def test_unstaged_secret_does_not_change_clean_index(self):
        self.write('clean'); self.git('add', '.')
        self.write(self.secret)
        self.assertEqual(self.scan('--staged'), 0)

    def test_head_scan_ignores_clean_worktree_and_index(self):
        self.commit(self.secret)
        self.write('clean'); self.git('add', '.')
        self.assertEqual(self.scan('--tracked'), 1)

    def test_push_detects_secret_in_cleaned_history(self):
        self.commit(self.secret)
        oid = self.commit('clean')
        self.assertEqual(self.scan('--pre-push', self.push_input(oid)), 1)

    def test_force_push_also_scans_all_reachable_history(self):
        old = self.commit('old')
        self.commit(self.secret)
        oid = self.commit('clean')
        self.assertEqual(self.scan('--pre-push', self.push_input(oid, old)), 1)

    def test_clean_push_and_deletion_pass(self):
        oid = self.commit('clean')
        self.assertEqual(self.scan('--pre-push', self.push_input(oid)), 0)
        self.assertEqual(self.scan('--pre-push', self.push_input('0' * 40, oid)), 0)

    def test_tag_to_commit_history_checked(self):
        oid = self.commit(self.secret)
        self.git('tag', '-a', 'v-test', '-m', 'test')
        tag = self.git('rev-parse', 'v-test')
        self.assertEqual(self.scan('--pre-push', self.push_input(tag)), 1)

    def test_missing_object_and_malformed_input_fail_closed(self):
        self.commit('clean')
        self.assertEqual(self.scan('--pre-push', self.push_input('f' * 40)), 2)
        self.assertEqual(self.scan('--pre-push', 'invalid\n'), 2)

    def test_blob_tag_fails_closed(self):
        self.commit('clean')
        blob = self.git('rev-parse', 'HEAD:sample.txt')
        self.assertEqual(self.scan('--pre-push', self.push_input(blob)), 2)

    def test_binary_and_oversized_blobs_are_not_silently_skipped(self):
        (self.repo / 'sample.txt').write_bytes(b'\x00binary')
        self.git('add', '.')
        self.assertEqual(self.scan('--staged'), 1)
        self.write('12345'); self.git('add', '.')
        with patch.object(h, 'MAX_SCAN_BYTES', 4):
            self.assertEqual(self.scan('--staged'), 1)

    def test_tracked_then_ignored_deleted_file_is_rejected(self):
        p = self.write('old')
        self.git('add', 'sample.txt')
        self.write('sample.txt\n', '.gitignore'); p.unlink()
        with self.assertRaises(UnsafeOutput):
            ensure_safe_output(p, is_dir=False)

    def test_staged_deletion_of_committed_path_is_rejected(self):
        self.commit('old')
        self.git('rm', '-q', 'sample.txt')
        self.write('sample.txt\n', '.gitignore')
        with self.assertRaises(UnsafeOutput):
            ensure_safe_output(self.repo / 'sample.txt', is_dir=False)

    def test_ignored_directory_with_tracked_children_is_rejected(self):
        p = self.write('old', 'reports/a.txt'); self.git('add', '.')
        self.write('reports/\n', '.gitignore'); p.unlink(); p.parent.rmdir()
        with self.assertRaises(UnsafeOutput):
            ensure_safe_output(p.parent)

    def test_new_ignored_output_still_allowed(self):
        self.write('reports/\n', '.gitignore')
        self.assertEqual(ensure_safe_output(self.repo / 'reports/new'), self.repo / 'reports/new')

    def test_git_failure_does_not_allow_output(self):
        self.write('reports/\n', '.gitignore')
        with patch('output_safety.subprocess.run', side_effect=subprocess.TimeoutExpired('git', 15)):
            with self.assertRaises(UnsafeOutput):
                ensure_safe_output(self.repo / 'reports/new')

    def test_literal_special_filename_cannot_bypass_tracking(self):
        p = self.write('old', '[draft].txt'); self.git('add', '.')
        self.write('*.txt\n', '.gitignore'); p.unlink()
        with self.assertRaises(UnsafeOutput):
            ensure_safe_output(p, is_dir=False)

    def test_unmerged_index_fails_closed(self):
        self.commit('base')
        original = self.git('branch', '--show-current')
        self.git('checkout', '-qb', 'side'); self.commit('side')
        self.git('checkout', '-q', original); self.commit('main')
        result = subprocess.run(['git', '-C', str(self.repo), 'merge', 'side'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.scan('--staged'), 2)

    def test_shallow_history_fails_closed(self):
        oid = self.commit('clean')
        (self.repo / '.git/shallow').write_text(oid + '\n')
        self.assertEqual(self.scan('--pre-push', self.push_input(oid)), 2)

    @unittest.skipIf(os.name == 'nt', 'POSIX shell hook integration')
    def test_real_precommit_hook_reads_index(self):
        self.install_hooks()
        self.write(self.secret); self.git('add', 'sample.txt'); self.write('clean')
        result = subprocess.run(['git', '-C', str(self.repo), 'commit', '-qm', 'blocked'],
                                capture_output=True, env={**os.environ, 'PYTHON': sys.executable})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(self.secret.encode(), result.stderr)
        self.assertNotEqual(subprocess.run(['git', '-C', str(self.repo), 'rev-parse', '--verify', 'HEAD'],
                                          capture_output=True).returncode, 0)

    @unittest.skipIf(os.name == 'nt', 'POSIX shell hook integration')
    def test_real_prepush_blocks_history_before_local_remote_receives_it(self):
        self.commit(self.secret); self.commit('clean')
        self.install_hooks()
        remote = Path(self.tmp.name) / 'remote.git'
        subprocess.run(['git', 'init', '--bare', '-q', str(remote)], check=True)
        result = subprocess.run(['git', '-C', str(self.repo), 'push', str(remote), 'HEAD:refs/heads/main'],
                                capture_output=True, env={**os.environ, 'PYTHON': sys.executable})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(self.secret.encode(), result.stderr)
        refs = subprocess.run(['git', '-C', str(remote), 'show-ref'], capture_output=True)
        self.assertEqual(refs.stdout, b'')

    def install_hooks(self):
        (self.repo / 'tools').mkdir(exist_ok=True)
        shutil.copy(ROOT / 'tools/check_repo_hygiene.py', self.repo / 'tools/check_repo_hygiene.py')
        hooks = self.repo / '.githooks'; hooks.mkdir(exist_ok=True)
        for name in ('pre-commit', 'pre-push'):
            target = hooks / name
            shutil.copy(ROOT / '.githooks' / name, target); target.chmod(0o755)
        self.git('config', 'core.hooksPath', '.githooks')


if __name__ == '__main__':
    unittest.main()
