import sys
from pathlib import Path
import copy
import inspect
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_geometry_reuse import match_samples, expanded_source
from strep import read, save, sha256


def actors():
    return {name: dict(sha256=name*64, placement=dict(translation_m=[0, 0, i], rotation_xyzw=[0, 0, 0, 1])) for i,name in enumerate(['a', 'b'])}


def rows(): return [dict(sample=i, time_s=t) for i,t in enumerate([1., 1.25, 1.5])]


def test_window_expansion_reuses_only_exact_times_with_unchanged_geometry():
    a = actors(); assert match_samples(a, copy.deepcopy(a), rows(), [.5, 1., 1.25, 1.5, 2.]) == [None, 0, 1, 2, None]
    assert match_samples(a, a, rows(), [1.00000001, 1.25]) == [None, 1]


@pytest.mark.parametrize('fault', ['bytes', 'placement', 'actor_order', 'duplicate_time', 'unordered_samples', 'unordered_new_time'])
def test_incompatible_source_or_clock_cannot_reuse_samples(fault):
    a = actors(); b = copy.deepcopy(a); r = rows(); times = [1., 1.25]
    if fault == 'bytes': b['a']['sha256'] = 'changed'
    if fault == 'placement': b['b']['placement']['translation_m'][0] = .001
    if fault == 'actor_order': b = dict(reversed(list(b.items())))
    if fault == 'duplicate_time': r[1]['time_s'] = r[0]['time_s']
    if fault == 'unordered_samples': r.reverse()
    if fault == 'unordered_new_time': times.reverse()
    with pytest.raises(ValueError): match_samples(a, b, r, times)


def source_samples(actors, output):
    rows = [dict(sample=i, time_s=float(t), marker='fresh') for i,t in enumerate(actors[0]['model'].times)]
    for row in rows: save(output/f"sample-{row['sample']:03d}.json", row)
    return rows


def donor_fixture(tmp_path):
    donor = tmp_path/'donor'; (donor/'source').mkdir(parents=True); (donor/'implementation').mkdir()
    prepared = donor/'prepared.json'; save(prepared, dict(actors=actors(), sample_times_seconds=[r['time_s'] for r in rows()]))
    driver = donor/'implementation/study_scene_pair_fit.py'; driver.write_text(inspect.getsource(source_samples), encoding='utf-8')
    index = {}
    for row in rows():
        name = f"sample-{row['sample']:03d}.json"; save(donor/'source'/name, row); index[name] = sha256(donor/'source'/name)
    save(donor/'source-index.json', index)
    save(donor/'request.json', dict(inputs={str(prepared):sha256(prepared)}, prepared_request=str(prepared), implementation={driver.name:sha256(driver)}))
    save(donor/'result.json', dict(status='complete', request_sha256=sha256(donor/'request.json'), source_index_sha256=sha256(donor/'source-index.json')))
    output = tmp_path/'new/source'; output.mkdir(parents=True)
    times = np.array([.5, 1., 1.25, 1.5, 2.])
    models = [dict(model=SimpleNamespace(times=times, source_world=np.zeros((5, 1, 4, 4)))) for _ in range(2)]
    return donor, output, models


def test_expansion_reindexes_copies_and_preserves_donor_and_fresh_observations(tmp_path):
    donor, output, models = donor_fixture(tmp_path); original_index = read(donor/'source-index.json')
    merged, bindings = expanded_source(donor, dict(actors=actors()), models, output, source_samples)
    assert [r['sample'] for r in merged] == list(range(5))
    assert [r['time_s'] for r in merged] == [.5, 1., 1.25, 1.5, 2.]
    proof = read(output.parent/'geometry-reuse.json'); assert (proof['reused'], proof['fresh']) == (3, 2)
    assert proof['samples'][-1]['source_sample'] == 1
    assert read(output.parent/'fresh-source/sample-001.json')['sample'] == 1
    assert read(output/'sample-004.json')['sample'] == 4
    for name,digest in original_index.items(): assert sha256(donor/'source'/name) == digest
    for name,digest in bindings.items(): assert sha256(name) == digest


@pytest.mark.parametrize('fault', ['sample', 'extractor', 'dependency', 'prepared'])
def test_invalid_donor_cannot_reach_fresh_queries(tmp_path, fault):
    donor, output, models = donor_fixture(tmp_path)
    if fault == 'sample': save(donor/'source/sample-000.json', {})
    elif fault == 'prepared': save(donor/'prepared.json', {})
    else:
        request = read(donor/'request.json')
        name = 'study_scene_pair_fit.py' if fault == 'extractor' else 'strep.py'
        path = donor/'implementation'/name
        path.write_text('def source_samples(actors, output):\n    return []\n' if fault == 'extractor' else 'different dependency', encoding='utf-8')
        request['implementation'][name] = sha256(path); save(donor/'request.json', request)
        result = read(donor/'result.json'); result['request_sha256'] = sha256(donor/'request.json'); save(donor/'result.json', result)
    with pytest.raises(ValueError): expanded_source(donor, dict(actors=actors()), models, output, source_samples)
    assert not (output.parent/'fresh-source').exists()
