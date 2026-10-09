"""Coupled values, cross-frame derivatives and fixed exterior keys without assets."""
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import coupled_pose_window as module
from test_sparse_pose_jacobian import FixtureProblem


def window(monkeypatch,frames=None):
    def make(folder,skin,frame,grouping):
        p=FixtureProblem(grouping,'box');p.frame=frame;p.names=['Root','Hand'];p.editable=[0]
        p.config.update(fps=30,max_root_lift_m=.22)
        p.references={n:p.t(np.broadcast_to([[0,.4,0],[.08,.4,.02]],(5,2,3)).copy()) for n in ['raw','limb','previous']}
        p.references['raw'][1,0,0]=.004
        p.neighbors={f:p.t([[0,.4,0],[.08,.4,.02]]) for f in [frame-1,frame+1] if 0<=f<5}
        p.labels=['point:LeftHand','normal:palm','floor','object:object:first','object:object:second']
        p.labels+=[prefix+':'+name for prefix in ['all-reference-position']+['all-reference-speed:'+str(f) for f in p.neighbors] for name in p.names]
        p.seed=np.array([.03,-.02,.01,.003])
        def independent(x,*,neighbors=None):
            positions=p.fk(p.t(x))[1].detach().numpy();neighbors=p.neighbors if neighbors is None else neighbors
            body={}
            for name,ref in p.references.items():
                displacement=positions-ref.numpy()[frame]
                speeds=[float(np.linalg.norm((displacement-(point.numpy()-ref.numpy()[f]))*30,axis=1).max()) for f,point in sorted(neighbors.items())]
                body[name]=dict(neighbor_max_added_speeds_m_s=speeds)
            return dict(pose_checks_passed=False,body=body),dict(posed_joints=positions[None])
        p.independent=independent
        return p
    monkeypatch.setattr(module,'RestorationProblem',make)
    return module.CoupledPoseWindow(None,None,[1,2,3] if frames is None else frames,row_chunk=4)


