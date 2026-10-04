"""Model-free geometry and dispatch checks; real conversion is a local study."""
import copy
import sys
from pathlib import Path
import numpy as np
import pytest
import trimesh
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import inspect_motion
import scene_target_preflight as module
from strep import save,sha256


@pytest.fixture
def fixture(tmp_path,monkeypatch):
    names=['Hips','LeftHand','RightHand']+[f'Joint{i}' for i in range(74)]
    monkeypatch.setattr(inspect_motion,'skeleton_metadata',lambda n:(names,[-1]+[0]*76,['LeftHand','RightHand']))
    mesh=trimesh.creation.box(extents=[.4,.4,.4]);mesh.apply_translation([0,1,0])
    skin=dict(bind_vertices=mesh.vertices.copy(),faces=mesh.faces.copy(),rig_joint_names=np.array(names),
        bind_rig_transform=np.tile(np.eye(4),(77,1,1)),lbs_indices=np.full((8,2),1),lbs_weights=np.full((8,2),.5))
    motions={};actors={};contacts=[]
    for i,name in enumerate(['A','B']):
        local=np.tile(np.eye(3),(3,77,1,1));motion=dict(local_rot_mats=local,global_rot_mats=local.copy(),
            root_positions=np.zeros((3,3)),posed_joints=np.zeros((3,77,3)),foot_contacts=np.zeros((3,4)))
        path=tmp_path/f'{name}.npz';np.savez(path,**motion);motions[name]=motion
        actors[name]=dict(motion=path.name,source_sha256=sha256(path),transform=dict(translation_m=[i*3.,0,0],rotation_xyzw=[0,0,0,1]))
        contacts.append(dict(id=name,actor=name,effector=dict(joint='LeftHand',surface_vertex=0),
            target=dict(space='world',point_m=(skin['bind_vertices'][0]+[i*3.,0,0]).tolist()),
            start_frame=i*2,end_frame=i*2,tolerance_m=.01))
    scene=dict(schema_version=1,id='test-reference',fps=30,frame_count=3,actors=actors,contacts=contacts,objects={})
    return scene,skin,motions,tmp_path


def test_every_actor_at_shared_contact_union_and_no_source_mutation(fixture):
    scene,skin,motions,root=fixture;before=copy.deepcopy(scene);arrays=copy.deepcopy(motions)
    result=module.measure(scene,skin,motions,project_root=root)
    assert scene==before and result['reference_screens_passed'] and result['frames']==[0,2]
    assert [(r['frame'],r['actor']) for r in result['floor']]==[(0,'A'),(0,'B'),(2,'A'),(2,'B')]
    assert len(result['partners'])==4 and all(r['vertices_checked']==8 for r in result['partners'])
    for name in motions:
        for key in motions[name]:np.testing.assert_array_equal(motions[name][key],arrays[name][key])


@pytest.mark.parametrize('defect',['point','floor','object','partner','normal'])
def test_full_surface_defects_are_distinct_from_contact_points(fixture,defect):
    scene,skin,motions,root=fixture
    if defect=='point':motions['A']['posed_joints'][0,1,0]=.04
    if defect=='floor':motions['A']['posed_joints'][2,1,1]=-1. # A has no guide at B's frame.
    if defect=='object':scene['objects']['box']=dict(shape='box',size_m=[.8,.8,.8],keyframes=[dict(frame=0,translation_m=[0,1,0],rotation_xyzw=[0,0,0,1])])
    if defect=='partner':scene['actors']['B']['transform']['translation_m']=[.1,.1,.1]
    if defect=='normal':scene['contacts'][0]['normal_target']=dict(space='world',direction=[0,1,0])
    result=module.measure(scene,skin,motions,project_root=root)
    flag={'point':'contact_reference_missed','floor':'floor_reference_penetration','object':'object_reference_penetration',
        'partner':'partner_reference_penetration','normal':'orientation_reference_missed'}[defect]
    assert not result['reference_screens_passed'] and flag in result['flags']


@pytest.mark.parametrize('defect',['missing_actor','stale_source','clock','path','nonfinite'])
def test_measurement_cannot_drop_sources_or_read_unbound_arrays(fixture,defect):
    scene,skin,motions,root=fixture
    if defect=='missing_actor':del motions['B']
    if defect=='stale_source':scene['actors']['A']['source_sha256']='0'*64
    if defect=='clock':motions['A']={k:v[:2] for k,v in motions['A'].items()}
    if defect=='path':scene['actors']['A']['motion']='../outside.npz'
    if defect=='nonfinite':motions['A']['posed_joints'][0,1,0]=np.nan
    with pytest.raises(ValueError):module.measure(scene,skin,motions,project_root=root)


