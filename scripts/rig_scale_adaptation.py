"""Explicit static-rig derivative with rigid nodes and preserved reference skin.

This changes the rig representation, not merely its scale metadata. It does not
preserve existing animation, infer joint limits or certify future motion quality.
"""
import argparse,copy,hashlib,json,struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from rig_asset import RigAsset,read_asset,array,index,parents_of
from gltf_tools import local_matrix,global_matrices,append_accessor
from strep import save,sha256

MAX_BYTES=32*1024**2


def reference_vertices(document,binary,reference,inverse,validated):
    """Original geometry from original matrices; shared validated influences."""
    result=[];skin=reference[validated.joints]@inverse
    for primitive in validated.primitives:
        node=primitive['node'];number=primitive['primitive']
        attributes=document['meshes'][document['nodes'][node]['mesh']]['primitives'][number]['attributes']
        positions=array(document,binary,attributes['POSITION'])
        points=np.column_stack([positions,np.ones(len(positions))])
        if primitive['joints'] is None:
            posed=(reference[node]@points.T).T[:,:3]
        else:
            posed=np.zeros((len(points),3))
            for influence in range(primitive['joints'].shape[1]):
                matrices=skin[primitive['joints'][:,influence]]
                transformed=(matrices@points[:,:,None])[:,:,0][:,:3]
                posed+=transformed*primitive['weights'][:,influence,None]
        result.append(posed)
    return np.concatenate(result)


def normalize(document,binary,*,maximum_reference_error_m=1e-5):
    if (type(maximum_reference_error_m) not in (int,float) or not np.isfinite(maximum_reference_error_m)
            or maximum_reference_error_m<=0):raise ValueError('Positive reference preservation limit required')
    if document.get('animations'):raise ValueError('Scale adaptation requires a static rig; existing animation is not converted')
    if len(document.get('skins',[]))!=1:raise ValueError('Exactly one skin required')
    nodes=document.get('nodes',[])
    if not 1<=len(nodes)<=512:raise ValueError('Adaptation supports 1-512 nodes')
    parents=parents_of(document)
    for node in nodes:
        if 'matrix' in node and any(k in node for k in ('translation','rotation','scale')):
            raise ValueError('Node combines matrix and TRS')
        for name,size in (('translation',3),('rotation',4),('scale',3)):
            if name in node:
                values=np.asarray(node[name])
                if values.shape!=(size,) or values.dtype.kind not in 'fiu' or not np.isfinite(values).all():
                    raise ValueError('Finite numeric node TRS required')
        if 'rotation' in node and abs(np.linalg.norm(node['rotation'])-1)>1e-5:
            raise ValueError('Normalized source quaternion required')
        if 'scale' in node and np.any(np.asarray(node['scale'])<=0):
            raise ValueError('Positive source scales required; reflection unsupported')
        matrix=local_matrix(node)
        if matrix.shape!=(4,4) or not np.isfinite(matrix).all() or not np.allclose(matrix[3],[0,0,0,1],atol=1e-7,rtol=0):
            raise ValueError('Finite affine source transforms required')
        linear=matrix[:3,:3];length=np.linalg.norm(linear,axis=0)
        if np.any(length<=0) or np.linalg.det(linear)<=0:
            raise ValueError('Singular or reflected source transform unsupported')
        normalized=linear/length
        if not np.allclose(normalized.T@normalized,np.eye(3),atol=1e-5,rtol=0):
            raise ValueError('Local matrix shear unsupported')
    primitives=[];population=0
    for number,node in enumerate(nodes):
        if 'mesh' not in node:continue
        mesh=index(document.get('meshes',[]),node['mesh'],'mesh')
        if node.get('weights') or mesh.get('weights'):raise ValueError('Morph weights unsupported')
        for primitive in mesh['primitives']:
            if primitive.get('targets'):raise ValueError('Morph targets unsupported')
            count=index(document['accessors'],primitive['attributes']['POSITION'],'position accessor')['count']
            if type(count) is not int or count<=0:raise ValueError('Positive vertex population required')
            population+=count;primitives.append((number,primitive))
    if population>250000 or len(primitives)>64:raise ValueError('Adaptation vertex/primitive budget exceeded')
    source_reference=global_matrices(document)
    rigid=np.repeat(np.eye(4)[None],len(nodes),axis=0)
    for number,matrix in enumerate(source_reference):
        linear=matrix[:3,:3]
        if not np.isfinite(matrix).all() or np.linalg.cond(linear)>1e8:
            raise ValueError('Non-finite or ill-conditioned world transform')
        u,_,vt=np.linalg.svd(linear);rotation=u@vt
        if np.linalg.det(rotation)<=0:raise ValueError('Reflected world basis unsupported')
        rigid[number,:3,:3]=rotation;rigid[number,:3,3]=matrix[:3,3]
    output=copy.deepcopy(document);data=bytearray(binary)
    for number,node in enumerate(output['nodes']):
        local=rigid[number] if parents[number]<0 else np.linalg.inv(rigid[parents[number]])@rigid[number]
        for name in ('translation','rotation','scale','matrix'):node.pop(name,None)
        node['translation']=local[:3,3].tolist();node['rotation']=Rotation.from_matrix(local[:3,:3]).as_quat().tolist()
    skin=document['skins'][0];joints=skin.get('joints',[])
    if not 1<=len(joints)<=256 or len(set(joints))!=len(joints):raise ValueError('Unique bounded source skin joints required')
    for joint in joints:index(nodes,joint,'skin joint')
    inverse=(array(document,binary,skin['inverseBindMatrices']) if 'inverseBindMatrices' in skin
        else np.repeat(np.eye(4)[None],len(joints),axis=0))
    if (inverse.shape!=(len(joints),4,4) or not np.isfinite(inverse).all()
            or not np.allclose(inverse[:,3],[0,0,0,1],atol=1e-5,rtol=0)
            or np.any(abs(np.linalg.det(inverse))<1e-10)):raise ValueError('Finite nonsingular affine inverse binds required')
    adapted=np.linalg.inv(rigid[joints])@source_reference[joints]@inverse
    output['skins'][0]['inverseBindMatrices']=append_accessor(output,data,adapted.transpose(0,2,1).reshape(len(joints),16),'MAT4')
    # Each unskinned instance gets its own baked derivative mesh. Original mesh
    # records and binary ranges remain untouched, including shared instances.
    for number,node in enumerate(nodes):
        if 'mesh' not in node or 'skin' in node:continue
        mesh=copy.deepcopy(document['meshes'][node['mesh']]);delta=np.linalg.inv(rigid[number])@source_reference[number]
        for primitive in mesh['primitives']:
            attributes=primitive['attributes'];positions=array(document,binary,attributes['POSITION'])
            if positions.ndim!=2 or positions.shape[1]!=3:raise ValueError('Float VEC3 positions required')
            points=(delta@np.column_stack([positions,np.ones(len(positions))]).T).T[:,:3]
            attributes['POSITION']=append_accessor(output,data,points,'VEC3')
            for attribute,kind in (('NORMAL','VEC3'),('TANGENT','VEC4')):
                if attribute not in attributes:continue
                values=array(document,binary,attributes[attribute])
                width=3 if attribute=='NORMAL' else 4
                if values.shape!=(len(positions),width):raise ValueError('Invalid static surface basis')
                transform=np.linalg.inv(delta[:3,:3]).T if attribute=='NORMAL' else delta[:3,:3]
                direction=values[:,:3]@transform.T;length=np.linalg.norm(direction,axis=1)
                if not np.isfinite(direction).all() or np.any(length<=0):raise ValueError('Invalid transformed surface basis')
                direction/=length[:,None]
                if attribute=='TANGENT':direction=np.column_stack([direction,values[:,3]])
                attributes[attribute]=append_accessor(output,data,direction,kind)
        output['nodes'][number]['mesh']=len(output['meshes']);output['meshes'].append(mesh)
    output['buffers'][0]['byteLength']=len(data)
    rig=RigAsset(output,bytes(data))
    source_vertices=reference_vertices(document,binary,source_reference,inverse,rig)
    target_vertices=rig.vertices(rig.reference)
    error=float(np.max(np.linalg.norm(target_vertices-source_vertices,axis=1)))
    if error>maximum_reference_error_m:raise ValueError(f'Reference shape error {error} exceeds {maximum_reference_error_m} m')
    assert bytes(data[:len(binary)])==binary
    return output,bytes(data),dict(schema='strep-static-rig-scale-adaptation-v1',vertices=len(source_vertices),
        maximum_reference_vertex_error_m=error,maximum_reference_error_m=maximum_reference_error_m,
        maximum_joint_origin_error_m=float(np.max(np.linalg.norm(rig.reference[joints,:3,3]-source_reference[joints,:3,3],axis=1))),
        original_binary_prefix_preserved=True,original_mesh_records_preserved=True,
        source_node_hierarchy_preserved=True,reference_shape_verified=True,
        existing_animation_preserved=False,source_deformation_model_preserved=False,
        future_motion_quality_verified=False,engine_verified=False,quality_approved=False,release_approved=False)


