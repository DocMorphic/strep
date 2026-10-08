import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import scene_placement_authoring as author
from strep import save,read,sha256


def fixture_data():
    names=['Hips','LeftHand']+[f'Joint{i}' for i in range(2,77)]
    skin=dict(bind_rig_transform=np.repeat(np.eye(4)[None],77,axis=0),bind_vertices=np.array([[.03,0,0]]),
        lbs_indices=np.ones((1,8),dtype=int),lbs_weights=np.array([[1.,0,0,0,0,0,0,0]]),rig_joint_names=np.array(names))
    motion=dict(posed_joints=np.zeros((4,77,3)),global_rot_mats=np.broadcast_to(np.eye(3),(4,77,3,3)).copy())
    pose=dict(translation_m=[0,0,0],rotation_xyzw=[0,0,0,1])
    scene=dict(schema_version=1,id='fixture',fps=30,frame_count=4,actors={'A':dict(transform=pose,motion='clip.npz',preview_glb='actor.glb')},
        objects={'box':dict(shape='box',size_m=[.4,.4,.4],keyframes=[dict(frame=0,translation_m=[0,.2,.55],rotation_xyzw=[0,0,0,1]),dict(frame=3,translation_m=[0,.3,.55],rotation_xyzw=[0,0,0,1])])},
        contacts=[dict(id='grip',actor='A',effector=dict(joint='LeftHand',surface_vertex=0),target=dict(space='object',object='box',point_m=[.2,.1,0]),start_frame=1,end_frame=2,tolerance_m=.03)])
    return scene,skin,{'A':motion}


def test_reach_uses_authored_anchor_tolerance_and_reports_geometry_unevaluated():
    scene,skin,motions=fixture_data()
    report,bundle=author.measure(scene,skin,motions)
    assert report['status']=='provably_incompatible'
    assert report['rows'][0]['incompatible_frames']==[1,2]
    assert report['rows'][0]['authored_tolerance_m']==.03
    assert not bundle['evaluation']['geometry_evaluated'] and not bundle['quality_approved']
    assert len(bundle['native_contact_tracks']['grip']['actual'])==4
    scene['contacts'][0]['tolerance_m']=1.
    report,_=author.measure(scene,skin,motions)
    assert report['status']=='not_ruled_out' # No hidden tighter 5 mm solver target.


def test_actor_and_prop_translation_moves_targets_with_current_placement():
    scene,skin,motions=fixture_data()
    before,_=author.measure(scene,skin,motions)
    draft=author.placements(scene)
    draft['actors']['A']['translation_m']=[0,0,.55]
    changed=author.apply_placement(scene,draft)
    after,_=author.measure(changed,skin,motions)
    assert after['rows'][0]['maximum_error_lower_bound_m'] < before['rows'][0]['maximum_error_lower_bound_m']
    assert scene['actors']['A']['transform']['translation_m']==[0,0,0]


def test_partner_targets_are_measured_but_not_ruled_out_as_frozen():
    scene,skin,motions=fixture_data();scene['actors']['B']=copy.deepcopy(scene['actors']['A']);motions['B']=copy.deepcopy(motions['A'])
    scene['contacts'][0]['target']=dict(space='actor',actor='B',joint='LeftHand',surface_vertex=0)
    report,bundle=author.measure(scene,skin,motions)
    assert not report['rows'] and report['skipped'] and report['status']=='not_ruled_out'
    assert 'target' in bundle['native_contact_tracks']['grip']


