import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_periodic_contact import clip_step,PeriodicFitter,contract,neighbor_constraints,review_targets
from target_rig_contact import RigAsset,baseline
from rig_contact_authoring import empty_spec
from strep import ROOT,read


def test_projected_step_obeys_both_neighbor_norms():
    random=np.random.default_rng(82)
    for _ in range(100):
        current=np.zeros(9);neighbors=[random.normal(size=9)*.001 for _ in range(2)]
        candidate=random.normal(size=9)*.1
        actual=clip_step(current,candidate,neighbors,.015,.025)
        for n in neighbors:
            assert np.linalg.norm(actual[:3]-n[:3])<=.015+1e-12
            assert max(np.linalg.norm((actual-n)[3:].reshape(-1,3),axis=1))<=.025+1e-12
        assert np.linalg.norm(np.cross(actual[:3],candidate[:3]))<1e-12


def test_periodic_endpoint_targets_and_rotated_neighbors():
    folder=ROOT/'reports/rig-jobs/20260926-212541-f05dcc66/transfer'
    report=read(folder/'report.json');rig=RigAsset.load(folder/'character.glb');world,local=baseline(rig,report['frames']);p,cycle,_=contract(folder,rig,world)
    spec=empty_spec(report);spec['patches']={'heel':dict(vertices=[7382])}
    target=np.array([.3,.0015,.1]);end=(cycle@np.r_[target,1])[:3]
    spec['contacts']=[dict(patch='heel',start_frame=0,end_frame_exclusive=1,target_position_m=target.tolist()),dict(patch='heel',start_frame=p,end_frame_exclusive=p+1,target_position_m=end.tolist())]
    fitter=PeriodicFitter(rig,spec,local,p,cycle)
    assert not fitter.target_conflicts
    np.testing.assert_allclose(fitter.active[0][-1]['target_position_m'],target,atol=1e-12)
    x=np.zeros((p,len(fitter.bounds)));x[0,:3]=[.005,0,.005];x[-1,:3]=cycle[:3,:3]@x[0,:3]
    np.testing.assert_allclose(fitter.neighbors(x,0)[0][:3],x[0,:3],atol=1e-12)
    np.testing.assert_allclose(fitter.neighbors(x,p-1)[1][:3],x[-1,:3],atol=1e-12)
    spec['contacts'][1]['target_position_m'][0]+=.2
    assert PeriodicFitter(rig,spec,local,p,cycle).target_conflicts[0]['unavoidable_endpoint_error_m']>.09
    world[-1,report['root_node'],1,3]+=.01
    with pytest.raises(ValueError,match='terminal pose'):contract(folder,rig,world)


def test_constraint_jacobian_and_boundary_tangent_search():
    from scipy.optimize import minimize
    x=np.array([.015,0.,0.]);neighbors=[np.zeros(3),np.zeros(3)]
    c,j=neighbor_constraints(x,neighbors,.015,.1)
    for i in range(3):
        d=np.eye(3)[i]*1e-7
        numeric=(neighbor_constraints(x+d,neighbors,.015,.1)[0]-neighbor_constraints(x-d,neighbors,.015,.1)[0])/2e-7
        np.testing.assert_allclose(numeric,j[:,i],rtol=1e-7,atol=1e-7)
    target=np.array([.015,.01,0.])
    fit=minimize(lambda y:float(np.sum((y-target)**2)),x,method='SLSQP',constraints={'type':'ineq','fun':lambda y:neighbor_constraints(y,neighbors,.015,.1)[0],'jac':lambda y:neighbor_constraints(y,neighbors,.015,.1)[1]},options={'ftol':1e-12})
    actual=clip_step(x,fit.x,neighbors,.015,.1)
    assert np.linalg.norm(actual)<=.015+1e-10 and actual[1]>.005
    assert np.linalg.norm(actual-target)<np.linalg.norm(x-target)


def test_terminal_only_targets_export_at_every_wrap():
    cycle=np.eye(4);cycle[0,3]=.2;patches={'heel':dict(vertices=[1])}
    # A terminal-only target has been folded back by the fitter to phase zero.
    active=[[dict(patch='heel',target_position_m=[.1,0,0])],[],[],[]]
    targets=review_targets(active,patches,4,cycle,13)
    assert [t['output_frames'] for t in targets]==[[dict(frame=f,weight=1.)] for f in [0,4,8,12]]
    np.testing.assert_allclose([t['target_position_m'][0] for t in targets],[.1,.3,.5,.7])


def test_periodic_export_keeps_terminal_only_constraint_in_repeated_track(tmp_path):
    import shutil
    from strep import save,sha256
    from rig_loop import encode
    from rig_periodic_contact import run
    original=ROOT/'reports/rig-jobs/20260926-212541-f05dcc66/transfer'
    rig=RigAsset.load(original/'character.glb');report=read(original/'report.json');world,_=baseline(rig,2)
    source=tmp_path/'input';source.mkdir();root=report['root_node']
    poses=np.repeat(world[:1],5,axis=0)
    encode(rig,poses,{c['target']['node'] for c in rig.document['animations'][0]['channels']},root,source/'character.glb','Synthetic constant-pose endpoint constraint regression')
    report.update(frames=5,glb_sha256=sha256(source/'character.glb'))
    save(source/'report.json',report)
    save(source/'timeline.json',dict(period_frames=4,cycle_transform=np.eye(4).tolist(),contributors=[[dict(frame=f%4,weight=1.,cycle_offset=f//4)] for f in range(5)]))
    save(source/'contacts.json',dict(origin='none_supplied',intervals=[]));save(source/'events.json',dict(events=[]))
    for name in ('inventory.json','rig-profile.json'):shutil.copyfile(original/name,source/name)
    spec=empty_spec(report);spec['patches']={'endpoint':dict(vertices=[7382])}
    spec['contacts']=[dict(patch='endpoint',start_frame=4,end_frame_exclusive=5,target_position_m=rig.vertices(world[0])[7382].tolist())]
    save(tmp_path/'spec.json',spec);run(source,tmp_path/'spec.json',tmp_path/'out')
    repeated=read(tmp_path/'out/repeated/contact-review.json')
    assert [e['frame'] for t in repeated['authored_targets'] for e in t['output_frames']]==[0,4,8,12]
    assert read(tmp_path/'out/runtime-cycle.json')['glb_sha256']==sha256(tmp_path/'out/character.glb')
