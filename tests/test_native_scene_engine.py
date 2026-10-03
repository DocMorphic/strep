"""Generic imported topology, clocks, raw skin and contact/scene comparisons."""
import copy
from pathlib import Path
import sys
import struct
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_scene_imported_skin import ImportedSceneSkin, godot_normalize
from native_scene_engine import EngineObservations, sample_times
from native_scene_contacts import SceneContacts
from native_scene_geometry import evaluate as geometry_audit, faces_for
from native_engine_contacts import packed_weights
from test_native_scene_geometry import closed_fixture, policy
from test_native_scene_contacts import setup, object_target
from test_native_support_skin_geometry import multiprimitive


def serialized(matrix): return np.vstack((matrix[:3,:3].T,matrix[:3,3])).tolist()


def mock_actor(rig,sampler,times,*,reverse=False,animation_index=0,path='actor.glb'):
    names = [rig.document['nodes'][n]['name'] for n in rig.joints]; bone_names = names[::-1]
    meshes = []; all_faces,_ = faces_for(rig); vertex_offset = 0; face_offset = 0
    for p in rig.primitives:
        count = len(p['positions']); number = rig.document['meshes'][rig.document['nodes'][p['node']]['mesh']]['primitives'][p['primitive']]
        from rig_asset import array
        face_count = len(array(rig.document,rig.binary,number['indices']))//3 if 'indices' in number else count//3
        faces = all_faces[face_offset:face_offset+face_count]-vertex_offset
        order = np.arange(count)[::-1]; inverse = np.empty(count,int); inverse[order] = np.arange(count)
        faces = inverse[faces]
        if reverse: faces = faces[:,::-1]
        from rig_asset import array
        attributes=number['attributes']
        raw=np.concatenate([array(rig.document,rig.binary,attributes[k]) for k in ('WEIGHTS_0','WEIGHTS_1') if k in attributes],axis=1)
        f32=lambda v:struct.unpack('<f',struct.pack('<f',float(v)))[0]
        normalized=[]
        for row in raw:
            total=0.
            for value in row:total=f32(total+f32(value))
            normalized.append([f32(f32(value)/total) for value in row])
        meshes.append(dict(node='mesh',surface=p['primitive'],positions=p['positions'][order].tolist(),
            bones=p['joints'][order,::-1].reshape(-1).tolist(),weights=packed_weights(normalized)[order,::-1].reshape(-1).tolist(),
            binds=[dict(bone=bone_names.index(name),pose=serialized(rig.inverse[i])) for i,name in enumerate(names)],
            primitive_type=3,indices=faces.reshape(-1).tolist()))
        vertex_offset += count; face_offset += face_count
    return dict(id='A',path=path,animation_index=animation_index,original_animation_count=len(rig.document['animations']),
        selected_animation='Imported',duration_s=sampler.duration,loop_mode=0,bone_names=bone_names,meshes=meshes,
        frames=[dict(requested_time_s=float(t),actual_time_s=float(t),skeleton_world=serialized(np.eye(4)),
            mesh_world=[dict(node='mesh',matrix=serialized(np.eye(4)))],
            bones=[serialized(sampler.sample(float(t))[rig.joints[names.index(name)]]) for name in bone_names]) for t in times])


@pytest.mark.parametrize('reverse',[False,True])
def test_complete_binding_and_topology_survive_bone_slot_vertex_and_winding_reordering(tmp_path,reverse):
    _,path,spec = closed_fixture(tmp_path); scene = SceneContacts(spec,tmp_path); actor=scene.actors['A']
    observed = mock_actor(actor['rig'],actor['sampler'],[0.,.853725,2.],reverse=reverse)
    skin = ImportedSceneSkin(actor['rig'],observed)
    assert skin.report['winding'] == ('globally-reversed' if reverse else 'unchanged')
    assert skin.report['source_faces']==skin.report['imported_faces']==12
    assert skin.report['source_vertex_coverage'] and not skin.report['raw_imported_weights_renormalized']
    for time in (0.,.853725,2.):
        world=actor['sampler'].sample(time)[actor['rig'].joints]
        np.testing.assert_allclose(skin.vertices(world),actor['rig'].vertices(actor['sampler'].sample(time)),atol=1e-15,rtol=0)


