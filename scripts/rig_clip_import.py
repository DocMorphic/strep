"""Preserve and sample existing rig animations for editable offline cleanup.

Interpolation follows Khronos glTF 2.0 Appendix C. Output is a documented
30fps sampled approximation; original STEP/cubic timing remains in source GLB.
"""
import copy
import math
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from rig_asset import RigAsset,array,index
from gltf_tools import authored_animation,global_matrices,append_accessor,write_glb,sample_animation
from strep import read,save,sha256,now


class AnimationSampler:
    def __init__(self,document,binary,animation_index):
        self.document=document;self.channels=[];self.duration=0.;self.scale_key_drift=0.
        animation=index(document.get('animations',[]),animation_index,'animation');seen=set()
        self.name=animation.get('name','Animation '+str(animation_index+1))
        for channel in animation.get('channels',[]):
            target=channel['target'];node=target.get('node');path=target.get('path')
            entry=index(document['nodes'],node,'animated node')
            if path not in ('translation','rotation','scale') or 'matrix' in entry or (node,path) in seen:
                raise ValueError('Animation requires distinct TRS channels on TRS nodes; morph/extension channels unsupported')
            seen.add((node,path));sampler=index(animation['samplers'],channel['sampler'],'animation sampler')
            times=array(document,binary,sampler['input']);values=array(document,binary,sampler['output']);mode=sampler.get('interpolation','LINEAR')
            input_accessor=document['accessors'][sampler['input']]
            if times.ndim!=1 or input_accessor['componentType']!=5126 or input_accessor.get('normalized') or times[0]<0 or np.any(np.diff(times)<=0):
                raise ValueError('Animation times must be increasing nonnegative float scalars')
            output_accessor=document['accessors'][sampler['output']]
            if path!='rotation' and (output_accessor['componentType']!=5126 or output_accessor.get('normalized')):
                raise ValueError('Translation and scale animation outputs must be float vectors')
            if mode not in ('LINEAR','STEP','CUBICSPLINE'):raise ValueError('Unsupported animation interpolation')
            width=4 if path=='rotation' else 3;count=len(times)*(3 if mode=='CUBICSPLINE' else 1)
            if values.shape!=(count,width) or mode=='CUBICSPLINE' and len(times)<2:raise ValueError('Animation key/tangent dimensions do not match')
            values=values.astype(float);keys=values[1::3] if mode=='CUBICSPLINE' else values
            if path=='rotation' and np.max(np.abs(np.linalg.norm(keys,axis=1)-1))>1e-5:raise ValueError('Animation rotation keys must be unit quaternions')
            if path=='scale':
                drift=float(np.max(np.abs(keys-1)));self.scale_key_drift=max(self.scale_key_drift,drift)
                if drift>1e-5 or mode=='CUBICSPLINE' and np.max(np.abs(values.reshape(-1,3,3)[:,[0,2]]))>1e-5:
                    raise ValueError('Animated non-unit scale is unsupported by rig contact editing')
            self.channels.append((node,path,times,values,mode));self.duration=max(self.duration,float(times[-1]))
        if not self.channels or not 0<self.duration<=30:raise ValueError('Choose an animated clip with duration greater than zero and at most 30 seconds')

    @staticmethod
    def value(path,times,values,mode,time):
        cubic=mode=='CUBICSPLINE';keys=values[1::3] if cubic else values
        if time<=times[0]:result=keys[0].copy()
        elif time>=times[-1]:result=keys[-1].copy()
        else:
            k=int(np.searchsorted(times,time,side='right')-1);dt=float(times[k+1]-times[k]);t=(time-float(times[k]))/dt
            if mode=='STEP':result=keys[k].copy()
            elif cubic:
                result=(2*t**3-3*t*t+1)*keys[k]+dt*(t**3-2*t*t+t)*values[3*k+2]+(-2*t**3+3*t*t)*keys[k+1]+dt*(t**3-t*t)*values[3*(k+1)]
            elif path=='rotation':
                a,b=keys[k]/np.linalg.norm(keys[k]),keys[k+1]/np.linalg.norm(keys[k+1]);dot=float(a@b)
                if dot<0:b=-b;dot=-dot
                angle=np.arccos(np.clip(dot,0,1))
                result=(1-t)*a+t*b if angle<1e-6 else (np.sin((1-t)*angle)*a+np.sin(t*angle)*b)/np.sin(angle)
            else:result=(1-t)*keys[k]+t*keys[k+1]
        if path=='rotation':
            norm=np.linalg.norm(result)
            if norm<1e-8:raise ValueError('Spline produced an invalid zero quaternion')
            result=result/norm
        return result

    def sample(self,time):
        nodes=copy.deepcopy(self.document['nodes'])
        for node,path,times,values,mode in self.channels:nodes[node][path]=self.value(path,times,values,mode,time).tolist()
        return global_matrices({**self.document,'nodes':nodes})


