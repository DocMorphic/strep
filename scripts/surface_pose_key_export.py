"""Export explicit native pose-key edits while preserving a finalized prefix.

Each export rebases buffers on the immutable source, preserving current values
outside the supplied keys. Identity of unchanged LINEAR keys is not a motion
quality or continuous collision certificate.
"""
import copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import append_accessor,write_glb
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from surface_pose_model import SurfacePoseModel
from strep import sha256


def replace_keys(source,current,*,root,rotations,edits,preserve_through,output,animation_index=0):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    if (type(animation_index) is not int or animation_index<0 or not isinstance(edits,dict) or not edits
            or any(type(f) is not int for f in edits) or type(preserve_through) is not int):
        raise ValueError('Explicit selected animation, native key edits and prefix index required')
    if current.binary[:len(source.binary)]!=source.binary:
        raise ValueError('Current asset must preserve the original binary prefix')
    for table in ('accessors','bufferViews'):
        original=source.document.get(table,[])
        if current.document.get(table,[])[:len(original)]!=original:
            raise ValueError('Original accessor and buffer-view definitions must remain unchanged')
    before=NativeSupportSampler(source.document,source.binary,animation_index)
    previous=NativeSupportSampler(current.document,current.binary,animation_index)
    allowed={'buffers','bufferViews','accessors','animations','extras'}
    if {k:v for k,v in source.document.items() if k not in allowed}!={k:v for k,v in current.document.items() if k not in allowed}:
        raise ValueError('Original asset geometry, scene and node definitions must remain unchanged')
    if len(source.document['animations'])!=len(current.document['animations']) or any(a!=b for i,(a,b) in enumerate(zip(source.document['animations'],current.document['animations'])) if i!=animation_index):
        raise ValueError('Unselected animations must remain unchanged')
    clock=before.channels[0][2];frames=sorted(edits);width=3+3*len(rotations)
    if (not -1<=preserve_through<len(clock) or frames[0]<=preserve_through or frames[0]<0 or frames[-1]>=len(clock)
            or any(np.asarray(edits[f]).shape!=(width,) or not np.isfinite(edits[f]).all() for f in frames)):
        raise ValueError('Complete finite edits strictly after the preserved native prefix required')
    if len(before.channels)!=len(previous.channels):raise ValueError('Unchanged channel population required')
    editable={(n,'rotation') for n in rotations}|{(root,'translation')};seen=set()
    for a,b in zip(before.channels,previous.channels):
        if a[:2]!=b[:2] or a[4]!='LINEAR' or b[4]!='LINEAR' or a[2].tobytes()!=b[2].tobytes() or not np.array_equal(a[2],clock):
            raise ValueError('Matching shared native clocks and LINEAR channel layouts required')
        if a[:2] not in editable and not np.array_equal(a[3],b[3]):raise ValueError('Unexpected edit outside declared pose channels')
        if a[:2] in editable:
            if a[:2] in seen:raise ValueError('Distinct editable channels required')
            seen.add(a[:2])
    if seen!=editable:raise ValueError('Every declared rotation and root translation needs an existing channel')
    models=[]
    for frame in frames:
        model=SurfacePoseModel(source,before.sample(float(clock[frame])),root,rotations)
        if models:model.skin=models[0].skin
        models.append(model)
    poses=[m.evaluate(np.asarray(edits[f],float),derivatives=False) for m,f in zip(models,frames)]
    document=copy.deepcopy(source.document);binary=bytearray(source.binary);animation=document['animations'][animation_index]
    for channel,old in zip(animation['channels'],previous.channels):
        node,path=old[:2]
        if (node,path) not in editable:continue
        sampler=copy.deepcopy(animation['samplers'][channel['sampler']]);values=old[3].copy()
        if path=='rotation':values[frames]=Rotation.from_matrix(np.array([p[1][node,:3,:3] for p in poses])).as_quat();kind='VEC4'
        else:values[frames]=np.array([p[1][node,:3,3] for p in poses]);kind='VEC3'
        sampler['output']=append_accessor(document,binary,values,kind);channel['sampler']=len(animation['samplers']);animation['samplers'].append(sampler)
    document.setdefault('extras',{})['strep_pose_key_edit']=dict(edited_keys=frames,preserved_through=preserve_through,quality_approved=False)
    write_glb(output,document,binary);decoded=RigAsset.load(output);after=NativeSupportSampler(decoded.document,decoded.binary,animation_index)
    outside=[f for f in range(len(clock)) if f not in edits]
    for a,b in zip(previous.channels,after.channels):
        if a[:2]!=b[:2] or a[2].tobytes()!=b[2].tobytes() or not np.array_equal(a[3][outside],b[3][outside]):
            raise AssertionError('Serialized export changed an unselected key or native clock')
    error=max(float(np.linalg.norm(decoded.vertices(after.sample(float(clock[f])))-pose[2],axis=1).max()) for f,pose in zip(frames,poses))
    if error>1e-5:raise AssertionError('Serialized pose differs from its declared key edit')
    return dict(edited_keys=frames,preserved_through=preserve_through,unchanged_key_values_verified=True,
                roundtrip_max_vertex_error_m=error,sha256=sha256(output),quality_approved=False,release_approved=False)
