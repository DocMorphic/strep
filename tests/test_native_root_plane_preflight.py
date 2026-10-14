"""Incoming partner contacts and full floor clocks constrain root-only shifts."""
from pathlib import Path
import copy,sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import action_worker_lock
from native_root_plane_preflight import run
from native_scene_contacts import SceneContacts
from strep import save,sha256
from test_native_scene_contacts import setup
from test_native_scene_geometry import policy


@pytest.mark.parametrize('incoming',[False,True])
def test_planted_incoming_or_outgoing_point_blocks_floor_lift(tmp_path,monkeypatch,incoming):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'worker-lock')
    source,rig,reader,spec=setup(tmp_path,mode='touch')
    point=rig.vertices(reader.sample(1.))[0].tolist()
    if incoming:
        spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
        spec['contacts'][0].update(actor='B',target=dict(space='actor',actor='A',vertices=[[6,0,0]],reduction='individual'))
    contacts=tmp_path/'contacts.json';save(contacts,spec)
    floor=point[1]+.02+.005;pp=tmp_path/'policy.json';save(pp,policy(contacts,planes=dict(ground=dict(normal_world=[0,1,0],offset_m=floor))))
    result=run(contacts,pp,'A',rig.joints[0],'ground',.22,tmp_path/'preflight')
    at=next(row for row in result['per_pose_intersections'] if row['time_s']==1.)
    assert not at['per_pose_interval_nonempty'] and at['upper_witness']['kind']=='contact'
    assert result['contact_rows_by_id']['arbitrary-body-patch']==1
    assert result['original_selected'] and not result['clip_feasibility_established'] and not result['release_approved']


def test_nonempty_intersections_are_not_clip_or_source_rate_approval(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path/'worker-lock')
    _,rig,_,spec=setup(tmp_path,mode='touch');contacts=tmp_path/'contacts.json';save(contacts,spec)
    pp=tmp_path/'policy.json';save(pp,policy(contacts,planes=dict(ground=dict(normal_world=[0,1,0],offset_m=-100.))))
    result=run(contacts,pp,'A',rig.joints[0],'ground',.22,tmp_path/'preflight')
    assert result['poses_with_empty_intersections']==0 and not result['clip_feasibility_established']
    assert result['observations_sha256']==sha256(tmp_path/'preflight/observations.npz')
    assert result['samples']==3
