"""Append explicit native-key edits while preserving untouched Float32 values."""
import copy
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import accessor,append_accessor


def append_track_deltas(document,binary,animation_index,frame_times,edits):
    """Return a diagnostic export and strict per-track stored-bound results.

    Rotation deltas are right-multiplied rotvecs in radians. Translation
    deltas are in source units. Source quaternion lengths are preserved before
    Float32 storage; zero deltas and protected keys remain byte-exact. Stored
    rounding failures are reported, never clipped or accepted with an epsilon.
    Caller-owned asset/permission binding and full saved-motion checks remain
    separate obligations.
    """
    times=np.asarray(frame_times)
    if (type(animation_index) is not int or not 0<=animation_index<len(document.get('animations',[]))
            or times.ndim!=1 or not 2<=len(times)<=300 or times.dtype.kind not in 'fiu'
            or not np.isfinite(times).all() or np.any(np.diff(times.astype(float))<=0)
            or not isinstance(edits,(list,tuple)) or not 1<=len(edits)<=256
            or not isinstance(binary,(bytes,bytearray)) or len(binary)>64*1024**2):
        raise ValueError('Explicit animation, complete bounded original clock and edits required')
    animation=document['animations'][animation_index];plans=[];seen=set()
    for edit in edits:
        if not isinstance(edit,dict) or set(edit)!={'node','path','delta','protected','maximum_norm'}:raise ValueError('Complete explicit track edit required')
        node,path=edit['node'],edit['path'];key=(node,path);delta=np.asarray(edit['delta']);protected=np.asarray(edit['protected']);limit=edit['maximum_norm']
        if (type(node) is not int or not 0<=node<len(document.get('nodes',[])) or path not in ('rotation','translation') or key in seen
                or delta.shape!=(len(times),3) or delta.dtype.kind not in 'fiu' or not np.isfinite(delta).all()
                or protected.dtype!=np.bool_ or protected.shape!=(len(times),)
                or type(limit) not in (int,float) or not np.isfinite(limit) or not 0<limit<= (np.pi if path=='rotation' else 1e6)):
            raise ValueError('Distinct complete finite three-vector edits, Boolean permissions and positive limits required')
        delta=np.array(delta,dtype=float,copy=True);intended=np.linalg.norm(delta,axis=1)
        if np.any(intended>limit) or np.any(delta[protected]!=0):raise ValueError('Original per-key author bound or protected key exceeded; no clipping')
        matches=[(i,c) for i,c in enumerate(animation['channels']) if (c['target']['node'],c['target']['path'])==key]
        if len(matches)!=1:raise ValueError('Exactly one matching original native channel required')
        index,channel=matches[0];sampler=animation['samplers'][channel['sampler']]
        if sampler.get('interpolation','LINEAR')!='LINEAR' or not np.array_equal(accessor(document,binary,sampler['input']),times):raise ValueError('Unchanged complete original LINEAR channel clock required')
        before=accessor(document,binary,sampler['output']);width=4 if path=='rotation' else 3
        if before.shape!=(len(times),width) or before.dtype!=np.dtype('<f4') or not np.isfinite(before).all():raise ValueError('Complete finite original Float32 channel values required')
        if path=='rotation' and np.any(abs(np.linalg.norm(before.astype(float),axis=1)-1)>4*np.finfo(np.float32).eps):raise ValueError('Near-unit original stored quaternions required')
        after=before.copy();changed=np.any(delta!=0,axis=1)
        if np.any(changed):
            if path=='rotation':
                a=before[changed].astype(float);b=Rotation.from_rotvec(delta[changed]).as_quat()
                edited=np.c_[a[:,3,None]*b[:,:3]+b[:,3,None]*a[:,:3]+np.cross(a[:,:3],b[:,:3]),a[:,3]*b[:,3]-np.sum(a[:,:3]*b[:,:3],axis=1)]
            else:edited=before[changed].astype(float)+delta[changed]
            after[changed]=edited.astype(np.float32)
        if path=='rotation':stored=(Rotation.from_quat(before).inv()*Rotation.from_quat(after)).magnitude()
        else:stored=np.linalg.norm(after.astype(float)-before.astype(float),axis=1)
        assert before[~changed].tobytes()==after[~changed].tobytes() and before[protected].tobytes()==after[protected].tobytes()
        plans.append((index,sampler,path,after,dict(node=node,path=path,changed_keys=int(changed.sum()),protected_keys=int(protected.sum()),maximum_intended_norm=float(intended.max()),maximum_stored_norm=float(stored.max()),maximum_norm=float(limit),stored_bound_pass=bool(np.all(stored<=limit)))))
        seen.add(key)
    output=copy.deepcopy(document);payload=bytearray(binary);target=output['animations'][animation_index]
    for index,sampler,path,after,report in plans:
        if not report['changed_keys']:continue
        appended=copy.deepcopy(sampler);appended['output']=append_accessor(output,payload,after,'VEC4' if path=='rotation' else 'VEC3')
        target['channels'][index]['sampler']=len(target['samplers']);target['samplers'].append(appended)
    reports=[p[-1] for p in plans]
    return output,payload,dict(schema='strep-stored-track-deltas-v1',tracks=reports,all_stored_track_bounds_pass=all(r['stored_bound_pass'] for r in reports),original_buffer_prefix_preserved=bytes(payload[:len(binary)])==bytes(binary),zero_delta_and_protected_keys_exact=True,original_samplers_unchanged=True,physical_tolerance_added=0.,quality_approved=False,release_approved=False)
