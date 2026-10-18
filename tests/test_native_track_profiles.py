"""Complete temporal controls, independent pose values and full-column directions."""
from pathlib import Path
import sys
import numpy as np
import pytest
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_track_profiles.py').is_file())
sys.path[:0]=[str(root/'scripts'),str(root/'tests')]
from native_track_profiles import NativeTrackProfiles,TrackProfilePoseRows
from test_native_basis_pose_rows import setup
from native_key_contact_initializer import encode
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset


def simple():
    clock=np.array([0.,.1,.3,.6,1.]);nodes=[7,3,9];seed=np.zeros((5,3,3));seed[0,0,0]=-0.
    seed[1:4]=.1;d=np.zeros_like(seed);d[1:4]=np.arange(27).reshape(3,3,3)/1000
    d[:,0]=0
    return clock,nodes,seed,d,[1,2,3],[0,4]


def test_complete_grid_matches_explicit_author_relative_edit_and_all_frozen_bytes():
    t,n,s,d,e,f=simple();p=NativeTrackProfiles(t,n,s,d,e,f);v=np.array([.7,-.2,.8]);actual=p.coefficients(v)
    for key in range(len(t)):
        for j in range(len(n)):
            for axis in range(3):
                if d[key,j,axis]:assert actual[key,j,axis]==s[key,j,axis]+d[key,j,axis]*v[j]
                else:assert actual[key,j,axis].tobytes()==s[key,j,axis].tobytes()
    assert p.size==3 and not p.report['quality_approved'] and not p.report['release_approved']
    assert p.report['nodes']==n and p.report['editable_keys']==e


def test_all_native_rows_columns_and_subsets_keep_zero_profile_and_last_column():
    args=simple();p=NativeTrackProfiles(*args);v=np.array([.3,-.2,.4]);allrows=[];alljac=[]
    for start,count in [(0,2),(2,3)]:
        r,j=p.native_chunk(v,start,count);allrows.extend(r);alljac.extend(j)
    r=np.array(allrows);j=np.array(alljac);assert r.shape==(15,) and j.shape==(15,3)
    assert not np.any(j[:,0]) and np.any(j[:,-1])
    step=1e-5;direction=np.array([.4,-.3,.6])
    a=p.native_chunk(v+step*direction,0,5)[0];b=p.native_chunk(v-step*direction,0,5)[0]
    np.testing.assert_allclose(j@direction,(a-b)/(2*step),atol=2e-11,rtol=0)
    for keys in [[4,1],[2],[0,1,2,3,4]]:
        c,m=p.endpoint_map(v,keys);np.testing.assert_array_equal(c,p.coefficients(v)[keys]);assert m.shape==(len(keys)*9,3)
    assert p.native_chunk(v,0,5,jacobian=False)[1] is None


def test_source_inputs_report_and_returned_arrays_are_owned_snapshots():
    t,n,s,d,e,f=simple();p=NativeTrackProfiles(t,n,s,d,e,f);v=np.array([.2,.3,.4]);before=p.coefficients(v)
    t[:]=123;s[:]=.2;d[:]=.5;n.reverse();e.clear();f.clear();p.report['nodes'].clear()
    c,j=p.endpoint_map(v,[1,2]);c[:]=99;j[:]=99;p.coefficients(v)[:]=99
    assert p.coefficients(v).tobytes()==before.tobytes() and p.report['nodes']==[7,3,9]


def test_zero_amplitude_keeps_seed_signed_zero_even_on_nonzero_directions():
    t,n,s,d,e,f=simple();s[2,2,1]=-0.;d[2,2,1]=.2;p=NativeTrackProfiles(t,n,s,d,e,f)
    assert p.coefficients(np.zeros(3)).tobytes()==s.tobytes()
    c,_=p.endpoint_map(np.zeros(3),[2]);assert c.tobytes()==s[[2]].tobytes()


def test_native_ball_failure_is_retained_until_export_and_never_clipped():
    t,n,s,d,e,f=simple();s[2,2]=[.99,0,0];d[2,2]=[.1,0,0];p=NativeTrackProfiles(t,n,s,d,e,f)
    assert p.native_chunk(np.ones(3),2,1)[0][-1]<0
    assert p.coefficients(np.ones(3))[2,2,0]==1.09
    with pytest.raises(ValueError,match='no projection or clipping'):p.export_coefficients(np.ones(3))
    assert p.export_coefficients(np.zeros(3)).tobytes()==s.tobytes()


@pytest.mark.parametrize('fault',['missing_node','clock','seed_shape','seed_nan','seed_ball','direction_shape','direction_nan','direction_large','frozen','outside','duplicate_keys','missing_endpoint','overlap','budget'])
def test_bad_or_incomplete_profile_is_rejected_whole(fault):
    t,n,s,d,e,f=simple();kw={}
    if fault=='missing_node':n.pop()
    elif fault=='clock':t[2]=t[1]
    elif fault=='seed_shape':s=s[:-1]
    elif fault=='seed_nan':s[2,0,0]=np.nan
    elif fault=='seed_ball':s[2,0]=[1,1,0]
    elif fault=='direction_shape':d=d[:,:-1]
    elif fault=='direction_nan':d[2,1,0]=np.inf
    elif fault=='direction_large':d[2,1,0]=1.1
    elif fault=='frozen':d[0,1,0]=.1
    elif fault=='outside':e=[2,3]
    elif fault=='duplicate_keys':e=[1,1,2,3]
    elif fault=='missing_endpoint':f=[0]
    elif fault=='overlap':f=[0,2,4]
    else:kw['maximum_bytes']=1
    with pytest.raises(ValueError):NativeTrackProfiles(t,n,s,d,e,f,**kw)


