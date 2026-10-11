"""Reference geometry with known scale, proportion and coordinate changes."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from test_native_rig_transfer import fixture
from rig_asset import RigAsset
from retarget_rig import resolve_profile
from rig_reference_diagnostics import diagnose
from strep import read


def setup(tmp_path):
    source_path, source_profile = fixture(tmp_path/'a', 'source', size=1., helpers=True)
    target_path, target_profile = fixture(tmp_path/'b', 'target', size=1.3, axes=27, reverse=True, helpers=True)
    source = RigAsset.load(source_path); target = RigAsset.load(target_path)
    mapping, _ = resolve_profile(source, read(source_profile)); names = list(mapping)
    neutral = np.array([source.reference[mapping[n], :3, 3] for n in names])
    return target, read(target_profile), names, neutral


def test_uniform_scale_preserves_relative_geometry(tmp_path):
    target, profile, names, neutral = setup(tmp_path); original = copy.deepcopy(target.document)
    result = diagnose(target, profile, names, neutral)
    assert result['leg_scale'] == pytest.approx(1.3)
    assert max(r['position_error_m'] for r in result['joints'].values()) < 1e-12
    assert all(r['ratio_relative_to_leg_scale'] == pytest.approx(1.) for r in result['edges'].values())
    assert target.document == original
    assert result['mesh_bounds']['target_default']['vertices'] == 63
    assert not result['cause_established'] and not result['contact_or_support_verified'] and not result['quality_approved']


def test_head_proportion_difference_is_retained_and_measured(tmp_path):
    target, profile, names, neutral = setup(tmp_path)
    mapping, _ = resolve_profile(target, profile); node = mapping['Head']; parent = target.parents[node]
    document = copy.deepcopy(target.document)
    change = target.reference[parent, :3, :3].T @ np.array([0, .11, 0])
    document['nodes'][node]['translation'] = (np.array(document['nodes'][node]['translation']) + change).tolist()
    target = RigAsset(document, target.binary); result = diagnose(target, profile, names, neutral)
    assert result['leg_scale'] == pytest.approx(1.3)
    assert result['joints']['Head']['position_error_m'] == pytest.approx(.11)
    edge = result['edges']['Head']
    assert edge['target_reference_length_m'] == pytest.approx(.17 * 1.3 + .11)
    assert edge['ratio_relative_to_leg_scale'] == pytest.approx((.17 * 1.3 + .11) / (.17 * 1.3))


def test_root_offset_and_source_origin_do_not_hide_proportion_errors(tmp_path):
    target, profile, names, neutral = setup(tmp_path)
    a = diagnose(target, profile, names, neutral)
    profile['world_offset_m'] = [2., -3., 4.]
    b = diagnose(target, profile, names, neutral + [13., -7., 9.])
    for role in a['joints']:
        np.testing.assert_allclose(a['joints'][role]['position_difference_m'], b['joints'][role]['position_difference_m'], atol=1e-12)
    assert not np.allclose(a['mesh_bounds']['target_aligned_identity']['minimum_m'], b['mesh_bounds']['target_aligned_identity']['minimum_m'])


@pytest.mark.parametrize('fault', ['duplicate', 'missing', 'bool', 'mixed_bool', 'nonfinite', 'shape', 'nonnumeric', 'empty'])
def test_invalid_source_reference_rejected(tmp_path, fault):
    target, profile, names, neutral = setup(tmp_path)
    if fault == 'duplicate': names[-1] = names[0]
    if fault == 'missing': names[-1] = 'Unmapped'
    if fault == 'bool': neutral = neutral.astype(bool)
    if fault == 'mixed_bool': neutral = neutral.tolist(); neutral[0][0] = True
    if fault == 'nonfinite': neutral[0, 0] = np.nan
    if fault == 'shape': neutral = neutral[:, :2]
    if fault == 'nonnumeric': neutral = neutral.astype(str)
    if fault == 'empty': names = []
    with pytest.raises(ValueError): diagnose(target, profile, names, neutral)


def test_degenerate_reference_rejected(tmp_path):
    target, profile, names, neutral = setup(tmp_path)
    neutral[names.index('LeftHand')] = neutral[names.index('LeftForeArm')]
    with pytest.raises(ValueError, match='Degenerate'): diagnose(target, profile, names, neutral)
