from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import torch
from test_export_point_position_objective import fixture, objective
from export_point_rate_objective import ExportPointRateObjective
from export_rate_objective import ExportRateObjective
from export_floor_objective import ExportFloorObjective
from native_body_objective import NativeBodyObjective
from native_support_objective import FixedPatchSupport
from native_contact_constraints import residuals


def test_complete_constraint_vector_matches_existing_guards_and_keeps_gradients():
    r, p, skin, spec = fixture()
    point = objective(r, p, skin, spec)
    with patch('export_point_rate_objective.regions', return_value={'LeftFoot': np.array([0])}):
        rate = ExportPointRateObjective(r, p, [-1], skin, spec, [0, 6])
    global_rate = ExportRateObjective(r, p, [-1])
    floor = ExportFloorObjective(r, p, [-1], skin)
    body = NativeBodyObjective({'raw': p, 'limb': p.clone()})
    group = FixedPatchSupport(point.skin(r, p).numpy(), .02)
    support = SimpleNamespace(skin=point.skin, groups={('raw', 'LeftFoot'): (np.array([0]), group)})
    q = p.clone(); q[:, 0, 0] = torch.arange(7)*.003; q[:, 0, 1] = -.002
    q.requires_grad_()
    g, labels = residuals(r, q, point, rate, global_rate, floor, body, support, with_labels=True)
    assert len(g) == len(labels)
    assert sum(label.startswith('pin/') for label in labels) == 10
    assert labels.count('floor') == 1
    point.loss(r, q); rate.loss(r, q); global_rate.loss(r, q); floor.loss(r, q); body.loss(q)
    group.loss(point.skin(r, q))
    expected = torch.cat([*point.last, *[v.max().reshape(1) for row in rate.last for v in row],
        *[v.max().reshape(1) for v in global_rate.last], floor.last.max().reshape(1),
        *[v.max().reshape(1) for row in body.last.values() for v in row], group.last])
    torch.testing.assert_close(g, expected, rtol=0, atol=0)
    floor_index = labels.index('floor')
    assert abs(g[floor_index].item()-.4) < 1e-12
    assert torch.isfinite(torch.autograd.grad(g.sum(), q)[0]).all()


def test_a_single_bad_pin_sample_is_not_averaged_away():
    r, p, skin, spec = fixture()
    point = objective(r, p, skin, spec)
    with patch('export_point_rate_objective.regions', return_value={'LeftFoot': np.array([0])}):
        rate = ExportPointRateObjective(r, p, [-1], skin, spec, [0, 6])
    support = SimpleNamespace(skin=point.skin, groups={})
    q = p.clone(); q[5, 0, 0] = .006
    g, labels = residuals(r, q, point, rate, ExportRateObjective(r, p, [-1]),
                         ExportFloorObjective(r, p, [-1], skin), NativeBodyObjective({'raw': p}),
                         support, with_labels=True)
    pins = g[[i for i, label in enumerate(labels) if label.startswith('pin/')]]
    assert pins.max() > .19 and (pins <= 0).sum() >= 8
