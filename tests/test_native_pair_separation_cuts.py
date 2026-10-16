"""Source cuts preserve all nine inequalities and disclose unresolved overlaps."""
from pathlib import Path
import copy, sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_partner_surface_rows import scene_fixture
from native_pair_separation_cuts import build


@pytest.fixture(scope='module')
def scene(tmp_path_factory):
    return scene_fixture(tmp_path_factory.mktemp('pair-cuts'))[0]


def pair(**changes):
    result = dict(time_s=0., left_actor='A', right_actor='B', left_triangle=0, right_triangle=0)
    result.update(changes); return result


def test_source_separated_triangle_has_every_vertex_pair_and_moves_with_both_actors(scene):
    source = copy.deepcopy(scene); p, r = source.actors['B']['placement']; source.actors['B']['placement'] = (p+[3., 0., 0.], r)
    rows, bounds = build(source, [pair()]); assert len(rows.rows) == len(bounds) == 9
    assert len({(v['left']['vertices'][0], v['right']['vertices'][0]) for v in rows.rows}) == 9
    assert rows.report['positive_source_axis_pairs'] == 1
    np.testing.assert_array_equal(bounds, np.full(9, .0001)); assert np.all(rows.gaps() >= bounds)
    original = rows.gaps(); normal = np.array(rows.rows[0]['normal_world'])
    def moved(name, time):
        actor = source.actors[name]; p, r = actor['placement']; vertices = actor['rig'].vertices(actor['sampler'].sample(time))@r.T+p
        return vertices+normal*(.01 if name == 'A' else -.02)
    np.testing.assert_allclose(rows.gaps(moved)-original, .03, atol=1e-14, rtol=0)


def test_source_overlaps_remain_explicit_and_do_not_become_clearance_certificates(scene):
    from native_scene_geometry import faces_for
    pairs = [pair(left_triangle=i, right_triangle=j) for i in range(len(faces_for(scene.actors['A']['rig'])[0])) for j in range(len(faces_for(scene.actors['B']['rig'])[0]))]
    rows, bounds = build(scene, pairs)
    gaps = np.array(rows.report['source_axis_gaps_m'])
    assert np.any(gaps < 0) and rows.report['unresolved_source_axis_pairs'] > 0
    np.testing.assert_array_equal(bounds.reshape(-1, 9)[:, 0], np.minimum(.0001, gaps))
    np.testing.assert_allclose(rows.gaps().reshape(-1, 9).min(axis=1), gaps, atol=1e-14, rtol=0)
    assert not rows.report['quality_approved'] and not rows.report['release_approved']


@pytest.mark.parametrize('fault', ['empty', 'duplicate', 'reverse-duplicate', 'boolean-id', 'bad-id', 'same-actor',
    'unknown-actor', 'time', 'nan-time', 'extra', 'budget', 'boolean-clearance', 'negative-clearance'])
def test_invalid_or_incomplete_pair_request_rejects(scene, fault):
    pairs = [pair()]; kwargs = {}
    if fault == 'empty': pairs = []
    elif fault == 'duplicate': pairs *= 2
    elif fault == 'reverse-duplicate': pairs.append(pair(left_actor='B', right_actor='A'))
    elif fault == 'boolean-id': pairs[0]['left_triangle'] = True
    elif fault == 'bad-id': pairs[0]['left_triangle'] = 1000000
    elif fault == 'same-actor': pairs[0]['right_actor'] = 'A'
    elif fault == 'unknown-actor': pairs[0]['right_actor'] = 'other'
    elif fault == 'time': pairs[0]['time_s'] = -1.
    elif fault == 'nan-time': pairs[0]['time_s'] = float('nan')
    elif fault == 'extra': pairs[0]['auto'] = True
    elif fault == 'budget': kwargs['maximum_rows'] = 8
    elif fault == 'boolean-clearance': kwargs['clearance'] = True
    else: kwargs['clearance'] = -.001
    with pytest.raises(ValueError): build(scene, pairs, **kwargs)
