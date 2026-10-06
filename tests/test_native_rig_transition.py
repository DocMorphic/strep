"""Generated arbitrary gestures and failed moving supports; no model or engine double."""
import copy
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'scripts')]
import native_rig_transition as transition
import action_worker_lock
from native_transition_curve import LocalBridge,localize,rates
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from gltf_tools import append_accessor,write_glb
from rig_asset import RigAsset
from strep import read,save,sha256
from test_native_rig_transfer import fixture as rig_fixture


def fixture(root,*,moving=False,asset=None):
    if asset is None:source,_=rig_fixture(root,'transition',animated=False)
    else:
        import shutil
        root.mkdir(parents=True);source=root/'transition.glb';shutil.copyfile(asset,source)
    rig=RigAsset.load(source);doc=copy.deepcopy(rig.document);binary=bytearray(rig.binary)
    root_node=next(i for i,n in enumerate(doc['nodes']) if n['name'].endswith('_Hips'))
    arm=next(i for i,n in enumerate(doc['nodes']) if n['name'].endswith('_LeftArm'))
    foot=next(i for i,n in enumerate(doc['nodes']) if n['name'].endswith('_LeftFoot'))
    from gltf_tools import local_matrix
    base=local_matrix(doc['nodes'][root_node])[:3,3];rest=Rotation.from_matrix(local_matrix(doc['nodes'][arm])[:3,:3])
    for node in (root_node,arm):
        entry=doc['nodes'][node]
        if 'matrix' in entry:
            local=local_matrix(entry);entry.pop('matrix');entry.update(translation=local[:3,3].tolist(),rotation=Rotation.from_matrix(local[:3,:3]).as_quat().tolist(),scale=[1,1,1])
    times=np.array([0,.2,.4,.8],dtype='<f4');first_index=len(doc['animations'])
    for index in range(2):
        animation=dict(name=['arbitrary raise','arbitrary lower'][index],channels=[],samplers=[])
        q=(Rotation.from_euler('z',[0,5,15,20] if index==0 else [20,17,12,-10],degrees=True)*rest).as_quat()
        ti=append_accessor(doc,binary,times,'SCALAR')
        values=[(arm,'rotation',q,'VEC4')]
        if moving:
            p=base+np.array([[0,0,0],[.05,0,0],[.1,0,0],[.2,0,0]])
            values.append((root_node,'translation',p,'VEC3'))
        for node,path,value,kind in values:
            vi=append_accessor(doc,binary,value,kind);animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=path)))
            animation['samplers'].append(dict(input=ti,output=vi,interpolation='LINEAR'))
        doc['animations'].append(animation)
    write_glb(source,doc,binary);rig=RigAsset.load(source);skin=NativeSupportSkin(rig)
    # Explicit generated skin patch, no name-based anatomical contact inference.
    selected=np.flatnonzero(np.any((skin.nodes==foot)&(skin.weights>0),axis=1))[:1]
    reader=NativeSupportSampler(rig.document,rig.binary,first_index);cut=float(times[2]);world=reader.sample(cut)
    vertices=rig.vertices(world)
    recipe=dict(schema=transition.SCHEMA,source=dict(path=source.name,sha256=sha256(source)),animation_indices=[first_index,first_index+1],
        cuts_s=[cut,float(times[1])],root_node=root_node,bridge_duration_s=.2,rate=240,label='arbitrary gesture transition',
        maximum_pose_vertex_queries=1000000,limits=dict(curve_control_rotation_degrees=170,bridge_root_excursion_m=.1,
            linear_boundary_jump_m_s=.1,angular_boundary_jump_degrees_s=2,root_acceleration_m_s2=20),
        floor=dict(height_m=float(vertices[:,1].min()),maximum_penetration_m=1e-5),supports=[dict(id='authored-generated-patch',
            vertices=skin.vertex_references[selected].tolist(),points_m=vertices[selected].tolist(),interval_u=[0.,1.],limits=dict(position_m=1e-5,relative_speed_m_s=1e-5))])
    path=root/'recipe.json';save(path,recipe);return path,recipe


@pytest.fixture(scope='module')
def study(tmp_path_factory):
    root=tmp_path_factory.mktemp('native-transition');patch=pytest.MonkeyPatch();patch.setattr(action_worker_lock,'ROOT',root)
    path,recipe=fixture(root);out=root/'transition';result=transition.run(path,out)
    yield root,path,recipe,out,result
    patch.undo()


