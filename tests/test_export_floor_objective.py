import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from export_floor_objective import ExportFloorObjective
from support_contact_v5 import rodrigues


def fixture(frames=3):
    r = torch.eye(3, dtype=torch.float64).repeat(frames, 1, 1, 1)
    p = torch.zeros(frames, 1, 3, dtype=torch.float64)
    skin = dict(lbs_indices=np.zeros((2, 8), dtype=int), lbs_weights=np.tile(np.arange(1, 9)/36, (2, 1)),
                bind_vertices=np.array([[1., .1, 0.], [0., .02, 0.]]), bind_rig_transform=np.eye(4)[None])
    return r, p, skin


def test_existing_depth_is_preserved_per_time_not_whole_clip_peak():
    r, p, skin = fixture(); p[0, 0, 1] = -.03
    obj = ExportFloorObjective(r, p, [-1], skin)
    assert obj.loss(r, p) == 0
    candidate = p.clone(); candidate[2, 0, 1] = -.025
    # New 5 mm penetration remains smaller than the original 10 mm peak;
    # a global-peak-only screen would miss this new local regression.
    assert obj.loss(r, candidate) > 0
    assert obj.record()['maximum_violation_m'] == pytest.approx(.005)
    obj.advance_stage(4)
    assert obj.penalty == 40 and obj.loss(r, candidate) > 0


def test_clear_native_keys_can_still_penetrate_between_them():
    r, p, skin = fixture(2); p[:, 0, 1] = .4
    skin['bind_vertices'] = np.array([[1., 0., 0.], [0., 1., 0.]])
    # Use the same positively weighted point twice so both native endpoints
    # remain clear while the interpolated half-turn dips through the floor.
    skin['bind_vertices'][1] = skin['bind_vertices'][0]
    obj = ExportFloorObjective(r, p, [-1], skin)
    angles = torch.zeros(2, 1, 3, dtype=torch.float64)
    angles[:, 0, 2] = torch.tensor([-.2, -np.pi+.2])
    candidate = rodrigues(angles)
    assert (obj.minimum_heights(candidate, p)[::4] > 0).all()
    assert obj.loss(candidate, p) > 0
    assert obj.record()['maximum_depth_m'] > .59


def test_full_mesh_minimum_and_translation_gradient():
    r, p, skin = fixture()
    obj = ExportFloorObjective(r, p, [-1], skin)
    candidate = p.clone(); candidate[:, 0, 1] = -.04; candidate.requires_grad_()
    # The second vertex, outside the first vertex's skin row, is the witness.
    assert obj.record()['vertex_count'] == 2
    assert torch.autograd.gradcheck(lambda x: obj.loss(r, x), (candidate,), atol=1e-4)
    assert obj.record()['maximum_violation_m'] == pytest.approx(.02, abs=2e-6)


def test_update_requires_a_measured_candidate_and_unchanged_clock():
    r, p, skin = fixture(); obj = ExportFloorObjective(r, p, [-1], skin)
    with pytest.raises(ValueError, match='accepted floor'):
        obj.advance_stage(4)
    with pytest.raises(ValueError, match='clocks'):
        obj.loss(r[:2], p[:2])
