import sys
from pathlib import Path

import pytest
import torch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact_v8 import normalized_support_residual, inequality_merit, refine
from run_contact_edit import run


def test_dimensionless_augmented_updates_remain_unit_invariant():
    # Exercise both the first subproblem and its multiplier update. A mixed-unit
    # update would agree initially and diverge in the second stage.
    g = torch.tensor([-.001, .0, .004], dtype=torch.float64, requires_grad=True)
    def stages(violation, tolerance):
        residual = normalized_support_residual(violation, tolerance)
        multiplier = torch.zeros_like(residual)
        terms = []
        for penalty in [300., 1200.]:
            terms.append(inequality_merit(residual, multiplier, penalty).sum())
            multiplier = torch.relu(multiplier+penalty*residual.detach())
        return sum(terms)
    a, b = stages(g, .005), stages(g*1000., 5.)
    torch.testing.assert_close(a, b)
    torch.testing.assert_close(torch.autograd.grad(a, g)[0], torch.autograd.grad(b, g)[0])
    assert torch.isfinite(a) and a > 0


def test_unknown_scaling_and_legacy_route_cannot_silently_change_method():
    with pytest.raises(ValueError, match='Unknown authored point scaling'):
        refine(None, None, None, authored_point_scaling='automatic')
    with pytest.raises(ValueError, match='checked plan'):
        run(None, None, None, authored_point_scaling='tolerance')


def test_real_closure_and_multiplier_update_use_same_scale(monkeypatch):
    from inspect_motion import skeleton_metadata
    from box_root_optimizer import BoxRootOptimizer
    names, _, _ = skeleton_metadata(77)
    frames = 7
    rotations = np.tile(np.eye(3), (frames, 77, 1, 1))
    positions = np.zeros((frames, 77, 3)); positions[:, :, 1] = 1.
    base = dict(local_rot_mats=rotations.copy(), global_rot_mats=rotations.copy(),
                posed_joints=positions, root_positions=positions[:, 0].copy())
    bind = np.tile(np.eye(4), (77, 1, 1)); bind[:, 1, 3] = 1.
    skin = dict(rig_joint_names=names, bind_rig_transform=bind,
                bind_vertices=positions[0].copy(), lbs_indices=np.repeat(np.arange(77)[:, None], 8, axis=1),
                lbs_weights=np.full((77, 8), 1/8))
    spec = dict(schema_version=1, fps=30, frame_count=frames,
                regions={'LeftFoot': dict(mode='explicit', segments=[dict(start_frame=1, end_frame=5,
                    space='world', position_m=[.02, 1., 0.], vertex_id=names.index('LeftFoot'))])})
    # Hold identical parameters so this exercises the actual closure and outer
    # multiplier update without making the test depend on optimizer convergence.
    def fixed_step(self, closure):
        closure(); self.summary = {'test_fixed_parameters': True}
    monkeypatch.setattr(BoxRootOptimizer, 'step', fixed_step)
    args = dict(contact_spec=spec, outer_stage_count=2, iteration_count=1, root_coordinate_mode='physical_box')
    default, before = refine(base, base, skin, **args)
    explicit, same = refine(base, base, skin, authored_point_scaling='metres', **args)
    scaled, after = refine(base, base, skin, authored_point_scaling='tolerance', **args)
    for key in default:
        np.testing.assert_array_equal(default[key], explicit[key])
        np.testing.assert_array_equal(default[key], scaled[key])
    for original, repeated, normalized in zip(before['stage_records'], same['stage_records'], after['stage_records']):
        assert original['objective'] == repeated['objective']
        assert normalized['max_active_point_violation_m'] == original['max_active_point_violation_m']
        assert normalized['objective']['authored_contact']/original['objective']['authored_contact'] == pytest.approx(1/.005**2)