def adapt_file(source,folder,*,maximum_reference_error_m=1e-5):
    source=Path(source);folder=Path(folder)
    with source.open('rb') as stream:raw=stream.read(MAX_BYTES+1)
    if not raw or len(raw)>MAX_BYTES:raise ValueError('Choose a self-contained static rig GLB up to 32 MiB')
    folder.mkdir(parents=True,exist_ok=False)
    original=folder/'source.glb';original.write_bytes(raw)
    try:
        document,binary=read_asset(original)
        output,data,result=normalize(document,binary,maximum_reference_error_m=maximum_reference_error_m)
        # Preserve buffer metadata; the legacy writer replaces the buffer record.
        encoded=json.dumps(output,separators=(',',':'),allow_nan=False).encode();encoded+=b' '*(-len(encoded)%4)
        padded=data+b'\0'*(-len(data)%4)
        packed=struct.pack('<III',0x46546c67,2,28+len(encoded)+len(padded))
        packed+=struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(padded),0x004e4942)+padded
        path=folder/'character.glb';path.write_bytes(packed);rig=RigAsset.load(path)
        assert rig.document==output and rig.binary==data
        result.update(status='complete',source_sha256=hashlib.sha256(raw).hexdigest(),character_sha256=sha256(path),method_sha256=sha256(__file__))
        save(folder/'result.json',result);return result
    except Exception as error:
        save(folder/'result.json',dict(status='failed',source_sha256=hashlib.sha256(raw).hexdigest(),
            error_type=type(error).__name__,error=str(error),quality_approved=False,release_approved=False))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(adapt_file(args.source,args.output)))
