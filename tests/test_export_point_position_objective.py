import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from export_point_position_objective import ExportPointPositionObjective
from support_contact_v5 import rodrigues


def fixture(frames=7):
    r = torch.eye(3, dtype=torch.float64).repeat(frames, 1, 1, 1)
    p = torch.zeros(frames, 1, 3, dtype=torch.float64)
    skin = dict(rig_joint_names=['LeftFoot'], lbs_indices=np.zeros((1, 8), dtype=int),
                lbs_weights=np.arange(1, 9)[None]/36, bind_vertices=np.array([[1., 0., 0.]]),
                bind_rig_transform=np.eye(4)[None])
    pins = [dict(start_frame=1, end_frame=2, vertex_id=0, space='world', position_m=[1., 0., 0.]),
            dict(start_frame=4, end_frame=5, vertex_id=0, space='world', position_m=[1., 0., 0.])]
    spec = dict(schema_version=1, fps=30, frame_count=frames, regions={'LeftFoot': dict(mode='explicit', segments=pins)})
    return r, p, skin, spec


def objective(r, p, skin, spec, **kwargs):
    with patch('export_point_position_objective.regions', return_value={'LeftFoot': np.array([0])}):
        return ExportPointPositionObjective(r, p, [-1], skin, spec, **kwargs)


def test_every_interval_keeps_fixed_identity_and_original_tolerance():
    r, p, skin, spec = fixture(); obj = objective(r, p, skin, spec)
    assert obj.loss(r, p) == 0
    q = p.clone(); q[4:6, 0, 0] = .006
    assert obj.loss(r, q) > 0
    rows = obj.record()['rows']
    assert rows[0]['samples'] == rows[1]['samples'] == 5
    assert rows[0]['maximum_error_m'] < 1e-12
    assert rows[1]['maximum_error_m'] == pytest.approx(.006)
    assert obj.record()['tolerance_m'] == .005
    assert obj.vertices == [0]


def test_rotation_arc_misses_pin_between_exact_native_endpoints():
    r, p, skin, spec = fixture(2)
    # Root translation cancels the rotating material point at both keys;
    # linear translation plus spherical rotation does not cancel between them.
    spec['regions']['LeftFoot']['segments'] = [dict(start_frame=0, end_frame=1, vertex_id=0,
        space='world', position_m=[0., 0., 0.])]
    angles = torch.zeros(2, 1, 3, dtype=torch.float64); angles[1, 0, 2] = 1.
    r = rodrigues(angles); p[:, 0] = -r[:, 0, :, 0]
    obj = objective(r, p, skin, spec)
    points = obj.points(r, p)
    assert torch.linalg.vector_norm(points[::4], dim=-1).max() < 1e-7
    assert obj.loss(r, p) > 0
    assert obj.record()['rows'][0]['maximum_error_m'] > .12


def test_loss_gradient_and_multiplier_updates():
    r, p, skin, spec = fixture(); obj = objective(r, p, skin, spec)
    q = p.clone(); q[:, 0, 0] = .01; q.requires_grad_()
    assert torch.autograd.gradcheck(lambda x: obj.loss(r, x), (q,), atol=1e-4)
    first = float(obj.loss(r, q).detach()); obj.advance_stage(4)
    assert float(obj.loss(r, q).detach()) > first
    assert obj.record()['penalty'] == 1200


def test_ambiguous_points_or_wrong_clocks_are_rejected():
    r, p, skin, spec = fixture(); obj = objective(r, p, skin, spec)
    with pytest.raises(ValueError, match='accepted point'): obj.advance_stage(4)
    with pytest.raises(ValueError, match='clocks'): obj.loss(r[:2], p[:2])
    spec['regions']['LeftFoot']['segments'][0].pop('vertex_id')
    with pytest.raises(ValueError, match='fixed material'): objective(r, p, skin, spec)
