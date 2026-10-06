"""Complete declared read graph for sealed Studio shared-transition fit jobs.

This transport adapter preserves the original full manifest verifier. Unknown,
missing, external or excessive graphs use it directly, without partial caching.
It is not installed into the server or numeric worker by importing this module.
"""
import hashlib
import json
from pathlib import Path
from verified_read_cache import ReadDependencies, VerifiedReadCache


class CacheIneligible(ValueError):
    pass


class _Graph:
    def __init__(self, reports, maximum_nodes=128):
        self.reports = Path(reports).resolve()
        self.maximum_nodes = maximum_nodes
        self.files, self.trees, self.headers = set(), set(), {}
        self.active, self.visited = set(), set()

    def path(self, value, base=None):
        if not isinstance(value, (str, Path)) or not str(value):
            raise CacheIneligible('Explicit dependency path required')
        path = (Path(base or self.reports) / value).absolute()
        if not path.resolve().is_relative_to(self.reports):
            raise CacheIneligible('Dependency outside report scope')
        return path

    def file(self, value, base=None):
        path = self.path(value, base); self.files.add(path); return path

    def read(self, value):
        path = self.file(value); raw = path.read_bytes()
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise CacheIneligible('Object metadata required')
        digest = hashlib.sha256(raw).hexdigest()
        if path in self.headers and self.headers[path] != digest:
            raise CacheIneligible('Discovery metadata changed')
        self.headers[path] = digest
        return value

    def bindings(self, mapping):
        if not isinstance(mapping, dict):
            raise CacheIneligible('Complete dependency map required')
        for path in mapping:
            self.file(path)

    def visit(self, kind, value):
        folder = self.path(value); key = kind, folder.resolve()
        if key in self.active:
            raise CacheIneligible('Dependency cycle')
        if key in self.visited:
            return
        if len(self.visited) + len(self.active) >= self.maximum_nodes:
            raise CacheIneligible('Dependency graph exceeds caching budget')
        self.active.add(key); self.trees.add(folder)
        try:
            if kind == 'studio':
                state = self.read(folder / 'pipeline.json')
                if state['status'] != 'complete':
                    raise CacheIneligible('Only completed jobs may reuse verification')
                request = self.read(folder / 'request.json')
                if request['schema'] != 'strep-studio-native-transition-fit-v1':
                    raise CacheIneligible('Unknown Studio job schema')
                self.visit('scene', self.path(request['source']['folder']))
                if request['resume_from'] is not None:
                    self.visit('correction', self.path(request['resume_from']['folder']))
                self.visit('correction', folder / 'candidate')
            elif kind == 'fit':
                request = self.read(folder / 'request.json')
                self.bindings(request['inputs_sha256'])
                self.bindings(request['source_inputs_sha256'])
                if request['resume'] is not None:
                    self.visit('fit', request['resume']['source_directory'])
            else:
                schemas = {'scene': 'strep-native-scene-transition-v1',
                           'transition': 'strep-native-rig-transition-v1',
                           'root-support': 'strep-native-transition-root-support-v1',
                           'correction': 'strep-native-transition-scene-fit-v1'}
                prepared = self.read(folder / 'prepared.json')
                recipe = self.read(folder / 'recipe.json')
                if prepared['schema'] != schemas[kind] or recipe['schema'] != schemas[kind]:
                    raise CacheIneligible('Unknown artifact schema')
                base = self.path(prepared['recipe_base'])
                if kind == 'correction':
                    self.file(prepared['recipe_original'])
                    self.visit('scene', self.path(recipe['source']['folder'], base))
                    self.visit('fit', folder / 'fit')
                    if prepared['resume_source'] is not None:
                        self.visit('fit', prepared['resume_source']['folder'])
                else:
                    self.file(prepared['recipe_original_path'])
                    if kind == 'scene':
                        self.bindings(prepared['inputs'])
                        for actor in recipe['actors'].values():
                            if actor['kind'] not in ('transition', 'root-support'):
                                raise CacheIneligible('Unknown actor dependency kind')
                            self.visit(actor['kind'], self.path(actor['folder'], base))
                    elif kind == 'root-support':
                        self.visit('transition', self.path(recipe['source']['folder'], base))
                    else:
                        self.bindings(prepared['inputs_sha256'])
        finally:
            self.active.remove(key)
        self.visited.add(key)

    def dependencies(self, methods, script_root):
        script_root = Path(script_root).resolve()
        for name in methods:
            if not isinstance(name, str) or Path(name).name != name:
                raise CacheIneligible('Exact implementation names required')
        files = self.files | {script_root / name for name in methods}
        return ReadDependencies(tuple(sorted(files, key=str)),
                                tuple(sorted(self.trees, key=str)),
                                (self.reports, script_root),
                                tuple(sorted(self.headers.items(), key=lambda pair: str(pair[0]))))


_CACHE = VerifiedReadCache()


def dependencies(job):
    import studio_native_transition_scene_fit as studio
    graph = _Graph(studio.ROOT / 'reports')
    try:
        graph.visit('studio', studio.folder_for(job))
        methods = tuple(studio.METHODS) + ('verified_read_cache.py', Path(__file__).name)
        return graph.dependencies(methods, studio.SCRIPT_ROOT)
    except (CacheIneligible, OSError, ValueError, TypeError, KeyError, RecursionError):
        return None


def manifest(job):
    import studio_native_transition_scene_fit as studio
    declared = dependencies(job)
    if declared is None:
        return studio.manifest(job)
    return _CACHE.read(job, studio.manifest, declared)


def served_file(relative):
    """Resolve the same exact published population after cached/full review.

    This is opt-in; the existing server and producer do not call it yet.
    Hash the selected payload again before returning its contained path.
    """
    import studio_native_transition_scene_fit as studio
    parts = relative.split('/')
    studio.require(len(parts) >= 3 and parts[0] == studio.NAMESPACE
                   and all(x not in ('', '.', '..') for x in parts)
                   and not any(c in relative for c in ('\\', '%', '?', '#')),
                   'Contained published bridge artifact required')
    value = manifest(parts[1])
    name = '/'.join(parts[2:])
    studio.require(value['status'] == 'complete' and name in value['files_sha256'],
                   'Unpublished bridge artifact')
    folder = studio.folder_for(parts[1])
    path = (folder / name).resolve()
    studio.require(path.is_relative_to(folder), 'Bridge artifact escapes job')
    studio.require(studio.sha256(path) == value['files_sha256'][name],
                   'Bridge artifact changed after review')
    return path
