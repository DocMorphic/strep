"""Wide fixed poses, bounded derivative columns and original-source rows."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_partitioned_affine_pose import PartitionedAffineKeyPose
from native_affine_region_pose import RegionPoseRows
from native_key_pose_map import KeyPoseMap
from native_key_contact_initializer import encode
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from rig_asset import RigAsset,array
from gltf_tools import append_accessor,write_glb
from test_native_partitioned_affine_pose import large_actor


def wide_actor(tmp_path):
    actor,nodes=large_actor(tmp_path);rig=actor['rig'];doc=copy.deepcopy(rig.document);buf=bytearray(rig.binary)
    first=len(doc['nodes']);extra=list(range(first,first+64-len(nodes)));parent=nodes[-1]
    for n in extra:
        doc['nodes'][parent].setdefault('children',[]).append(n)
        doc['nodes'].append(dict(name='wide-chain-'+str(n),translation=[.01,0,0],rotation=[0,0,0,1]));parent=n
    doc['skins'][0]['joints'].extend(extra)
    inverse=np.concatenate([rig.inverse,np.repeat(np.eye(4)[None],len(extra),axis=0)])
    doc['skins'][0]['inverseBindMatrices']=append_accessor(doc,buf,inverse.transpose(0,2,1).reshape(-1,16),'MAT4')
    primitive=doc['meshes'][doc['nodes'][rig.primitives[0]['node']]['mesh']]['primitives'][0]
    joints=array(rig.document,rig.binary,primitive['attributes']['JOINTS_0']).astype('<u2');joints[0,0]=len(doc['skins'][0]['joints'])-1
    while len(buf)%4:buf.append(0)
    offset=len(buf);buf.extend(joints.tobytes());view=len(doc['bufferViews']);doc['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=joints.nbytes));accessor=len(doc['accessors']);doc['accessors'].append(dict(bufferView=view,componentType=5123,count=len(joints),type='VEC4'));primitive['attributes']['JOINTS_0']=accessor
    clock=next(c[2] for c in actor['sampler'].channels if c[:2]==(nodes[0],'rotation'));stamps=append_accessor(doc,buf,clock,'SCALAR');animation=doc['animations'][actor['animation_index']]
    for n in extra:
        values=append_accessor(doc,buf,np.repeat([[0,0,0,1]],len(clock),axis=0),'VEC4');index=len(animation['samplers']);animation['samplers'].append(dict(input=stamps,output=values,interpolation='LINEAR'));animation['channels'].append(dict(sampler=index,target=dict(node=n,path='rotation')))
    path=tmp_path/'wide-source.glb';write_glb(path,doc,buf);fresh=RigAsset.load(path)
    result=dict(rig=fresh,skin=NativeSupportSkin(fresh),animation_index=actor['animation_index'],sampler=NativeSupportSampler(fresh.document,fresh.binary,actor['animation_index']),placement=actor['placement'])
    return result,nodes+extra,clock


@pytest.mark.parametrize('columns_kind',['empty','nonprefix','reversed'])
def test_selected_columns_retain_full_wide_pose_and_match_full_and_differences(tmp_path,columns_kind):
    actor,nodes,clock=wide_actor(tmp_path);model=PartitionedAffineKeyPose(actor,float(clock[5]),nodes,[20.]*len(nodes));assert len(nodes)==64
    value=np.linspace(-.07,.09,model.size);columns=[] if columns_kind=='empty' else [model.size-1,0,61]
    if columns_kind=='reversed':columns.reverse()
    whole=model.evaluate(value);part=model.evaluate_columns(value,columns)
    np.testing.assert_array_equal(part[0],whole[0]);np.testing.assert_array_equal(part[1],whole[1])
    np.testing.assert_allclose(part[2],whole[2][:,:,columns],atol=2e-13,rtol=0)
    np.testing.assert_allclose(part[3],whole[3][:,:,columns],atol=2e-13,rtol=0)
    world,jac=model.transforms(value,columns=columns);np.testing.assert_array_equal(world,whole[0]);np.testing.assert_array_equal(jac,part[3])
    for i,column in enumerate(columns):
        delta=np.zeros(model.size);delta[column]=1e-6
        fd=(model.evaluate_columns(value+delta,[])[1]-model.evaluate_columns(value-delta,[])[1])/2e-6
        np.testing.assert_allclose(part[2][:,:,i],fd,atol=2e-8,rtol=3e-6)


def test_transform_only_path_does_not_skin_and_partial_budget_rejects_full_request(tmp_path,monkeypatch):
    actor,nodes,clock=wide_actor(tmp_path);model=PartitionedAffineKeyPose(actor,float(clock[5]),nodes,[20.]*len(nodes),maximum_derivative_controls=6)
    value=np.linspace(-.03,.03,model.size);expected=model.evaluate_columns(value,[0,1,2])[0]
    monkeypatch.setattr(model,'skin',object())
    world,jac=model.transforms(value,columns=[]);np.testing.assert_array_equal(world,expected);assert jac.shape==(len(model.rig.joints),3,0)
    with pytest.raises(ValueError,match='budget'):model.evaluate(value)
    assert model.construction['complete_controls']==192 and model.construction['maximum_derivative_controls']==6


def test_native_float32_export_keeps_all_controls_with_only_selected_derivatives(tmp_path):
    actor,nodes,clock=wide_actor(tmp_path);stamp=float(clock[5]);model=PartitionedAffineKeyPose(actor,stamp,nodes,[20.]*len(nodes),maximum_derivative_controls=3)
    value=np.linspace(-.03,.04,model.size);world,points,*_=model.evaluate_columns(value,[0,1,2]);controls=np.zeros((len(clock),len(nodes),3));controls[5]=value.reshape(-1,3)
    channels=[next(c for c in actor['sampler'].channels if c[:2]==(n,'rotation')) for n in nodes];path=tmp_path/'candidate.glb';index=encode(actor['rig'],actor['animation_index'],nodes,channels,controls,[20.]*len(nodes),path)
    rig=RigAsset.load(path);reader=NativeSupportSampler(rig.document,rig.binary,index)
    np.testing.assert_allclose(world,reader.sample(stamp),atol=2e-6,rtol=0);np.testing.assert_allclose(points,rig.vertices(reader.sample(stamp)),atol=2e-6,rtol=0)
    assert rig.binary[:len(actor['rig'].binary)]==actor['rig'].binary and rig.document['animations'][:-1]==actor['rig'].document['animations']


def test_partial_region_map_preserves_fixed_pose_rows_and_all_native_balls(tmp_path):
    actor,nodes,clock=wide_actor(tmp_path);stamp=float((clock[5]+clock[6])/2);active=[nodes[-1],nodes[0],nodes[20]]
    model=PartitionedAffineKeyPose(actor,stamp,nodes,[20.]*len(nodes),maximum_derivative_controls=9)
    seed=np.repeat(np.linspace(-.02,.02,model.size).reshape(1,len(nodes),3),len(clock),axis=0)
    pairs=[(6,nodes[0]),(5,nodes[-1]),(6,nodes[20]),(1,nodes[4])];mapper=KeyPoseMap(model,stamp,seed,pairs);value=mapper.initial.copy();full=mapper.controls(value)
    region=[dict(vertices=[0,1,2],normal_world=[0.,1.,0.],offset_m=0.,sign=1,minimum_gap_m=.001)]
    problem=RegionPoseRows(model,stamp,full,active,np.full(len(model.rig.joints),.1),region)
    rows,jac,world,vertices,effective=mapper.region_rows(problem,value)
    np.testing.assert_array_equal(effective,full);assert len(rows)==64+len(model.rig.joints)+3+len(pairs)
    fixed=set(range(len(nodes)))-{nodes.index(n) for n in active};assert all(rows[i]==pytest.approx(1-np.sum(full[3*i:3*i+3]**2)) for i in fixed)
    for column in range(mapper.size):
        delta=np.eye(mapper.size)[column]*2e-6;fd=(mapper.region_rows(problem,value+delta)[0]-mapper.region_rows(problem,value-delta)[0])/4e-6;np.testing.assert_allclose(jac[:,column],fd,atol=4e-6,rtol=4e-6)
    wrong=full.copy();wrong[3*nodes.index(nodes[4])]+=.01
    mismatch=RegionPoseRows(model,stamp,wrong,active,np.full(len(model.rig.joints),.1),region)
    with pytest.raises(ValueError,match='Fixed pose controls'):mapper.region_rows(mismatch,value)
    missing=RegionPoseRows(model,stamp,full,active[:-1],np.full(len(model.rig.joints),.1),region)
    with pytest.raises(ValueError,match='pose-dependent'):mapper.region_rows(missing,value)
    value[-3:]=[1.01,0,0];assert mapper.region_rows(problem,value)[0][-1]<0


@pytest.mark.parametrize('columns',[None,True,np.array(1),[True],[0,0],[-1],[192],[1.],[[0]],np.array([2**64-1],dtype=np.uint64),list(range(7))])
def test_invalid_or_over_budget_columns_reject(tmp_path,columns):
    actor,nodes,clock=wide_actor(tmp_path);model=PartitionedAffineKeyPose(actor,float(clock[5]),nodes,[20.]*len(nodes),maximum_derivative_controls=6)
    with pytest.raises(ValueError):model.evaluate_columns(np.zeros(model.size),columns)


@pytest.mark.parametrize('limit',[0,True,1.,193])
def test_invalid_derivative_budget_rejects_before_constructor_parts(tmp_path,monkeypatch,limit):
    actor,nodes,clock=wide_actor(tmp_path)
    import native_partitioned_affine_pose as module
    monkeypatch.setattr(module,'AffineKeyPose',lambda *a,**k:pytest.fail('Invalid derivative budget constructed a block'))
    with pytest.raises(ValueError):module.PartitionedAffineKeyPose(actor,float(clock[5]),nodes,[20.]*len(nodes),maximum_derivative_controls=limit)


def test_changed_derivative_budget_cannot_relinearize_region_or_map(tmp_path):
    actor,nodes,clock=wide_actor(tmp_path);stamp=float(clock[5]);model=PartitionedAffineKeyPose(actor,stamp,nodes,[20.]*len(nodes),maximum_derivative_controls=3)
    seed=np.zeros((len(clock),len(nodes),3));mapper=KeyPoseMap(model,stamp,seed,[(5,nodes[0])]);full=mapper.controls(mapper.initial)
    region=RegionPoseRows(model,stamp,full,[nodes[0]],np.full(len(model.rig.joints),.1),[dict(vertices=[0],normal_world=[0.,1.,0.],offset_m=0.,sign=1,minimum_gap_m=0.)])
    model.maximum_derivative_controls=6
    with pytest.raises(ValueError):mapper.evaluate(mapper.initial)
    with pytest.raises(ValueError):region.evaluate(np.zeros(3))
