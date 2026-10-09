"""Whole saved-key coverage and fixed boundary checks without native assets."""
import sys
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
import numpy as np
import torch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_contact_interval as module


def motion():
    return dict(posed_joints=np.zeros((10,77,3),dtype=np.float32),root_positions=np.zeros((10,3),dtype=np.float32),
        local_rot_mats=np.tile(np.eye(3,dtype=np.float32),(10,77,1,1)),global_rot_mats=np.tile(np.eye(3,dtype=np.float32),(10,77,1,1)))


def factory(block):
    class Window:
        pose_dim=1;seed=np.zeros(len(block))
        def __init__(self):
            refs={n:torch.zeros((10,77,3),dtype=torch.float64) for n in ['raw','limb','previous']}
            self.problems=[SimpleNamespace(frame=f,names=['J'+str(j) for j in range(77)],references=refs,headroom_m=1e-6,
                neighbors={n:torch.zeros((77,3),dtype=torch.float64) for n in [f-1,f+1]},
                t=lambda a:torch.as_tensor(a,dtype=torch.float64),
                audit_motion=lambda saved,**k:dict(pose_checks_passed=bool(np.all(saved['posed_joints']==0)))) for f in block]
            self.representation_labels=['point:left:frame-'+str(f) for f in block]
        def set_fixed_neighbors(self,positions):
            for p in self.problems:
                for f,value in positions.items():
                    if f in p.neighbors:p.neighbors[f]=p.t(value)
        def saved_representation(self,x,*,motion):return .005-np.abs(motion['posed_joints'][:,0,0])
    return Window()


def test_pose_only_continuation_never_invents_contacts_or_heading_metadata():
    source=motion();source['foot_contacts']=np.ones((10,6),dtype=bool);source['global_root_heading']=np.zeros((10,2),dtype=np.float32)
    pose=module.pose_tracks(source)
    assert set(pose)==set(module.POSE_TRACKS) and 'foot_contacts' not in pose and 'global_root_heading' not in pose
    pose['posed_joints'][0,0,0]=.1
    assert source['posed_joints'][0,0,0]==0
    source.pop('root_positions')
    with pytest.raises(ValueError):module.pose_tracks(source)


def test_native_predecessor_extra_tracks_and_double_root_survive_without_downcasting():
    source=motion();source['foot_contacts']=np.zeros((10,6),dtype=bool)
    parent={key:value[2:5].copy() for key,value in source.items()}
    parent['root_positions']=parent['root_positions'].astype(np.float64);parent['root_positions'][0,1]=.4+1e-8
    parent['smooth_root_pos']=np.ones((3,3),dtype=np.float32)
    proposed=module.overlay_pose_tracks(source,[2,3,4],parent)
    assert set(proposed)==set(module.POSE_TRACKS) and proposed['root_positions'].dtype==np.float64
    assert proposed['root_positions'][2,1]==.4+1e-8
    assert proposed['root_positions'][2,1]!=np.float32(.4+1e-8)
    np.testing.assert_array_equal(proposed['root_positions'][[0,1,5,6,7,8,9]],source['root_positions'][[0,1,5,6,7,8,9]])
    assert source['root_positions'].dtype==np.float32 and not source['root_positions'].any()


@pytest.mark.parametrize('damage',['shape','root-int','pose-double','missing'])
def test_incompatible_predecessor_is_rejected_before_expensive_replay(damage):
    source=motion();parent={k:v[2:5].copy() for k,v in source.items()}
    if damage=='shape':parent['posed_joints']=parent['posed_joints'][:2]
    if damage=='root-int':parent['root_positions']=parent['root_positions'].astype(int)
    if damage=='pose-double':parent['local_rot_mats']=parent['local_rot_mats'].astype(np.float64)
    if damage=='missing':parent.pop('root_positions')
    with pytest.raises(ValueError):module.overlay_pose_tracks(source,[2,3,4],parent)


@pytest.mark.parametrize('width',[2,3,4,5])
def test_every_saved_key_and_both_exterior_speed_sides_are_measured(width):
    source=motion();source['posed_joints'][6,0,0]=.06;before={k:v.copy() for k,v in source.items()}
    report,labels,values=module.evaluate_interval(factory,list(range(2,7)),source,width=width)
    assert report['contact_frames']==[2,3,4,5,6] and report['audited_frames']==[1,2,3,4,5,6,7]
    assert report['exterior_body_only_frames']==[1,7]
    row=labels.index('all-reference-speed:6:J0:frame-7')
    assert values[row]<0 and report['ranked_windows'][0]['frames'][-1]==6
    assert not report['physical_contact_keys_passed'] and not report['complete_keyed_rows_passed']
    assert len(report['per_frame_physical'])==5 and len(labels)==len(set(labels))
    for key in source:np.testing.assert_array_equal(before[key],source[key])


@pytest.mark.parametrize('damage',['missing','joints','clock','nan','parameters'])
def test_partial_native_clock_or_parameters_cannot_be_measured(damage):
    source=motion();parameters={}
    if damage=='missing':source.pop('posed_joints')
    if damage=='joints':source['local_rot_mats']=source['local_rot_mats'][:,:76]
    if damage=='clock':source['root_positions']=source['root_positions'][:-1]
    if damage=='nan':source['posed_joints'][4,0,0]=np.nan
    if damage=='parameters':parameters={9:[0.]}
    with pytest.raises(ValueError):module.evaluate_interval(factory,[2,3],source,parameters)


@pytest.mark.parametrize('frames,width',[([],3),([1],3),([1,3],3),([1,2],True),([1,2],6)])
def test_invalid_request_never_acquires_worker(tmp_path,monkeypatch,frames,width):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Invalid audit acquired worker'))
    with pytest.raises(ValueError):module.run(tmp_path/'source',tmp_path/'out',frames,width=width)
    assert not (tmp_path/'out').exists()


def test_failure_is_preserved_and_existing_output_never_overwritten(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',nullcontext)
    monkeypatch.setattr(module,'threadpool_limits',lambda **k:nullcontext())
    def fail(study,output,*a):output.mkdir();raise ValueError('Malformed saved source')
    monkeypatch.setattr(module,'_run',fail);output=tmp_path/'out'
    with pytest.raises(ValueError):module.run(tmp_path/'source',output,[2,3])
    data=(output/'pipeline.json').read_bytes();assert module.read(output/'pipeline.json')['status']=='failed'
    with pytest.raises(FileExistsError):module.run(tmp_path/'source',output,[2,3])
    assert data==(output/'pipeline.json').read_bytes()


@pytest.mark.parametrize('output,resume',[('source/new',None),('source',None),('parent/new','parent'),('parent','parent/new')])
def test_sources_and_predecessors_stay_immutable(tmp_path,monkeypatch,output,resume):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'worker_lock',lambda:pytest.fail('Overlapping output acquired worker'))
    with pytest.raises(ValueError):module.run(tmp_path/'source',tmp_path/output,[2,3],resume=tmp_path/resume if resume else None)
