"""Added tracks remain bound to original static transforms and original caps."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_stored_pair_job import prepare as old_prepare
from native_static_rotation_variant import run as variant_run,SCHEMA as VARIANT
from native_stored_pair_job import Job,run,SCHEMA,STATIC_SCHEMA
from native_scene_contacts import SceneContacts
from native_scene_boundary_edit import BoundarySceneEdits
from native_rotation_storage_repair import StorageAdjustedEdits,authoring_digest
from strep import save,read,sha256


def prepare(tmp_path):
    path=old_prepare(tmp_path);job=read(path);spec=read(Path(job['source_scene']['path']));original=copy.deepcopy(job)
    source=(tmp_path/spec['actors']['A']['glb']).resolve()
    request=dict(schema=VARIANT,source=dict(path=str(source),sha256=sha256(source),animation_index=0),nodes=[0],
        clock_from=dict(node=0,path='translation'),sample_times_s=[0.,1.,2.],limits=dict(matrix_error_max=1e-7,vertex_error_max_m=1e-7),
        label='static joint rotation',acknowledge_float32_pose_drift=True)
    vp=tmp_path/'variant-request.json';save(vp,request);variant=variant_run(vp,tmp_path/'variant')
    spec['actors']['A'].update(glb=variant['candidate']['path'],sha256=variant['candidate']['sha256'],animation_index=1)
    source_scene=Path(job['source_scene']['path']);save(source_scene,spec);digest=sha256(source_scene)
    edit=read(Path(job['edit_request']['path']));edit['permissions']['contacts_sha256']=digest
    edit['permissions']['actors']['A']['tracks'].append(dict(node=0,path='rotation',maximum_change=5.))
    scene=SceneContacts(spec,tmp_path);base=BoundarySceneEdits(edit,scene,digest,rotation_storage_policy='source-scale')
    storage=read(Path(job['storage_policy']['path']));storage['authoring_sha256']=authoring_digest(base)
    editor=StorageAdjustedEdits(base,storage,[]);anchor=tmp_path/'new-anchor.glb';editor.export('A',base.initial,anchor)
    cp=tmp_path/'new-controls.npz';np.savez(cp,controls=base.initial)
    geometry=read(Path(job['geometry_policy']['path']));geometry['contacts_sha256']=digest
    save(Path(job['edit_request']['path']),edit);save(Path(job['storage_policy']['path']),storage);save(Path(job['geometry_policy']['path']),geometry)
    for role in ('source_scene','edit_request','storage_policy','geometry_policy'):job[role]['sha256']=sha256(Path(job[role]['path']))
    pin=lambda p:dict(path=str(p),sha256=sha256(p))
    contract=dict(schema='strep-native-static-reference-tracks-v1',source_scene_sha256=digest,reference_scene_sha256=original['reference_scene']['sha256'],
        actors={'A':[dict(node=0,path='rotation',clock_from=dict(node=0,path='translation'))]},acknowledge_original_static_baselines=True)
    binding=tmp_path/'static-reference.json';save(binding,contract)
    job.update(schema=STATIC_SCHEMA,static_reference_tracks=pin(binding));job['anchor']['controls']=pin(cp);job['anchor']['actor_files']={'A':pin(anchor)}
    save(path,job);return path,original


def test_complete_v2_job_keeps_original_reference_caps_and_static_baseline(tmp_path):
    path,original=prepare(tmp_path);job=Job(path)
    assert job.problem.size==6 and job.static_reference_keys=={('A',0,'rotation')}
    assert job.request['reference_scene']==original['reference_scene'] and job.request['source_rate_caps']==original['source_rate_caps']
    assert sha256(job.roles['reference_scene'])==original['reference_scene']['sha256'] and sha256(job.roles['source_rate_caps'])==original['source_rate_caps']['sha256']
    with np.load(job.roles['source_rate_caps'],allow_pickle=False) as data:
        for i,c in enumerate(job.problem.caps['A'].caps):np.testing.assert_array_equal(c,data['A_metric_'+str(i)])
    _,worlds=job.problem.decoded(job.files,job.value);bounds=job.reference_bounds(job.files,worlds)
    assert bounds['passed'] and bounds['tracks'][1]['baseline']=='original-static-transform'
    for i,t in enumerate(job.problem.times):np.testing.assert_array_equal(job.problem.source_world['A'][i],job.reference.actors['A']['sampler'].sample(float(t)))
    result=run(path,tmp_path/'output')
    assert result['schema']==STATIC_SCHEMA and result['records'] and result['controls']==6 and result['original_rate_caps_recomputed']
    assert result['original_selected'] and not result['release_approved']
    pin=result['input_snapshots']['static_reference_tracks'];assert sha256(tmp_path/'output'/pin['path'])==pin['sha256']
    assert all(r['reference_bounds']['tracks'][1]['baseline']=='original-static-transform' for r in result['records'])


@pytest.mark.parametrize('fault',['v1','missing','reference-pin','source-pin','ack','animated','clock','duplicate','path','actor','undeclared'])
def test_static_binding_rejects_implicit_or_rebased_reference(tmp_path,fault):
    path,_=prepare(tmp_path);value=read(path);p=Path(value['static_reference_tracks']['path']);binding=read(p)
    if fault=='v1':value['schema']=SCHEMA;value.pop('static_reference_tracks')
    elif fault=='missing':value.pop('static_reference_tracks')
    elif fault=='reference-pin':binding['reference_scene_sha256']='a'*64
    elif fault=='source-pin':binding['source_scene_sha256']='a'*64
    elif fault=='ack':binding['acknowledge_original_static_baselines']=False
    elif fault=='animated':binding['actors']['A'][0]=dict(node=0,path='translation',clock_from=dict(node=0,path='translation'))
    elif fault=='clock':binding['actors']['A'][0]['clock_from']['node']=5
    elif fault=='duplicate':binding['actors']['A']*=2
    elif fault=='path':binding['actors']['A'][0]['path']='scale'
    elif fault=='actor':binding['actors']={'B':binding['actors']['A']}
    elif fault=='undeclared':binding['actors']['A'][0]['node']=5
    save(p,binding)
    if 'static_reference_tracks' in value:value['static_reference_tracks']['sha256']=sha256(p)
    save(path,value);out=tmp_path/'output'
    with pytest.raises(ValueError):run(path,out)
    assert not out.exists()
