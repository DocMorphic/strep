"""Explicit variable tracks retain complete original bounds and inactive motion."""
import copy
import numpy as np
import pytest
from test_native_affine_interval_seed import inputs
from native_key_interval_model import KeyIntervalModel
from native_key_interval_restoration import run,validate,SCHEMA
from audit_native_key_restoration import run as replay
from native_key_restoration_continuation import load as load_continuation
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from gltf_tools import append_accessor,write_glb
from strep import read,save,sha256


def two_tracks(tmp_path):
    paths=inputs(tmp_path);spec=read(paths['contacts']);source=tmp_path/spec['actors']['A']['glb'];rig=RigAsset.load(source)
    document=copy.deepcopy(rig.document);binary=bytearray(rig.binary);animation=document['animations'][0]
    rotation=next(c for c in animation['channels'] if c['target']==dict(node=3,path='rotation'))
    clock=animation['samplers'][rotation['sampler']]['input'];count=document['accessors'][clock]['count']
    if not any(c['target']==dict(node=2,path='rotation') for c in animation['channels']):
        animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=2,path='rotation')))
        values=np.tile(document['nodes'][2].get('rotation',[0.,0.,0.,1.]),(count,1))
        animation['samplers'].append(dict(input=clock,output=append_accessor(document,binary,values,'VEC4'),interpolation='LINEAR'))
    write_glb(source,document,binary);spec['actors']['A']['sha256']=sha256(source);save(paths['contacts'],spec)
    request=read(paths['request']);request['rotations'].insert(0,dict(node=2,maximum_degrees=30.));request['contacts_sha256']=sha256(paths['contacts']);save(paths['request'],request)
    geometry=read(paths['geometry']);geometry['contacts_sha256']=sha256(paths['contacts']);save(paths['geometry'],geometry)
    with np.load(paths['controls']) as data:
        times=data['times_s'];seed=np.zeros((len(times),2,3));seed[:,1]=data['controls'][:,0];seed[7,0]=[0.,.015,0.]
    np.savez_compressed(paths['controls'],times_s=times,controls=seed)
    return paths


def build(paths,output,nodes=None):
    return KeyIntervalModel.from_inputs(**paths,active_keys=[3,4,5],output=output,
        expected_sha256={k:sha256(p) for k,p in paths.items()},active_nodes=nodes)


def test_selected_track_matches_actual_export_and_keeps_every_constraint(tmp_path):
    paths=two_tracks(tmp_path);selected=build(paths,tmp_path/'selected',[2]);all_tracks=build(paths,tmp_path/'all')
    assert selected.size==9 and all_tracks.size==18
    value=selected.initial.copy()+.02;full=selected.controls(value)
    np.testing.assert_array_equal(full[:,1],selected.seed[:,1])
    inactive=np.setdiff1d(np.arange(len(selected.clock)),selected.active);np.testing.assert_array_equal(full[inactive],selected.seed[inactive])
    all_value=full[all_tracks.active].ravel();np.testing.assert_array_equal(all_tracks.controls(all_value),full)
    path=tmp_path/'actual.glb';index=selected.export(value,path);rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,index)
    world=np.array([reader.sample(float(t)) for t in selected.times]);np.testing.assert_allclose(selected.worlds(value),world,atol=1e-12,rtol=0)
    a=selected.rows(value,world);b=all_tracks.rows(all_value,world)
    for name in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(a,name),getattr(b,name))
    assert selected.edit_count==all_tracks.edit_count and selected.rate_count==all_tracks.rate_count
    sa,ja,ia=selected.linearize(value,world,.01);sb,jb,ib=all_tracks.linearize(all_value,world,.01)
    assert ia['hard_rows']==ib['hard_rows'] and ia['original_rate_rows']==ib['original_rate_rows']
    assert ia['complete_floor_rows']==ib['complete_floor_rows'] and ia['witnesses']==ib['witnesses']
    e=selected.edit_count;r=selected.rate_count;f=ia['complete_floor_rows'];same=np.r_[np.arange(e+r),np.arange(e+r+f,e+2*r+f)]
    for name in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(sa,name)[same],getattr(sb,name)[same])
    np.testing.assert_array_equal(sa.scales,sb.scales)
    columns=np.arange(all_tracks.size).reshape(3,2,3)[:,0].ravel();difference=ja-jb[:,columns]
    assert not difference.nnz or np.max(abs(difference.data))<1e-10
    # Halfspace lifting chooses a trust-box-dependent offset. Physical floor
    # residuals remain equal even when the equivalent cone coefficients differ.
    for delta in (np.zeros(selected.size),np.linspace(-.005,.005,selected.size),np.linspace(.005,-.005,selected.size)):
        embedded=np.zeros(all_tracks.size);embedded[columns]=delta
        np.testing.assert_allclose(sa.residual(ja,delta),sb.residual(jb,embedded),atol=1e-11,rtol=0)
    fixed=next(c for c in reader.channels if c[:2]==(3,'rotation'))
    seed_rig=RigAsset.load(tmp_path/'selected/character.glb');original=NativeSupportSampler(seed_rig.document,seed_rig.binary,index)
    np.testing.assert_array_equal(fixed[3],next(c[3] for c in original.channels if c[:2]==(3,'rotation')))
    reordered=build(paths,tmp_path/'reordered',[3,2]);np.testing.assert_array_equal(reordered.controls(reordered.initial),reordered.seed)


