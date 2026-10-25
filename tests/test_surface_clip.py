from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from surface_clip import SurfaceClip
from surface_pose_key_export import replace_keys
from surface_pose_interpolation import SampledPoseWindow
from surface_pose_feasibility import propose
from rig_asset import RigAsset
from gltf_tools import write_glb
from test_native_support import fixture


def options():
    return dict(animation_index=0,root=0,rotations=[1,2,3],angles_degrees=[45.,45.,45.],contacts=[],
        limits=dict(root_horizontal_m=.15,root_vertical_m=.75,floor_depth_m=.005,contact_error_m=.02,root_step_m=.025,rotation_step_degrees=5.),
        fitting=dict(root_reserve_m=1e-5,angle_reserve_radians=1e-5,step_reserve_m=1e-5,step_reserve_radians=1e-5,floor_reserve_m=.0005,contact_reserve_m=.0005),
        sampling=dict(dense_hz=20,initial_fractions=[.25,.5,.75],maximum_samples=1000))


def test_arbitrary_rig_window_export_and_complete_audit(tmp_path):
    path,rig,reader,_=fixture(tmp_path);raw=path.read_bytes();context=SurfaceClip(rig,**options());frames=[0,1,2]
    seed=context.controls(rig,frames);np.testing.assert_array_equal(seed,np.zeros((3,12)))
    seed[1:,1]=1e-5
    native,checks,samples,clock=context.build_window(frames,seed)
    window=SampledPoseWindow(native,[v for _,v in sorted(samples.items())]);window.grow(seed.reshape(-1),batch_size=32)
    x,result=propose(window,seed.reshape(-1),max_iterations=10)
    np.testing.assert_array_equal(x[:12],seed[0]);assert context.dense_check(native,checks,clock,frames,x)[2]
    output=tmp_path/'candidate.glb';replace_keys(rig,rig,root=0,rotations=[1,2,3],edits={1:x[12:24],2:x[24:36]},preserve_through=0,output=output)
    checked=context.audit(output,list(range(11)));assert checked['passed'] and len(checked['samples'])>11
    assert path.read_bytes()==raw and not checked['quality_approved'] and not checked['release_approved']


def test_selected_animation_and_no_study_dependencies(tmp_path):
    _,rig,_,_=fixture(tmp_path);doc=copy.deepcopy(rig.document);doc['animations'].append(copy.deepcopy(doc['animations'][0]))
    doc['animations'][0]['samplers'][0]['interpolation']='STEP'
    path=tmp_path/'two.glb';write_glb(path,doc,rig.binary);rig=RigAsset.load(path)
    kwargs=options();kwargs['animation_index']=1;context=SurfaceClip(rig,**kwargs)
    assert context.audit(path,list(range(11)))['passed']
    with pytest.raises(ValueError,match='LINEAR'):SurfaceClip(rig,**options())
    x=np.zeros(12);x[1]=.01;out=tmp_path/'edited.glb'
    replace_keys(rig,rig,root=0,rotations=[1,2,3],edits={5:x},preserve_through=4,output=out,animation_index=1)
    assert context.audit(out,list(range(11)))['passed']
    assert RigAsset.load(out).document['animations'][0]==doc['animations'][0]


def test_contact_phase_clocks_and_input_copies(tmp_path):
    path,rig,reader,_=fixture(tmp_path);kwargs=options();t=float(reader.channels[0][2][2]);target=rig.vertices(reader.sample(t))[0].tolist();target[0]+=1
    kwargs['contacts']=[dict(vertex=0,target_m=target,start_time_s=t,end_time_s=t)]
    context=SurfaceClip(rig,**kwargs);kwargs['contacts'][0]['target_m'][0]-=1;kwargs['limits']['contact_error_m']=100
    audit=context.audit(path,[0,1,2]);failed=[r for r in audit['samples'] if not r['numerical_pose_pass']]
    assert len(failed)==1 and failed[0]['time_s']==t and failed[0]['contact_error_m']>.99
    assert context.settings['contact_error_m']==.02


