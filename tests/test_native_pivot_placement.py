"""Bounded placement amendments retain source assets, clocks and target declarations."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_pivot_placement import apply,stage,verify,SCHEMA
from native_scene_contacts import SceneContacts,pose
from strep import read,save,sha256
from test_native_shared_placement import data


def permission(spec,axis=None):
    return dict(axis_world=[0,1,0] if axis is None else axis,pivot_world_m=[0,1.5,0],
        actors={name:dict(maximum_degrees=10.,maximum_origin_displacement_m=.1) for name in spec['actors']})


@pytest.mark.parametrize('axis',[[0,1,0],[1,0,0],[0,0,1]])
def test_world_pivot_composes_after_original_orientation_and_preserves_local_curves(tmp_path,axis):
    asset,spec,_,_,_,_=data(tmp_path);before=copy.deepcopy(spec);original=SceneContacts(spec,tmp_path)
    limits=permission(spec,axis)
    for bound in limits['actors'].values():bound['maximum_origin_displacement_m']=1.
    derived,meta=apply(spec,dict(A=5.,B=-7.),limits);placed=SceneContacts(derived,tmp_path)
    assert spec==before and derived['contacts']==spec['contacts'] and derived['objects']==spec['objects']
    assert not meta['original_root_world_placement_contract_preserved'] and not meta['local_animation_edited']
    assert not meta['joint_world_displacement_checked'] and not meta['quality_approved']
    for name in spec['actors']:
        delta=np.array(meta['actors'][name]['world_delta']);pivot=np.r_[limits['pivot_world_m'],1.]
        np.testing.assert_allclose(delta@pivot,pivot,atol=5e-16,rtol=0)
        p,r=original.actors[name]['placement'];q,s=placed.actors[name]['placement']
        np.testing.assert_allclose(s,delta[:3,:3]@r,atol=5e-16,rtol=0)
        np.testing.assert_allclose(q,delta[:3,:3]@p+delta[:3,3],atol=5e-16,rtol=0)
        for time in (0.,.371,original.duration):
            a,b=original.actors[name],placed.actors[name]
            world=a['sampler'].sample(time);np.testing.assert_array_equal(world,b['sampler'].sample(time))
            old=a['rig'].vertices(world)@r.T+p;new=b['rig'].vertices(world)@s.T+q
            np.testing.assert_allclose(new,old@delta[:3,:3].T+delta[:3,3],atol=2e-15,rtol=0)
            np.testing.assert_allclose(np.linalg.norm(new-limits['pivot_world_m'],axis=1),
                np.linalg.norm(old-limits['pivot_world_m'],axis=1),atol=2e-15,rtol=0)
    assert sha256(asset)==original.inputs[str(asset.resolve())]


def test_zero_rotations_preserve_original_quaternion_sign_and_complete_spec(tmp_path):
    _,spec,_,_,_,_=data(tmp_path);spec['actors']['A']['placement']['rotation_xyzw']=[0,0,0,-1]
    derived,meta=apply(spec,dict(A=0.,B=0.),permission(spec))
    assert derived==spec and meta['original_root_world_placement_contract_preserved']
    assert all(a['origin_displacement_m']==0 for a in meta['actors'].values())


def test_common_angle_preserves_relative_surface_distances(tmp_path):
    _,spec,_,_,_,_=data(tmp_path);old=SceneContacts(spec,tmp_path)
    derived,_=apply(spec,dict(A=7.,B=7.),permission(spec));new=SceneContacts(derived,tmp_path)
    def point(scene,name):
        a=scene.actors[name];p,r=a['placement'];return a['rig'].vertices(a['sampler'].sample(.371))[0]@r.T+p
    np.testing.assert_allclose(np.linalg.norm(point(old,'A')-point(old,'B')),
        np.linalg.norm(point(new,'A')-point(new,'B')),atol=1e-15,rtol=0)


@pytest.mark.parametrize('fault',['missing-angle','extra-angle','missing-permission','bool','nan','zero-axis','scaled-axis',
    'angle-bound','origin-bound','negative-bound','bad-rotation','unknown-field'])
def test_undeclared_invalid_or_over_budget_changes_reject(tmp_path,fault):
    _,spec,_,_,_,_=data(tmp_path);angles=dict(A=5.,B=-7.);limits=permission(spec)
    if fault=='missing-angle':angles.pop('B')
    elif fault=='extra-angle':angles['C']=0.
    elif fault=='missing-permission':limits['actors'].pop('B')
    elif fault=='bool':angles['A']=True
    elif fault=='nan':angles['B']=float('nan')
    elif fault=='zero-axis':limits['axis_world']=[0,0,0]
    elif fault=='scaled-axis':limits['axis_world']=[0,2,0]
    elif fault=='angle-bound':angles['A']=11.
    elif fault=='origin-bound':limits['actors']['B']['maximum_origin_displacement_m']=.0001
    elif fault=='negative-bound':limits['actors']['A']['maximum_degrees']=-1.
    elif fault=='bad-rotation':spec['actors']['A']['placement']['rotation_xyzw']=[0,0,0,0]
    else:limits['actors']['A']['implicit_override']=True
    with pytest.raises(ValueError):apply(spec,angles,limits)


def amendment(tmp_path):
    asset,spec,cp,gp,path,_=data(tmp_path)
    request=dict(schema=SCHEMA,source_contacts=dict(path=cp.name,sha256=sha256(cp)),
        source_geometry=dict(path=gp.name,sha256=sha256(gp)),label='bounded facing variant',
        angles_degrees=dict(A=5.,B=-7.),permission=permission(spec))
    save(path,request);return asset,spec,cp,gp,path,request


def test_stage_and_replay_preserve_every_source_target_object_clock_and_limit(tmp_path):
    asset,spec,cp,gp,path,request=amendment(tmp_path);before=asset.read_bytes()
    result=stage(path,tmp_path/'variant');derived=read(tmp_path/'variant/contacts.json')
    assert result['variant_contract_exact'] and result['geometry_clock_exact'] and result['source_bindings_exact']
    assert derived['contacts']==spec['contacts'] and derived['objects']==spec['objects'] and read(cp)==spec
    assert asset.read_bytes()==before and not result['asset_payloads_copied']
    policy=read(tmp_path/'variant/geometry.json');original=read(gp)
    assert policy['contacts_sha256']==sha256(tmp_path/'variant/contacts.json')
    policy['contacts_sha256']=original['contacts_sha256'];assert policy==original
    assert verify(tmp_path/'variant')=={k:v for k,v in result.items() if k not in ('status','label')}


@pytest.mark.parametrize('fault',['target','limit','placement','asset','source','archive','claim','missing-artifact'])
def test_rebinding_checksums_cannot_change_authored_variant_or_source(tmp_path,fault):
    asset,_,cp,_,path,_=amendment(tmp_path);out=tmp_path/'variant';stage(path,out)
    if fault=='asset':asset.write_bytes(asset.read_bytes()+b'changed')
    elif fault=='source':cp.write_bytes(cp.read_bytes()+b'\n')
    elif fault=='archive':(out/'implementation/native_pivot_placement.py').write_bytes(b'changed')
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


def test_fixed_actor_is_retained_and_no_unlisted_participant_can_move(tmp_path):
    _,spec,_,_,_,_=data(tmp_path);limits=permission(spec)
    limits['actors']['B']=dict(maximum_degrees=0.,maximum_origin_displacement_m=0.)
    derived,meta=apply(spec,dict(A=5.,B=0.),limits)
    assert derived['actors']['B']==spec['actors']['B'] and list(derived['actors'])==list(spec['actors'])
    assert meta['actors']['B']['original_world_placement_preserved']
