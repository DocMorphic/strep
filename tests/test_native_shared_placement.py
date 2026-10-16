from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_shared_placement import apply,stage,verify,SCHEMA
from native_scene_contacts import SceneContacts
from strep import read,save,sha256
from test_native_scene_contacts import setup,object_target


def data(tmp_path):
    asset,rig,reader,spec=setup(tmp_path,rotating=True,mode='touch');spec['actors']['B']=copy.deepcopy(spec['actors']['A']);spec['actors']['B']['placement']['translation_m']=[.1,0,-.2]
    spec['actors']['B']['placement']['rotation_xyzw']=[0,.7071067811865475,0,.7071067811865476]
    permission=dict(actors=['A','B'],lower_world_m=[0,0,0],upper_world_m=[0,.006,0],maximum_displacement_m=.006)
    cp=tmp_path/'source.json';gp=tmp_path/'policy.json';save(cp,spec)
    policy=dict(schema='strep-native-scene-geometry-v1',contacts_sha256=sha256(cp),clock=dict(mode='explicit',times_s=[0.,reader.duration]),limits=dict(penetration_m=.005,depth_resolution_m=.0001,surface_tolerance_m=1e-6),planes=dict(floor=dict(normal_world=[0,1,0],offset_m=0)))
    save(gp,policy);amendment=tmp_path/'amendment.json';request=dict(schema=SCHEMA,source_contacts=dict(path=cp.name,sha256=sha256(cp)),source_geometry=dict(path=gp.name,sha256=sha256(gp)),label='shared placement',translation_world_m=[0,.00593630736098651,0],permission=permission);save(amendment,request)
    return asset,spec,cp,gp,amendment,request


def test_world_translation_preserves_local_assets_targets_and_relative_surfaces(tmp_path):
    asset,source,cp,gp,amendment,request=data(tmp_path);before=asset.read_bytes();original=SceneContacts(source,tmp_path)
    result=stage(amendment,tmp_path/'variant');derived=read(tmp_path/'variant/contacts.json');placed=SceneContacts(derived,tmp_path/'variant');delta=np.array(request['translation_world_m'])
    assert result['variant_contract_exact'] and not result['original_root_world_placement_contract_preserved'] and not result['quality_approved'];assert asset.read_bytes()==before
    assert derived['contacts']==source['contacts'] and derived['objects']==source['objects'] and read(cp)==source
    for t in (0.,.371,original.duration):
        points={}
        for name in source['actors']:
            a,b=original.actors[name],placed.actors[name];world=a['sampler'].sample(t);np.testing.assert_array_equal(world,b['sampler'].sample(t));p,r=a['placement'];q,s=b['placement'];np.testing.assert_array_equal(r,s)
            raw=a['rig'].vertices(world)@r.T+p;moved=b['rig'].vertices(world)@s.T+q;np.testing.assert_allclose(moved,raw+delta,atol=5e-16,rtol=0);points[name]=(raw,moved)
        np.testing.assert_allclose(points['A'][1]-points['B'][1],points['A'][0]-points['B'][0],atol=5e-16,rtol=0)
    policy=read(gp);new=read(tmp_path/'variant/geometry.json');new['contacts_sha256']=policy['contacts_sha256'];assert new==policy


@pytest.mark.parametrize('fault',['actors','bool','bounds','norm','permission','rotation'])
def test_undeclared_or_invalid_world_changes_reject(tmp_path,fault):
    _,spec,_,_,_,request=data(tmp_path);permission=request['permission'];delta=request['translation_world_m']
    if fault=='actors':permission['actors']=['A']
    elif fault=='bool':delta[1]=True
    elif fault=='bounds':delta[1]=.007
    elif fault=='norm':permission['maximum_displacement_m']=.001
    elif fault=='permission':permission['lower_world_m']=[0,.001,0]
    else:spec['actors']['A']['placement']['rotation_xyzw']=[0,0,0,0]
    with pytest.raises(ValueError):apply(spec,delta,permission)


@pytest.mark.parametrize('fault',['target','contact-limit','limit','placement','asset','source','archive'])
def test_replay_detects_changed_targets_limits_placements_assets_and_sources(tmp_path,fault):
    asset,_,cp,_,amendment,_=data(tmp_path);out=tmp_path/'variant';stage(amendment,out)
    if fault=='asset':asset.write_bytes(asset.read_bytes()+b'changed')
    elif fault=='source':cp.write_text(cp.read_text()+' ')
    elif fault=='archive':(out/'implementation/native_shared_placement.py').write_text('changed')
    else:
        p=out/('geometry.json' if fault=='limit' else 'contacts.json');value=read(p)
        if fault=='target':value['contacts'][0]['target']['points_m'][0][0]+=.1
        elif fault=='contact-limit':value['contacts'][0]['limits']['position_m']=1.
        elif fault=='limit':value['limits']['penetration_m']=.01
        else:value['actors']['B']['placement']['translation_m'][0]+=.001
        save(p,value)
        # Updating the outer checksum cannot authorize a semantic change.
        receipt=read(out/'provenance.json');receipt['files_sha256'][p.name]=sha256(p);save(out/'provenance.json',receipt)
    with pytest.raises(ValueError):verify(out)


@pytest.mark.parametrize('space',['object','actor'])
def test_shared_variant_preserves_object_tracks_and_all_target_frames(tmp_path,space):
    _,spec,cp,gp,amendment,request=data(tmp_path);loaded=SceneContacts(spec,tmp_path)
    if space=='object':
        object_target(spec,loaded.actors['A']['sampler'],loaded.actors['A']['rig']);spec['contacts'][0]['mode']='hold'
    else:spec['contacts'][0]['target']=dict(space='actor',actor='B',vertices=spec['contacts'][0]['vertices'],reduction='individual')
    save(cp,spec);policy=read(gp);policy['contacts_sha256']=sha256(cp);save(gp,policy);request['source_contacts']['sha256']=sha256(cp);request['source_geometry']['sha256']=sha256(gp);save(amendment,request)
    out=tmp_path/'variant';stage(amendment,out);derived=read(out/'contacts.json');assert derived['objects']==spec['objects'] and derived['contacts']==spec['contacts']
    if space=='actor':
        _,before=SceneContacts(spec,tmp_path).evaluate();_,after=SceneContacts(derived,out).evaluate();np.testing.assert_allclose(before['contact_0_error_m'],after['contact_0_error_m'],atol=1e-15,rtol=0)


def test_existing_output_and_changed_original_hash_reject_without_source_edits(tmp_path):
    _,_,cp,_,amendment,request=data(tmp_path);out=tmp_path/'variant';out.mkdir()
    with pytest.raises(ValueError):stage(amendment,out)
    request['source_contacts']['sha256']='0'*64;save(amendment,request)
    with pytest.raises(ValueError):stage(amendment,tmp_path/'other')
    assert not (tmp_path/'other').exists() and cp.is_file()
