import numpy as np
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from native_contact_mask_probe import stencils
import native_contact_mask_probe as probe
from strep import save, read, sha256
from test_native_surface_contact import scene_fixture, policy


def test_both_signed_stencils_preserve_every_unselected_control_and_baseline():
    baseline = np.linspace(-.3, .4, 72); before = baseline.copy()
    proposals = stencils(baseline, [30, 35, 66], .005)
    assert len(proposals) == 6
    for index, sign, value in proposals:
        other = np.arange(72) != index
        np.testing.assert_array_equal(value[other], baseline[other])
        assert value[index] == baseline[index] + sign*.005
    np.testing.assert_array_equal(baseline, before)


@pytest.mark.parametrize('indices', [[], [1, 1], [True], [-1], [72], list(range(25)), (0,)])
def test_unbounded_or_implicit_masks_reject(indices):
    with pytest.raises(ValueError, match='indices'):
        stencils(np.zeros(72), indices, .005)


@pytest.mark.parametrize('step', [0, .006, True, float('nan'), float('inf')])
def test_nonfinite_or_excessive_step_reject(step):
    with pytest.raises(ValueError, match='step'):
        stencils(np.zeros(72), [1], step)


def test_near_box_edge_rejects_without_clipping_a_step():
    with pytest.raises(ValueError, match='Both exact'):
        stencils(np.array([.998, 0.]), [0], .005)
    assert len(stencils(np.array([.998, 0.]), [1], .005)) == 2


@pytest.mark.parametrize('baseline', [np.array([1.1]), np.array([float('nan')]), np.zeros((1, 2)), np.array([])])
def test_invalid_baseline_reject(baseline):
    with pytest.raises(ValueError, match='baseline'):
        stencils(baseline, [0], .001)


def probe_fixture(tmp_path):
    _, _, _, spec, path, _ = scene_fixture(tmp_path)
    permissions = dict(schema='strep-native-scene-edit-v1', contacts_sha256=sha256(path),
        actors=dict(A=dict(window_s=[0., 2.], protected_s=[], knots_s=[0., 1., 2.],
            tracks=[dict(node=3, path='rotation', maximum_change=5.)],
            maximum_joint_displacement_m=.02)))
    permission_path, surface_path, baseline_path = [tmp_path/n for n in ('permissions.json', 'surface.json', 'baseline.npy')]
    save(permission_path, permissions); save(surface_path, policy(path, spec))
    np.save(baseline_path, np.zeros(3))
    return path, permission_path, surface_path, baseline_path


def test_actual_small_glb_exports_decodes_and_complete_probes_never_retain(tmp_path):
    paths = probe_fixture(tmp_path); output = tmp_path/'probe'
    result = probe.run(*paths, output, indices=[1], step=.001)
    assert result['status'] == 'complete' and len(result['predicted']) == 2
    assert result['baseline']['independently_decoded'] and result['decoded']
    assert all(r['independently_decoded'] and r['static_audits']['A']['passed'] for r in result['decoded'])
    assert len({r['native_rows'] for r in [result['baseline'], *result['predicted'], *result['decoded']]}) == 1
    assert result['original_selected'] and result['unselected_controls_frozen']
    assert not result['native_caps_rebuilt_from_candidate']
    for field in ('collision_verified', 'engine_executed', 'quality_approved', 'training_admitted', 'release_approved'):
        assert result[field] is False
    assert not (output/'retained-controls.npy').exists()
    for k in range(2):
        saved = np.load(output/f'predicted-{k}'/'conditions.npz', allow_pickle=False)
        np.testing.assert_array_equal(saved['controls'][[0, 2]], [0, 0])
    with pytest.raises(ValueError, match='Fresh'):
        probe.run(*paths, output, indices=[1], step=.001)


def test_mutated_input_preserves_partial_evidence_without_complete_receipt(tmp_path, monkeypatch):
    paths = probe_fixture(tmp_path); output = tmp_path/'probe'
    original = probe.CachedContactNorms.residual
    mutated = False
    def change_once(self, worlds):
        nonlocal mutated
        result = original(self, worlds)
        if not mutated:
            np.save(paths[3], np.ones(3)*.01); mutated = True
        return result
    monkeypatch.setattr(probe.CachedContactNorms, 'residual', change_once)
    with pytest.raises(ValueError, match='inputs or methods changed'):
        probe.run(*paths, output, indices=[1], step=.001)
    assert (output/'request.json').exists() and (output/'baseline'/'conditions.npz').exists()
    assert not (output/'result.json').exists()
