import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from action_requests import validate_request, request_digest
from generation_constraints import compile_guides, load_guides
from kimodo.skeleton import SOMASkeleton30
from strep import ROOT, read, sha256


def fixture():
    return copy.deepcopy(read(ROOT / 'benchmarks/kneel-start-guides-v1.json')['requests'][1])


def test_explicit_origin_matches_independently_translated_source():
    original = fixture()
    source = ROOT / original['generation_constraints'][0]['motion']
    digest = sha256(source)
    request = copy.deepcopy(original)
    request['guide_origin'] = 'start_pose'
    compiled, provenance = compile_guides(request)
    canonical = read(ROOT / 'reports/kneel-start-guides-plan-v2/compiled-guides.json')['constraints']
    skeleton = SOMASkeleton30()
    actual, expected = load_guides(compiled, skeleton)[0], load_guides(canonical, skeleton)[0]
    np.testing.assert_allclose(actual.global_joints_positions, expected.global_joints_positions, atol=2e-7, rtol=0)
    np.testing.assert_array_equal(actual.global_joints_rots, expected.global_joints_rots)
    assert compiled[0]['smooth_root_2d'] == [[0., 0.]]
    assert provenance[0]['origin_transform']['mode'] == 'start_pose'
    assert sha256(source) == digest
    assert request['generation_constraints'] == original['generation_constraints']
    assert request_digest(dict(schema_version=1, requests=[request])) != request_digest(dict(schema_version=1, requests=[original]))


def test_all_guides_move_together_preserving_relative_targets_and_height():
    request = fixture()
    later = copy.deepcopy(request['generation_constraints'][0])
    later.update(type='root2d', source_frames=[60], frame_indices=[90])
    request['generation_constraints'].append(later)
    before, _ = compile_guides(request)
    request['guide_origin'] = 'start_pose'
    after, _ = compile_guides(request)
    delta = np.asarray(before[0]['smooth_root_2d'])[0]
    for b, a in zip(before, after):
        np.testing.assert_allclose(np.asarray(b['smooth_root_2d']) - np.asarray(a['smooth_root_2d']), [delta], atol=1e-12)
        if 'root_positions' in b:
            np.testing.assert_array_equal(np.asarray(b['root_positions'])[:, 1], np.asarray(a['root_positions'])[:, 1])
            np.testing.assert_array_equal(b['local_joints_rot'], a['local_joints_rot'])
    assert compile_guides(fixture())[0][0]['smooth_root_2d'] == before[0]['smooth_root_2d']


@pytest.mark.parametrize('setting', [None, True, 'automatic', {}])
def test_invalid_origin_modes_are_not_ignored(setting):
    request = fixture()
    request['guide_origin'] = setting
    with pytest.raises(ValueError, match='guide_origin'):
        validate_request(request)


def test_missing_start_anchor_is_rejected():
    request = fixture()
    request['guide_origin'] = 'start_pose'
    request['generation_constraints'][0]['frame_indices'] = [30]
    with pytest.raises(ValueError, match='frame 0'):
        validate_request(request)
