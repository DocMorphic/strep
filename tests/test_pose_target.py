import copy
import sys
import threading
import urllib.request
import urllib.error
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import pose_target
from strep import ROOT,sha256
from inspect_motion import skeleton_metadata


@pytest.fixture
def source(tmp_path,monkeypatch):
    original=ROOT/'reports/action-jobs/profile-response-v1/takes/wave-high-seed-301/motion.npz'
    with np.load(original,allow_pickle=False) as archive:data={k:v[[60,60]] for k,v in archive.items()}
    folder=tmp_path/'reports';folder.mkdir();np.savez_compressed(folder/'input.npz',**data)
    license_folder=tmp_path/'vendor/kimodo';license_folder.mkdir(parents=True)
    (license_folder/'LICENSE').write_bytes((ROOT/'vendor/kimodo/LICENSE').read_bytes())
    monkeypatch.setattr(pose_target,'ROOT',tmp_path)
    payload=dict(motion='reports/input.npz',sha256=sha256(folder/'input.npz'),source_frame=0,effector='RightHand',offset_m=[0,0,0],max_edit_degrees=45)
    return data,payload


def test_zero_target_preserves_every_joint_and_orientation(source):
    data,payload=source;names,parents,_=skeleton_metadata(77);tip=names.index('RightHand')
    local,audit=pose_target.solve_pose(data['local_rot_mats'][0],data['global_rot_mats'][0],data['posed_joints'][0],parents,names,'RightHand',data['posed_joints'][0,tip],45)
    assert audit['reached'] and audit['target_error_m']<1e-6
    assert np.max(np.abs(local-data['local_rot_mats'][0]))<1e-6
    assert audit['unchanged_joint_position_max_error_m']<1e-6


@pytest.mark.parametrize('effector',['LeftHand','RightHand','LeftFoot','RightFoot'])
def test_all_four_chains_preserve_other_limbs_under_a_reachable_offset(source,effector):
    data,_=source;names,parents,_=skeleton_metadata(77);tip=names.index(effector)
    target=data['posed_joints'][0,tip]+[0,.04,0]
    _,audit=pose_target.solve_pose(data['local_rot_mats'][0],data['global_rot_mats'][0],data['posed_joints'][0],parents,names,effector,target,60)
    assert audit['reached'] and audit['target_error_m']<=.005
    assert audit['unchanged_joint_position_max_error_m']<1e-6
    assert audit['effector_orientation_error_degrees']<1e-4


def test_reachable_pose_uses_native_fk_and_roundtrips_as_guide(source):
    data,payload=source;payload['offset_m']=[0,.08,0]
    result=pose_target.author(payload)
    assert result['reached']
    assert result['audit']['actual_native_fk_target_error_m']<=.005
    assert result['audit']['max_local_edit_degrees']<=45+1e-5
    assert result['audit']['effector_orientation_error_degrees']<1e-4
    candidate=pose_target.ROOT/result['guide']['motion']
    with np.load(candidate,allow_pickle=False) as output:
        names,parents,_=skeleton_metadata(77)
        assert np.array_equal(output['root_positions'],data['root_positions'])
        for name in ['LeftHand','LeftFoot','RightFoot','Neck1']:
            np.testing.assert_allclose(output['posed_joints'][:,names.index(name)],data['posed_joints'][:,names.index(name)],atol=1e-6)
        assert not output['foot_contacts'].any()
    assert sha256(pose_target.ROOT/payload['motion'])==payload['sha256']
    # Exercise the real source-pose guide compiler, including FK validation.
    import generation_constraints
    old=generation_constraints.ROOT;generation_constraints.ROOT=pose_target.ROOT
    try:
        compiled,_=generation_constraints.compile_guides(dict(segments=[dict(duration_s=4)],generation_constraints=[result['guide']]))
        assert compiled[0]['joint_names']==['RightHand']
    finally:generation_constraints.ROOT=old


def test_far_target_retains_bounded_candidate_but_never_returns_guide(source):
    data,payload=source;payload.update(offset_m=[0,.5,0],max_edit_degrees=1)
    result=pose_target.author(payload)
    assert not result['reached'] and result['guide'] is None
    assert result['audit']['max_local_edit_degrees']<=1.00001
    folder=pose_target.ROOT/'reports'/result['base'].removeprefix('/files/')
    assert (folder/'candidate.glb').exists() and (folder/'audit.json').exists()


@pytest.mark.parametrize('change',[dict(offset_m=[True,0,0]),dict(offset_m=[0,float('nan'),0]),dict(offset_m=[.5,.5,0]),dict(max_edit_degrees=0),dict(source_frame=True),dict(effector='Hips'),dict(motion='reports/../secret.npz'),dict(sha256='0'*64)])
def test_invalid_target_rejected_before_creation(source,change):
    _,payload=source;payload.update(change)
    with pytest.raises(ValueError):pose_target.validate(payload)
    assert not (pose_target.ROOT/'reports/pose-targets').exists()


def test_live_api_rejects_cross_origin_and_preserves_source(source, monkeypatch):
    from http.server import ThreadingHTTPServer
    from action_studio_server import Handler
    import action_worker_lock
    # Exercise the real lock without contending with a running project job.
    monkeypatch.setattr(action_worker_lock, 'ROOT', pose_target.ROOT)
    _,payload=source
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);host=f'127.0.0.1:{server.server_port}';server.allowed_hosts={host};server.worker=None;server.job_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        request=urllib.request.Request(f'http://{host}/api/pose-target',json.dumps(payload).encode(),headers={'Content-Type':'application/json','Origin':'http://untrusted.invalid'})
        with pytest.raises(urllib.error.HTTPError) as exc:urllib.request.urlopen(request)
        assert exc.value.code==403
        request.add_header('Origin','http://'+host)
        with action_worker_lock.worker_lock():
            with pytest.raises(urllib.error.HTTPError) as exc:
                urllib.request.urlopen(request)
            assert exc.value.code == 409
            assert not (pose_target.ROOT/'reports/pose-targets').exists()
            assert sha256(pose_target.ROOT/payload['motion']) == payload['sha256']
        with urllib.request.urlopen(request) as response:result=json.load(response)
        assert result['reached'] and result['guide']['source_frames']==[0]
        assert sha256(pose_target.ROOT/payload['motion'])==payload['sha256']
    finally:server.shutdown();server.server_close();thread.join()