def test_saved_marker_tracks_remain_local_while_distances_use_each_actor_world_pose():
    from scipy.spatial.transform import Rotation
    from scene_constraints import effector_track,transform_motion
    scene,skin,motions=fixture_data()
    scene['actors']['B']=copy.deepcopy(scene['actors']['A']);motions['B']=copy.deepcopy(motions['A'])
    scene['actors']['A']['transform']=dict(translation_m=[2,1,3],rotation_xyzw=Rotation.from_euler('y',45,degrees=True).as_quat().tolist())
    scene['actors']['B']['transform']=dict(translation_m=[-1,2,.5],rotation_xyzw=Rotation.from_euler('x',30,degrees=True).as_quat().tolist())
    contact=scene['contacts'][0];contact['target']=dict(space='actor',actor='B',joint='LeftHand',surface_vertex=0)
    _,bundle=author.measure(scene,skin,motions)
    points=bundle['native_contact_tracks']['grip']
    assert np.allclose(points['actual'],[[.03,0,0]]*4)
    assert np.allclose(points['target'],[[.03,0,0]]*4)
    worlds=[effector_track(transform_motion(motions[n],scene['actors'][n]['transform']),contact['effector'],skin) for n in ['A','B']]
    assert bundle['evaluation']['contacts'][0]['max_interval_error_m']==pytest.approx(np.linalg.norm(worlds[0]-worlds[1],axis=1).max())
    assert bundle['evaluation']['anchor_only'] is True


def test_joint_offset_effector_supported_without_rigid_skin_approximation():
    scene,skin,motions=fixture_data();scene['contacts'][0]['effector']=dict(joint='LeftHand',offset_m=[.03,0,0])
    report,_=author.measure(scene,skin,motions)
    assert report['rows'][0]['incompatible_frames']==[1,2]


@pytest.mark.parametrize('bad',['actor_id','object_id','frame_removed','frame_retime','quaternion','distance','extra_field','nan'])
def test_invalid_placement_preserves_source(bad):
    scene,_,_=fixture_data();draft=author.placements(scene);before=copy.deepcopy(scene)
    if bad=='actor_id':draft['actors']['B']=draft['actors'].pop('A')
    if bad=='object_id':draft['objects']['other']=draft['objects'].pop('box')
    if bad=='frame_removed':draft['objects']['box'].pop()
    if bad=='frame_retime':draft['objects']['box'][1]['frame']=2
    if bad=='quaternion':draft['actors']['A']['rotation_xyzw']=[0,0,0,2]
    if bad=='distance':draft['objects']['box'][0]['translation_m']=[101,0,0]
    if bad=='extra_field':draft['actors']['A']['scale']=2
    if bad=='nan':draft['actors']['A']['translation_m'][0]=float('nan')
    with pytest.raises(ValueError):author.apply_placement(scene,draft)
    assert scene==before


@pytest.fixture
def workspace(tmp_path,monkeypatch):
    real=author.ROOT
    for name in author.METHODS:
        target=tmp_path/'scripts'/name;target.parent.mkdir(exist_ok=True);target.write_bytes((real/'scripts'/name).read_bytes())
    scene,skin,motions=fixture_data();base=tmp_path/'reports/original';base.mkdir(parents=True)
    np.savez(base/'clip.npz',**motions['A']);(base/'actor.glb').write_bytes(b'Fixture GLB bytes; not an engine fixture')
    scene['actors']['A']['motion']='reports/original/clip.npz';scene['actors']['A']['source_sha256']=sha256(base/'clip.npz')
    bundle=dict(scene=scene,evaluation=dict(old_geometry_claim=True));save(base/'source.json',bundle)
    (base/'SOMA-preview-LICENSE.txt').write_text('Fixture license')
    asset=tmp_path/'skin.npz';np.savez(asset,**skin)
    files={p:sha256(p) for p in [base/'source.json',base/'clip.npz',base/'actor.glb',base/'SOMA-preview-LICENSE.txt']}
    data=dict(base=base,bundle=bundle,revision='fixture-source-revision',files=files)
    monkeypatch.setattr(author,'ROOT',tmp_path);monkeypatch.setattr(author,'JOBS',tmp_path/'reports/scene-placement-jobs');monkeypatch.setattr(author,'SKIN',asset)
    monkeypatch.setattr(author,'source',lambda url:copy.deepcopy(data))
    payload=dict(source_url='/files/original/source.json',revision=author.revision(data),placement=author.placements(scene),label='Moved box')
    return tmp_path,data,payload