def test_complete_coupled_values_and_every_derivative_match_dense(monkeypatch):
    w=window(monkeypatch)
    for x in [w.seed,w.seed+np.array([.001,-.002,.003,.001]*3)]:
        values,jac=w.pair(x);dense,derivatives=w.dense_pair(x)
        np.testing.assert_allclose(values,dense,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(jac,derivatives,rtol=1e-10,atol=1e-10)
        assert len(values)==len(w.labels) and jac.shape==(len(w.labels),12)


def test_internal_speed_has_both_control_blocks_and_fixed_edges_do_not(monkeypatch):
    w=window(monkeypatch);x=w.seed.copy();x[7]+=.004
    _,jac=w.pair(x)
    internal=w.labels.index('all-reference-speed:2:Root:frame-1')
    exterior=w.labels.index('all-reference-speed:0:Root:frame-1')
    assert jac[internal,3]!=0 and jac[internal,7]==-jac[internal,3]
    assert jac[exterior,3]!=0 and np.all(jac[exterior,4:]==0)
    direction=np.zeros(w.dim);direction[3]=direction[7]=1
    assert jac[internal]@direction==0 and jac[exterior]@direction!=0


def test_coordinated_ramp_can_pass_speed_limits_that_frozen_center_cannot(monkeypatch):
    w=window(monkeypatch);x=np.zeros(w.dim);x[3]=.04;x[7]=.08;x[11]=.04
    values,_=w.pair(x)
    body_rows=[i for i,label in enumerate(w.labels) if label.startswith('all-reference-')]
    assert np.all(values[body_rows]>=0)
    center=w.problems[1];isolated=center.geometry_slack(center.t(x[4:8])).detach().numpy()
    speed_rows=[i for i,label in enumerate(center.labels) if label.startswith('all-reference-speed:')]
    assert np.all(isolated[speed_rows]<0)
    # Contacts and geometry remain separate gates; this proves temporal coupling only.
    assert not w.independent(x)[0]['window_checks_passed']


def test_every_vector_reference_population_matches_coupled_rows_and_derivatives(monkeypatch):
    w=window(monkeypatch);x=w.seed.copy();x[7]+=.002;x[11]+=.001
    vectors=w.vector_linearization(x);values,jac=w.pair(x)
    offsets=vectors['offsets'];derivatives=vectors['jacobian'];radii=vectors['limits'];scales=vectors['scales'];distance=vectors['distance'];rows=vectors['rows']
    length=np.linalg.norm(offsets,axis=1)
    slacks=np.where(distance,(radii-length)/scales,1-length**2/radii**2)
    gradients=np.where(distance[:,None],-np.einsum('rk,rkd->rd',offsets,derivatives)/np.maximum(length,1e-12)[:,None]/scales[:,None],
        -2*np.einsum('rk,rkd->rd',offsets,derivatives)/radii[:,None]**2)
    for row in set(rows):
        active=(rows==row)&(slacks==slacks[rows==row].min())
        np.testing.assert_allclose(slacks[active],values[row],rtol=1e-11,atol=1e-11)
        np.testing.assert_allclose(gradients[active].mean(0),jac[row],rtol=1e-9,atol=1e-9)
    direction=np.random.default_rng(902).normal(size=w.dim);step=1e-6
    plus=w.vector_linearization(x+step*direction);minus=w.vector_linearization(x-step*direction)
    np.testing.assert_allclose((plus['offsets']-minus['offsets'])/(2*step),np.einsum('rkd,d->rk',derivatives,direction),rtol=2e-5,atol=1e-8)


def test_vector_scaling_cannot_modify_cached_derivatives(monkeypatch):
    w=window(monkeypatch);before=w.vector_linearization(w.seed)
    changed=w.vector_linearization(w.seed);changed['jacobian']*=17;changed['offsets'][:]=0
    after=w.vector_linearization(w.seed)
    for key in before:np.testing.assert_array_equal(before[key],after[key])


def test_independent_audit_uses_edited_neighbors_without_mutating_fixed_poses(monkeypatch):
    w=window(monkeypatch);x=w.seed.copy();x[7]+=.008
    frozen={p.frame:{f:v.numpy().copy() for f,v in p.neighbors.items()} for p in w.problems}
    audit,motion=w.independent(x)
    poses=motion['posed_joints'];assert poses.shape==(3,2,3)
    actual=audit['frames'][0]['body']['raw']['neighbor_max_added_speeds_m_s'][1]
    reference=w.problems[0].references['raw'].numpy()
    expected=np.linalg.norm(((poses[0]-reference[1])-(poses[1]-reference[2]))*30,axis=1).max()
    assert actual==expected and not audit['window_checks_passed']
    for p in w.problems:
        for f,v in p.neighbors.items():np.testing.assert_array_equal(v.numpy(),frozen[p.frame][f])


@pytest.mark.parametrize('frames',[[0,1],[3,4],[0,1,2,3,4]])
def test_available_clip_endpoint_edges_are_preserved(monkeypatch,frames):
    w=window(monkeypatch,frames);values,jac=w.pair(w.seed);dense,derivatives=w.dense_pair(w.seed)
    np.testing.assert_allclose(values,dense,rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(jac,derivatives,rtol=1e-10,atol=1e-10)


@pytest.mark.parametrize('frames',[[],[1],[1,3],[2,1],[1,1],[True,2],[-1,0],list(range(6)),(1,2)])
def test_invalid_frames_never_load_native_assets(monkeypatch,frames):
    monkeypatch.setattr(module,'RestorationProblem',lambda *a,**k:pytest.fail('Invalid frames reached assets'))
    with pytest.raises(ValueError):module.CoupledPoseWindow(None,None,frames)


@pytest.mark.parametrize('x',[np.zeros(11),np.full(12,float('nan'))])
def test_invalid_controls_rejected_before_queries(monkeypatch,x):
    w=window(monkeypatch)
    for p in w.problems:p.fk=lambda *a:pytest.fail('Invalid controls reached FK')
    with pytest.raises(ValueError):w.pair(x)
    with pytest.raises(ValueError):w.independent(x)


@pytest.mark.parametrize('chunk',[True,0,33])
def test_invalid_derivative_chunk_rejected(monkeypatch,chunk):
    monkeypatch.setattr(module,'RestorationProblem',lambda *a,**k:pytest.fail('Invalid chunk reached assets'))
    with pytest.raises(ValueError):module.CoupledPoseWindow(None,None,[1,2],row_chunk=chunk)
