"""Orientation and facing-side proposal rows on unchanged authored contacts.

Normals follow complete posed incident faces. These local models do not replace
the separately decoded surface-contact audit or full geometry checks.
"""
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows
from native_surface_contact import policy_for,normals
from native_scene_geometry import faces_for
from native_surface_lift import lift


class ContactNorms:
    def __init__(self,problem,policy,digest,*,maximum_rows=20000):
        self.problem=problem;self.policy=policy
        if type(maximum_rows) is not int or not 1<=maximum_rows<=100000:raise ValueError('Finite explicit contact norm-row budget required')
        self.maximum_rows=maximum_rows
        self.limits,self.budget=policy_for(policy,problem.scene,digest)
        self.faces={n:faces_for(a['rig'])[0] for n,a in problem.scene.actors.items()}

    def sample(self,worlds):
        problem=self.problem;scene=problem.scene;vectors=[];sides=[];identity=[];queries=0
        if set(worlds)!=set(scene.actors):raise ValueError('Complete actor pose dictionary required')
        for data in problem.rows:
            entry=data['entry'];row=entry['authored'];target=row['target'];clock=data['times']
            if target['space']=='object':positions,rotations=scene.object_poses(target['object'],clock)
            for index,time in enumerate(clock):
                cache={};stamp=int(np.searchsorted(problem.times,time))
                if stamp==len(problem.times) or problem.times[stamp]!=time:raise ValueError('Exact contact clock missing')
                def surface(name):
                    nonlocal queries
                    if name not in cache:
                        queries+=1
                        if queries>self.budget:raise ValueError('Complete contact proposal exceeds explicit pose budget')
                        actor=scene.actors[name];skin=actor['skin'];world=np.asarray(worlds[name],float)
                        if world.shape!=(len(problem.times),len(actor['rig'].parents),4,4) or not np.isfinite(world).all():
                            raise ValueError('Complete finite native pose population required')
                        points=np.einsum('vkij,vkj,vk->vi',world[stamp,skin.nodes,:3,:],skin.points,skin.weights)
                        p,r=actor['placement'];cache[name]=points@r.T+p
                    return cache[name]
                def oriented(name,ids,reduction):
                    v=surface(name);groups=[ids] if reduction=='centroid' else [[int(i)] for i in ids]
                    report=normals(v,self.faces[name],groups,minimum_area=self.limits['minimum_normal_area_m2'],minimum_coherence=self.limits['minimum_normal_coherence'])
                    if not all(r['available'] for r in report):raise ValueError('Unavailable contact normal cannot guide a proposal')
                    points=v[ids].mean(0,keepdims=True) if reduction=='centroid' else v[ids]
                    return points,np.asarray([r['normal_world'] for r in report])
                left,na=oriented(row['actor'],entry['ids'],row['reduction'])
                if target['space']=='actor':right,nb=oriented(target['actor'],entry['target_ids'],target['reduction'])
                else:
                    nb=np.asarray(self.policy['contacts'][row['id']]['target_normal']['normals'],float)
                    right=entry['target_ids']
                    if target['space']=='object':right=right@rotations[index].T+positions[index];nb=nb@rotations[index].T
                delta=right-left
                for k in range(len(left)):
                    if 3*(len(vectors)+1)>self.maximum_rows:raise ValueError('Complete contact norms exceed row budget; no subset returned')
                    vectors.append(na[k]+nb[k]);sides.extend([float(na[k]@delta[k]),float(-nb[k]@delta[k])])
                    identity.append(dict(contact=row['id'],time_s=float(time),point=k))
        scene.check_inputs()
        vectors=np.asarray(vectors,float);sides=np.asarray(sides,float)
        if not len(vectors) or not np.isfinite(np.r_[vectors.ravel(),sides]).all():raise ValueError('Complete finite contact norm rows required')
        chord=2*np.sin(np.deg2rad(self.limits['maximum_opposition_error_degrees'])/2)
        rows=NormRows(vectors,np.full(len(vectors),chord),np.full(len(vectors),max(chord,.001)))
        return rows,sides+self.limits['backface_allowance_m'],dict(identity=identity,actor_pose_queries=queries,
            original_references_and_clocks=True,maximum_norm_rows=self.maximum_rows,orientation_cap_chord=float(chord),backface_allowance_m=self.limits['backface_allowance_m'])

    def residual(self,worlds):
        rows,gaps,_=self.sample(worlds)
        return np.r_[rows.residual(),-gaps/.005]

    def linearize(self,value,decoded_worlds,trust,*,step=.001):
        problem=self.problem;value=problem.edits.controls(value)
        if type(step) not in (int,float) or not np.isfinite(step) or not 1e-6<=step<=.01:raise ValueError('Bounded contact difference step required')
        base,gaps,identity=self.sample(decoded_worlds)
        smooth,smooth_gaps,_=self.sample(problem.worlds(value,quantized=False));vcols=[];scols=[]
        for i in range(len(value)):
            room=problem.upper[i]-value[i] if problem.upper[i]-value[i]>=value[i]-problem.lower[i] else problem.lower[i]-value[i]
            h=np.copysign(min(step,abs(room)),room)
            if h==0:raise ValueError('No contact finite-difference room')
            other=value.copy();other[i]+=h
            rows,other_gaps,other_identity=self.sample(problem.worlds(other,quantized=False))
            if other_identity['identity']!=identity['identity'] or not np.array_equal(rows.caps,base.caps) or not np.array_equal(rows.scales,base.scales):
                raise ValueError('Contact row population or caps changed')
            vcols.append(((rows.vectors-smooth.vectors)/h).ravel());scols.append((other_gaps-smooth_gaps)/h)
        vector_jac=sparse.csc_matrix(np.stack(vcols,axis=1));side_jac=sparse.csr_matrix(np.stack(scols,axis=1))
        side_rows,side_vector_jac,conversion=lift(gaps,side_jac,value,problem.lower,problem.upper,trust,clearance=0.,scale=.005)
        combined=NormRows(np.r_[base.vectors,side_rows.vectors],np.r_[base.caps,side_rows.caps],np.r_[base.scales,side_rows.scales])
        return combined,sparse.vstack([vector_jac,side_vector_jac],format='csc'),dict(**identity,
            norm_rows=len(combined.caps),orientation_rows=len(base.caps),side_rows=len(gaps),conversion=conversion,
            difference_step=step,scope='Decoded orientation vectors and signed side gaps with continuous proposal derivatives. Complete original conditions, surface audit and mesh checks remain authoritative.')


