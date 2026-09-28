from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read, sha256
from coupled_support_context import context, derivative_proof
from midpoint_support_block import MidpointCoupledBlock, interpolate_rotations
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from types import SimpleNamespace
from target_rig_contact import Fitter
from serialized_pose import SerializedPose


def test_shortest_rotation_arc_near_wrap():
    a = Rotation.from_euler('y', [179], degrees=True).as_matrix()
    b = Rotation.from_euler('y', [-179], degrees=True).as_matrix()
    half = interpolate_rotations(a, b, .5)
    assert np.isclose(Rotation.from_matrix(half).magnitude()[0], np.pi)


def test_safe_endpoint_skin_can_penetrate_halfway():
    class Pendulum(Fitter):
        def __init__(self):
            self.local = np.tile(np.eye(4), (6, 2, 1, 1))
            self.local[:, 0, 1, 3] = .5
            self.local[2, 1, :3, :3] = Rotation.from_euler('z', 60, degrees=True).as_matrix()
            self.local[3, 1, :3, :3] = Rotation.from_euler('z', -60, degrees=True).as_matrix()
            self.nodes, self.order, self.spec = [1], [0, 1], {'root_node': 0}
            self.descendants = {0: np.array([True, True]), 1: np.array([False, True])}
            self.skin = SimpleNamespace(parts=[(np.array([[1]]), np.array([[[0., -1., 0., 1.]]]), np.ones((1, 1)))])
            self.rig = SimpleNamespace(parents=[-1, 0], document={'nodes': [{}, {}]},
                vertices=lambda w: (w[1] @ np.array([0., -1., 0., 1.]))[None, :3])
    fitter = Pendulum()
    p = object.__new__(MidpointCoupledBlock)
    p.fitter, p.root, p.columns, p.width, p.lookup = fitter, 0, 6, 12, {2: 0, 3: 1}
    p.oracle = SerializedPose(fitter.rig, {0, 1}, 0, 6)
    values = np.zeros((6, 6))
    endpoints = [fitter.rig.vertices(fitter.pose(f, values[f])[0])[0, 1] for f in (2, 3)]
    assert np.max(np.abs(endpoints)) < 1e-12
    height, jac = p.midpoint_surface(2, values, quantized=True)
    assert np.isclose(height[0], -.5, atol=1e-7)
    # Moving either endpoint root up affects the midpoint, so the new row
    # provides a usable correction direction rather than only reporting failure.
    assert np.allclose(jac.toarray()[0, [1, 7]], [.5, .5], atol=1e-6)


@pytest.mark.parametrize('identity', ['motion-046-rig-01', 'motion-011-rig-02', 'motion-031-rig-03'])
def test_real_midpoint_derivatives_source_and_neighbor_isolation(identity):
    source = ROOT/'reports/coupled-support-boundaries-v2'/identity/'base'
    with threadpool_limits(limits=1):
        ctx = context(source, source/'selected/character.glb')
        frames = ctx['selection'][0]['frames']
        # Three frames exercise both fixed/edited endpoints and an internal edge.
        frames = frames[:3]
        p = MidpointCoupledBlock(ctx['fitter'], ctx['oracle'], ctx['initial'],
            ctx['source_world'], ctx['source_points'], frames, ctx['envelope'], ctx['targets'])
        proof = derivative_proof(p)
        assert proof['passed'], proof
        assert 'midpoint_floor' in proof['linear_errors']
        assert min(proof['initial_margins'].values()) >= -1e-8, proof
        x = p.initial[p.frames].ravel().copy()
        _, _, constraints, _ = p.pair(x)
        midpoint = [row for row in constraints.linear if row[2] == 'midpoint_floor']
        assert len(midpoint) == len(frames)+1
        for edge, (_, jac, _) in zip(p.affected_edges, midpoint):
            used = set(jac.nonzero()[1]//p.columns)
            allowed = {p.lookup[f] for f in (edge, edge+1) if f in p.lookup}
            assert used <= allowed
        # Source floor exactly matches the separate serialized-pose guard.
        assert p.midpoint_guard(p.initial)[0]
