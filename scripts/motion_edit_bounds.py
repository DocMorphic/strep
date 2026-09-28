"""Explicit edit budgets in local SO(3) and native root coordinates.

These constrain corrections relative to an input clip, not anatomy or raw
movement. Sparse-anchor checks are necessary feasibility tests only.
"""
import numpy as np
from scipy.spatial.transform import Rotation


class EditBoundsError(ValueError):
    def __init__(self,report):
        self.report=report
        super().__init__('Motion correction exceeds declared edit budgets: '+', '.join(v['kind'] for v in report['violations']))


def _rotations(value,label):
    value=np.asarray(value,dtype=float)
    if value.ndim!=4 or value.shape[-2:]!=(3,3) or not np.isfinite(value).all():raise ValueError(label+' must be finite frames by joints by3 by3')
    if np.max(np.abs(value.swapaxes(-1,-2)@value-np.eye(3)),initial=0)>1e-5 or np.max(np.abs(np.linalg.det(value)-1),initial=0)>1e-5:raise ValueError(label+' must contain proper rotations')
    return value


def _angles(matrices):
    return np.degrees(Rotation.from_matrix(matrices.reshape(-1,3,3)).magnitude()).reshape(matrices.shape[:-2])


def check(original_local,candidate_local,original_root,candidate_root,times,joint_names,limits):
    """Report every violating joint/category; never silently clamp a result."""
    a=_rotations(original_local,'Original rotations');b=_rotations(candidate_local,'Candidate rotations')
    if a.shape!=b.shape or a.shape[0]<1 or a.shape[1]<1:raise ValueError('Matching nonempty rotation arrays required')
    count,joints=a.shape[:2];times=np.asarray(times,dtype=float);root=np.asarray(original_root,dtype=float);other=np.asarray(candidate_root,dtype=float)
    if times.shape!=(count,) or not np.isfinite(times).all() or np.any(np.diff(times)<=0):raise ValueError('Use finite strictly increasing timestamps')
    if root.shape!=(count,3) or other.shape!=root.shape or not np.isfinite(root).all() or not np.isfinite(other).all():raise ValueError('Matching finite roots required')
    if len(joint_names)!=joints or any(not isinstance(n,str) or not n for n in joint_names) or len(set(joint_names))!=joints:raise ValueError('Distinct joint names required')
    required={'joint_rotation_degrees','joint_correction_speed_degrees_s','root_components_m','root_correction_speed_m_s'}
    if not isinstance(limits,dict) or set(limits)!=required:raise ValueError('Provide every explicit edit budget')
    def joint_budget(key,maximum=None):
        values=limits[key]
        if not isinstance(values,dict) or set(values)!=set(joint_names):raise ValueError('Every joint requires an explicit '+key)
        if any(type(values[n]) not in (int,float) for n in joint_names):raise ValueError('Budgets must be numeric')
        result=np.array([values[n] for n in joint_names],dtype=float)
        if not np.isfinite(result).all() or np.any(result<0) or (maximum is not None and np.any(result>maximum)):raise ValueError('Invalid joint budget')
        return result
    angle_limit=joint_budget('joint_rotation_degrees',180);speed_limit=joint_budget('joint_correction_speed_degrees_s')
    root_limit=np.asarray(limits['root_components_m'],dtype=float);root_speed=limits['root_correction_speed_m_s']
    if root_limit.shape!=(3,) or not np.isfinite(root_limit).all() or np.any(root_limit<0) or type(root_speed) not in (int,float) or not np.isfinite(root_speed) or root_speed<0:raise ValueError('Invalid root budgets')
    correction=a.swapaxes(-1,-2)@b;angles=_angles(correction);delta=other-root;dt=np.diff(times)
    speeds=_angles(correction[:-1].swapaxes(-1,-2)@correction[1:])/dt[:,None] if count>1 else np.empty((0,joints))
    root_speeds=np.linalg.norm(np.diff(delta,axis=0),axis=1)/dt if count>1 else np.empty(0)
    violations=[];joint_results=[]
    # Only numerical tolerances are added, never tolerance proportional to budget.
    for j,name in enumerate(joint_names):
        peak=int(angles[:,j].argmax());value=float(angles[peak,j]);speed=float(speeds[:,j].max(initial=0))
        joint_results.append(dict(joint=name,max_edit_degrees=value,peak_time_s=float(times[peak]),max_correction_speed_degrees_s=speed))
        ids=np.flatnonzero(angles[:,j]>angle_limit[j]+1e-4)
        if len(ids):violations.append(dict(kind='joint_rotation',joint=name,limit=float(angle_limit[j]),peak=value,times_s=times[ids].tolist()))
        ids=np.flatnonzero(speeds[:,j]>speed_limit[j]+1e-3)
        if len(ids):violations.append(dict(kind='joint_correction_speed',joint=name,limit=float(speed_limit[j]),peak=speed,intervals_s=[[float(times[i]),float(times[i+1])] for i in ids]))
    for axis in range(3):
        ids=np.flatnonzero(np.abs(delta[:,axis])>root_limit[axis]+1e-6)
        if len(ids):violations.append(dict(kind='root_component',axis=axis,limit=float(root_limit[axis]),peak=float(np.abs(delta[:,axis]).max()),times_s=times[ids].tolist()))
    ids=np.flatnonzero(root_speeds>root_speed+1e-5)
    if len(ids):violations.append(dict(kind='root_correction_speed',limit=float(root_speed),peak=float(root_speeds.max()),intervals_s=[[float(times[i]),float(times[i+1])] for i in ids]))
    return dict(passed=not violations,violations=violations,joints=joint_results,root_component_max_m=np.abs(delta).max(0).tolist(),
        root_correction_speed_max_m_s=float(root_speeds.max(initial=0)),samples=count,quality_approved=False,
        scope='Local geodesic edit and correction-speed budgets; native root-axis and correction-speed budgets. Input motion speed is not constrained. No anatomy, surface, semantic or continuous-time certificate.')


def enforce(*args,**kwargs):
    report=check(*args,**kwargs)
    if not report['passed']:raise EditBoundsError(report)
    return report
