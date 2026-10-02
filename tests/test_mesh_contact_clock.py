"""Explicit timing, serialized protection and independent contact derivatives."""
from pathlib import Path
from types import SimpleNamespace
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_mesh_contact_feasibility import setup
from mesh_contact_clock import layout,validate_clock
from mesh_contact_playback import MeshPlaybackFloor
from mesh_contact_feasibility import MeshContactFeasibility
from rig_mesh_trajectory import MeshContactTrajectoryFitter,CoupledMeshContactFitter,run
from rig_asset import RigAsset
from rig_loop import encode
from native_support_clock import NativeSupportSampler
from rig_subframe_contacts import inspect
from strep import sha256,read,save


@pytest.mark.parametrize('choice',[True,None,1,'keys','FRAME-HOLD'])
def test_unknown_contact_clock_is_rejected(choice):
    with pytest.raises(ValueError,match='Contact clock'):validate_clock(choice)


def test_half_open_holds_include_last_active_frame_tail_but_exclude_next_key():
    keys=(np.arange(5,dtype=np.float32)/30).astype(float)
    times=np.sort(np.r_[keys,keys[1:]+1e-10,(keys[:-1]+keys[1:])/2])
    spec=dict(frames=4,fps=30,contacts=[dict(start_frame=1,end_frame_exclusive=3)])
    authored,groups=layout(spec,times,'authored-keys');held,hgroups=layout(spec,times,'frame-hold')
    np.testing.assert_array_equal(authored,keys[1:3])
    np.testing.assert_array_equal(held,times[(times>=keys[1])&(times<keys[3])])
    assert (keys[2]+keys[3])/2 in held and keys[3] not in held and np.all(hgroups==0)


@pytest.mark.parametrize('choice',['authored-keys','frame-hold'])
def test_quantized_centroid_values_match_independent_full_mesh_export(tmp_path,choice):
    _,spec,f,c,_=setup(tmp_path)
    spec['patches']['Second proxy']=dict(vertices=[0,2])
    spec['contacts'].append(dict(patch='Second proxy',start_frame=2,end_frame_exclusive=5,target_position_m=[-.2,.19,.1]))
    f=MeshContactTrajectoryFitter(f.rig,spec,f.local,np.ones(7));c=CoupledMeshContactFitter(f,c.basis)
    p=MeshPlaybackFloor(c,contact_clock=choice);x=np.random.default_rng(621).normal(size=np.prod(c.shape))*.003
    values=c.parameters(x);world=np.array([f.pose(i,v)[0] for i,v in enumerate(values)])
    path=tmp_path/'baked.glb';encode(f.rig,world,set(p.animated),spec['root_node'],path,'fixture')
    rig=RigAsset.load(path);sampler=NativeSupportSampler(rig.document,rig.binary,0)
    expected=[]
    for time,index in zip(p.contact_times,p.contact_groups):
        target=spec['contacts'][index];ids=spec['patches'][target['patch']]['vertices']
        point=rig.vertices(sampler.sample(float(time)))[ids].mean(axis=0)
        expected.append(1-np.linalg.norm(point-target['target_position_m'])/.02)
    np.testing.assert_allclose(p.contact_values(x),expected,atol=2e-6,rtol=0)
    exported=copy.deepcopy(spec);exported['glb_sha256']=sha256(path);screen=inspect(path,exported,choice)
    np.testing.assert_allclose([1-r['error_max_m']/.02 for r in screen['contacts']],
        [p.contact_values(x)[p.contact_groups==i].min() for i in range(2)],atol=2e-6,rtol=0)
    assert screen['samples']==len(p.contact_times) and not screen['quality_approved']


def continuous_contacts(f,c,p,x):
    from scipy.spatial.transform import Rotation
    from rig_transition import localize
    from rig_clip_import import AnimationSampler
    from gltf_tools import global_matrices
    values=c.parameters(x);world=np.array([f.pose(i,v)[0] for i,v in enumerate(values)]);local=localize(world,f.rig.parents)
    found=[]
    for time,index,sample in zip(p.contact_times,p.contact_groups,p.contact_indices):
        a,b=p.left[sample],p.right[sample];nodes=copy.deepcopy(f.rig.document['nodes']);clock=p.clock[a:b+1]
        for node in p.animated:
            nodes[node].pop('matrix',None);nodes[node]['scale']=[1,1,1]
            nodes[node]['translation']=AnimationSampler.value('translation',clock,local[a:b+1,node,:3,3],'LINEAR',time).tolist()
            nodes[node]['rotation']=AnimationSampler.value('rotation',clock,Rotation.from_matrix(local[a:b+1,node,:3,:3]).as_quat(),'LINEAR',time).tolist()
        target=f.spec['contacts'][index];ids=f.spec['patches'][target['patch']]['vertices']
        point=f.rig.vertices(global_matrices({'nodes':nodes}))[ids].mean(axis=0)
        found.append(1-np.linalg.norm(point-target['target_position_m'])/.02)
    return np.array(found)


