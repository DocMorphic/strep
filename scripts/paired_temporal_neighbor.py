"""Small source-relative temporal trial; preserve authored contact keys exactly."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import read_glb,accessor,append_accessor,write_glb

BODY=['Spine1','Spine2','Chest','Neck1','Neck2','Head','LeftShoulder','LeftArm','LeftForeArm','LeftHand']


def placed_joint_positions(world,joints,rotation,translation):
    """Keep time first when selecting a skin's joint list from node transforms."""
    world=np.asarray(world)
    if world.ndim!=4 or world.shape[-2:]!=(4,4):raise ValueError('Time by node world matrices required')
    return world[:,joints][:,:,:3,3]@np.asarray(rotation).T+np.asarray(translation)


def bounded_neighbor(previous,current,next_,weight,limit_radians):
    if not np.isfinite([weight,limit_radians]).all() or not 0<=weight<=1 or limit_radians<=0:raise ValueError('Bounded finite smoothing settings required')
    center=Rotation.from_matrix(current)
    step=((center.inv()*Rotation.from_matrix(previous)).as_rotvec()+(center.inv()*Rotation.from_matrix(next_)).as_rotvec())*.5*weight
    norm=np.linalg.norm(step,axis=-1,keepdims=True);step*=np.minimum(1,limit_radians/np.maximum(norm,1e-15))
    return (center*Rotation.from_rotvec(step)).as_matrix()


def rotation_channels(document,binary):
    if len(document['animations'])!=1:raise ValueError('One animation required')
    result={};animation=document['animations'][0]
    for channel in animation['channels']:
        if channel['target']['path']!='rotation':continue
        node=channel['target']['node'];sampler=animation['samplers'][channel['sampler']]
        if sampler.get('interpolation','LINEAR')!='LINEAR' or node in result:raise ValueError('Distinct linear rotation channels required')
        result[node]=(channel['sampler'],accessor(document,binary,sampler['input']),accessor(document,binary,sampler['output']))
    return result


def smooth_export(source,target,include_fingers,first=70,event=75,last=80,strength=.25,limit_degrees=5.):
    doc,binary=read_glb(source);output=copy.deepcopy(doc);payload=bytearray(binary);channels=rotation_channels(doc,binary)
    if not 0<first<event<last<149:raise ValueError('Interior single-event window required')
    names={node['name']:i for i,node in enumerate(doc['nodes']) if 'name' in node}
    fingers=sorted(n for n in names if n.startswith('LeftHand') and n[-1:].isdigit())
    selected=BODY+(fingers if include_fingers else [])
    if len(fingers)!=19 or any(name not in names for name in selected):raise ValueError('Declared SOMA arm/finger layout required')
    frames=[f for f in range(first+1,last) if f!=event];changes=[]
    for name in selected:
        node=names[name];sampler,times,quaternions=channels[node]
        np.testing.assert_array_equal(times,np.arange(150,dtype=np.float32)/30)
        local=Rotation.from_quat(quaternions).as_matrix();edited=quaternions.copy()
        for frame in frames:
            t=(frame-first)/(last-first);weight=strength*16*t*t*(1-t)*(1-t)
            matrix=bounded_neighbor(local[frame-1],local[frame],local[frame+1],weight,np.deg2rad(limit_degrees))
            q=Rotation.from_matrix(matrix).as_quat()
            if q@quaternions[frame]<0:q=-q
            edited[frame]=q
        actual=Rotation.from_quat(edited);delta=(Rotation.from_quat(quaternions).inv()*actual).magnitude()
        if np.rad2deg(delta.max())>limit_degrees+1e-5:raise ValueError('Serialized local edit exceeds declared budget')
        frozen=np.setdiff1d(np.arange(150),frames);np.testing.assert_array_equal(edited[frozen],quaternions[frozen])
        output['animations'][0]['samplers'][sampler]['output']=append_accessor(output,payload,edited,'VEC4')
        changes.append(dict(joint=name,maximum_edit_degrees=float(np.rad2deg(delta.max()))))
    write_glb(target,output,payload)
    return dict(frames=frames,selected_joints=selected,changes=changes,locked_keys=150-len(frames))
