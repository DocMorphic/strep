"""Portable full-source prop bindings; no engine evidence from these fixtures."""
import copy,json,sys,zipfile
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_runtime import fixture
from scene_prop_runtime import compile_request,package
from strep import save,read,sha256


def request_for(source,scene):
    node=int(scene.actors['A']['rig'].joints[0])
    return dict(schema='strep-scene-prop-runtime-request-v1',source_game_zip_sha256=sha256(source),
        root_modes={n:'extracted' for n in scene.actors},object_modes={n:'grip-physics' for n in scene.objects},
        grips={'left':dict(actor='A',joint_node=node,prop_offsets={'item':np.eye(4).tolist()})},
        commands=[dict(event_id='marker:grasp',object='item',grip='left',action='acquire'),dict(event_id='marker:terminal',object='item',grip='left',action='release')],
        physics={'item':dict(mass_kg=2,friction=.6,restitution=0,linear_damping=0,angular_damping=0,collision_layer=1,collision_mask=1)},
        physics_fps=120,history_capacity=80)


def test_full_source_bound_modes_joint_offsets_geometry_and_package_readback(tmp_path):
    folder,source,manifest,config,scene,_,events,_=fixture(tmp_path);request=request_for(source,scene)
    before=sha256(source);expected=compile_request(request,config,scene,events,before)
    assert expected['props']['item']['geometry']==scene.objects['item']['geometry'].record()
    assert expected['grip_bindings']['left']['character_glb_sha256']==manifest['files_sha256']['actors/0.glb']
    assert expected['ownership']['clock']==events['clock'] and expected['source_contacts_apply_to']=='unchanged-authored-reference-only'
    path=tmp_path/'request.json';save(path,request);request_before=path.read_bytes();output=tmp_path/'runtime'
    result=package(source,path,output)
    assert result['source_bytes_unchanged'] and not result['engine_executed'] and not result['physics_verified'] and not result['release_approved']
    assert sha256(source)==before and path.read_bytes()==request_before
    with zipfile.ZipFile(source) as original,zipfile.ZipFile(output/'prop-runtime-assets.zip') as exported:
        for n in original.namelist():assert exported.read('source-game-package.json' if n=='package.json' else n)==original.read(n)
        assert json.loads(exported.read('ownership-v1/prop-runtime.json'))==expected
        assert exported.read('ownership-v1/ownership-authoring-request.json')==request_before
        assert 'common/physics_ticks_per_second=120' in exported.read('project.godot').decode()
        assert set(exported.namelist())==set(result['files_sha256'])|{'package.json'}
    assert read(output/'pipeline.json')['status']=='complete'
    with pytest.raises(ValueError,match='Fresh'):package(source,path,output)


@pytest.mark.parametrize('fault',['hash','root-mode','prop-mode','no-physics','missing-physics','joint-bool','joint-outside','actor','offset-missing','offset-extra','offset-scale','offset-reflection','offset-lastrow','offset-bool','mass','friction','damping','layer-bool','layer-large','rate-bool','rate','history','unconfirmed','contact','extra'])
def test_no_guessed_or_partial_source_ownership(tmp_path,fault):
    _,source,_,config,scene,_,events,_=fixture(tmp_path);r=request_for(source,scene);digest=sha256(source)
    if fault=='hash':r['source_game_zip_sha256']='0'*64
    elif fault=='root-mode':r['root_modes'].pop('B')
    elif fault=='prop-mode':r['object_modes']['item']='guess'
    elif fault=='no-physics':r['object_modes']['item']='authored'
    elif fault=='missing-physics':r['physics'].clear()
    elif fault=='joint-bool':r['grips']['left']['joint_node']=True
    elif fault=='joint-outside':r['grips']['left']['joint_node']=999
    elif fault=='actor':r['grips']['left']['actor']='ghost'
    elif fault=='offset-missing':r['grips']['left']['prop_offsets'].clear()
    elif fault=='offset-extra':r['grips']['left']['prop_offsets']['ghost']=np.eye(4).tolist()
    elif fault=='offset-scale':r['grips']['left']['prop_offsets']['item'][0][0]=2
    elif fault=='offset-reflection':r['grips']['left']['prop_offsets']['item'][0][0]=-1
    elif fault=='offset-lastrow':r['grips']['left']['prop_offsets']['item'][3][0]=1
    elif fault=='offset-bool':r['grips']['left']['prop_offsets']['item'][0][0]=True
    elif fault=='mass':r['physics']['item']['mass_kg']=0
    elif fault=='friction':r['physics']['item']['friction']=2
    elif fault=='damping':r['physics']['item']['angular_damping']=float('nan')
    elif fault=='layer-bool':r['physics']['item']['collision_layer']=True
    elif fault=='layer-large':r['physics']['item']['collision_mask']=2**32
    elif fault=='rate-bool':r['physics_fps']=True
    elif fault=='rate':r['physics_fps']=90
    elif fault=='history':r['history_capacity']=1
    elif fault=='unconfirmed':r['commands'][0]['event_id']='marker:review'
    elif fault=='contact':r['commands'][0]['event_id']=next(e['id'] for e in events['events'] if e['kind']=='contact_intent')
    else:r['guess_anatomy']=True
    with pytest.raises(ValueError):compile_request(r,config,scene,events,digest)


def test_mixed_modes_keep_all_props_and_exact_offsets(tmp_path):
    _,source,_,config,scene,_,events,_=fixture(tmp_path)
    scene.objects['authored_reference']=copy.deepcopy(scene.objects['item'])
    config['objects']['names'].append('authored_reference')
    r=request_for(source,scene);r['object_modes']['authored_reference']='authored'
    compiled=compile_request(r,config,scene,events,sha256(source))
    assert set(compiled['object_modes'])==set(scene.objects) and compiled['ownership']['objects']==['item']
    assert 'authored_reference' not in compiled['props']


def test_failed_package_preserves_inputs_and_retains_failure_receipt(tmp_path):
    _,source,_,_,scene,_,_,_=fixture(tmp_path);r=request_for(source,scene);r['grips']['left']['joint_node']=True
    path=tmp_path/'request.json';save(path,r);before=(source.read_bytes(),path.read_bytes());out=tmp_path/'failure'
    with pytest.raises(ValueError):package(source,path,out)
    assert read(out/'pipeline.json')['status']=='failed' and not (out/'prop-runtime-assets.zip').exists()
    assert (source.read_bytes(),path.read_bytes())==before


def test_binary_callback_clock_rejects_rounded_or_forged_equal_decimal_times():
    from study_scene_prop_runtime import verify_event_bits
    times=np.array([0.,1/480,2.]);events={'events':[dict(id='fraction',sample_index=1,runtime_dispatch_allowed=True)]}
    bits=np.asarray([times[1]],dtype='<f8').tobytes().hex()
    row=dict(id='fraction',source_time_s=.00208333333333333,pose_time_s=.00208333333333333,source_time_f64le=bits,pose_time_f64le=bits)
    verify_event_bits([row],events,times)
    forged=dict(row,source_time_f64le=np.asarray([row['source_time_s']],dtype='<f8').tobytes().hex(),pose_time_f64le=np.asarray([row['pose_time_s']],dtype='<f8').tobytes().hex())
    with pytest.raises(AssertionError):verify_event_bits([forged],events,times)
