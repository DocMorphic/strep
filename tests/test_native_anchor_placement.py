"""Explicit placement composition and independent bounds; no contact approval."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_anchor_placement import apply,stage,verify,SCHEMA
from native_scene_contacts import SceneContacts,pose
from test_native_shared_placement import data
from test_native_pivot_placement import permission as pivot_permission
from strep import read,save,sha256


def permission(spec):
    return dict(pivot=pivot_permission(spec),actors={n:dict(maximum_translation_m=.1,maximum_origin_displacement_m=.2) for n in spec['actors']})


@pytest.mark.parametrize('axis',[[0,1,0],[1,0,0],[0,0,1]])
def test_world_translation_occurs_after_pivot_and_preserves_complete_local_motion(tmp_path,axis):
    asset,spec,*_=data(tmp_path);before=copy.deepcopy(spec);old=SceneContacts(spec,tmp_path);limits=permission(spec)
    limits['pivot']['axis_world']=axis
    for bound in limits['pivot']['actors'].values():bound['maximum_origin_displacement_m']=1.
    for bound in limits['actors'].values():bound['maximum_origin_displacement_m']=1.
    shifts=dict(A=[.03,.01,-.02],B=[-.01,.005,.04]);new,meta=apply(spec,dict(A=5.,B=-7.),shifts,limits);placed=SceneContacts(new,tmp_path)
    assert spec==before and new['contacts']==spec['contacts'] and new['objects']==spec['objects']
    for n in spec['actors']:
        delta=np.array(meta['actors'][n]['world_delta']);p,q=pose(spec['actors'][n]['placement']);s,r=pose(new['actors'][n]['placement'])
        np.testing.assert_allclose(s,delta[:3,:3]@p+delta[:3,3],atol=3e-16,rtol=0)
        np.testing.assert_allclose(r,delta[:3,:3]@q,atol=5e-16,rtol=0)
        assert meta['actors'][n]['translation_world_m']==shifts[n]
        for time in (0.,.371,old.duration):
            a,b=old.actors[n],placed.actors[n];local=a['sampler'].sample(time)
            np.testing.assert_array_equal(local,b['sampler'].sample(time))
            p,q=a['placement'];s,r=b['placement'];v=a['rig'].vertices(local)@q.T+p
            np.testing.assert_allclose(b['rig'].vertices(local)@r.T+s,v@delta[:3,:3].T+delta[:3,3],atol=2e-15,rtol=0)
    assert not meta['quality_approved'] and not meta['joint_world_displacement_checked'] and not meta['local_animation_edited']


def test_zero_changes_preserve_original_quaternion_sign_and_spec(tmp_path):
    _,spec,*_=data(tmp_path);spec['actors']['A']['placement']['rotation_xyzw']=[0,0,0,-1]
    new,meta=apply(spec,dict(A=0.,B=0.),dict(A=[0,0,0],B=[0,0,0]),permission(spec))
    assert new==spec and meta['original_root_world_placement_contract_preserved']


@pytest.mark.parametrize('fault',['missing-shift','extra-shift','bool','nan','translation-bound','total-bound','missing-permission','negative-bound','unknown-field','bad-angle','pivot-bound'])
def test_undeclared_or_over_budget_changes_reject(tmp_path,fault):
    _,spec,*_=data(tmp_path);limits=permission(spec);angles=dict(A=5.,B=-7.);shifts=dict(A=[.03,.01,-.02],B=[-.01,.005,.04])
    if fault=='missing-shift':shifts.pop('A')
    elif fault=='extra-shift':shifts['C']=[0,0,0]
    elif fault=='bool':shifts['A'][0]=True
    elif fault=='nan':shifts['B'][1]=float('nan')
    elif fault=='translation-bound':limits['actors']['A']['maximum_translation_m']=.001
    elif fault=='total-bound':limits['actors']['B']['maximum_origin_displacement_m']=.0001
    elif fault=='missing-permission':limits['actors'].pop('B')
    elif fault=='negative-bound':limits['actors']['A']['maximum_translation_m']=-1.
    elif fault=='unknown-field':limits['actors']['A']['relax_contacts']=True
    elif fault=='bad-angle':angles['A']=11.
    else:limits['pivot']['actors']['A']['maximum_origin_displacement_m']=0.
    with pytest.raises(ValueError):apply(spec,angles,shifts,limits)


def amendment(tmp_path):
    asset,spec,cp,gp,path,_=data(tmp_path)
    request=dict(schema=SCHEMA,source_contacts=dict(path=cp.name,sha256=sha256(cp)),source_geometry=dict(path=gp.name,sha256=sha256(gp)),
        label='explicit anchored facing',angles_degrees=dict(A=5.,B=-7.),translations_world_m=dict(A=[.03,.01,-.02],B=[-.01,.005,.04]),permission=permission(spec))
    save(path,request);return asset,spec,cp,gp,path


def test_staging_and_semantic_replay_preserve_clips_targets_objects_clocks_and_limits(tmp_path):
    asset,spec,cp,gp,path=amendment(tmp_path);raw=asset.read_bytes();result=stage(path,tmp_path/'variant')
    assert asset.read_bytes()==raw and read(cp)==spec and result['variant_contract_exact']
    assert verify(tmp_path/'variant')=={k:v for k,v in result.items() if k not in ('status','label')}
    derived=read(tmp_path/'variant/contacts.json');assert derived['contacts']==spec['contacts'] and derived['objects']==spec['objects']
    policy=read(tmp_path/'variant/geometry.json');policy['contacts_sha256']=sha256(cp);assert policy==read(gp)


@pytest.mark.parametrize('fault',['target','limit','placement','asset','source','archive','claim','missing-artifact'])
def test_outer_rehash_cannot_authorize_semantic_or_provenance_changes(tmp_path,fault):
    asset,spec,cp,gp,path=amendment(tmp_path);out=tmp_path/'variant';stage(path,out)
    if fault=='asset':asset.write_bytes(asset.read_bytes()+b'changed')
    elif fault=='source':cp.write_bytes(cp.read_bytes()+b'\n')
    elif fault=='archive':(out/'implementation/native_anchor_placement.py').write_bytes(b'changed')
    elif fault=='claim':
        receipt=read(out/'provenance.json');receipt['quality_approved']=True;save(out/'provenance.json',receipt)
    elif fault=='missing-artifact':
        receipt=read(out/'provenance.json');receipt['files_sha256'].pop('source-geometry.json');save(out/'provenance.json',receipt)
    else:
        p=out/('geometry.json' if fault=='limit' else 'contacts.json');value=read(p)
        if fault=='target':value['contacts'][0]['target']['points_m'][0][0]+=.1
        elif fault=='limit':value['limits']['penetration_m']=.01
        else:value['actors']['B']['placement']['translation_m'][0]+=.001
        save(p,value);receipt=read(out/'provenance.json');receipt['files_sha256'][p.name]=sha256(p);save(out/'provenance.json',receipt)
    with pytest.raises(ValueError):verify(out)
