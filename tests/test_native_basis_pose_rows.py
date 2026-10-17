"""Independent full pose chain, encoded GLB, complete native chunks and source bindings."""
from pathlib import Path
import sys,copy
import numpy as np
import pytest
root=next(p for p in Path(__file__).resolve().parents if (p/'scripts/native_key_basis.py').is_file())
sys.path[:0]=[str(Path(__file__).parent),str(root/'scripts'),str(root/'tests')]
from native_basis_pose_rows import BasisPoseRows
from native_key_basis import NativeKeyBasis
from native_key_pose_map import KeyPoseMap
from native_affine_pose_bounds import PoseBoundsRows
from native_support_clock import NativeSupportSampler
from native_key_contact_initializer import encode
from rig_asset import RigAsset
from test_native_key_pose_map import inputs


def setup(tmp_path,mode='subkey'):
    model,stamp,seed,_=inputs(tmp_path,mode);seed[0,0,0]=-0.
    clock=next(c[2] for c in model.actor['sampler'].channels if c[:2]==(model.nodes[0],'rotation')).astype(float)
    key=int(np.searchsorted(clock,stamp,side='left'));keys=[0] if key==0 else [len(clock)-1] if key==len(clock) else [key] if clock[key]==stamp else [key-1,key]
    mapper=KeyPoseMap(model,stamp,seed,[(int(k),n) for k in keys for n in model.nodes])
    basis=NativeKeyBasis(clock,list(model.nodes),seed,[0,5,6,len(clock)-1],[0,len(clock)-1])
    caps=np.linspace(.1,.2,len(model.rig.joints));adapter=BasisPoseRows(mapper,basis,caps)
    point=np.linspace(-.015,.02,basis.size)
    return model,mapper,basis,caps,adapter,point


@pytest.mark.parametrize('mode',['start','native','subkey','end'])
def test_complete_pose_rows_match_existing_independent_helper_and_full_chain(tmp_path,mode):
    model,mapper,basis,caps,adapter,point=setup(tmp_path,mode)
    result=adapter.evaluate(point);endpoints,endpoint_jac=basis.endpoint_map(point,mapper.bracket.tolist());full,local=mapper.evaluate(endpoints.ravel())
    original=PoseBoundsRows(model,mapper.time_s,mapper.controls(mapper.initial),list(model.nodes),caps)
    values,jac,world,points,_=original.evaluate(full);mapping=local@endpoint_jac
    assert result['margins'].tobytes()==values.tobytes() and result['world'].tobytes()==world.tobytes()
    np.testing.assert_allclose(result['jacobian'],jac@mapping,atol=2e-12,rtol=0)
    np.testing.assert_array_equal(result['full_controls'],full)
    assert result['jacobian'].shape==(len(model.nodes)+len(model.rig.joints),basis.size)
    assert result['world_jacobian'].shape==world.shape+(basis.size,) and not np.any(result['world_jacobian'][:,3,:,:])
    assert not result['quality_approved'] and not result['release_approved'] and result['original_selected']
    if mode in ['start','end']:assert not np.any(result['jacobian']) and not np.any(result['world_jacobian'])


def test_complete_world_and_pose_directions_include_last_basis_column(tmp_path):
    model,mapper,basis,caps,adapter,point=setup(tmp_path);actual=adapter.evaluate(point)
    directions=[np.eye(basis.size)[-1]]
    for seed in [17,43]:
        d=np.random.default_rng(seed).normal(size=basis.size);directions.append(d/np.linalg.norm(d))
    for d in directions:
        step=1e-5;a=adapter.evaluate(point+step*d,jacobian=False);b=adapter.evaluate(point-step*d,jacobian=False)
        np.testing.assert_allclose(actual['jacobian']@d,(a['margins']-b['margins'])/(2*step),atol=2e-6,rtol=2e-5)
        np.testing.assert_allclose(np.einsum('nijc,c->nij',actual['world_jacobian'],d),(a['world']-b['world'])/(2*step),atol=2e-7,rtol=2e-5)