def score(residual):
    residual=np.asarray(residual,float)
    if residual.ndim!=1 or not len(residual) or not np.isfinite(residual).all():raise ValueError('Complete finite surface-contact residuals required')
    positive=np.maximum(0.,residual)
    return np.array([positive.max(),float(positive@positive)])


def nonregressing(before,after):
    before,after=score(before),score(after)
    return bool(np.all(after<=before+np.array([1e-9,1e-12])))


def improved(before,after):
    before,after=score(before),score(after)
    return bool(np.all(after<=before+np.array([1e-9,1e-12])) and np.any(after<before-np.array([1e-9,1e-12])))


def row_regression(before,after):
    """Each passing row stays passing; each failed row cannot gain excess."""
    before,after=np.asarray(before,float),np.asarray(after,float)
    if (before.ndim!=1 or not len(before) or after.shape!=before.shape
            or not np.isfinite(np.r_[before,after]).all()):
        raise ValueError('Matching complete finite contact residual populations required')
    return after-np.maximum(0.,before)


def protect_rows(system,jacobian,native_rows,contact_before,*,reference=None):
    """Duplicate contact rows into the hard prefix without changing authored caps.

    Failed rows have a separate no-worsening bound at their decoded base norm.
    A recentered model supplies the original contact-only reference explicitly;
    the rejected candidate cannot become a new no-worsening baseline.
    Their original authored rows remain in the objective and final audit.
    """
    before=np.asarray(contact_before,float);jacobian=sparse.csc_matrix(jacobian)
    if (type(native_rows) is not int or not 1<=native_rows<=len(system.caps)
            or before.ndim!=1 or not len(before) or not np.isfinite(before).all()
            or native_rows+len(before)>len(system.caps)
            or jacobian.shape[0]!=3*len(system.caps) or not np.isfinite(jacobian.data).all()):
        raise ValueError('Complete native prefix and contact suffix required for protection')
    count=len(before);suffix=np.arange(len(system.caps)-count,len(system.caps))
    anchor=NormRows(system.vectors[suffix],system.caps[suffix],system.scales[suffix]) if reference is None else reference
    if (not isinstance(anchor,NormRows) or anchor.vectors.shape!=(count,3)
            or not np.array_equal(anchor.caps,system.caps[suffix])
            or not np.array_equal(anchor.scales,system.scales[suffix])):
        raise ValueError('Complete original contact reference with unchanged caps/scales required')
    np.testing.assert_allclose(anchor.residual(),before,atol=1e-9,rtol=1e-12)
    order=np.r_[np.arange(native_rows),suffix,np.arange(native_rows,len(system.caps))]
    caps=system.caps[order].copy()
    caps[native_rows:native_rows+count]=np.maximum(anchor.caps,np.linalg.norm(anchor.vectors,axis=1))
    protected=NormRows(system.vectors[order],caps,system.scales[order])
    derivative=jacobian[(3*order[:,None]+np.arange(3)).ravel()]
    return protected,derivative,dict(native_rows=native_rows,protected_contact_rows=count,
        hard_rows=native_rows+count,geometry_rows=len(system.caps)-native_rows-count,
        authored_norm_rows_unchanged=True,contact_baseline_residual=before.tolist(),
        scope='Separate per-row no-worsening proposal bounds. Original authored caps/scales retained in soft rows and final decoded audit.')
