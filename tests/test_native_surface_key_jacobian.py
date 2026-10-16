"""Exact-key material derivatives retain both placements and control ordering."""
from pathlib import Path
import copy, sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_pair_contact_objectives import separated
from native_partner_surface_rows import SurfaceRows
from native_surface_key_jacobian import linearize


def fixture(models):
    scene = copy.deepcopy(models['A'].scene)
    scene.actors['A']['placement'] = (np.array([.2, -.1, .3]), Rotation.from_euler('xyz', [12, 34, -9], degrees=True).as_matrix())
    scene.actors['B']['placement'] = (np.array([-.3, .2, -.1]), Rotation.from_euler('zy', [-14, 7], degrees=True).as_matrix())
    layouts = {n: dict(nodes=m.nodes, degrees=m.degrees, active_keys=m.active.tolist()) for n, m in models.items()}
    point = lambda n: dict(actor=n, vertices=[0, 1], weights=[.3, .7])
    rows = []
    for key in [2, 3, 4, 5]:
        rows.append(dict(kind='triangle-separation', time_s=float(models['A'].clock[key]),
            normal_world=[.6, .8, 0.], left=point('A'), right=point('B'), constant_m=0.))
    rows.append(dict(kind='world-plane', time_s=float(models['A'].clock[3]),
        normal_world=[0., 1., 0.], left=point('A'), right=None, constant_m=.12))
    return SurfaceRows(scene, rows, {}), layouts


def test_complete_sparse_key_jacobian_matches_native_interval_finite_differences(separated):
    models, _ = separated; surface, layouts = fixture(models)
    gaps, jac, report = linearize(surface, layouts)
    def evaluate(value):
        offset = 0; worlds = {}
        for n, m in models.items():
            worlds[n] = m.worlds(value[offset:offset+m.size], quantized=False); offset += m.size
        def vertices(name, time):
            m = models[name]; index = int(np.flatnonzero(m.times == time)[0])
            p, r = surface.scene.actors[name]['placement']
            return m.rig.vertices(worlds[name][index])@r.T+p
        return surface.gaps(vertices)
    np.testing.assert_allclose(gaps, evaluate(np.zeros(report['controls'])), atol=1e-12, rtol=0)
    fd = []
    for i in range(report['controls']):
        delta = np.eye(report['controls'])[i]*1e-6
        fd.append((evaluate(delta)-evaluate(-delta))/2e-6)
    np.testing.assert_allclose(jac.toarray(), np.stack(fd, axis=1), atol=3e-9, rtol=2e-7)
    assert jac.shape == (len(surface.rows), sum(m.size for m in models.values()))
    assert jac[0].nnz == jac[3].nnz == 0 and jac[1:3, :models['A'].size].nnz
    assert jac[1:3, models['A'].size:].nnz and not report['quality_approved']
    assert report['native_pose_vertex_maximum_error_m'] <= 1e-12


@pytest.mark.parametrize('fault', ['fractional-time', 'endpoint', 'boolean-key', 'repeated-key',
    'missing-actor', 'zero-cap', 'bad-weights', 'bad-normal', 'envelope', 'budget'])
def test_unsupported_or_incomplete_surface_model_rejects(separated, fault):
    models, _ = separated; surface, layouts = fixture(models); layouts = copy.deepcopy(layouts)
    kwargs = {}
    if fault == 'fractional-time': surface.rows[0]['time_s'] += .00001
    elif fault == 'endpoint': layouts['A']['active_keys'] = [0, 3]
    elif fault == 'boolean-key': layouts['A']['active_keys'] = [True, 3]
    elif fault == 'repeated-key': layouts['A']['active_keys'] = [3, 3]
    elif fault == 'missing-actor': layouts.pop('B')
    elif fault == 'zero-cap': layouts['A']['degrees'] = [0.]
    elif fault == 'bad-weights': surface.rows[0]['left']['weights'] = [-.1, 1.1]
    elif fault == 'bad-normal': surface.rows[0]['normal_world'] = [0., 0., 0.]
    elif fault == 'envelope': surface.rows[0]['plane_guidance'] = 'minimum-envelope'
    else: kwargs['maximum_nonzeros'] = 1
    with pytest.raises(ValueError): linearize(surface, layouts, **kwargs)


def test_canonical_vertex_disagreement_rejects_before_any_proposal(separated, monkeypatch):
    import native_surface_key_jacobian as module
    models, _ = separated; surface, layouts = fixture(models); original = module.AffineKeyPose.evaluate
    def changed(self, value):
        world, vertices, skin, joints = original(self, value); vertices = vertices.copy(); vertices[0, 0] += 1e-8
        return world, vertices, skin, joints
    monkeypatch.setattr(module.AffineKeyPose, 'evaluate', changed)
    with pytest.raises(ValueError, match='disagree'): linearize(surface, layouts)
