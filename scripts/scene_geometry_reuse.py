"""Reuse source geometry across edit windows only for identical placed actors."""
import ast
import copy
import inspect
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from strep import ROOT, read, save, sha256


def match_samples(old_actors, new_actors, rows, times):
    if list(old_actors) != list(new_actors) or len(old_actors) != 2:
        raise ValueError('Matching ordered source actors required')
    for name in old_actors:
        for key in ['sha256', 'placement']:
            if old_actors[name][key] != new_actors[name][key]: raise ValueError('Placed source geometry differs')
    if [r['sample'] for r in rows] != list(range(len(rows))): raise ValueError('Ordered donor samples required')
    clock = [r['time_s'] for r in rows]
    if not np.isfinite(clock).all() or len(set(clock)) != len(clock) or np.any(np.diff(clock) <= 0): raise ValueError('Distinct increasing donor times required')
    times = np.asarray(times)
    if times.ndim != 1 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0): raise ValueError('Distinct increasing new times required')
    lookup = {t:i for i,t in enumerate(clock)}
    return [lookup.get(float(t)) for t in times]


def expanded_source(previous, prepared_record, actors, output, extractor):
    previous, output = Path(previous).resolve(), Path(output).resolve()
    result = read(previous/'result.json'); record = read(previous/'request.json'); files = {}
    if result['status'] != 'complete': raise ValueError('Completed donor study required')
    for name in ['request.json', 'source-index.json']:
        key = name.split('.')[0].replace('-', '_')+'_sha256'
        if sha256(previous/name) != result[key]: raise ValueError('Donor geometry binding changed')
        files[str(previous/name)] = result[key]
    files[str(previous/'result.json')] = sha256(previous/'result.json')
    for path, digest in record['inputs'].items():
        if sha256(path) != digest: raise ValueError('Donor input changed')
        files[path] = digest
    driver = 'study_scene_pair_fit.py'
    for name, digest in record['implementation'].items():
        path = previous/'implementation'/name
        if sha256(path) != digest: raise ValueError('Donor snapshot changed')
        if name != driver and sha256(ROOT/'scripts'/name) != digest: raise ValueError('Geometry dependency changed: '+name)
        files[str(path)] = digest
    old_code = (previous/'implementation'/driver).read_text(encoding='utf-8')
    node = next(n for n in ast.parse(old_code).body if isinstance(n, ast.FunctionDef) and n.name == 'source_samples')
    if ast.get_source_segment(old_code, node).strip() != inspect.getsource(extractor).strip(): raise ValueError('Source geometry extractor changed')
    old_prepared_path = Path(record['prepared_request']); old_prepared = read(old_prepared_path)
    if files.get(str(old_prepared_path)) != sha256(old_prepared_path): raise ValueError('Donor actor identities unbound')
    index = read(previous/'source-index.json'); rows = []; paths = []
    for name, digest in index.items():
        path = (previous/'source'/name).resolve()
        if path.parent != previous/'source' or sha256(path) != digest: raise ValueError('Donor sample changed')
        rows.append(read(path)); paths.append(path); files[str(path)] = digest
    if not np.array_equal([r['time_s'] for r in rows], old_prepared['sample_times_seconds']): raise ValueError('Incomplete donor clock')
    times = actors[0]['model'].times; np.testing.assert_array_equal(times, actors[1]['model'].times)
    mapping = match_samples(old_prepared['actors'], prepared_record['actors'], rows, times)
    missing = [i for i, old in enumerate(mapping) if old is None]
    fresh_folder = output.parent/'fresh-source'; fresh_folder.mkdir()
    fresh_actors = [dict(a, model=SimpleNamespace(times=times[missing], source_world=a['model'].source_world[missing])) for a in actors]
    fresh = extractor(fresh_actors, fresh_folder) if missing else []
    if len(fresh) != len(missing): raise ValueError('Incomplete fresh geometry')
    by_new_index = dict(zip(missing, fresh)); merged = []; provenance = []
    for new_index, old_index in enumerate(mapping):
        if old_index is None:
            row = copy.deepcopy(by_new_index[new_index]); origin = fresh_folder/f"sample-{row['sample']:03d}.json"
            source_index = row['sample']; kind = 'fresh'
        else:
            row = copy.deepcopy(rows[old_index]); origin = paths[old_index]; source_index = old_index; kind = 'reused'
        if row['time_s'] != float(times[new_index]): raise ValueError('Geometry time differs')
        row['sample'] = new_index; target = output/f'sample-{new_index:03d}.json'; save(target, row); merged.append(row)
        provenance.append(dict(sample=new_index, time_s=row['time_s'], kind=kind, source=str(origin), source_sample=source_index,
            source_sha256=sha256(origin), remapped_sha256=sha256(target)))
    save(output.parent/'geometry-reuse.json', dict(donor=str(previous), reused=len(mapping)-len(missing), fresh=len(missing), samples=provenance,
        scope='Same exact GLB bytes, placements, extraction code/dependencies and sample times. Only sample indices are remapped; newly included times are queried. No constraints or candidate geometry reused.', quality_approved=False))
    return merged, files
