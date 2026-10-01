"""Small native foot-world orientation edits under unchanged support/rate gates.

Unlike the swivel-only search, this experimental parameterization allows foot
orientation to change. Ankle targets, native clocks and frozen keys are retained.
The serialized audit, not the least-squares objective, determines acceptance.
"""
from itertools import chain
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from native_support_swivel import SupportSwivelProblem
from native_leg_floor import export_rotations
from strep import save,sha256


class SupportOrientationProblem(SupportSwivelProblem):
    def __init__(self,rig,reader,rows,tau=.05,mu=.5,*,orientation_limit_degrees=1.):
        if type(orientation_limit_degrees) not in (int,float) or not np.isfinite(orientation_limit_degrees) or not 0<orientation_limit_degrees<=1:
            raise ValueError('Choose positive native foot orientation freedom up to 1 degree')
        super().__init__(rig,reader,rows,tau,mu)
        self.swivel_variables=len(self.initial)-self.bend_variables
        self.orientation_limit_degrees=orientation_limit_degrees
        initial=self.initial.tolist();lower=self.lower.tolist();upper=self.upper.tolist()
        for d in self.data:
            keys=d['swivel_keys'];start=len(initial)
            # Component boxes imply a hard bound on the rotation-vector norm.
            bound=np.deg2rad(min(orientation_limit_degrees,d['row']['angle']))/np.sqrt(3)
            initial.extend(np.zeros(3*len(keys)));lower.extend(np.full(3*len(keys),-bound));upper.extend(np.full(3*len(keys),bound))
            d.update(orientation_keys=keys,orientation_ids=np.arange(start,len(initial)).reshape(-1,3))
        self.initial,self.lower,self.upper=map(np.asarray,(initial,lower,upper))

    def dependencies(self,d):
        return chain(super().dependencies(d),((key,int(col)) for key,cols in zip(d['orientation_keys'],d['orientation_ids']) for col in cols))

    def rotations(self,x):
        x=np.asarray(x,float)
        values,_=super().rotations(x);angles=[]
        for d in self.data:
            r=d['row'];a,b=r['edit_keys'];foot=r['chain'][-1]
            vectors=np.zeros((len(d['clock']),3));vectors[d['orientation_keys']]=x[d['orientation_ids']]
            source=d['worlds'][:,foot,:3,:3];delta=Rotation.from_rotvec(vectors).as_matrix()
            local=Rotation.from_quat(values[foot][a:b+1]).as_matrix()
            # R_parent R_local = R_source. Conjugate a world-space rotation
            # into the local foot frame without moving its ankle origin.
            changed=local@source.transpose(0,2,1)@delta@source
            q=Rotation.from_matrix(changed).as_quat()
            q*=np.where(np.sum(q*d['original'][:,-1],axis=1)<0,-1.,1.)[:,None]
            untouched=np.all(vectors==0,axis=1);q[untouched]=values[foot][a:b+1][untouched]
            q[[0,-1]]=d['original'][[0,-1],-1]
            values[foot][a:b+1]=q
            current=np.stack([values[n][a:b+1] for n in r['chain']],axis=1)
            angles.append(np.rad2deg((Rotation.from_quat(d['original'].reshape(-1,4)).inv()*Rotation.from_quat(current.reshape(-1,4))).magnitude()).reshape(-1,3))
        return values,angles


def propose(rig,reader,rows,path,acceleration_time=.05,reference_weight=.5,*,maximum_evaluations=80):
    if type(maximum_evaluations) is not int or not 1<=maximum_evaluations<=2000:raise ValueError('Choose 1–2000 joint-search evaluations')
    controls_path=Path(path).with_suffix('.controls.json')
    if controls_path.exists():raise ValueError('Choose a fresh orientation-control file')
    problem=SupportOrientationProblem(rig,reader,rows,acceleration_time,reference_weight)
    initial=problem.residual(problem.initial)
    fit=least_squares(problem.residual,problem.initial,bounds=(problem.lower,problem.upper),jac_sparsity=problem.sparsity(),
        max_nfev=maximum_evaluations,ftol=1e-9,xtol=1e-9,gtol=1e-9,x_scale='jac',diff_step=1e-5)
    values,_=problem.rotations(fit.x);final=problem.residual(fit.x);export_rotations(rig.document,rig.binary,values,path)
    save(controls_path,dict(schema='strep-native-support-orientation-controls-v1',
        acceleration_time_s=acceleration_time,reference_weight_per_s2=reference_weight,
        orientation_limit_degrees=problem.orientation_limit_degrees,swivel_limit_degrees=5.,
        parameters=fit.x.tolist(),lower=problem.lower.tolist(),upper=problem.upper.tolist(),
        intervals=[dict(id=d['row']['id'],chain=d['row']['chain'],clock_s=d['clock'].tolist(),
            edit_keys=d['row']['edit_keys'],bend_ids=d['ids'].tolist(),swivel_ids=d['swivel_ids'].tolist(),
            orientation_ids=d['orientation_ids'].tolist()) for d in problem.data],
        proposal_sha256=sha256(path),scope='Replay requires the separately frozen source, support draft and implementation; not an acceptance receipt'))
    maximum_angle=max(np.rad2deg(np.linalg.norm(fit.x[d['orientation_ids']],axis=1)).max(initial=0) for d in problem.data)
    return [dict(method='joint_support_source_rate_orientation_search',variables=len(fit.x),bend_variables=problem.bend_variables,
        swivel_variables=problem.swivel_variables,orientation_limit_degrees=problem.orientation_limit_degrees,
        maximum_native_orientation_edit_degrees=float(maximum_angle),
        controls_file=controls_path.name,controls_sha256=sha256(controls_path),
        initial_squared_residual=float(initial@initial),final_squared_residual=float(final@final),
        evaluations=int(fit.nfev),maximum_evaluations=maximum_evaluations,success=bool(fit.success),message=str(fit.message),
        sample_times=len(problem.times),source_rate_tolerance=problem.caps.tolerance,
        scope='Bounded bends, knee-plane swivels and native foot-world orientations; ankle targets retained. Serialized audits remain separate.')]