@pytest.mark.parametrize('v',[np.zeros(2),np.array([0.,np.nan,0.]),np.array([0.,1.01,0.]),np.zeros(3,dtype=bool)])
def test_invalid_amplitudes_reject(v):
    p=NativeTrackProfiles(*simple())
    with pytest.raises(ValueError):p.coefficients(v)


def test_complete_endpoint_matrix_over_budget_is_rejected_without_column_reduction():
    t=np.arange(65,dtype=float);s=np.zeros((65,256,3));p=NativeTrackProfiles(t,list(range(256)),s,s.copy(),list(range(1,64)),[0,64])
    with pytest.raises(ValueError,match='no keys/columns removed'):p.endpoint_map(np.zeros(256),list(range(64)))


def posed(tmp_path,mode):
    model,mapper,_,caps,_,_=setup(tmp_path,mode);d=np.zeros_like(mapper.seed)
    d[3:7]=np.random.default_rng(17).uniform(-.02,.02,size=d[3:7].shape)
    profiles=NativeTrackProfiles(mapper.clock,list(mapper.nodes),mapper.seed,d,[3,4,5,6],[0,2,len(d)-1])
    return model,mapper,caps,profiles,TrackProfilePoseRows(mapper,profiles,caps)


@pytest.mark.parametrize('mode',['start','native','subkey','end'])
def test_complete_pose_matches_direct_original_mapper_and_full_vector_directions(tmp_path,mode):
    model,mapper,caps,p,adapter=posed(tmp_path,mode);v=np.linspace(-.2,.3,p.size);actual=adapter.evaluate_vectors(v)
    endpoints,chain=p.endpoint_map(v,mapper.bracket.tolist());full,local=mapper.evaluate(endpoints.ravel())
    independent=model._forward(full,[])[0];np.testing.assert_array_equal(actual['world'],independent)
    delta=independent[np.asarray(model.rig.joints),:3,3]-model.source[np.asarray(model.rig.joints),:3,3]
    expected=np.vstack([full.reshape(-1,3),delta]);assert actual['vectors'].tobytes()==expected.tobytes()
    np.testing.assert_array_equal(actual['radii'],np.r_[np.ones(len(model.nodes)),caps])
    assert actual['jacobian'].shape==(len(expected),3,p.size)
    for direction in [np.eye(p.size)[-1],np.random.default_rng(5).normal(size=p.size)]:
        h=1e-5;a=adapter.evaluate_vectors(v+h*direction,jacobian=False);b=adapter.evaluate_vectors(v-h*direction,jacobian=False)
        np.testing.assert_allclose(actual['jacobian']@direction,(a['vectors']-b['vectors'])/(2*h),atol=2e-7,rtol=2e-5)
        np.testing.assert_allclose(actual['world_jacobian']@direction,(a['world']-b['world'])/(2*h),atol=2e-7,rtol=2e-5)
    if mode in ['start','end']:assert not np.any(actual['world_jacobian'])


def test_encoded_profile_pose_matches_independently_saved_native_clip(tmp_path):
    model,mapper,caps,p,adapter=posed(tmp_path,'subkey');v=np.linspace(-.2,.3,p.size);path=tmp_path/'profile.glb'
    channels=[next(c for c in model.actor['sampler'].channels if c[:2]==(n,'rotation')) for n in model.nodes]
    index=encode(model.rig,model.actor['animation_index'],list(model.nodes),channels,p.export_coefficients(v),np.degrees(model.caps),path)
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,index)
    actual=adapter.evaluate_vectors(v,jacobian=False,encoded=True)
    np.testing.assert_allclose(actual['world'],reader.sample(mapper.time_s),atol=2e-12,rtol=0)
    assert actual['jacobian'] is actual['world_jacobian'] is None
    with pytest.raises(ValueError):adapter.evaluate_vectors(v,encoded=True)


def test_changed_original_map_rejects_before_any_pose(tmp_path,monkeypatch):
    model,mapper,caps,p,adapter=posed(tmp_path,'subkey');mapper.seed=mapper.seed*.9
    monkeypatch.setattr(model,'_forward',lambda *a:pytest.fail('changed source evaluated'))
    with pytest.raises(ValueError):adapter.evaluate_vectors(np.zeros(p.size))


def test_profile_pose_rejects_mismatched_seed_and_whole_workspace(tmp_path):
    model,mapper,caps,p,adapter=posed(tmp_path,'subkey')
    other=NativeTrackProfiles(mapper.clock,list(mapper.nodes),mapper.seed*.9,p._direction,[3,4,5,6],[0,2,len(mapper.clock)-1])
    with pytest.raises(ValueError,match='must match'):TrackProfilePoseRows(mapper,other,caps)
    with pytest.raises(ValueError):TrackProfilePoseRows(mapper,p,caps,maximum_bytes=1)
