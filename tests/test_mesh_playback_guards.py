"""Playback values, independent derivatives, protected targets and mode isolation."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
from threadpoolctl import threadpool_limits
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_mesh_contact_feasibility import setup
from mesh_contact_playback import MeshPlaybackFloor
from mesh_contact_feasibility import MeshContactFeasibility
from mesh_contact_guarded_trials import GuardedMeshTrials
from rig_mesh_trajectory import MeshContactTrajectoryFitter,CoupledMeshContactFitter,run
from rig_loop import encode
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from rig_subframe_floor import inspect
from strep import save,read,sha256


@pytest.mark.parametrize('shift',[0.,-.26])
def test_playback_matches_actual_exported_mesh_and_native_clock(tmp_path,shift):
    _,_,f,c,_=setup(tmp_path,shift);p=MeshPlaybackFloor(c)
    x=np.random.default_rng(428).normal(size=np.prod(c.shape))*.002
    values=c.parameters(x);world=np.array([f.pose(i,v)[0] for i,v in enumerate(values)])
    path=tmp_path/'baked.glb';encode(f.rig,world,set(p.animated),f.spec['root_node'],path,'fixture')
    rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,0)
    floor=np.array([1+rig.vertices(sampler.sample(float(t)))[:,1].min()/f.spec['screen']['floor_depth_m'] for t in p.times])
    np.testing.assert_allclose(p.values(x),floor,atol=2e-5,rtol=0)
    assert len(p.times)==inspect(path,.005)['samples']


def test_playback_derivatives_match_independent_continuous_skin_witnesses(tmp_path):
    _,_,f,c,_=setup(tmp_path,-.26);p=MeshPlaybackFloor(c)
    x=np.random.default_rng(41).normal(size=np.prod(c.shape))*.003
    floor,jac=p.pair(x);ids=p.data[2].copy()
    def continuous(z):
        values=c.parameters(z);world=np.array([f.pose(i,v)[0] for i,v in enumerate(values)])
        from rig_transition import localize
        from scipy.spatial.transform import Rotation
        from rig_clip_import import AnimationSampler
        local=localize(world,f.rig.parents);found=[]
        for t,a,b in zip(p.times,p.left,p.right):
            nodes=copy.deepcopy(f.rig.document['nodes']);clock=p.clock[a:b+1]
            for node in p.animated:
                nodes[node].pop('matrix',None);nodes[node]['scale']=[1,1,1]
                nodes[node]['translation']=AnimationSampler.value('translation',clock,local[a:b+1,node,:3,3],'LINEAR',t).tolist()
                q=Rotation.from_matrix(local[a:b+1,node,:3,:3]).as_quat()
                nodes[node]['rotation']=AnimationSampler.value('rotation',clock,q,'LINEAR',t).tolist()
            from gltf_tools import global_matrices
            found.append(f.rig.vertices(global_matrices({'nodes':nodes}))[ids[len(found)],1])
        return 1+np.array(found)/.005
    for _ in range(4):
        d=np.random.default_rng(79+_).normal(size=len(x));d/=np.linalg.norm(d);eps=1e-6
        numeric=(continuous(x+eps*d)-continuous(x-eps*d))/(2*eps)
        np.testing.assert_allclose(jac@d,numeric,atol=3e-5,rtol=2e-5)


def test_playback_root_lift_is_verified_under_the_original_limits(tmp_path):
    _,_,f,c,_=setup(tmp_path,-.26);p=MeshPlaybackFloor(c);guard=GuardedMeshTrials(c,.01,p)
    zero=np.zeros(np.prod(c.shape));floor,_,lift=guard.observe(zero)
    assert floor.min()<.01 and lift is not None
    values=zero+guard.lift_direction*lift
    assert c.inequality_pair(values)[0].min()>=-1e-8
    assert guard.observe(values)[0].min()>=.01-1e-8
    assert p.values(values).min()>=.01-1e-8


def test_protected_input_contact_survives_pursuit_of_an_unreachable_target(tmp_path):
    _,spec,f,c,_=setup(tmp_path)
    spec['contacts'][0]['target_position_m']=f.rig.vertices(f.world[3]).mean(axis=0).tolist()
    spec['contacts'].append(dict(patch=spec['contacts'][0]['patch'],start_frame=4,end_frame_exclusive=5,target_position_m=[0.,-2.,0.]))
    f=MeshContactTrajectoryFitter(f.rig,spec,f.local,np.ones(7));c=CoupledMeshContactFitter(f,c.basis)
    stage=MeshContactFeasibility(c,True,True)
    assert stage.protected.tolist()==[0,2]
    with threadpool_limits(limits=1):values,_,result=stage.solve(tmp_path,3,6)
    assert result['protected_contacts_reached'] and result['floor_reached'] and not result['contacts_reached']
    records=read(tmp_path/'contacts-trials.json')['records'];data=np.load(tmp_path/'contacts-trials.npz',allow_pickle=False)
    assert data['protected_contact_indices'].tolist()==[0,2]
    for r in records:
        if r['status']=='retained':
            parameters=data['warm_parameters']+data['basis']@data['controls'][r['index']].reshape(c.shape)
            points=f.rig.vertices(f.pose(3,parameters[3])[0]);error=np.linalg.norm(points.mean(axis=0)-spec['contacts'][0]['target_position_m'])
            assert error<=.02+1e-10
    np.testing.assert_allclose(values,data['warm_parameters']+data['basis']@data['selected_controls'].reshape(c.shape),atol=1e-12)


def test_actual_cli_opt_in_archives_playback_and_preservation_contract(tmp_path):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    result=run(source,draft,tmp_path/'trial',2,5,True,3,True,True)
    q=read(tmp_path/'trial/request.json')
    assert q['playback_guards'] and 'mesh_contact_playback.py' in q['implementation']
    assert result['solver']['playback_guards'] and not result['quality_approved']
    assert sha256(tmp_path/'trial/contact-spec.json')==sha256(draft)


@pytest.mark.parametrize('choice',[1,None,'true'])
def test_playback_flag_requires_boolean(tmp_path,choice):
    _,_,_,c,_=setup(tmp_path)
    with pytest.raises(ValueError,match='Playback guards'):MeshContactFeasibility(c,True,choice)


def test_playback_requires_guarded_mode_before_creating_output(tmp_path):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    with pytest.raises(ValueError,match='Playback guards'):run(source,draft,tmp_path/'trial',feasibility=True,playback_guards=True)
    assert not (tmp_path/'trial').exists()


def test_aborted_optimizer_preserves_evaluated_proposals_and_best_controls(tmp_path,monkeypatch):
    import mesh_contact_feasibility as module
    _,_,_,c,_=setup(tmp_path);stage=MeshContactFeasibility(c,True,True)
    def abort(fun,z,**kwargs):
        trial=z.copy();controls=trial[:-1].reshape(c.shape);controls[:,1]=.005
        kwargs['constraints']['fun'](trial)
        raise RuntimeError('Deliberate optimizer interruption')
    monkeypatch.setattr(module,'minimize',abort)
    with pytest.raises(RuntimeError,match='interruption'):stage.solve(tmp_path,3,3)
    report=read(tmp_path/'contacts-trials.json');rows=report['records'];data=np.load(tmp_path/'contacts-trials.npz',allow_pickle=False)
    assert report['aborted'] and report['error_type']=='RuntimeError' and 'interruption' in report['error']
    assert len(rows)==len(data['controls'])==1 and rows[0]['status']=='retained'
    np.testing.assert_array_equal(data['selected_controls'],data['controls'][0])


def test_fixed_playback_floor_cannot_be_rescued_by_root_controls(tmp_path):
    _,_,_,c,_=setup(tmp_path,-.26,fixed=True);p=MeshPlaybackFloor(c)
    assert p.lift(np.zeros(np.prod(c.shape)),.01) is None


def test_floor_restoration_can_use_verified_lift_without_invoking_optimizer(tmp_path,monkeypatch):
    import mesh_contact_feasibility as module
    _,_,f,c,_=setup(tmp_path,-.26);stage=MeshContactFeasibility(c,True,True)
    def forbidden(*args,**kwargs):raise AssertionError('Feasible direct restoration must not invoke optimizer')
    monkeypatch.setattr(module,'minimize',forbidden)
    values,trace,result=stage.phase(tmp_path,'floor',3)
    assert result['deterministic_floor_restoration'] and result['solver_success'] and result['iterations']==0
    assert result['initial_violation']>0 and result['final_violation']==0 and result['floor_constraint_min']>=.01
    assert not trace and stage.playback.values(data:=np.load(tmp_path/'floor-trials.npz')['selected_controls']).min()>=.01
    assert c.inequality_pair(data)[0].min()>=-1e-8
