"""Prepare the pinned Kimodo source without installing packages or models."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

UPSTREAM = 'https://github.com/nv-tlabs/kimodo.git'


def git(folder, *arguments):
    return subprocess.check_output(['git', '-c', f'safe.directory={folder.as_posix()}',
        '-C', str(folder), *arguments], text=True, encoding='utf-8', errors='replace', stderr=subprocess.PIPE).strip()


def verify(folder, commit):
    if not (folder/'.git').exists():
        raise ValueError('Existing vendor/kimodo is not a Git checkout; it was left unchanged')
    if Path(git(folder, 'rev-parse', '--show-toplevel')).resolve() != folder.resolve():
        raise ValueError('Kimodo must be its own checkout')
    if git(folder, 'rev-parse', '--verify', 'HEAD') != commit:
        raise ValueError('Kimodo revision differs from sources.lock.json; existing checkout was left unchanged')
    if git(folder, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Kimodo has local changes; existing checkout was left unchanged')


def prepare(root, *, check_only=False, remote=UPSTREAM):
    root = Path(root).resolve(); lock = root/'benchmarks/sources.lock.json'
    captured = lock.read_bytes(); commit = json.loads(captured.decode('utf-8-sig')).get('kimodo_git_commit')
    if not isinstance(commit, str) or re.fullmatch(r'[0-9a-f]{40}', commit) is None:
        raise ValueError('Source lock must contain a full lowercase Git commit SHA')
    vendor = root/'vendor'; target = vendor/'kimodo'
    if vendor.is_symlink() or target.is_symlink() or not target.resolve().is_relative_to(root):
        raise ValueError('Vendor source must be a real directory inside the project')
    def unchanged_lock():
        if lock.read_bytes() != captured: raise ValueError('Source lock changed during preparation')
    if target.exists():
        verify(target, commit); unchanged_lock()
        return dict(status='verified_existing', commit=commit, lock_sha256=hashlib.sha256(captured).hexdigest())
    if check_only: raise ValueError('Pinned Kimodo source is missing; run prepare_vendor.py without --check to acquire it')
    vendor.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.kimodo-source-', dir=vendor)).resolve()
    try:
        git(stage, 'init', '--quiet')
        git(stage, 'remote', 'add', 'origin', remote)
        git(stage, 'fetch', '--quiet', '--no-tags', '--depth', '1', 'origin', commit)
        git(stage, 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
        verify(stage, commit); unchanged_lock()
        # Resolve both endpoints before moving a directory. Existing checkouts
        # are never reset, cleaned or replaced, including after a failed fetch.
        if stage.parent != vendor.resolve() or target.resolve().parent != vendor.resolve() or target.exists() or target.is_symlink():
            raise ValueError('Source destination changed during preparation')
        stage.rename(target)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f'Pinned source preparation failed; staged files retained at {stage}') from error
    verify(target, commit); unchanged_lock()
    return dict(status='prepared', commit=commit, upstream=remote, lock_sha256=hashlib.sha256(captured).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify existing source without acquiring anything')
    args = parser.parse_args()
    print(json.dumps(prepare(Path(__file__).resolve().parents[1], check_only=args.check), indent=2))
