"""Vector forms of native scene conditions for norm-preserving proposals.

Actual decoded SceneProblem constraints remain the acceptance authority.
"""
from dataclasses import dataclass
import numpy as np
from scipy import sparse
from scipy.spatial.transform import Rotation
from sampled_motion_caps import features, measures


@dataclass
class NormRows:
    vectors: np.ndarray
    caps: np.ndarray
    scales: np.ndarray

    def __post_init__(self):
        self.vectors = np.asarray(self.vectors, float)
        self.caps = np.asarray(self.caps, float)
        self.scales = np.asarray(self.scales, float)
        if (self.vectors.ndim != 2 or self.vectors.shape[1] != 3 or not len(self.vectors)
                or self.caps.shape != (len(self.vectors),) or self.scales.shape != self.caps.shape
                or any(not np.isfinite(a).all() for a in (self.vectors,self.caps,self.scales))
                or np.any(self.scales <= 0)):
            raise ValueError('Complete finite three-vector rows, caps and positive scales required')

    def residual(self, jacobian=None, delta=None):
        vectors = self.vectors
        if jacobian is not None:
            delta = np.asarray(delta,float)
            if sparse.issparse(jacobian):
                if (delta.ndim!=1 or jacobian.shape!=(vectors.size,len(delta))
                        or not np.isfinite(jacobian.data).all() or not np.isfinite(delta).all()):
                    raise ValueError('Matching finite sparse vector Jacobian and step required')
                vectors = vectors + np.asarray(jacobian@delta).reshape(vectors.shape)
            else:
                jacobian = np.asarray(jacobian,float)
                if (delta.ndim != 1 or jacobian.shape != (*vectors.shape,len(delta))
                        or not np.isfinite(jacobian).all() or not np.isfinite(delta).all()):
                    raise ValueError('Matching finite vector Jacobian and step required')
                vectors = vectors + np.einsum('rci,i->rc',jacobian,delta)
        elif delta is not None:
            raise ValueError('A vector step needs its Jacobian')
        return (np.linalg.norm(vectors,axis=1)-self.caps)/self.scales


def rate_vectors(payload, dt):
    # Reuse the existing validation, rotation convention and ambiguity guard.
    measures(payload,dt)
    p,r = payload['positions'],payload['rotations']
    relative = r[1:] @ r[:-1].transpose(0,1,3,2)
    angular = Rotation.from_matrix(relative.reshape(-1,3,3)).as_rotvec().reshape(len(p)-1,p.shape[1],3)/dt
    return [np.diff(p,axis=0)/dt, np.diff(p,n=2,axis=0)/dt**2,
        angular, np.diff(angular,axis=0)/dt]


def rows(problem, value, worlds=None):
    value = problem.edits.controls(value)
    worlds = problem.worlds(value) if worlds is None else worlds
    vectors,caps,scales = [],[],[]
    def add(vector,cap,scale):
        vector = np.asarray(vector,float).reshape(-1,3)
        vectors.append(vector)
        caps.append(np.broadcast_to(cap,(len(vector),)).copy())
        scales.append(np.broadcast_to(scale,(len(vector),)).copy())
    for name,actor_edit in problem.edits.actors.items():
        for entry in actor_edit['tracks']:
            add(entry['weights'] @ value[entry['controls']],1.,1.)
        joints = problem.scene.actors[name]['rig'].joints
        original = problem.source_world[name][problem.rate_ids]
        current = worlds[name][problem.rate_ids]
        # Match the established displacement row order, including its advanced
        # indexing order. Every joint and every uniform time is still present.
        add(current[:,joints,:3,3]-original[:,joints,:3,3],actor_edit['displacement'],actor_edit['displacement'])
        rate = problem.caps[name]
        for vector,cap in zip(rate_vectors(features(current,joints),rate.dt),rate.caps):
            add(vector, (cap+rate.tolerance).ravel(), np.maximum(cap,.001).ravel())
    for data in problem.rows:
        entry = data['entry']; row = entry['authored']; target = row['target']; ids = data['ids']
        effector = problem.skin_points(row['actor'],entry['ids'],worlds,ids,row['reduction'])
        if target['space']=='actor':
            goal = problem.skin_points(target['actor'],entry['target_ids'],worlds,ids,target['reduction'])
        elif target['space']=='world':
            goal = np.repeat(entry['target_ids'][None],len(ids),axis=0)
        else:
            p,r = data['object_pose']; goal = np.einsum('fij,vj->fvi',r,entry['target_ids'])+p[:,None]
        error = effector-goal
        if target['space']=='object':error = np.einsum('fvi,fij->fvj',error,r)
        limit = row['limits']['position_m']; add(error,limit,max(limit,.0001))
        for pop in data['populations']:
            clock = pop['times_s']
            if len(clock)<2:
                # An unavailable speed clock is an explicit fixed failed row.
                add(np.zeros((1,3)),-1.,1.); continue
            sample_ids = np.searchsorted(data['times'],clock)
            limit = row['limits']['relative_speed_m_s']
            add(np.diff(error[sample_ids],axis=0)*pop['rate_hz'],limit,max(limit,.001))
    return NormRows(np.concatenate(vectors),np.concatenate(caps),np.concatenate(scales))


