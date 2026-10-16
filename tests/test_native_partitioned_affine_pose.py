"""Cross-partition native affine derivatives retain full hierarchy and skin."""
import copy,sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import native_partitioned_affine_pose as wider
from native_affine_key_pose import AffineKeyPose
from test_native_affine_key_pose import affine_setup
from native_scene_contacts import SceneContacts
from rig_asset import array
from gltf_tools import append_accessor,write_glb
from strep import read,sha256


def large_actor(tmp_path):
    source,scene,cp,*_=affine_setup(tmp_path);rig=scene.actors['A']['rig'];doc=copy.deepcopy(rig.document);buf=bytearray(rig.binary)
    first=len(doc['nodes']);new_nodes=list(range(first,first+18));parent=3
    for n in new_nodes:
        doc['nodes'][parent].setdefault('children',[]).append(n)
        doc['nodes'].append(dict(name='test-chain-'+str(n),translation=[.01,0,0],rotation=[0,0,0,1]));parent=n
    doc['skins'][0]['joints'].extend(new_nodes)
    inverse=np.concatenate([rig.inverse,np.repeat(np.eye(4)[None],18,axis=0)])
    doc['skins'][0]['inverseBindMatrices']=append_accessor(doc,buf,inverse.transpose(0,2,1).reshape(-1,16),'MAT4')
    def integer_accessor(values):
        values=np.asarray(values,dtype='<u2')
        while len(buf)%4:buf.append(0)
        offset=len(buf);buf.extend(values.tobytes());view=len(doc['bufferViews'])
        doc['bufferViews'].append(dict(buffer=0,byteOffset=offset,byteLength=values.nbytes))
        result=len(doc['accessors']);doc['accessors'].append(dict(bufferView=view,componentType=5123,count=len(values),type='VEC4'));return result
    primitive=doc['meshes'][doc['nodes'][rig.primitives[0]['node']]['mesh']]['primitives'][0];attrs=primitive['attributes']
    for group in range(2):
        if 'JOINTS_'+str(group) not in attrs:continue
        js=array(rig.document,rig.binary,attrs['JOINTS_'+str(group)]).copy();ws=array(rig.document,rig.binary,attrs['WEIGHTS_'+str(group)]).copy()
        js[0]=0;ws[0]=0
        if group==0:js[0,0]=len(doc['skins'][0]['joints'])-1;ws[0,0]=1
        attrs['JOINTS_'+str(group)]=integer_accessor(js);attrs['WEIGHTS_'+str(group)]=append_accessor(doc,buf,ws,'VEC4')
    clock=next(c[2] for c in scene.actors['A']['sampler'].channels if c[:2]==(3,'rotation'))
    stamps=append_accessor(doc,buf,clock,'SCALAR');animation=doc['animations'][0]
    for n in new_nodes:
        values=append_accessor(doc,buf,np.repeat([[0,0,0,1]],len(clock),axis=0),'VEC4');index=len(animation['samplers'])
        animation['samplers'].append(dict(input=stamps,output=values,interpolation='LINEAR'));animation['channels'].append(dict(sampler=index,target=dict(node=n,path='rotation')))
    write_glb(source,doc,buf);spec=read(cp)
    for value in spec['actors'].values():value['sha256']=sha256(source)
    return SceneContacts(spec,tmp_path).actors['A'],[3,*new_nodes]


@pytest.mark.parametrize('width',[1,4,16])
def test_construction_partition_does_not_change_qualified_evaluation(tmp_path,width):
    actor,nodes=large_actor(tmp_path);nodes=nodes[:12];caps=[15.]*len(nodes)
    a=AffineKeyPose(actor,1.,nodes,caps);b=wider.PartitionedAffineKeyPose(actor,1.,nodes,caps,constructor_block_nodes=width)
    assert type(b).evaluate is AffineKeyPose.evaluate
    x=np.linspace(-.2,.2,b.size)
    for expected,actual in zip(a.evaluate(x),b.evaluate(x)):np.testing.assert_array_equal(actual,expected)
    np.testing.assert_array_equal(b.evaluate(np.zeros(b.size))[0],b.source)


def test_more_than_sixteen_controls_keep_cross_partition_ancestry_and_weighted_leaf(tmp_path):
    actor,nodes=large_actor(tmp_path);caps=[20.]*len(nodes)
    with pytest.raises(ValueError):AffineKeyPose(actor,1.,nodes,caps)
    model=wider.PartitionedAffineKeyPose(actor,1.,nodes,caps);assert len(nodes)==19 and model.size==57
    x=np.linspace(-.1,.15,model.size);world,vertices,jac,jj=model.evaluate(x);h=1e-6
    for column in (0,44,45,46,54,56):
        delta=np.eye(model.size)[column]*h;plus=model.evaluate(x+delta);minus=model.evaluate(x-delta)
        np.testing.assert_allclose(jac[:,:,column],(plus[1]-minus[1])/(2*h),atol=3e-9,rtol=3e-7)
        np.testing.assert_allclose(jj[:,:,column],(plus[0][actor['rig'].joints,:3,3]-minus[0][actor['rig'].joints,:3,3])/(2*h),atol=3e-9,rtol=3e-7)
    assert model.construction['complete_controls']==57 and len(model.construction['constructor_blocks'])==2
    assert np.linalg.norm(jac[0,:,54:])>0


@pytest.mark.parametrize('fault',['duplicate','missing-cap','bool-cap','over-cap','invalid-node','block-zero','block-large','nan-time','time-range','derivative-budget','workspace-budget'])
def test_invalid_unbounded_or_partial_inputs_reject_before_evaluation(tmp_path,monkeypatch,fault):
    actor,nodes=large_actor(tmp_path);caps=[20.]*len(nodes);kwargs={};stamp=1.
    if fault=='duplicate':nodes[-1]=nodes[0]
    elif fault=='missing-cap':caps.pop()
    elif fault=='bool-cap':caps[0]=True
    elif fault=='over-cap':caps[0]=31.
    elif fault=='invalid-node':nodes[-1]=99999
    elif fault=='block-zero':kwargs['constructor_block_nodes']=0
    elif fault=='block-large':kwargs['constructor_block_nodes']=17
    elif fault=='nan-time':stamp=float('nan')
    elif fault=='time-range':stamp=actor['sampler'].duration+1
    elif fault=='derivative-budget':monkeypatch.setattr(wider,'MAX_DERIVATIVE_BYTES',1)
    else:monkeypatch.setattr(wider,'MAX_ESTIMATED_WORKSPACE_BYTES',1)
    with pytest.raises(ValueError):wider.PartitionedAffineKeyPose(actor,stamp,nodes,caps,**kwargs)
