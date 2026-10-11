"""Rig-space reference pose from motion directions and explicit rotation caps.

Reference points supply soft directional preferences, not copied absolute joint
coordinates. Rigid target branches share one fitted orientation, preserving
target proportions/helper locals. This constructs a pose proposal; contacts,
surfaces, temporal motion and animation quality require separate checks.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from bounded_pose_ik import hierarchy_order,world_matrices
from retarget_rig import swing


def branch_rotation(current,desired):
    """Unit-direction least squares, with minimum swing for rank-one branches."""
    current=np.asarray(current,float);desired=np.asarray(desired,float)
    if current.shape!=desired.shape or current.ndim!=2 or current.shape[1]!=3 or not len(current):raise ValueError('Matching branch vectors required')
    if not np.isfinite(current).all() or not np.isfinite(desired).all():raise ValueError('Finite branch vectors required')
    cn=np.linalg.norm(current,axis=1);dn=np.linalg.norm(desired,axis=1)
    if np.any(cn<1e-7) or np.any(dn<1e-7):raise ValueError('Nondegenerate branch vectors required')
    a=current/cn[:,None];b=desired/dn[:,None]
    u,s,vt=np.linalg.svd(b.T@a);rank=int(np.sum(s>1e-10))
    if rank==0:return np.eye(3),rank
    if rank==1:return swing(vt[0],u[:,0]),rank
    return u@np.diag([1,1,np.linalg.det(u@vt)])@vt,rank


def propose(local,parents,mapping,reference_points,edit_limits_degrees):
    local=np.asarray(local,float);parents=np.asarray(parents);order=hierarchy_order(parents)
    if not 1<=len(parents)<=512 or local.shape!=(len(parents),4,4) or not np.isfinite(local).all():raise ValueError('Bounded complete local pose required')
    if not np.allclose(local[:,3],[0,0,0,1],atol=1e-12,rtol=0):raise ValueError('Affine local pose required')
    r=local[:,:3,:3]
    if np.max(abs(r.swapaxes(-1,-2)@r-np.eye(3)))>1e-10 or np.max(abs(np.linalg.det(r)-1))>1e-10:raise ValueError('Proper rigid local pose required')
    if (not isinstance(mapping,dict) or not 2<=len(mapping)<=128
            or any(type(role) is not str or not 1<=len(role)<=64 or type(n) is not int or not 0<=n<len(parents) for role,n in mapping.items())
            or len(set(mapping.values()))!=len(mapping)):raise ValueError('Distinct explicit role/node mapping required')
    if not isinstance(reference_points,dict) or set(reference_points)!=set(mapping):raise ValueError('One reference point per mapped role required')
    points={}
    for role,value in reference_points.items():
        raw=np.asarray(value)
        if raw.shape!=(3,) or raw.dtype.kind not in 'fiu' or not np.isfinite(raw).all():raise ValueError('Finite numeric reference points required')
        points[role]=raw.astype(float)
    if (not isinstance(edit_limits_degrees,dict) or not edit_limits_degrees
            or any(type(n) is not int or n not in mapping.values() for n in edit_limits_degrees)
            or any(type(v) not in (int,float) or not np.isfinite(v) or not 0<v<=90 for v in edit_limits_degrees.values())):
        raise ValueError('Explicit mapped rotation caps up to 90 degrees required')
    inverse={n:role for role,n in mapping.items()};children={n:[] for n in inverse};edges=[]
    for node,role in inverse.items():
        p=int(parents[node])
        while p>=0 and p not in inverse:p=int(parents[p])
        if p>=0:
            children[p].append(node);edges.append((p,node))
            if np.linalg.norm(points[role]-points[inverse[p]])<1e-7:raise ValueError('Nondegenerate source role edges required')
    before=world_matrices(local,parents,order);changed=local.copy();world=np.empty_like(local);trace=[]
    for node in order:
        p=int(parents[node]);parent=np.eye(4) if p<0 else world[p]
        original=parent@local[node]
        if node in edit_limits_degrees:
            selected=children[node]
            if selected:
                relative=[before[node,:3,:3].T@(before[c,:3,3]-before[node,:3,3]) for c in selected]
                current=np.array([original[:3,:3]@v for v in relative])
                desired=np.array([points[inverse[c]]-points[inverse[node]] for c in selected])
                delta,rank=branch_rotation(current,desired);desired_world=delta@original[:3,:3]
            else:desired_world=before[node,:3,:3];rank=None
            desired_local=parent[:3,:3].T@desired_world
            vector=Rotation.from_matrix(local[node,:3,:3].T@desired_local).as_rotvec()
            angle=float(np.linalg.norm(vector));cap=np.deg2rad(edit_limits_degrees[node])
            if angle>cap:vector*=cap/angle
            changed[node,:3,:3]=local[node,:3,:3]@Rotation.from_rotvec(vector).as_matrix()
            trace.append(dict(node=node,role=inverse[node],branch_children=[inverse[c] for c in selected],branch_rank=rank,
                requested_local_change_degrees=float(np.rad2deg(angle)),applied_local_change_degrees=float(np.rad2deg(np.linalg.norm(vector))),
                cap_degrees=float(edit_limits_degrees[node]),clamped=bool(angle>cap)))
        world[node]=parent@changed[node]
    metrics=[]
    for a,b in edges:
        wanted=points[inverse[b]]-points[inverse[a]];wanted/=np.linalg.norm(wanted)
        vectors=[w[b,:3,3]-w[a,:3,3] for w in (before,world)]
        lengths=[float(np.linalg.norm(v)) for v in vectors]
        if min(lengths)<1e-7:raise ValueError('Nondegenerate target role edges required')
        angles=[float(np.rad2deg(np.arccos(np.clip(v@wanted/length,-1,1)))) for v,length in zip(vectors,lengths)]
        metrics.append(dict(parent=inverse[a],child=inverse[b],original_length_m=lengths[0],proposed_length_m=lengths[1],
            before_direction_error_degrees=angles[0],after_direction_error_degrees=angles[1]))
    unchanged=[n for n in range(len(parents)) if n not in edit_limits_degrees]
    if not np.array_equal(changed[:,:3,3],local[:,:3,3]) or not np.array_equal(changed[unchanged],local[unchanged]):raise ValueError('Protected target locals changed')
    if any(t['applied_local_change_degrees']>t['cap_degrees']+1e-9 for t in trace):raise ValueError('Source-relative rotation cap exceeded')
    length_error=max((abs(e['original_length_m']-e['proposed_length_m']) for e in metrics),default=0.)
    if length_error>1e-8:raise ValueError('Target role edge length changed')
    return changed,world,dict(schema='strep-rig-pose-scaffold-v1',status='proposed',edits=trace,edges=metrics,
        mapped_positions_m={role:world[n,:3,3].tolist() for role,n in mapping.items()},
        maximum_role_edge_length_change_m=length_error,local_translations_unchanged=True,unmapped_locals_unchanged=True,
        contact_verified=False,temporal_verified=False,quality_approved=False,release_approved=False,
        scope='Target-proportion pose proposal from soft observed edge directions; shared rigid branches fitted jointly, source-relative local rotation caps enforced. Leaf world orientation favored within caps. Original root/local translations and helper locals retained. Adapted joint points are constructed FK targets, not matching original captured absolute coordinates or proven supports/surfaces/timing/physics.')