def test_region_normals_keep_authored_requirements_instead_of_rejecting_whole_scene(fixture):
    from scene_region_contact import SCHEMA,mesh_fingerprint
    scene,skin,motions,root=fixture
    # Bottom face, above a box top by 2mm: distributed contact and winding match.
    ids=np.flatnonzero(np.all(np.isclose(skin['bind_vertices'][skin['faces'],1],.8),axis=1)).tolist()
    scene['contacts']=scene['contacts'][:1];c=scene['contacts'][0];c['effector']['surface_vertex']=int(skin['faces'][ids[0],0])
    scene['objects']['box']=dict(shape='box',size_m=[1.,1.,1.],keyframes=[dict(frame=0,translation_m=[0,.298,0],rotation_xyzw=[0,0,0,1])])
    c['target']=dict(space='object',object='box',point_m=[0,.5,0]);c['tolerance_m']=.4
    c['region_contact']=dict(schema=SCHEMA,mesh_sha256=mesh_fingerprint(skin),hand='LeftHand',face_ids=ids,
        limits=dict(clearance_m=.001,contact_gap_m=.003,spacing_m=.02,area_m2=.000025,centroid_error_m=.3,local_radius_m=.4,normal_degrees=10.))
    passed=module.measure(scene,skin,motions,project_root=root)
    assert passed['reference_screens_passed'] and passed['orientation']['region_normals_in_contact_evaluation']==['A']
    skin['bind_vertices'][np.unique(skin['faces'][ids]),1]+=.1
    c['region_contact']['mesh_sha256']=mesh_fingerprint(skin)
    failed=module.measure(scene,skin,motions,project_root=root)
    assert 'contact_reference_missed' in failed['flags']
    assert failed['contacts']['contacts'][0]['anchor_all_requested_frames_within_tolerance']


def test_authored_tangent_cannot_disappear_without_a_normal_basis(fixture):
    scene,skin,motions,root=fixture
    scene['contacts'][0]['tangent_target']=dict(space='world',direction=[1,0,0])
    with pytest.raises(ValueError,match='tangent needs'):module.measure(scene,skin,motions,project_root=root)


def test_orientation_rows_and_failure_counts_cannot_be_dropped(fixture):
    scene,skin,motions,root=fixture;scene['contacts'][0]['normal_target']=dict(space='world',direction=[0,1,0])
    record=module.measure(scene,skin,motions,project_root=root)
    saved=copy.deepcopy(record);record['orientation']['contacts']=[]
    with pytest.raises(ValueError,match='orientation population'):module.population(scene,record)
    saved['orientation']['contacts'][0]['frames_over_tolerance']=0
    with pytest.raises(ValueError,match='orientation decision'):module.population(scene,saved)


@pytest.fixture
def bound(fixture,tmp_path,monkeypatch):
    scene,skin,motions,root=fixture;folder=root/'batch';folder.mkdir();audit_folder=folder/'target-preflight'
    (audit_folder/'methods').mkdir(parents=True);(audit_folder/'model-reference').mkdir()
    monkeypatch.setattr(module,'ROOT',root);monkeypatch.setattr(module,'ASSET',root/'skin.npz')
    monkeypatch.setattr(module,'source_check',lambda:'test-pin')
    np.savez(module.ASSET,**skin);(root/'scripts').mkdir();(root/'vendor/kimodo').mkdir(parents=True)
    for name in module.METHODS:
        (root/'scripts'/name).write_text(name);(audit_folder/'methods'/name).write_text(name)
    for name in module.VENDOR_FILES:
        path=root/'vendor/kimodo'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(name)
    batch=dict(schema_version=1,requests=[dict(id='test',label='Test reference',segments=[dict(prompt='Move.',duration_s=1)],seeds=[1])])
    save(folder/'authored-scene.json',scene);save(folder/'request.json',batch)
    records={}
    for i,(name,entry) in enumerate(scene['actors'].items()):
        path=audit_folder/'model-reference'/f'actor-{i}.npz';np.savez(path,**motions[name])
        records[name]=dict(source_path=entry['motion'],source_sha256=entry['source_sha256'],projected_file=path.relative_to(audit_folder).as_posix(),projected_sha256=sha256(path))
    measurement=module.measure(scene,skin,motions,project_root=root)
    report=dict(schema=module.SCHEMA,status='complete',kimodo_commit='test-pin',scene_sha256=sha256(folder/'authored-scene.json'),limits=module.LIMITS.copy(),
        skin_sha256=sha256(module.ASSET),actors=records,methods_sha256={n:sha256(root/'scripts'/n) for n in module.METHODS},
        vendor_sha256={n:sha256(root/'vendor/kimodo'/n) for n in module.VENDOR_FILES},native=measurement,model=copy.deepcopy(measurement),
        reference_screens_passed=True,quality_approved=False,release_approved=False)
    save(audit_folder/'audit.json',report)
    freeze=dict(target_preflight_sha256=sha256(audit_folder/'audit.json'),target_preflight_mode='strict',
        scene_sha256=report['scene_sha256'],request_sha256=module.request_digest(batch))
    save(folder/'freeze.json',freeze)
    return folder,batch,report,freeze,root