def test_snapshot_preserves_assets_and_original_evidence_and_becomes_new_source(workspace):
    root,data,payload=workspace
    payload['placement']['objects']['box'][0]['translation_m'][2]=.1
    result=author.stage(payload)
    folder=root/'reports'/result['collection'];bundle=read(folder/'scene.json')
    assert (folder/'assets/A/actor.glb').read_bytes()==(data['base']/'actor.glb').read_bytes()
    assert (folder/'assets/A/motion.npz').read_bytes()==(data['base']/'clip.npz').read_bytes()
    assert read(folder/'source-bundle.json')==data['bundle']
    assert 'old_geometry_claim' not in bundle['evaluation'] and not bundle['evaluation']['geometry_evaluated']
    assert bundle['scene']['objects']['box']['keyframes'][0]['translation_m'][2]==.1
    assert data['bundle']['scene']['objects']['box']['keyframes'][0]['translation_m'][2]==.55
    provenance=read(folder/'provenance.json')
    assert all(sha256(folder/name)==digest for name,digest in provenance['files_sha256'].items())
    assert not provenance['animation_generated'] and not provenance['optimizer_ran']
    assert read(folder/'pipeline.json')['status']=='complete'
    assert bundle['scene']['id']==result['scene_id']=='placement'


@pytest.mark.parametrize('bad',['revision','label','field','placement','outside'])
def test_bad_request_does_not_create_output(workspace,bad):
    root,data,payload=workspace;folder=author.JOBS/'test'
    if bad=='revision':payload['revision']='stale'
    if bad=='label':payload['label']=''
    if bad=='field':payload['secret']='not accepted'
    if bad=='placement':payload['placement']['actors']={}
    if bad=='outside':folder=root/'elsewhere'
    with pytest.raises(ValueError):author.stage(payload,folder)
    assert not folder.exists()


def test_changed_source_read_is_rejected_without_output(workspace):
    root,data,payload=workspace
    (data['base']/'actor.glb').write_bytes(b'Changed asset')
    with pytest.raises(ValueError,match='Source changed'):author.check(payload)
    assert not author.JOBS.exists()


def test_snapshot_copy_failure_retains_failed_receipt(workspace,monkeypatch):
    root,data,payload=workspace;folder=author.JOBS/'test'
    original=author.shutil.copyfile
    def corrupt(source,destination):
        original(source,destination)
        if str(destination).endswith('actor.glb'):Path(destination).write_bytes(b'corrupted')
    monkeypatch.setattr(author.shutil,'copyfile',corrupt)
    with pytest.raises(ValueError,match='Source asset changed'):author.stage(payload,folder)
    assert read(folder/'pipeline.json')['status']=='failed'
    assert not (folder/'manifest.json').exists()


def test_loopback_routes_bind_sources_check_drafts_and_save_immutable_snapshots(workspace):
    import http.client,json,threading
    from http.server import ThreadingHTTPServer
    from action_studio_server import Handler,allowed_file
    root,data,payload=workspace
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    host='127.0.0.1:'+str(server.server_port)
    server.allowed_hosts={host};server.worker=None;server.job_lock=threading.Lock()
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def request(path,body=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
        values={'Host':host,'Origin':'http://'+host,'Content-Type':'application/json',**(headers or {})}
        connection.request('POST' if body is not None else 'GET',path,body=json.dumps(body) if body is not None else None,headers=values)
        response=connection.getresponse();result=(response.status,json.loads(response.read()));connection.close();return result
    try:
        status,meta=request('/api/scene-placement-source?path=/files/original/source.json')
        assert status==200 and meta['revision']==payload['revision']
        assert request('/api/scene-placement-source?path=a&path=b')[0]==400
        status,report=request('/api/scene-placement-check',payload)
        assert status==200 and report['status']=='provably_incompatible' and not author.JOBS.exists()
        assert request('/api/scene-placement-check',payload,{'Origin':'https://elsewhere.example'})[0]==403
        assert request('/api/scene-placement-check',payload,{'Content-Type':'text/plain'})[0]==415
        assert request('/api/scene-placement-check',{**payload,'revision':'stale'})[0]==400
        status,result=request('/api/scene-placement-snapshots',payload)
        assert status==201 and (root/'reports'/result['collection']/'scene.json').is_file()
        assert allowed_file('/scene-placement-editor.mjs').name=='scene-placement-editor.mjs'
        assert allowed_file('/files/scene-placement-jobs/../../README.md') is None
        assert allowed_file('/files/'+result['collection']+'/scene.json').suffix=='.json'
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