def catalog(path):
    rig=RigAsset.load(path);clips=[]
    for number,animation in enumerate(rig.document.get('animations',[])):
        item=dict(index=number,name=animation.get('name','Animation '+str(number+1)))
        try:
            sampler=AnimationSampler(rig.document,rig.binary,number)
            item.update(supported=True,duration_s=sampler.duration,channels=len(sampler.channels))
        except (ValueError,KeyError,IndexError,TypeError) as error:item.update(supported=False,reason=str(error))
        clips.append(item)
    return clips


def export(character,profile_path,animation_index,output):
    from retarget_rig import resolve_profile
    character,profile_path,output=map(lambda p:Path(p).resolve(),(character,profile_path,output))
    rig=RigAsset.load(character);profile=read(profile_path)
    if profile['character_sha256']!=sha256(character):raise ValueError('Clip mapping belongs to another asset')
    mapping,_=resolve_profile(rig,profile);sampler=AnimationSampler(rig.document,rig.binary,animation_index)
    # Tiny float32 key-time drift should not add a whole output frame.
    frames=int(math.ceil(sampler.duration*30-1e-5))+1;times=np.arange(frames,dtype=np.float32)/30
    world=np.array([sampler.sample(min(float(t),sampler.duration)) for t in times])
    local=world.copy()
    for node,parent in enumerate(rig.parents):
        if parent>=0:local[:,node]=np.linalg.inv(world[:,parent])@world[:,node]
    document,binary=copy.deepcopy(rig.document),bytearray(rig.binary);animation=authored_animation(sampler.name)
    time_accessor=append_accessor(document,binary,times,'SCALAR')
    for node in sorted({c[0] for c in sampler.channels}):
        quaternions=Rotation.from_matrix(local[:,node,:3,:3]).as_quat()
        for f in range(1,frames):
            if quaternions[f]@quaternions[f-1]<0:quaternions[f]*=-1
        for path,values,kind in [('translation',local[:,node,:3,3],'VEC3'),('rotation',quaternions,'VEC4')]:
            acc=append_accessor(document,binary,values,kind);animation['channels'].append(dict(sampler=len(animation['samplers']),target=dict(node=node,path=path)))
            animation['samplers'].append(dict(input=time_accessor,output=acc,interpolation='LINEAR'))
    document['animations']=[animation];document.setdefault('extras',{})['strep_imported_animation']=dict(source_sha256=sha256(character),animation_index=animation_index,fps=30,source_duration_s=sampler.duration)
    output.mkdir(parents=True,exist_ok=False);write_glb(output/'character.glb',document,binary)
    decoded=RigAsset.load(output/'character.glb');matrix_error=vertex_error=0.;floor=[]
    for f,expected in enumerate(world):
        actual=sample_animation(decoded.document,decoded.binary,0,f)
        matrix_error=max(matrix_error,float(np.abs(actual-expected).max()))
        vertices=decoded.vertices(actual);vertex_error=max(vertex_error,float(np.linalg.norm(vertices-rig.vertices(expected),axis=1).max()));floor.append(max(0.,-float(vertices[:,1].min())))
    if max(matrix_error,vertex_error)>1e-5:raise ValueError('Imported clip changed sampled transforms or skin')
    root=mapping['Hips'];save(output/'root-motion.json',dict(space='Original mapped pelvis world transform, Y-up metres; no retargeting, placement edit or root extraction',node=root,times_s=times.tolist(),positions_m=world[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(world[:,root,:3,:3]).as_quat().tolist()))
    save(output/'contacts.json',dict(provenance='No source contact annotations supplied; no generated model predictions',mapping={},intervals=[]))
    save(output/'inventory.json',rig.inventory());shutil.copyfile(profile_path,output/'rig-profile.json')
    np.savez_compressed(output/'target-transforms.npz',global_matrices=world,times_s=times)
    report=dict(created_at=now(),source_kind='gltf_animation',source=str(character),source_sha256=sha256(character),character=str(character),character_sha256=sha256(character),profile_sha256=sha256(profile_path),
        animation_index=animation_index,animation_name=sampler.name,source_duration_s=sampler.duration,frames=frames,fps=30,last_key_time_s=float(times[-1]),duration_extension_s=float(times[-1])-sampler.duration,source_scale_key_drift=sampler.scale_key_drift,
        mapping=mapping,root_node=root,glb_sha256=sha256(output/'character.glb'),target_mesh_floor_depth_max_m=max(floor),target_mesh_floor_frames_above_1cm=sum(d>.01 for d in floor),
        roundtrip_max_matrix_error=matrix_error,roundtrip_max_vertex_error_m=vertex_error,implementation_sha256=sha256(__file__),human_approved=False,
        note='Existing clip sampled at 30fps from t=0; out-of-range samplers clamp. Original source timing/interpolation preserved separately. Between-frame STEP/cubic behavior is approximated by linear output samples. Nominal unit-scale float drift up to 1e-5 is accepted, with all-frame matrix/skin error checked against 1e-5. Mapping identifies the root and edit roles only; profile reference-axis and placement corrections are not applied. No contacts, generated motion or semantic improvement inferred.')
    save(output/'report.json',report);return report