@pytest.mark.parametrize('nodes',[[],[2,2],[999],[True],[2.], '2'])
def test_invalid_variable_track_declarations_reject(tmp_path,nodes):
    paths=two_tracks(tmp_path)
    with pytest.raises(ValueError,match='active rotation nodes'):build(paths,tmp_path/'bad',nodes)
    assert not (tmp_path/'bad').exists()


@pytest.mark.parametrize('nodes',[None,[],[True],[2,2],[-1],list(range(17))])
def test_recipe_mask_must_be_explicit_distinct_integer_nodes(nodes):
    recipe=dict(schema=SCHEMA,producer=dict(path='source',result_sha256='a'*64,request_sha256='b'*64),
        active_keys=[3,4],active_nodes=nodes,iterations=1,trust=.01,difference_step=.001,backoffs=2,maximum_seconds=60.)
    with pytest.raises(ValueError,match='active rotation nodes'):validate(recipe)


def test_public_seeded_mask_replays_complete_final_controls(tmp_path):
    paths=two_tracks(tmp_path)
    with np.load(paths['controls']) as data:times=data['times_s'];seed=np.zeros(data['controls'].shape)
    np.savez_compressed(paths['controls'],times_s=times,controls=seed)
    recipe=dict(schema=SCHEMA,seed={k:dict(path=str(p),sha256=sha256(p)) for k,p in paths.items()},
        active_keys=[3,4,5],active_nodes=[2],iterations=1,trust=.01,difference_step=.001,backoffs=2,maximum_seconds=60.)
    declaration=tmp_path/'recipe.json';save(declaration,recipe);out=tmp_path/'job';result=run(declaration,out)
    assert result['sampled_conditions_pass'] and read(out/'request.json')['controls']==9
    checked=replay(out,tmp_path/'replay',sha256(out/'result.json'),sha256(out/'request.json'))
    assert checked['retention_history_replayed'] and not checked['optimizer_executed']
    with np.load(out/'key-controls.npz') as data:
        np.testing.assert_array_equal(data['controls'],seed);assert data['controls'].shape[1]==2
    proof=tmp_path/'replay/result.json'
    problem,value,current,receipt=load_continuation(out,sha256(out/'result.json'),sha256(out/'request.json'),proof,sha256(proof),tmp_path/'continued')
    assert problem.active_nodes==[2] and problem.size==9 and receipt['original_rate_caps_preserved']
    np.testing.assert_array_equal(problem.controls(value),seed)