def test_all_materials_and_eight_influences_preserve_raw_imported_weight_deficit(tmp_path):
    rig,sampler = multiprimitive(tmp_path)
    from gltf_tools import append_accessor
    data=bytearray(rig.binary)
    for p in rig.primitives[1:]:
        attributes={}
        for slot in range(p['weights'].shape[1]//4):
            attributes['WEIGHTS_'+str(slot)]=append_accessor(rig.document,data,p['weights'][:,slot*4:(slot+1)*4],'VEC4')
        rig.document['meshes'][0]['primitives'].append(dict(attributes=attributes))
    rig.binary=bytes(data)
    observed=mock_actor(rig,sampler,[.853725])
    skin = ImportedSceneSkin(rig,observed)
    assert skin.report['imported_surfaces']==3 and skin.report['triangle_population_pass']
    assert np.any(skin.weights.sum(axis=1)<1)
    assert np.max(abs(skin.vertices(sampler.sample(.853725)[rig.joints])-rig.vertices(sampler.sample(.853725))))>0


def test_serial_float32_normalization_exposes_real_import_quantization_boundary():
    raw=np.array([[.13801783323287964,.5409290790557861,.2641514241695404,.05690164491534233],
        [.00570780411362648,.1994321644306183,.5112840533256531,.2835760712623596]],np.float32)
    raw=np.pad(raw,((0,0),(0,4)))
    serial=godot_normalize(raw)
    numpy=raw/raw.sum(axis=1,keepdims=True)
    assert not np.array_equal(serial,numpy)
    assert packed_weights(serial)[0,0] != packed_weights(numpy)[0,0]
    assert packed_weights(serial)[1,2] != packed_weights(numpy)[1,2]
    for row,out in zip(raw,serial):
        f32=lambda v:struct.unpack('<f',struct.pack('<f',float(v)))[0]
        total=0.
        for value in row:total=f32(total+float(value))
        np.testing.assert_array_equal(out,[f32(float(v)/total) for v in row])


@pytest.mark.parametrize('fault',['lost-face','repeat-face','partial-winding','wrong-bone','weight','lost-surface',
    'duplicate-surface','nontriangle','index-float','index-range','nan-bind','missing-bone'])
def test_changed_imported_geometry_cannot_pass_correspondence(tmp_path,fault):
    _,path,spec = closed_fixture(tmp_path); scene=SceneContacts(spec,tmp_path); actor=scene.actors['A']
    observed=mock_actor(actor['rig'],actor['sampler'],[0]); mesh=observed['meshes'][0]
    if fault=='lost-face': del mesh['indices'][:3]
    if fault=='repeat-face': mesh['indices'][:3]=mesh['indices'][3:6]
    if fault=='partial-winding': mesh['indices'][:3]=mesh['indices'][:3][::-1]
    if fault=='wrong-bone': mesh['bones'][3]=0 if mesh['bones'][3]!=0 else 1
    if fault=='weight': mesh['weights'][3]=.5
    if fault=='lost-surface': observed['meshes']=[]
    if fault=='duplicate-surface': observed['meshes'].append(copy.deepcopy(mesh))
    if fault=='nontriangle': mesh['primitive_type']=1
    if fault=='index-float': mesh['indices']=[float(i) for i in mesh['indices']]
    if fault=='index-range': mesh['indices'][0]=len(mesh['positions'])
    if fault=='nan-bind': mesh['binds'][0]['pose'][0][0]=np.nan
    if fault=='missing-bone': observed['bone_names'].pop()
    with pytest.raises(ValueError): ImportedSceneSkin(actor['rig'],observed)


def test_near_distinct_source_functions_are_ambiguous_not_nearest_best_fit(tmp_path):
    _,path,spec=closed_fixture(tmp_path); scene=SceneContacts(spec,tmp_path); actor=scene.actors['A']
    actor['rig'].primitives[0]['positions'][1]=actor['rig'].primitives[0]['positions'][0]+[1e-7,0,0]
    observed=mock_actor(actor['rig'],actor['sampler'],[0])
    with pytest.raises(ValueError,match='Unique complete'): ImportedSceneSkin(actor['rig'],observed)


def test_world_contacts_and_geometry_use_observed_actor_values_and_authored_placement(tmp_path):
    _,path,spec=closed_fixture(tmp_path); spec['actors']['A']['placement']['translation_m']=[2.,0,0]
    scene=SceneContacts(spec,tmp_path); native,arrays=scene.evaluate(); times=sample_times(scene,arrays,policy(path),policy(path)['contacts_sha256'])
    actor=scene.actors['A']; case=dict(id='A',path='actor.glb',animation_index=0)
    observed=mock_actor(actor['rig'],actor['sampler'],times)
    provider=EngineObservations(scene,dict(cases=[observed],objects=[]),[case],times)
    imported,_=scene.evaluate(actor_points=provider.actor_points)
    assert imported['contacts'][0]['maximum_position_error_m']==native['contacts'][0]['maximum_position_error_m']
    # Shift actual imported bones, retaining sources and authored world targets.
    for f in observed['frames']:
        for bone in f['bones']: bone[3][0]+=.05
    changed=EngineObservations(scene,dict(cases=[observed],objects=[]),[case],times)
    assert not changed.reports['A']['pose_samples_pass']
    new,_=scene.evaluate(actor_points=changed.actor_points)
    assert new['contacts'][0]['maximum_position_error_m']>native['contacts'][0]['maximum_position_error_m']+.049
    p=policy(path,planes=dict(wall=dict(normal_world=[-1.,0,0],offset_m=-2.21)))
    baseline,_=geometry_audit(scene,p,p['contacts_sha256'],actor_vertices=provider.actor_vertices)
    shifted,_=geometry_audit(scene,p,p['contacts_sha256'],actor_vertices=changed.actor_vertices)
    assert baseline['sampled_conditions_pass'] and not shifted['sampled_conditions_pass']


def test_object_and_partner_contacts_measure_actual_imported_counterparts(tmp_path):
    source,rig,reader,spec=setup(tmp_path,rotating=True); object_target(spec,reader,rig,gap=.001)
    from strep import save
    path=tmp_path/'contacts.json';save(path,spec);scene=SceneContacts(spec,tmp_path)
    native,arrays=scene.evaluate();times=sample_times(scene,arrays);actor=scene.actors['A'];case=dict(id='A',path='actor.glb')
    p,r=scene.object_poses('crate',times)
    frames=[]
    for t,position,rotation in zip(times,p,r):
        m=np.eye(4);m[:3,:3]=rotation;m[:3,3]=position
        frames.append(dict(requested_time_s=float(t),matrix=serialized(m),rotation_xyzw=Rotation.from_matrix(rotation).as_quat().tolist()))
    actual=dict(cases=[mock_actor(rig,reader,times)],objects=[dict(id='crate',frames=frames)])
    provider=EngineObservations(scene,actual,[case],times)
    assert provider.object_report['crate']['pose_samples_pass']
    imported,_=scene.evaluate(actor_points=provider.actor_points,object_poses=provider.object_poses)
    assert imported['passed']==native['passed']
    for f in frames:f['matrix'][3][0]+=.05
    changed=EngineObservations(scene,actual,[case],times)
    assert not changed.object_report['crate']['pose_samples_pass']
    failed,_=scene.evaluate(actor_points=changed.actor_points,object_poses=changed.object_poses)
    assert not failed['passed'] and failed['contacts'][0]['maximum_position_error_m']>.049
    # Partner measurement uses B's observed bones; it cannot reuse A or the source.
    spec['objects']={};spec['actors']['B']=copy.deepcopy(spec['actors']['A'])
    spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=[[6,0,0]],reduction='individual')
    scene=SceneContacts(spec,tmp_path); native,arrays=scene.evaluate();times=sample_times(scene,arrays)
    b=mock_actor(rig,reader,times,path='B.glb');b['id']='B'
    for f in b['frames']:
        for bone in f['bones']:bone[3][0]+=.04
    observed=EngineObservations(scene,dict(cases=[mock_actor(rig,reader,times),b],objects=[]),
        [case,dict(id='B',path='B.glb')],times)
    measured,_=scene.evaluate(actor_points=observed.actor_points)
    assert measured['contacts'][0]['maximum_position_error_m']>.039 and not measured['passed']


