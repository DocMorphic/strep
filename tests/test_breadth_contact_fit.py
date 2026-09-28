import numpy as np
import pytest
from test_rig_clearance import setup
from breadth_contact_fit import SupportClearanceFitter


def test_support_objective_derivative_and_zero_weight_control():
    from rig_clearance_fit import ClearanceFitter
    rig, world, local, spec, targets = setup()
    surfaces = np.array([rig.vertices(w) for w in world])
    guides = {side:dict(anchors_xz_m=[[.02,.04]]*3, weights=[.25,1,.25]) for side in spec['patches']}
    fitter = SupportClearanceFitter(rig,spec,local,targets,np.ones(3),surfaces,guides=guides,support_weight=40)
    x = np.random.default_rng(799).normal(size=len(fitter.bounds))*.012
    residual, jac = fitter.objective_pair(1,x,[])
    for col in range(len(x)):
        d = np.eye(len(x))[col]*1e-7
        numeric = (fitter.objective_pair(1,x+d,[])[0]-fitter.objective_pair(1,x-d,[])[0])/2e-7
        np.testing.assert_allclose(jac[:,col],numeric,atol=5e-7,rtol=4e-5)
    control = SupportClearanceFitter(rig,spec,local,targets,np.ones(3),surfaces,guides=guides,support_weight=0)
    original = ClearanceFitter(rig,spec,local,targets,np.ones(3),surfaces)
    base_r, base_j = original.objective_pair(1,x,[])
    actual_r, actual_j = control.objective_pair(1,x,[])
    np.testing.assert_array_equal(actual_r[:len(base_r)],base_r)
    np.testing.assert_array_equal(actual_j[:len(base_j)],base_j)
    assert np.count_nonzero(actual_r[len(base_r):]) == 0


def test_support_guides_skip_short_airborne_and_fade(monkeypatch):
    import breadth_contact_fit as module
    masks={side+role:np.ones(10,bool) for side in ['Left','Right'] for role in ['Foot','ToeBase']}
    monkeypatch.setattr(module,'signals',lambda report:(masks,'source_model_predictions'))
    native={side:np.array([0,0,.1,0,0,0,0,0,0,.1]) for side in ['Left','Right']}
    surfaces=np.zeros((10,24,3));surfaces[:,:,0]=np.arange(10)[:,None]*.01
    regions={'Left':np.arange(12),'Right':np.arange(12,24)}
    result=module.support_guides({},native,surfaces,regions)
    assert result['confirmed'] is False
    assert [(i['start_frame'],i['end_frame_exclusive']) for i in result['intervals']]==[(3,9),(3,9)]
    g=result['guides']['Left']
    np.testing.assert_allclose(g['weights'],[0,0,0,.25,.75,1,1,.75,.25,0])
    np.testing.assert_allclose(np.array(g['anchors_xz_m'])[3:9,0],.04)