@pytest.mark.parametrize('choice',['authored-keys','frame-hold'])
def test_contact_jacobian_matches_independent_continuous_full_mesh(tmp_path,choice):
    _,_,f,c,_=setup(tmp_path);p=MeshPlaybackFloor(c,contact_clock=choice)
    rng=np.random.default_rng(65);x=rng.normal(size=np.prod(c.shape))*.003;_,jac=p.contact_pair(x)
    for _ in range(4):
        direction=rng.normal(size=len(x));direction/=np.linalg.norm(direction);eps=1e-6
        numeric=(continuous_contacts(f,c,p,x+eps*direction)-continuous_contacts(f,c,p,x-eps*direction))/(2*eps)
        np.testing.assert_allclose(jac@direction,numeric,atol=3e-5,rtol=2e-5)


def test_derivative_cache_respects_changed_step(tmp_path):
    _,_,_,c,_=setup(tmp_path);p=MeshPlaybackFloor(c);zero=np.zeros(np.prod(c.shape))
    _,first=p.contact_pair(zero,1e-5);_,second=p.contact_pair(zero,.02)
    assert not np.array_equal(first,second)
    _,first=p.pair(zero,1e-5);_,second=p.pair(zero,.02)
    assert not np.array_equal(first,second)


def moving_fixture(tmp_path):
    source,spec,f,c,_=setup(tmp_path)
    world=f.world.copy();world[4:,:,:3,3]+=[.12,0,0]
    path=tmp_path/'moving.glb';encode(f.rig,world,set(range(len(f.order))),spec['root_node'],path,'key success with released tail')
    spec['glb_sha256']=sha256(path)
    spec['contacts'][0]['target_position_m']=RigAsset.load(path).vertices(NativeSupportSampler(RigAsset.load(path).document,RigAsset.load(path).binary,0).sample(float(np.float32(3/30)))).mean(axis=0).tolist()
    return path,spec


def test_full_frame_hold_detects_departure_after_last_active_key(tmp_path):
    path,spec=moving_fixture(tmp_path)
    assert inspect(path,spec,'authored-keys')['sampled_contacts_passed']
    held=inspect(path,spec,'frame-hold')
    assert not held['sampled_contacts_passed'] and held['failed_intervals']==1
    assert held['contacts'][0]['error_max_m']>.05
    assert held['contacts'][0]['worst_time_s']>float(np.float32(3/30))
    assert max(held['contacts'][0]['times_s'])<float(np.float32(4/30))