@pytest.mark.parametrize('mode',['native','subkey','end'])
def test_value_only_encoded_pose_matches_actual_saved_gltf_without_derivatives(tmp_path,mode):
    model,mapper,basis,caps,adapter,point=setup(tmp_path,mode);path=tmp_path/'edited.glb'
    actor=model.actor;channels=[next(c for c in actor['sampler'].channels if c[:2]==(n,'rotation')) for n in model.nodes]
    coefficients=adapter.export_coefficients(point)
    assert coefficients[[0,-1]].tobytes()==mapper.seed[[0,-1]].tobytes()
    index=encode(actor['rig'],actor['animation_index'],list(model.nodes),channels,coefficients,np.degrees(model.caps),path)
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,index);actual=adapter.evaluate(point,jacobian=False,encoded=True)
    np.testing.assert_allclose(actual['world'],reader.sample(mapper.time_s),atol=2e-12,rtol=0)
    assert actual['jacobian'] is actual['world_jacobian'] is None and actual['encoded']
    with pytest.raises(ValueError):adapter.evaluate(point,encoded=True)


def test_every_native_key_and_node_is_retained_with_correct_raw_ball_gradients(tmp_path):
    model,mapper,basis,caps,adapter,point=setup(tmp_path);values=[];gradients=[]
    for start in range(0,len(mapper.clock),4):
        rows,jac=adapter.native_chunk(point,start,min(4,len(mapper.clock)-start));values.extend(rows);gradients.extend(jac)
    values=np.array(values);gradients=np.array(gradients);coefficients=basis.coefficients(point)
    assert values.tobytes()==(1-np.sum(coefficients*coefficients,axis=2)).ravel().tobytes()
    assert len(values)==len(mapper.clock)*len(mapper.nodes) and gradients.shape==(len(values),basis.size)
    direction=np.random.default_rng(17).normal(size=basis.size);direction/=np.linalg.norm(direction);step=1e-5
    a=(1-np.sum(basis.coefficients(point+step*direction)**2,axis=2)).ravel();b=(1-np.sum(basis.coefficients(point-step*direction)**2,axis=2)).ravel()
    np.testing.assert_allclose(gradients@direction,(a-b)/(2*step),atol=1e-9,rtol=0)
    assert not np.any(gradients.reshape(len(mapper.clock),len(mapper.nodes),-1)[[0,-1]])
    rows,jac=adapter.native_chunk(point,0,2,jacobian=False);assert jac is None


def test_owned_basis_and_all_returned_outputs_are_snapshots(tmp_path):
    model,mapper,basis,caps,adapter,point=setup(tmp_path);before=adapter.evaluate(point);saved={k:v.copy() for k,v in before.items() if isinstance(v,np.ndarray)}
    caps[:]=.5;basis._weights=np.zeros_like(basis.weights);basis._seed=np.zeros_like(mapper.seed)
    for v in before.values():
        if isinstance(v,np.ndarray):v[:]=123.
    adapter.report['basis']['frozen_keys'].clear()
    after=adapter.evaluate(point)
    for key,expected in saved.items():np.testing.assert_array_equal(after[key],expected)
    assert adapter.report['basis']['frozen_keys']==[0,len(mapper.clock)-1]


@pytest.mark.parametrize('fault',['missing_pair','pair_order','seed','clock','node_order','caps_nan','caps_shape','caps_bool','caps_small','caps_large','jacobian_budget','working_budget'])
def test_constructor_rejects_incomplete_source_domains_before_pose(tmp_path,monkeypatch,fault):
    model,mapper,basis,caps,adapter,point=setup(tmp_path);kwargs={}
    if fault=='missing_pair':mapper=KeyPoseMap(model,mapper.time_s,mapper.seed,list(mapper.pairs)[:-1])
    elif fault=='pair_order':mapper=KeyPoseMap(model,mapper.time_s,mapper.seed,list(reversed(mapper.pairs)))
    elif fault=='seed':basis=NativeKeyBasis(mapper.clock,list(model.nodes),mapper.seed*.9,[0,5,6,len(mapper.clock)-1],[0,len(mapper.clock)-1])
    elif fault=='clock':basis=NativeKeyBasis(mapper.clock*1.001,list(model.nodes),mapper.seed,[0,5,6,len(mapper.clock)-1],[0,len(mapper.clock)-1])
    elif fault=='node_order':basis=NativeKeyBasis(mapper.clock,list(reversed(model.nodes)),mapper.seed,[0,5,6,len(mapper.clock)-1],[0,len(mapper.clock)-1])
    elif fault=='caps_nan':caps[0]=np.nan
    elif fault=='caps_shape':caps=caps[:-1]
    elif fault=='caps_bool':caps=np.ones(len(caps),bool)
    elif fault=='caps_small':caps[0]=1e-7
    elif fault=='caps_large':caps[0]=1.1
    elif fault=='jacobian_budget':kwargs['maximum_jacobian_bytes']=1
    else:kwargs['maximum_working_bytes']=1
    monkeypatch.setattr(model,'_forward',lambda *a:pytest.fail('invalid input evaluated pose'))
    with pytest.raises(ValueError):BasisPoseRows(mapper,basis,caps,**kwargs)


