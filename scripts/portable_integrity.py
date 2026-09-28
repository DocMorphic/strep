"""Integrity of locally exported source; not a publisher signature or trust boundary."""
from pathlib import Path, PurePosixPath
from strep import read, sha256


def contained(root, relative):
    p = PurePosixPath(relative)
    if not relative or p.is_absolute() or '..' in p.parts or '\\' in relative or ':' in relative:
        raise ValueError('Unsafe package path')
    target = (Path(root) / relative).resolve()
    if not target.is_relative_to(Path(root).resolve()):
        raise ValueError('Package path escapes installation')
    return target


def verify_files(root, files):
    for relative, digest in files.items():
        path = contained(root, relative)
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError('Missing or changed package file: ' + relative)


def verify_vendor(root):
    root = Path(root)
    attestation = read(root / 'benchmarks/vendor-export.json')
    commit = read(root / 'benchmarks/sources.lock.json')['kimodo_git_commit']
    if attestation.get('schema') != 1 or attestation.get('commit') != commit or not attestation.get('files_sha256'):
        raise RuntimeError('Invalid pinned vendor export')
    vendor = root / 'vendor/kimodo'
    expected = attestation['files_sha256']
    actual = {p.relative_to(vendor).as_posix() for p in vendor.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    if actual != set(expected):
        raise RuntimeError('Vendor export file set changed')
    verify_files(vendor, expected)
    return commit