def test_noncommuting_spherical_curve_matches_both_endpoint_angular_and_translation_tangents():
    a=np.tile(np.eye(4),(3,1,1));b=a.copy()
    a[:,:3,:3]=Rotation.from_euler('xyz',[[20,-35,12],[40,12,-15],[-7,25,4]],degrees=True).as_matrix()
    b[:,:3,:3]=Rotation.from_euler('zyx',[[30,15,-20],[10,22,40],[18,-12,5]],degrees=True).as_matrix()
    va=np.array([[.2,-.1,.4],[0,.2,.1],[.1,.1,0]]);vb=-va/2
    wa=np.array([[.1,.3,-.2],[.4,-.1,.2],[.05,.2,.1]]);wb=-wa/2
    curve=LocalBridge(a,b,va,vb,wa,wb,.4,170);h=1e-7
    samples=curve.sample([0,h,.4-h,.4]);assert np.array_equal(samples[0],a) and np.array_equal(samples[-1],b)
    v,w=rates(samples,np.array([0,h,.4-h,.4]));np.testing.assert_allclose(v[[0,-1]],[va,vb],atol=2e-6,rtol=0)
    np.testing.assert_allclose(w[[0,-1]],[wa,wb],atol=3e-6,rtol=0)


def test_preserves_every_old_clip_and_payload_while_matching_native_rates_and_support(study):
    root,_,recipe,out,r=study;assert r['all_declared_samples_pass'] is True
    assert transition.verify(out)==r and all(r[n] is False for n in transition.FALSE_FLAGS)
    old=RigAsset.load(root/recipe['source']['path']);new=RigAsset.load(out/'character.glb')
    assert new.document['animations'][:-1]==old.document['animations'] and new.binary[:len(old.binary)]==old.binary
    assert all(c['target']['node']!=recipe['root_node'] and c['target']['path']=='rotation' for c in new.document['animations'][-1]['channels'])
    assert r['animation_index']==3 and r['support_conditions_available'] and r['floor_conditions_available']
    assert r['supports'][0]['passed'] and r['supports'][0]['maximum_slip_m_s']<1e-10
    p=transition.Problem(recipe,root);reader=NativeSupportSampler(new.document,new.binary,r['animation_index'])
    for t in p.times[p.times<=p.start]:np.testing.assert_allclose(reader.sample(float(t)),p.readers[0].sample(float(t)),atol=1e-6,rtol=0)
    for t,original in p.tail_source.items():np.testing.assert_allclose(reader.sample(t),p.readers[1].sample(original),atol=1e-6,rtol=0)
    before=[]
    for i,(cut,source) in enumerate(zip(recipe['cuts_s'],p.readers)):
        clock=np.unique(np.concatenate([c[2] for c in source.channels])).astype(float);at=int(np.searchsorted(clock,cut));pair=clock[at-1:at+1] if i==0 else clock[at:at+2]
        world=np.array([source.sample(t) for t in pair]);_,omega=rates(world,pair);before.append(omega[0])
    direct_jump=float(np.degrees(np.linalg.norm(before[1][old.joints]-before[0][old.joints],axis=1)).max())
    assert max(x['angular_jump_degrees_s'] for x in r['boundaries'])<direct_jump/10


def test_failed_moving_support_is_retained_without_quality_or_empty_success(tmp_path,monkeypatch):
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path);path,_=fixture(tmp_path,moving=True);out=tmp_path/'out';r=transition.run(path,out)
    assert r['checks']['supports'] is False and r['all_declared_samples_pass'] is False
    assert r['supports'][0]['maximum_position_error_m']>1e-3 and r['supports'][0]['maximum_slip_m_s']>1e-3
    assert read(out/'pipeline.json')['status']=='complete' and r['original_selected'] is True and not r['quality_approved']
    assert transition.verify(out)==r


def test_undeclared_floor_and_support_are_unavailable(study):
    root,_,recipe,_,_=study;p=copy.deepcopy(recipe);p.update(floor=None,supports=[])
    problem=transition.Problem(p,root)
    # Same deterministic animation: declarations change auditing, not curve generation.
    r=problem.audit(root/'transition/character.glb')
    assert r['floor_conditions_available'] is False and r['support_conditions_available'] is False
    assert r['floor_maximum_penetration_m'] is None and not any(n in r['checks'] for n in ('floor','supports'))