def linearize(problem, value, *, step=1e-5, maximum_elements=60_000_000, difference_source='stored', base_worlds=None):
    value = problem.edits.controls(value); base = rows(problem,value)
    if difference_source not in ('stored','continuous'):raise ValueError('Choose stored or continuous vector differences')
    smooth = rows(problem,value,problem.worlds(value,quantized=False)) if difference_source=='continuous' else base
    if base_worlds is not None:
        anchored=rows(problem,value,base_worlds)
        if (anchored.vectors.shape!=base.vectors.shape or not np.array_equal(anchored.caps,base.caps)
                or not np.array_equal(anchored.scales,base.scales)):
            raise ValueError('Decoded vector anchoring changed original caps or population')
        base=anchored  # Differences still use their matching proxy origin.
    if (type(step) not in (int,float) or not np.isfinite(step) or step<=0
            or type(maximum_elements) is not int or maximum_elements<=0):
        raise ValueError('Positive difference step and vector Jacobian resource limit required')
    lower,upper = problem.lower,problem.upper
    if np.any(value<lower) or np.any(value>upper):raise ValueError('Vector difference point outside control boxes')
    data,indices,pointers = [],[],[0]; steps = []
    for column in range(len(value)):
        room = upper[column]-value[column] if upper[column]-value[column]>=value[column]-lower[column] else lower[column]-value[column]
        h = np.copysign(min(step,abs(room)),room)
        if h==0:raise ValueError('No vector finite-difference room')
        other = value.copy(); other[column]+=h
        sample = rows(problem,other,problem.worlds(other,quantized=False)) if difference_source=='continuous' else rows(problem,other)
        if (sample.vectors.shape != base.vectors.shape or not np.array_equal(sample.caps,base.caps)
                or not np.array_equal(sample.scales,base.scales)):
            raise ValueError('Vector constraint population changed during differences')
        derivative = ((sample.vectors-smooth.vectors)/h).ravel()
        if not np.isfinite(derivative).all():raise ValueError('Nonfinite native scene vector derivative')
        nonzero = np.flatnonzero(derivative)
        if pointers[-1]+len(nonzero)>maximum_elements:
            raise ValueError('Native scene sparse vector Jacobian exceeds the declared nonzero resource limit')
        # Exact zeros only: no small derivative, row or actor is discarded.
        indices.append(nonzero); data.append(derivative[nonzero]); pointers.append(pointers[-1]+len(nonzero)); steps.append(float(h))
    jacobian = sparse.csc_matrix((np.concatenate(data),np.concatenate(indices),pointers),shape=(base.vectors.size,len(value)))
    return base,jacobian,dict(difference_step_control_fraction=step,actual_steps=steps,
        norm_rows=len(base.vectors),maximum_nonzero_jacobian_elements=maximum_elements,
        dense_jacobian_elements=base.vectors.size*len(value),stored_nonzero_jacobian_elements=jacobian.nnz,
        jacobian_storage='sparse CSC; exact nonzero entries only',
        quantized_native_keys=True,difference_source=difference_source,decoded_base_anchor=base_worlds is not None,
        conservative_dense_dependencies=True)
