"""Region authoring uses exact topology/weights without implying anatomy."""
from pathlib import Path
from types import SimpleNamespace
import sys,copy,json,io
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rig_patch_selection import select,inspect_request,SCHEMA
from test_studio_mesh_playback import seed
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from strep import sha256


def toy(count=3):
    # Slot order deliberately differs from node IDs; repeated slots must sum.
    joints=np.tile([0,1,0,0,1,2,3,0],(count,1))
    weights=np.tile([.2,.1,.05,0,.2,.1,.35,0],(count,1))
    points=np.c_[np.arange(count),np.zeros(count),np.arange(count)*.2]
    return SimpleNamespace(joints=[4,1,2,0],parents=[-1,0,1,0,0],
        primitives=[dict(positions=np.zeros((2,3)),joints=None,weights=None),dict(positions=points,joints=joints,weights=weights)],
        vertices=lambda _:np.r_[np.full((2,3),999.),points])


def test_all_eight_influences_repeated_slots_global_offsets_and_static_exclusion():
    r=toy();result=select(r,None,1,False,.3)
    assert result['vertices']==[2,3,4] and result['selected_nodes']==[1]
    assert result['matched_count']==3 and result['vertex_count']==5
    assert result['bounds_world_m']==dict(min=[0,0,0],max=[2,0,.4])
    assert result['can_apply'] and not result['anatomy_verified'] and not result['quality_approved']
    assert select(r,None,1,False,.31)['vertices']==[]
    assert select(r,None,1,True,.39)['vertices']==[2,3,4]
    assert select(r,None,1,True,.41)['vertices']==[]
    assert select(r,None,0,True,1.)['vertices']==[2,3,4]


def test_box_uses_decoded_pose_and_inclusive_world_coordinates():
    r=toy();box=dict(min=[1,0,.2],max=[1,0,.2]);result=select(r,None,1,False,.3,box)
    assert result['vertices']==[3]
    r.vertices=lambda _:np.r_[np.full((2,3),999.),[[0,1,0],[1,1,.2],[2,1,.4]]]
    assert select(r,None,1,False,.3,box)['matched_count']==0


def test_oversized_region_is_not_downsampled_or_applicable():
    result=select(toy(257),None,1,False,.3)
    assert result['matched_count']==257 and result['vertices']==[] and not result['can_apply']
    assert result['bounds_world_m']['max'][0]==256


@pytest.mark.parametrize('node,children,weight,box',[(True,False,.5,None),(99,False,.5,None),(1,1,.5,None),
    (1,False,True,None),(1,False,0,None),(1,False,1.01,None),(1,False,float('nan'),None),
    (1,False,.5,{}),(1,False,.5,dict(min=[1,0,0],max=[0,0,0])),
    (1,False,.5,dict(min=[False,0,0],max=[1,1,1])),(1,False,.5,dict(min=[0,0],max=[1,1,1]))])
def test_invalid_selectors_reject(node,children,weight,box):
    with pytest.raises(ValueError):select(toy(),None,node,children,weight,box)


def body(parent,**changes):
    return dict(schema=SCHEMA,source_job=parent.name,variant='transfer',glb_sha256=sha256(parent/'transfer/character.glb'),
        frame=2.5,node=3,include_children=False,minimum_weight=.5,box_world_m=None,**changes)


def test_actual_published_source_is_read_only_and_decoded_box_is_reproducible(tmp_path,monkeypatch):
    parent,_=seed(tmp_path,monkeypatch);before={str(p):sha256(p) for p in parent.rglob('*') if p.is_file()}
    request=body(parent);result=inspect_request(request);assert result['vertices']==[0,1,2]
    rig=RigAsset.load(parent/'transfer/character.glb');world=AnimationSampler(rig.document,rig.binary,0).sample(float(np.float32(2.5/30)))
    points=rig.vertices(world)
    np.testing.assert_array_equal(result['bounds_world_m']['min'],points.min(axis=0))
    request['box_world_m']=dict(min=points[0].tolist(),max=points[0].tolist())
    assert inspect_request(request)['vertices']==[0]
    assert before=={str(p):sha256(p) for p in parent.rglob('*') if p.is_file()}


@pytest.mark.parametrize('field,value',[('schema','other'),('glb_sha256','0'*64),('frame',True),('frame',7),('frame',-.1),('frame',float('inf')),('source_job','../bad')])
def test_bad_request_bindings_reject(tmp_path,monkeypatch,field,value):
    parent,_=seed(tmp_path,monkeypatch);request=body(parent);request[field]=value
    with pytest.raises(ValueError):inspect_request(request)


def test_handler_uses_read_only_path_before_busy_worker_gate(tmp_path,monkeypatch):
    import action_studio_server as server
    parent,_=seed(tmp_path,monkeypatch);payload=json.dumps(body(parent)).encode();replies=[]
    host='127.0.0.1:8768';handler=SimpleNamespace(path='/api/rig-patch-selection',
        headers={'Host':host,'Origin':'http://'+host,'Content-Type':'application/json','Content-Length':str(len(payload))},
        server=SimpleNamespace(allowed_hosts={host}),rfile=io.BytesIO(payload),respond=lambda code,value:replies.append((code,value)))
    monkeypatch.setattr(server,'worker_busy',lambda:(_ for _ in ()).throw(AssertionError('Read-only selection must not enter worker gate')))
    server.Handler.do_POST(handler);assert replies[-1][0]==200 and replies[-1][1]['vertices']==[0,1,2]
    handler.headers['Origin']='http://unrelated.example';server.Handler.do_POST(handler);assert replies[-1][0]==403