@pytest.mark.parametrize('fault',['source-hash','index-bool','root-bool','cut-bool','cut-nonnative','cut-endpoint','rate-bool','budget','budget-bool','duration-nan','duration-zero','control-branch','limit-bool','floor-bool','support-empty-span','support-ref','support-duplicate','extra-field'])
def test_invalid_or_unbounded_recipe_rejects_before_output(study,tmp_path,fault):
    root,_,recipe,_,_=study;p=copy.deepcopy(recipe);p['source']['path']=str(root/p['source']['path'])
    if fault=='source-hash':p['source']['sha256']='f'*64
    elif fault=='index-bool':p['animation_indices'][1]=True
    elif fault=='root-bool':p['root_node']=True
    elif fault=='cut-bool':p['cuts_s'][0]=True
    elif fault=='cut-nonnative':p['cuts_s'][0]=.333333
    elif fault=='cut-endpoint':p['cuts_s'][0]=0
    elif fault=='rate-bool':p['rate']=True
    elif fault=='budget':p['maximum_pose_vertex_queries']=1
    elif fault=='budget-bool':p['maximum_pose_vertex_queries']=True
    elif fault=='duration-nan':p['bridge_duration_s']=float('nan')
    elif fault=='duration-zero':p['bridge_duration_s']=0
    elif fault=='control-branch':p['limits']['curve_control_rotation_degrees']=180
    elif fault=='limit-bool':p['limits']['linear_boundary_jump_m_s']=True
    elif fault=='floor-bool':p['floor']['height_m']=False
    elif fault=='support-empty-span':p['supports'][0]['interval_u']=[.5,.5]
    elif fault=='support-ref':p['supports'][0]['vertices'][0][2]=999999
    elif fault=='support-duplicate':p['supports'].append(copy.deepcopy(p['supports'][0]))
    else:p['approve']=True
    path=tmp_path/'bad.json';out=tmp_path/'out'
    if fault=='duration-nan':path.write_text(__import__('json').dumps(p),encoding='utf-8')
    else:save(path,p)
    with pytest.raises(ValueError):transition.run(path,out)
    assert not out.exists()


@pytest.mark.parametrize('fault',['approval','boundary','support','typed-flag','glb','glb-label','source-snapshot','drop-original','method'])
def test_rehashed_summary_payload_or_provenance_changes_reject(study,fault):
    _,_,_,out,_=study;changed={p:p.read_bytes() for p in [out/'result.json',out/'completion.json']}
    def edit(name,fn):
        p=out/name;changed.setdefault(p,p.read_bytes());v=read(p);fn(v);save(p,v)
    try:
        if fault=='approval':edit('result.json',lambda v:v.update(quality_approved=True))
        elif fault=='boundary':edit('result.json',lambda v:v['boundaries'][0].update(angular_jump_degrees_s=0))
        elif fault=='support':edit('result.json',lambda v:v['supports'][0].update(samples=1))
        elif fault=='typed-flag':edit('result.json',lambda v:v.update(original_selected=1))
        elif fault=='drop-original':edit('prepared.json',lambda v:v['inputs_sha256'].pop(next(iter(v['inputs_sha256']))))
        elif fault=='glb-label':
            p=out/'character.glb';changed[p]=p.read_bytes();rig=RigAsset.load(p);doc=copy.deepcopy(rig.document)
            doc['animations'][-1]['name']='Another authored label';write_glb(p,doc,rig.binary)
        else:
            name={'glb':'character.glb','source-snapshot':'source.glb','method':'implementation/native_transition_curve.py'}[fault]
            p=out/name;changed[p]=p.read_bytes();p.write_bytes(p.read_bytes()+b'changed')
        edit('result.json',lambda v:v.update(prepared_sha256=sha256(out/'prepared.json'),glb_sha256=sha256(out/'character.glb')))
        save(out/'completion.json',dict(result_sha256=sha256(out/'result.json')))
        with pytest.raises(ValueError):transition.verify(out)
    finally:
        for p,data in changed.items():p.write_bytes(data)


def test_too_short_spherical_control_budget_rejects_not_rescales_source(study,tmp_path):
    root,_,recipe,_,_=study;p=copy.deepcopy(recipe);p['limits']['curve_control_rotation_degrees']=.01
    with pytest.raises(ValueError,match='control'):transition.Problem(p,root)


def test_floor_failure_keeps_candidate_and_unchanged_authored_limit(study):
    root,_,recipe,_,_=study;p=copy.deepcopy(recipe);p['floor']['height_m']+=.01
    r=transition.Problem(p,root).audit(root/'transition/character.glb')
    assert r['checks']['floor'] is False and r['floor_maximum_penetration_m']>.00999
    assert not r['all_declared_samples_pass'] and not r['quality_approved']


def test_unwrapped_tangent_cannot_alias_through_multiple_turns():
    a=np.tile(np.eye(4),(1,1,1));zero=np.zeros((1,3));omega=np.array([[0.,0.,100.]])
    with pytest.raises(ValueError,match='Unwrapped'):LocalBridge(a,a,zero,zero,omega,zero,.4,170)