@pytest.mark.parametrize('fault',['source_curve','seed','fixed_quaternions','parent','joint_order','pose_order','affected','rotation','scale','time','step','inverse'])
def test_changed_original_context_rejects_without_recentering(tmp_path,monkeypatch,fault):
    model,mapper,basis,caps,adapter,point=setup(tmp_path)
    if fault=='source_curve':
        channel=next(c for c in model.actor['sampler'].channels if c[:2]==(model.nodes[0],'rotation'));channel[3][0]*=-1
    elif fault=='seed':mapper.seed=mapper.seed*.9
    elif fault=='fixed_quaternions':mapper.fixed_quaternions=-mapper.fixed_quaternions
    elif fault=='parent':model.rig.parents=model.rig.parents.copy();model.rig.parents[-1]=0
    elif fault=='joint_order':model.rig.joints=list(reversed(model.rig.joints))
    elif fault=='pose_order':model.order=list(reversed(model.order))
    elif fault=='affected':model.affected=~model.affected
    elif fault=='rotation':model.rotations[0]=model.rotations[0]*.99
    elif fault=='scale':model.scales[0]=model.scales[0]*.99
    elif fault=='time':mapper.time_s+=1e-5
    elif fault=='step':mapper.step*=2
    else:mapper.original_inverse=mapper.original_inverse.inv()
    monkeypatch.setattr(model,'_forward',lambda *a:pytest.fail('changed source evaluated pose'))
    with pytest.raises(ValueError):adapter.evaluate(point)


def test_native_chunk_respects_stricter_adapter_budget_before_delegation(tmp_path,monkeypatch):
    model,mapper,basis,caps,adapter,point=setup(tmp_path)
    limit=max(adapter.report['world_jacobian_bytes'],adapter.report['pose_jacobian_bytes'],model.size*mapper.size*8,mapper.size*basis.size*8,len(model.source)*16*model.size*8,model.size*basis.size*8)
    adapter=BasisPoseRows(mapper,basis,caps,maximum_jacobian_bytes=limit)
    monkeypatch.setattr(adapter._basis,'native_chunk',lambda *a,**k:pytest.fail('over-budget native chunk allocated'))
    with pytest.raises(ValueError):adapter.native_chunk(point,0,min(64,len(mapper.clock)))


@pytest.mark.parametrize('kwargs',[dict(jacobian=1),dict(encoded=1),dict(encoded=True),dict(jacobian=False,encoded='yes')])
def test_invalid_modes_reject_without_inventing_encoded_derivatives(tmp_path,kwargs):
    *_,adapter,point=setup(tmp_path)
    with pytest.raises(ValueError):adapter.evaluate(point,**kwargs)


def test_failed_rotation_balls_are_reported_and_export_rejects_without_clipping(tmp_path):
    model,mapper,basis,caps,adapter,point=setup(tmp_path,'native');point=np.ones(basis.size)
    rows,_=adapter.native_chunk(point,5,1);assert np.any(rows<0)
    assert np.any(adapter.evaluate(point,jacobian=False)['margins'][:len(model.nodes)]<0)
    with pytest.raises(ValueError):adapter.export_coefficients(point)


@pytest.mark.parametrize('fault',['short','nan','infinite','bool','outside'])
def test_invalid_complete_basis_point_rejects_before_pose(tmp_path,monkeypatch,fault):
    model,mapper,basis,caps,adapter,point=setup(tmp_path)
    if fault=='short':point=point[:-1]
    elif fault=='nan':point[0]=np.nan
    elif fault=='infinite':point[0]=np.inf
    elif fault=='bool':point=point>0
    else:point[0]=1.01
    monkeypatch.setattr(model,'_forward',lambda *a:pytest.fail('invalid point evaluated pose'))
    with pytest.raises(ValueError):adapter.evaluate(point)
