"""Differentiate native LINEAR quaternion interpolation between edited poses.

Edited local bases must be rigid rotations. The root-parent basis and source
root translation interpolation are checked at each declared sample. Ambiguous
half-turn quaternion branches are rejected. No continuous-motion guarantee.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from surface_pose_model import right_jacobian, skew
from native_support_clock import NativeSupportSampler


def tangent(quaternion):
    vector, scalar = quaternion[:3], quaternion[3]
    return np.vstack([scalar*np.eye(3)+skew(vector), -vector])


def rotation_parameters(left, right, baseline, left_edit, right_edit, fraction, *, derivatives=True):
    """Return a sampled right-local edit and its 3-by-6 endpoint derivative."""
    a = (Rotation.from_matrix(left)*Rotation.from_rotvec(left_edit)).as_quat()
    b = (Rotation.from_matrix(right)*Rotation.from_rotvec(right_edit)).as_quat()
    dot = float(a@b)
    if abs(dot) < 1e-8:
        raise ValueError('Ambiguous half-turn interpolation requires an explicit branch')
    sign = -1. if dot < 0 else 1.
    b *= sign
    dot = float(np.clip(a@b, 0., 1.))
    angle = float(np.arccos(dot))
    if derivatives:
        da = np.zeros((4, 6)); db = np.zeros((4, 6))
        da[:, :3] = .5*tangent(a)@right_jacobian(left_edit)
        db[:, 3:] = .5*tangent(b)@right_jacobian(right_edit)
    if angle < 1e-6:
        q = (1-fraction)*a+fraction*b
        if derivatives: dq = (1-fraction)*da+fraction*db
    else:
        sine = np.sin(angle)
        wa = np.sin((1-fraction)*angle)/sine
        wb = np.sin(fraction*angle)/sine
        q = wa*a+wb*b
        if derivatives:
            wa_prime = ((1-fraction)*np.cos((1-fraction)*angle)*sine-np.sin((1-fraction)*angle)*np.cos(angle))/sine**2
            wb_prime = (fraction*np.cos(fraction*angle)*sine-np.sin(fraction*angle)*np.cos(angle))/sine**2
            angle_gradient = -(b@da+a@db)/sine
            dq = wa*da+wb*db+np.outer(wa_prime*a+wb_prime*b, angle_gradient)
    norm = float(np.linalg.norm(q)); q /= norm
    relative = Rotation.from_matrix(baseline).inv()*Rotation.from_quat(q)
    value = relative.as_rotvec()
    if np.linalg.norm(value) > np.pi-1e-6:
        raise ValueError('Sampled correction reaches the principal-log branch boundary')
    jac = None
    if derivatives:
        dq = (np.eye(4)-np.outer(q,q))@dq/norm
        jac = np.linalg.solve(right_jacobian(value), 2*tangent(q).T@dq)
    return value, jac


class InterpolatedPoseMap:
    def __init__(self, left, right, sampled, fraction):
        self.left, self.right, self.sampled = left, right, sampled
        if (type(fraction) not in (int,float) or not np.isfinite(fraction) or not 0 <= fraction <= 1
                or any(m.rig is not left.rig or m.root != left.root or m.rotations != left.rotations
                       or m.parents != left.parents for m in (right,sampled))):
            raise ValueError('Compatible same-rig pose layouts and an explicit fraction required')
        self.fraction = float(fraction); self.width = left.size
        root = left.root
        if (not np.allclose(left.root_translation_map,right.root_translation_map,atol=1e-12,rtol=0)
                or not np.allclose(left.root_translation_map,sampled.root_translation_map,atol=1e-12,rtol=0)
                or not np.allclose(sampled.local[root,:3,3],(1-fraction)*left.local[root,:3,3]+fraction*right.local[root,:3,3],atol=1e-10,rtol=0)):
            raise ValueError('Fixed root-parent basis and LINEAR source root translation required')
        for node in left.rotations:
            bases = [m.local[node,:3,:3] for m in (left,right,sampled)]
            if any(not np.allclose(b.T@b,np.eye(3),atol=1e-10,rtol=0) or abs(np.linalg.det(b)-1)>1e-10 for b in bases):
                raise ValueError('Edited local rotation bases must be rigid; affine drift is unsupported here')
            q = NativeSupportSampler.value('rotation',np.array([0.,1.]),Rotation.from_matrix(np.array(bases[:2])).as_quat(),'LINEAR',float(fraction))
            if not np.allclose(Rotation.from_quat(q).as_matrix(),bases[2],atol=1e-10,rtol=0):
                raise ValueError('Sampled source rotation must match native LINEAR interpolation')

    def parameters(self, values, *, derivatives=True):
        values = np.asarray(values,float)
        if values.shape != (2*self.width,) or not np.isfinite(values).all():
            raise ValueError('Complete finite endpoint edit parameters required')
        a,b = values.reshape(2,self.width); t = self.fraction
        result = np.empty(self.width); result[:3] = (1-t)*a[:3]+t*b[:3]
        jac = np.zeros((self.width,2*self.width)) if derivatives else None
        if derivatives:
            jac[:3,:3] = (1-t)*np.eye(3); jac[:3,self.width:self.width+3] = t*np.eye(3)
        for i,node in enumerate(self.left.rotations):
            part = slice(3+3*i,6+3*i)
            value,gradient = rotation_parameters(self.left.local[node,:3,:3],self.right.local[node,:3,:3],
                self.sampled.local[node,:3,:3],a[part],b[part],t,derivatives=derivatives)
            result[part] = value
            if derivatives:
                jac[part,part] = gradient[:,:3]
                jac[part,slice(self.width+part.start,self.width+part.stop)] = gradient[:,3:]
        return result,jac


class SampledPoseWindow:
    def __init__(self, keys, samples):
        if not isinstance(samples,list) or not 1 <= len(samples) <= 64:
            raise ValueError('One to 64 explicit between-key constraints required')
        identities = set()
        for interval,mapping,problem in samples:
            if (type(interval) is not int or not 0 <= interval < len(keys.problems)-1
                    or mapping.left is not keys.problems[interval].model
                    or mapping.right is not keys.problems[interval+1].model
                    or mapping.sampled is not problem.model or problem.neighbors
                    or not 0 < mapping.fraction < 1 or (interval,mapping.fraction) in identities):
                raise ValueError('Distinct interior samples bound to their exact endpoint models required')
            identities.add((interval,mapping.fraction))
        self.keys, self.samples = keys,samples.copy()
        self.size,self.width,self.bounds = keys.size,keys.width,keys.bounds

    def mapped(self, values, *, derivatives=False):
        poses = self.keys.unpack(values)
        return [(i,p,*mapping.parameters(poses[i:i+2].reshape(-1),derivatives=derivatives)) for i,mapping,p in self.samples]

    def values(self, values, *, full=False):
        return np.concatenate([self.keys.values(values,full=full),
            *[(p.full_values(x) if full else p.values(x)) for _,p,x,_ in self.mapped(values)]])

    def pair(self, values):
        gaps,jac = self.keys.pair(values); rows=[gaps];gradients=[jac]
        for i,p,x,chain in self.mapped(values,derivatives=True):
            g,j = p.pair(x); block=np.zeros((len(g),self.size));block[:,i*self.width:(i+2)*self.width]=j@chain
            rows.append(g);gradients.append(block)
        return np.concatenate(rows),np.vstack(gradients)

    def grow(self, values, *, batch_size=32):
        additions=[p.grow(x,batch_size=batch_size) for p,x in zip(self.keys.problems,self.keys.unpack(values))]
        additions.extend(p.grow(x,batch_size=batch_size) for _,p,x,_ in self.mapped(values))
        return additions

    def assess(self, values):
        native=self.keys.assess(values);sampled=[p.assess(x) for _,p,x,_ in self.mapped(values)]
        return dict(numerical_sampled_window_pass=bool(native['numerical_window_pass'] and all(p['numerical_constraints_pass'] for p in sampled)),
                    keys=native,samples=sampled,minimum_fitting_gap=float(self.values(values,full=True).min()))