@pytest.mark.parametrize('fault',['bool_index','bool_root','duplicate_node','angles','unknown_limit','nan_limit','reserve','sampling_budget','bool_rate','fractions','contact_vertex','contact_interval','overlapping_contacts'])
def test_invalid_contract_rejected(tmp_path,fault):
    _,rig,_,_=fixture(tmp_path);k=options()
    if fault=='bool_index':k['animation_index']=True
    elif fault=='bool_root':k['root']=False
    elif fault=='duplicate_node':k['rotations']=[1,1,3]
    elif fault=='angles':k['angles_degrees'][0]=float('nan')
    elif fault=='unknown_limit':k['limits']['extra']=1
    elif fault=='nan_limit':k['limits']['root_step_m']=float('nan')
    elif fault=='reserve':k['fitting']['floor_reserve_m']=k['limits']['floor_depth_m']
    elif fault=='sampling_budget':k['sampling']['maximum_samples']=10
    elif fault=='bool_rate':k['sampling']['dense_hz']=True
    elif fault=='fractions':k['sampling']['initial_fractions']=[.3]
    else:
        phase=dict(vertex=0,target_m=[0.,0.,0.],start_time_s=0.,end_time_s=1.)
        if fault=='contact_vertex':phase['vertex']=3
        elif fault=='contact_interval':phase['end_time_s']=3.
        k['contacts']=[phase]
        if fault=='overlapping_contacts':k['contacts'].append(dict(phase,start_time_s=1.,end_time_s=2.))
    with pytest.raises(ValueError):SurfaceClip(rig,**k)


@pytest.mark.parametrize('frames',[[True],[2,1],[0,2],[],[-1],[11]])
def test_invalid_frames_cannot_silently_drop_samples(tmp_path,frames):
    path,rig,_,_=fixture(tmp_path);context=SurfaceClip(rig,**options())
    with pytest.raises(ValueError):context.audit(path,frames)


def test_changed_geometry_rejected_by_audit(tmp_path):
    _,rig,_,_=fixture(tmp_path);context=SurfaceClip(rig,**options());doc=copy.deepcopy(rig.document);doc['nodes'][5]['translation'][0]+=.1
    path=tmp_path/'changed.glb';write_glb(path,doc,rig.binary)
    with pytest.raises(ValueError):context.audit(path,[0,1])


def test_all_eighth_initial_samples_use_exact_check_clock(tmp_path):
    _,rig,_,_=fixture(tmp_path);k=options();k['sampling']['initial_fractions']=[i/8 for i in range(1,8)]
    context=SurfaceClip(rig,**k);frames=[3,4,5];seed=context.controls(rig,frames)
    _,checks,samples,clock=context.build_window(frames,seed)
    assert len(samples)==14 and all(t in checks and t in clock for t in samples)


@pytest.mark.parametrize('fault',['clock','checks'])
def test_dense_check_refuses_missing_population(tmp_path,fault):
    _,rig,_,_=fixture(tmp_path);context=SurfaceClip(rig,**options());frames=[0,1,2];seed=context.controls(rig,frames)
    native,checks,_,clock=context.build_window(frames,seed)
    if fault=='clock':clock=clock[:-1]
    else:checks.pop(next(iter(checks)))
    with pytest.raises(ValueError,match='population'):context.dense_check(native,checks,clock,frames,seed.reshape(-1))


@pytest.mark.parametrize('fault',['points','controls','missing_vertex','time'])
def test_measure_rejects_incomplete_or_nonfinite_geometry(tmp_path,fault):
    _,rig,reader,_=fixture(tmp_path);context=SurfaceClip(rig,**options());points=rig.vertices(reader.sample(0.));controls=np.zeros(12);t=0.
    if fault=='points':points[0,1]=np.nan
    elif fault=='controls':controls[0]=np.nan
    elif fault=='missing_vertex':points=points[:-1]
    else:t=True
    with pytest.raises(ValueError):context.measure(points,controls,t)
