"""Process-local reuse of a pure verifier under complete file dependencies.

Callers must declare every input, implementation file and population-sensitive
directory read by their verifier. This component supplies no semantic approval.
"""
import copy
import hashlib
import re
import stat
import threading
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


class EvidenceChangedError(RuntimeError):
    """Inputs changed during verification; no result may be reused or returned."""


class _Uncacheable(Exception):
    pass


@dataclass(frozen=True)
class ReadDependencies:
    files: tuple
    trees: tuple
    roots: tuple
    discovery_sha256: tuple = ()

    def __post_init__(self):
        for values in (self.files, self.trees, self.roots):
            if type(values) is not tuple or any(not isinstance(p, (str, Path)) for p in values):
                raise ValueError('Immutable tuples of dependency paths required')
        if type(self.discovery_sha256) is not tuple or any(
                type(pair) is not tuple or len(pair) != 2
                or not isinstance(pair[0], (str, Path))
                or not isinstance(pair[1], str) or re.fullmatch(r'[0-9a-f]{64}', pair[1]) is None
                for pair in self.discovery_sha256):
            raise ValueError('Exact immutable dependency-discovery digests required')


class VerifiedReadCache:
    def __init__(self, *, maximum_entries=8, maximum_paths=65536,
                 maximum_bytes=2 * 1024**3):
        for value, minimum in ((maximum_entries, 1), (maximum_paths, 1),
                               (maximum_bytes, 0)):
            if type(value) is not int or value < minimum:
                raise ValueError('Finite integer cache limits required')
        self.maximum_entries = maximum_entries
        self.maximum_paths = maximum_paths
        self.maximum_bytes = maximum_bytes
        self._entries = OrderedDict()
        self._mutex = threading.RLock()
        self._gates = {}

    @contextmanager
    def _gate(self, key):
        with self._mutex:
            gate, users = self._gates.get(key, (threading.RLock(), 0))
            self._gates[key] = gate, users + 1
        try:
            with gate:
                yield
        finally:
            with self._mutex:
                gate, users = self._gates[key]
                if users == 1:
                    del self._gates[key]
                else:
                    self._gates[key] = gate, users - 1

    def _snapshot(self, dependencies):
        """Read bytes, never use mtime as evidence; refuse partial signatures."""
        try:
            roots = tuple(sorted({Path(p).resolve(strict=True)
                                  for p in dependencies.roots}, key=str))
            if not roots or any(not p.is_dir() for p in roots):
                raise _Uncacheable()
            entries, hashed, total = {}, {}, 0

            def capture(path, directory=False):
                nonlocal total
                path = Path(path).absolute()
                before = path.lstat()
                reparse = getattr(before, 'st_file_attributes', 0) & getattr(
                    stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
                if stat.S_ISLNK(before.st_mode) or reparse:
                    raise _Uncacheable()
                resolved = path.resolve(strict=True)
                if not any(resolved.is_relative_to(root) for root in roots):
                    raise _Uncacheable()
                if str(path) not in entries and len(entries) >= self.maximum_paths:
                    raise _Uncacheable()
                if directory:
                    if not stat.S_ISDIR(before.st_mode):
                        raise _Uncacheable()
                    value = ('directory', str(resolved))
                else:
                    if not stat.S_ISREG(before.st_mode):
                        raise _Uncacheable()
                    if resolved not in hashed:
                        if before.st_size > self.maximum_bytes - total:
                            raise _Uncacheable()
                        digest = hashlib.sha256()
                        with path.open('rb') as stream:
                            while block := stream.read(65536):
                                total += len(block)
                                if total > self.maximum_bytes:
                                    raise _Uncacheable()
                                digest.update(block)
                        hashed[resolved] = digest.hexdigest()
                    value = ('file', str(resolved), hashed[resolved])
                entries[str(path)] = value
                if len(entries) > self.maximum_paths:
                    raise _Uncacheable()

            for path in dependencies.files:
                capture(path)
            for tree in dependencies.trees:
                tree = Path(tree).absolute()
                capture(tree, directory=True)
                for path in tree.rglob('*'):
                    capture(path, directory=path.is_dir())
            for path, digest in dependencies.discovery_sha256:
                if hashed.get(Path(path).resolve(strict=True)) != digest:
                    raise _Uncacheable()
            return tuple(map(str, roots)), tuple(sorted(entries.items()))
        except (OSError, ValueError, _Uncacheable):
            # An ineligible/oversized graph still uses the full verifier.
            return None

    def read(self, key, reader, dependencies):
        """reader(key) must be pure under the complete declared dependencies."""
        cache_key = key, reader
        with self._gate(cache_key):
            before = self._snapshot(dependencies)
            with self._mutex:
                previous = self._entries.get(cache_key)
                hit = before is not None and previous is not None and previous[0] == before
                if not hit:
                    self._entries.pop(cache_key, None)
            if hit:
                value = copy.deepcopy(previous[1])
                after = self._snapshot(dependencies)
                if after is None or after != before:
                    with self._mutex:
                        self._entries.pop(cache_key, None)
                    raise EvidenceChangedError('Cached verifier dependencies changed during the read')
                with self._mutex:
                    if self._entries.get(cache_key) is previous:
                        self._entries.move_to_end(cache_key)
                return value
            value = reader(key)
            if before is None:
                return value
            after = self._snapshot(dependencies)
            if after is None or after != before:
                raise EvidenceChangedError('Verifier dependencies changed during the read')
            with self._mutex:
                self._entries[cache_key] = before, copy.deepcopy(value)
                self._entries.move_to_end(cache_key)
                while len(self._entries) > self.maximum_entries:
                    self._entries.popitem(last=False)
            return value