def test_actual_cli_rejects_hold_even_with_passing_key_and_solver_screens(tmp_path,monkeypatch):
    path,spec=moving_fixture(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    def unchanged(stage,*args,**kwargs):return stage.coupled.fitter.values.copy(),[],dict(solver_success=True,constraint_min=1.)
    monkeypatch.setattr(MeshContactFeasibility,'solve',unchanged)
    result=run(path,draft,tmp_path/'fit',2,2,True,2,True,True,'frame-hold')
    assert read(tmp_path/'fit/independent-inspection.json')['failed_intervals']==0
    assert read(tmp_path/'fit/subframe-floor-inspection.json')['sampled_floor_passed']
    assert result['solver']['solver_success'] and result['retained_input']
    assert read(tmp_path/'fit/audit.json')['flags']==['decoded_contact_clock_screen_failed']
    request=read(tmp_path/'fit/request.json')
    assert request['contact_clock']=='frame-hold' and request['decoded_contact_sampling_hz']==120
    assert 'rig_subframe_contacts.py' in request['implementation'] and 'mesh_contact_clock.py' in request['implementation']
    assert sha256(tmp_path/'fit/playback-contact-inspection.json')==result['outputs']['playback-contact-inspection.json']


def test_frame_hold_requires_playback_before_creating_output(tmp_path):
    source,spec,_,_,_=setup(tmp_path);draft=tmp_path/'draft.json';save(draft,spec)
    with pytest.raises(ValueError,match='require playback'):run(source,draft,tmp_path/'fit',contact_clock='frame-hold')
    assert not (tmp_path/'fit').exists()


def test_serialized_contact_crossing_is_rejected_before_retention(tmp_path,monkeypatch):
    import mesh_contact_feasibility as module
    _,spec,f,c,_=setup(tmp_path);local=f.local.copy();local[:,0,1,3]=1.20000002
    f=MeshContactTrajectoryFitter(f.rig,spec,local,np.ones(7))
    spec['contacts'][0]['target_position_m']=(f.positions[3].mean(axis=0)-[0,.01-1e-8,0]).tolist()
    spec['contacts'].append(dict(patch=spec['contacts'][0]['patch'],start_frame=4,end_frame_exclusive=5,target_position_m=[0,-2,0]))
    f=MeshContactTrajectoryFitter(f.rig,spec,local,np.ones(7));c=CoupledMeshContactFitter(f,c.basis)
    stage=MeshContactFeasibility(c,True,True);x=np.zeros(c.shape);x[:,1]=.01;x=x.ravel()
    raw,_,all_contacts,_=stage.pair(x)
    assert all_contacts[0]>0 and stage.playback.contact_values(x)[0]<0
    values=c.parameters(x);world=np.array([f.pose(i,v)[0] for i,v in enumerate(values)])
    path=tmp_path/'roundoff.glb';encode(f.rig,world,set(stage.playback.animated),spec['root_node'],path,'roundoff crossing')
    exported=copy.deepcopy(spec);exported['glb_sha256']=sha256(path)
    assert inspect(path,exported)['contacts'][0]['failed_samples']==1
    def proposed(fun,z,**kwargs):
        proposal=np.r_[x,z[-1]];kwargs['constraints']['fun'](proposal)
        return SimpleNamespace(x=proposal,success=False,status=9,nit=1)
    monkeypatch.setattr(module,'minimize',proposed)
    stage.solve(tmp_path,2,2)
    rows=read(tmp_path/'contacts-trials.json')['records']
    assert rows[0]['reason']=='protected_contact' and rows[0]['status']=='rejected'


def test_full_hold_protection_depends_on_selected_input_clock(tmp_path):
    path,spec=moving_fixture(tmp_path)
    from target_rig_contact import baseline
    from rig_coupled_pose import window_basis
    rig=RigAsset.load(path);_,local=baseline(rig,7);f=MeshContactTrajectoryFitter(rig,spec,local,np.ones(7));c=CoupledMeshContactFitter(f,window_basis(f.envelope,2))
    keys=MeshContactFeasibility(c,True,True)
    hold=MeshContactFeasibility(c,True,True,contact_clock='frame-hold')
    assert len(keys.protected)==2 and not len(hold.protected)


def test_end_of_clip_hold_is_clipped_to_available_animation(tmp_path):
    _,spec,f,c,_=setup(tmp_path);spec['contacts'][0].update(start_frame=6,end_frame_exclusive=7,target_position_m=f.positions[-1].mean(axis=0).tolist())
    p=MeshPlaybackFloor(c,contact_clock='frame-hold')
    assert p.contact_times.tolist()==[float(p.clock[-1])]
    path=tmp_path/'clip.glb';encode(f.rig,f.world,set(p.animated),spec['root_node'],path,'last frame')
    exported=copy.deepcopy(spec);exported['glb_sha256']=sha256(path)
    result=inspect(path,exported,'frame-hold')
    assert result['sampled_contacts_passed'] and result['samples']==1


def test_contact_inspection_rejects_changed_source(tmp_path,monkeypatch):
    import rig_subframe_contacts as module
    path,spec=moving_fixture(tmp_path);original=module.RigAsset.vertices;changed=[]
    def mutate(self,world):
        result=original(self,world)
        if not changed:path.write_bytes(path.read_bytes()+b'\0');changed.append(True)
        return result
    monkeypatch.setattr(module.RigAsset,'vertices',mutate)
    with pytest.raises(ValueError,match='source changed'):inspect(path,spec)
