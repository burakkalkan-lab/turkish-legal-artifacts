"""Keep evidence and reports out of version-controlled work trees.

Downloaded legal sources, evidence bundles and reports can contain client data. They must
never end up in a Git repository (and therefore on GitHub) by accident. This module
refuses to write inside a Git work tree unless Git itself says the target is ignored.
It never runs ``git add``, ``commit`` or ``push`` and never contacts any remote.
"""
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404 - fixed, read-only 'git check-ignore' call only

DEFAULT_EVIDENCE_DIR = Path.home() / '.cite-check-tr' / 'evidence'


class UnsafeOutput(ValueError):
    """Output path is inside a Git work tree and is not git-ignored."""


def git_root(path):
    """Return the nearest ancestor containing a .git entry (dir or worktree file), else None."""
    current = Path(path).expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / '.git').exists():
            return candidate
    return None


def _git(root, *args):
    git = shutil.which('git')
    if not git:
        raise UnsafeOutput('Git bulunamadı; çıktı güvenliği doğrulanamadı.')
    try:
        return subprocess.run(
            [git, '-C', str(root), *args], capture_output=True, timeout=15,
            env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_REPLACE_OBJECTS': '1'})
    except (OSError, subprocess.SubprocessError) as exc:
        raise UnsafeOutput('Git denetimi tamamlanamadı; çıktı reddedildi.') from exc


def _has_tracked_path(root, target):
    # Check both the index and HEAD: staged deletions are not permission to overwrite
    # a previously committed path. Literal comparisons avoid wildcard pathspec bypasses.
    relative = target.relative_to(root).as_posix()
    indexed = _git(root, 'ls-files', '--cached', '-z')
    if indexed.returncode:
        raise UnsafeOutput('Git index okunamadı; çıktı reddedildi.')
    names = indexed.stdout.split(b'\0')
    head = _git(root, 'rev-parse', '--verify', 'HEAD')
    if head.returncode == 0:
        committed = _git(root, 'ls-tree', '-r', '--name-only', '-z', 'HEAD')
        if committed.returncode:
            raise UnsafeOutput('Git HEAD okunamadı; çıktı reddedildi.')
        names += committed.stdout.split(b'\0')
    else:
        # Only an unborn branch is allowed to have no HEAD.
        symbolic = _git(root, 'symbolic-ref', '-q', 'HEAD')
        if symbolic.returncode:
            raise UnsafeOutput('Git HEAD doğrulanamadı; çıktı reddedildi.')
        ref = symbolic.stdout.decode('utf-8').strip()
        exists = _git(root, 'show-ref', '--verify', '--quiet', ref)
        if exists.returncode != 1:
            raise UnsafeOutput('Git HEAD eksik veya bozuk; çıktı reddedildi.')
    for raw in names:
        if not raw:
            continue
        name = os.fsdecode(raw)
        if name == relative or name.startswith(relative + '/') or relative.startswith(name + '/'):
            return True
    return False


def _is_ignored(root, target):
    # --no-index is safe only AFTER rejecting paths tracked in index or HEAD.
    result = _git(root, 'check-ignore', '-q', '--no-index', '--', str(target))
    if result.returncode not in (0, 1):
        raise UnsafeOutput('Git ignore denetimi başarısız; çıktı reddedildi.')
    return result.returncode == 0


def ensure_safe_output(path, is_dir=True):
    """Return the resolved path, or raise UnsafeOutput when it is in a non-ignored Git work tree."""
    target = Path(path).expanduser().resolve()
    root = git_root(target if target.exists() and target.is_dir() else target.parent)
    if root is None:
        return target
    if _has_tracked_path(root, target):
        raise UnsafeOutput('Çıktı yolu Git tarafından izleniyor; ignore kuralı bunu güvenli yapmaz.')
    # Neutral probe name: file-level ignore rules (evidence.json, *.log ...) must not make a plain folder look safe.
    probe = target / 'cite-check-output-probe' if is_dir else target
    if _is_ignored(root, probe):
        return target
    raise UnsafeOutput(
        'Çıktı yolu bir Git deposunun içinde ve .gitignore kapsamında değil: kanıt ve raporlar yanlışlıkla '
        'GitHub’a gönderilebilir. Depo dışında bir klasör seçin (ör. ~/.cite-check-tr/evidence/...) veya '
        'yolu .gitignore’a ekleyin.')


def make_private_dir(path):
    """Create a NEW directory readable only by the current user (best effort on Windows)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir(mode=0o700, exist_ok=False)
    return path