@pytest.mark.parametrize('fault',['index','path','count','clock','missing-clock','object','object-clock'])
def test_observation_identity_and_complete_clock_population_required(tmp_path,fault):
    _,path,spec=closed_fixture(tmp_path);scene=SceneContacts(spec,tmp_path);actor=scene.actors['A'];times=[0.,1.,2.]
    item=mock_actor(actor['rig'],actor['sampler'],times);actual=dict(cases=[item],objects=[])
    if fault=='index':item['animation_index']=1
    if fault=='path':item['path']='wrong.glb'
    if fault=='count':item['original_animation_count']=2
    if fault=='clock':item['frames'][1]['requested_time_s']+=.0001
    if fault=='missing-clock':item['frames'].pop()
    if fault.startswith('object'):actual['objects']=[dict(id='missing',frames=[])]
    with pytest.raises(ValueError):EngineObservations(scene,actual,[dict(id='A',path='actor.glb')],times)


@pytest.mark.parametrize('mode',['import','native-authoring'])
def test_complete_engine_job_records_provenance_and_retains_originals(tmp_path,monkeypatch,mode):
    import native_scene_engine as engine
    from strep import save,read,sha256
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    from types import SimpleNamespace
    source,path,spec=closed_fixture(tmp_path); pp=tmp_path/'policy.json'
    save(pp,policy(path,planes=dict(ground=dict(normal_world=[0.,1.,0.],offset_m=-2.))))
    exe=tmp_path/'fixture-engine';exe.write_bytes(b'fixture only')
    def execute(command,**kwargs):
        request=read(command[-2]); cases=[]
        for c in request['cases']:
            rig=RigAsset.load(c['path']);sampler=NativeSupportSampler(rig.document,rig.binary,c['animation_index'])
            item=mock_actor(rig,sampler,request['sample_times_s'],reverse=True,path=c['path'],animation_index=c['animation_index'])
            item['id']=c['id'];cases.append(item)
            if 'animation_output' in c:Path(c['animation_output']).write_bytes(b'fixture resource')
        save(command[-1],dict(engine=dict(string='fixture'),cases=cases,objects=[]))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(engine.subprocess,'run',execute)
    out=tmp_path/'audit';result=engine.run(path,out,geometry_policy=pp,engine=exe,playback_mode=mode)
    assert result['original_selected'] and result['imported_pose_samples_pass'] and result['imported_geometry_samples_pass']
    assert not result['imported_contact_samples_pass'] and not result['quality_approved'] and not result['gpu_skin_verified']
    assert not result['imported_contacts']['loaded_skin_weights_normalized']
    assert read(out/'pipeline.json')['status']=='complete'
    assert result['engine_executable_sha256']==sha256(exe)
    assert result['engine_output_sha256']==sha256(out/'engine-output.json')
    assert sha256(source)==spec['actors']['A']['sha256']
    for p,entry in result['source_snapshots'].items():assert sha256(p)==sha256(out/entry['path'])
    with pytest.raises(ValueError):engine.run(path,out,geometry_policy=pp,engine=exe)
    def changed(command,**kwargs):
        result=execute(command,**kwargs);path.write_bytes(path.read_bytes()+b'\n');return result
    monkeypatch.setattr(engine.subprocess,'run',changed)
    with pytest.raises(ValueError,match='source changed'):engine.run(path,tmp_path/'changed',geometry_policy=pp,engine=exe)
    assert read(tmp_path/'changed/pipeline.json')['status']=='failed'
    assert not (tmp_path/'changed/result.json').exists()
