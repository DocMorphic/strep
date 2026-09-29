"""Exercise real local fitting, reconstruction and correct warm-start selection."""
import sys
from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import support_contact_v8 as fitter
from inspect_motion import skeleton_metadata
from floor_contact import reconstruct
from held_pose_preservation import POSE_KEYS
from localized_spline import localized_controls


@pytest.mark.parametrize('warm', [False, True])
@pytest.mark.parametrize('window', [[12, 47], [0, 59]])
def test_refine_preserves_correct_seed_and_keeps_all_free_fitted_keys(monkeypatch, warm, window):
    names, parents, _ = skeleton_metadata(77)
    frames = 60
    rotations = np.tile(np.eye(3), (frames, 77, 1, 1)).astype('float32')
    rotations[:, 0] = Rotation.from_euler('y', .07).as_matrix().astype('float32')
    positions = np.zeros((frames, 77, 3), dtype='float32'); positions[:, :, 1] = 1.
    source = dict(local_rot_mats=rotations.copy(), global_rot_mats=rotations.copy(),
                  posed_joints=positions, root_positions=positions[:, 0].copy())
    source = reconstruct(source, rotations.copy(), parents)
    seed = deepcopy(source)
    if warm:
        seed['root_positions'][:, 1] += .01
        local = seed['local_rot_mats'].copy()
        local[:, names.index('LeftForeArm')] = Rotation.from_euler('z', .1).as_matrix().astype('float32')
        seed = reconstruct(seed, local, parents)
    bind = np.tile(np.eye(4), (77, 1, 1)); bind[:, 1, 3] = 1.
    skin = dict(rig_joint_names=names, bind_rig_transform=bind,
                bind_vertices=positions[0].copy(), lbs_indices=np.repeat(np.arange(77)[:, None], 8, axis=1),
                lbs_weights=np.full((77, 8), 1/8))
    spec = dict(schema_version=1, fps=30, frame_count=frames,
                regions={'LeftFoot': dict(mode='explicit', segments=[dict(start_frame=20, end_frame=35,
                    space='world', position_m=[0., 1.02, 0.], vertex_id=names.index('LeftFoot'))])})
    captured = []
    def capture(*args):
        output = reconstruct(*args); captured.append(deepcopy(output)); return output
    monkeypatch.setattr(fitter, 'reconstruct', capture)
    source_before, seed_before = deepcopy(source), deepcopy(seed)
    result, recipe = fitter.refine(source, source, skin, contact_spec=spec, outer_stage_count=1,
        iteration_count=1, root_coordinate_mode='physical_box', edit_window=window,
        warm_start=seed if warm else None)
    _, locked, _ = localized_controls(np.eye(frames), window)
    expected = seed if warm else source
    assert len(captured) == 1
    for key in POSE_KEYS:
        assert result[key][locked].tobytes() == expected[key][locked].tobytes()
        assert result[key][~locked].tobytes() == captured[0][key][~locked].tobytes()
        assert source[key].tobytes() == source_before[key].tobytes()
        assert seed[key].tobytes() == seed_before[key].tobytes()
    assert np.max(abs(result['root_positions'][~locked] - expected['root_positions'][~locked])) > 1e-7
    assert recipe['localization']['held_pose_arrays_bit_exact']
    assert recipe['localization']['held_seed'] == ('warm_start' if warm else 'original')
    if warm and locked.any():
        assert result['local_rot_mats'][locked].tobytes() != source['local_rot_mats'][locked].tobytes()
        assert result['root_positions'][locked].tobytes() != source['root_positions'][locked].tobytes()