def test_bound_preflight_accepts_exact_artifacts_and_preserves_legacy_batches(bound,tmp_path):
    folder,batch,report,_,_=bound
    assert module.validate_preflight(folder,batch)==report
    assert module.validate_preflight(tmp_path/'old',batch) is None


@pytest.mark.parametrize('defect',['source','projection','skin','method','vendor','missing_actor','request','scene','dropped_binding','approval','rebound','missing_geometry','missing_contact','negative_depth','upstream_revision'])
def test_preflight_rejects_changed_contracts_before_inference(bound,defect):
    folder,batch,report,freeze,root=bound;path=folder/'target-preflight/audit.json'
    if defect=='source':(root/'A.npz').write_bytes(b'changed')
    if defect=='projection':(folder/'target-preflight/model-reference/actor-0.npz').write_bytes(b'changed')
    if defect=='skin':(root/'skin.npz').write_bytes(b'changed')
    if defect=='method':(root/'scripts/scene_constraints.py').write_text('changed')
    if defect=='vendor':(root/'vendor/kimodo'/module.VENDOR_FILES[0]).write_text('changed')
    if defect=='missing_actor':del report['actors']['B']
    if defect=='request':batch['requests'][0]['seeds']=[2]
    if defect=='scene':save(folder/'authored-scene.json',{})
    if defect=='dropped_binding':del freeze['target_preflight_sha256']
    if defect=='approval':report['quality_approved']=True
    if defect=='rebound':report['model']['floor'][0]['depth_m']=.1
    if defect=='missing_geometry':report['model']['floor'].pop()
    if defect=='missing_contact':report['model']['contacts']['contacts'].pop()
    if defect=='negative_depth':report['model']['floor'][0]['depth_m']=-1
    if defect=='upstream_revision':report['kimodo_commit']='changed-pin'
    save(path,report)
    if defect!='dropped_binding':freeze['target_preflight_sha256']=sha256(path)
    save(folder/'freeze.json',freeze)
    with pytest.raises(ValueError):module.validate_preflight(folder,batch)


def test_partial_or_failed_preflight_cannot_fall_back_to_ordinary_generation(tmp_path):
    folder=tmp_path/'failed-preparation';save(folder/'target-preflight/state.json',dict(status='failed'))
    with pytest.raises(ValueError,match='binding was dropped'):module.validate_preflight(folder,{})


@pytest.mark.parametrize('value',[float('nan'),float('inf'),True])
def test_invalid_depths_cannot_become_false_comparisons(bound,value):
    _,_,report,_,_=bound;report['model']['floor'][0]['depth_m']=value
    with pytest.raises(ValueError,match='depth observations'):module.flags(report['model'])


def test_diagnostic_failed_reference_requires_explicit_mode_and_never_approval(bound):
    folder,batch,report,freeze,_=bound
    report['model']['floor'][0]['depth_m']=.1;report['model']['flags']=module.flags(report['model'])
    report['model']['reference_screens_passed']=False;report['reference_screens_passed']=False
    save(folder/'target-preflight/audit.json',report);freeze['target_preflight_sha256']=sha256(folder/'target-preflight/audit.json')
    save(folder/'freeze.json',freeze)
    with pytest.raises(ValueError,match='references fail'):module.validate_preflight(folder,batch)
    freeze['target_preflight_mode']='diagnostic';save(folder/'freeze.json',freeze)
    result=module.validate_preflight(folder,batch)
    assert not result['reference_screens_passed'] and not result['quality_approved']


def test_run_actions_checks_request_parent_even_with_different_output(bound,monkeypatch):
    import run_actions
    folder,batch,report,freeze,root=bound
    report['model']['floor'][0]['depth_m']=.1;report['model']['flags']=module.flags(report['model'])
    report['model']['reference_screens_passed']=False;report['reference_screens_passed']=False
    save(folder/'target-preflight/audit.json',report);freeze['target_preflight_sha256']=sha256(folder/'target-preflight/audit.json')
    save(folder/'freeze.json',freeze)
    monkeypatch.setattr(run_actions.subprocess,'Popen',lambda *a,**k:pytest.fail('Rejected references must not launch a subprocess'))
    with pytest.raises(ValueError,match='references fail'):run_actions.run(folder/'request.json',root/'other-output')
    assert not (root/'other-output').exists()
