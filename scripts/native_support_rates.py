"""Native bend-box proposals jointly evaluated against support and source rates.

The optimizer is a finite sampled search, not a feasibility certificate. Exact
serialized acceptance remains in native_support_job; no caps are relaxed here.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
from scipy.spatial.transform import Rotation
from native_support_path import bend_box
from native_leg_smoothing import smooth,lifts
from native_leg_floor import foot_region,export_rotations
from native_support_skin import NativeSupportSkin as BoundSkin
from contact_rate_path import ProjectedSkin
from paired_temporal_neighbor import rotation_channels
from native_engine_clock import audit_clock
from elbow_swivel import descendants
from timed_rotation_edit import sampled_rotations
from sampled_motion_caps import features,measures,SampledMotionCaps


def aligned(a,b):
    """Batch two_bone_waypoint.align_vectors, including antiparallel directions."""
    a,b=np.asarray(a,float),np.asarray(b,float)
    if a.ndim!=2 or a.shape!=b.shape or a.shape[1]!=3 or not np.isfinite([a,b]).all():raise ValueError('Finite matching direction rows required')
    lengths_a=np.linalg.norm(a,axis=1);lengths_b=np.linalg.norm(b,axis=1)
    if min(lengths_a.min(),lengths_b.min())<1e-12:raise ValueError('Nonzero direction rows required')
    a=a/lengths_a[:,None];b=b/lengths_b[:,None];axis=np.cross(a,b)
    sine=np.linalg.norm(axis,axis=1);cosine=np.clip(np.einsum('ij,ij->i',a,b),-1,1)
    vectors=np.zeros_like(a);active=sine>=1e-12
    vectors[active]=axis[active]/sine[active,None]*np.arctan2(sine[active],cosine[active])[:,None]
    reverse=~active&(cosine<0)
    if reverse.any():
        cross=np.cross(a[reverse],np.eye(3)[np.argmin(np.abs(a[reverse]),axis=1)])
        vectors[reverse]=cross/np.linalg.norm(cross,axis=1)[:,None]*np.pi
    return Rotation.from_rotvec(vectors).as_matrix()


def reach_rotations(worlds,parents,chain,amounts,up,original,swivels=None):
    """Source-plane two-bone reach with retained native foot world orientation."""
    upper,knee,foot=chain;points=worlds[:,:,:3,3][:,chain]
    shoulder,old_knee,old_foot=points.transpose(1,0,2)
    target=old_foot+amounts[:,None]*up;u=old_knee-shoulder;v=old_foot-old_knee
    a=np.linalg.norm(u,axis=1);b=np.linalg.norm(v,axis=1)
    delta=target-shoulder;d=np.linalg.norm(delta,axis=1)
    if np.any(d<1e-8) or np.any(d<abs(a-b)-1e-10) or np.any(d>a+b+1e-10):raise ValueError('Bend target outside exact reach')
    axis=delta/d[:,None];old_axis=old_foot-shoulder;old_axis/=np.linalg.norm(old_axis,axis=1)[:,None]
    bend=u-old_axis*np.einsum('ij,ij->i',u,old_axis)[:,None]
    fallback=np.linalg.norm(bend,axis=1)<1e-10
    bend[fallback]=np.cross(old_axis[fallback],np.eye(3)[np.argmin(abs(old_axis[fallback]),axis=1)])
    bend/=np.linalg.norm(bend,axis=1)[:,None]
    swivel=np.zeros(len(worlds)) if swivels is None else np.asarray(swivels,float)
    if swivel.shape!=(len(worlds),) or not np.isfinite(swivel).all() or np.any(abs(swivel)>np.pi):raise ValueError('Finite matching swivel angles within pi required')
    transported=aligned(old_axis,axis)
    if np.any(swivel):transported=Rotation.from_rotvec(axis*swivel[:,None]).as_matrix()@transported
    along=(a*a-b*b+d*d)/(2*d)
    new_knee=shoulder+axis*along[:,None]+np.einsum('nij,nj->ni',transported,bend)*np.sqrt(np.maximum(0,a*a-along*along))[:,None]
    rotation_u=aligned(np.einsum('nij,nj->ni',transported,u),new_knee-shoulder)@transported@worlds[:,upper,:3,:3]
    rotation_k=aligned(np.einsum('nij,nj->ni',transported,v),target-new_knee)@transported@worlds[:,knee,:3,:3]
    parent=parents[upper];parent_rotation=worlds[:,parent,:3,:3] if parent>=0 else np.tile(np.eye(3),(len(worlds),1,1))
    local=np.stack([parent_rotation.transpose(0,2,1)@rotation_u,rotation_u.transpose(0,2,1)@rotation_k,rotation_k.transpose(0,2,1)@worlds[:,foot,:3,:3]],axis=1)
    q=Rotation.from_matrix(local.reshape(-1,3,3)).as_quat().reshape(len(worlds),3,4)
    q*=np.where(np.sum(q*original,axis=2)<0,-1.,1.)[:,:,None]
    unchanged=(np.abs(amounts)<=1e-12)&(swivel==0)
    q[unchanged]=original[unchanged]
    return q


class SupportRateProblem:
    def __init__(self,rig,reader,rows,tau=.05,mu=.5):
        self.rig,self.reader,self.rows=rig,reader,rows;self.channels=rotation_channels(rig.document,rig.binary)
        self.uniform=np.arange(int(np.floor(reader.duration*120))+1)/120
        if len(self.uniform)<3:raise ValueError('At least three rate samples required')
        declared=self.uniform.tolist()+[t for r in rows for t in r['stance_s']+r['edit_s']]
        self.times=audit_clock(reader.duration,[c[2] for c in reader.channels],declared,rows[0]['stance_s'][0])
        self.raw=np.array([reader.sample(float(t)) for t in self.times]);self.rate_ids=np.searchsorted(self.times,self.uniform)
        self.caps=SampledMotionCaps(features(self.raw[self.rate_ids],rig.joints),self.uniform,np.linspace(0,self.uniform[-1],5))
        self.local=self.raw.copy()
        for node,parent in enumerate(rig.parents):
            if parent>=0:self.local[:,node]=np.linalg.inv(self.raw[:,parent])@self.raw[:,node]
        self.nodes=sorted({n for r in rows for n in r['chain']});self.affected=np.zeros(len(rig.parents),bool)
        for r in rows:self.affected|=descendants(rig.parents,r['chain'][0])
        # Match the scalar decoder's installed NumPy endpoint comparisons.
        # Vector float64 comparisons can interpolate a time that it clamps.
        self.endpoint_masks={n:tuple(np.fromiter((compare(float(t),clock[key]) for t in self.times),bool,len(self.times))
            for compare,key in ((np.less_equal,0),(np.greater_equal,-1))) for n,(_,clock,_) in self.channels.items() if n in self.nodes}
        self.columns=np.flatnonzero(self.affected[rig.joints]);self.data=[];initial=[];lower=[];upper=[];skin=BoundSkin(rig)
        for r in rows:
            first,last=r['edit_keys'];clock=r['clock'][first:last+1];worlds=np.array([reader.sample(float(t)) for t in clock])
            region=foot_region(skin,rig.parents,r['chain'][-1]);projection=ProjectedSkin(skin,region,r['up'],r['offset'])
            box=bend_box(worlds,rig.parents,r['chain'],projection.evaluate(worlds).min(axis=1),clock,r)
            bend,seed=smooth(clock,box['lower'],box['upper'],acceleration_time=tau,reference_weight=mu,reference=box['reference'])
            free=np.flatnonzero(box['upper']>box['lower']);start=len(initial)
            initial.extend(bend[free]);lower.extend(box['lower'][free]);upper.extend(box['upper'][free])
            original=np.stack([self.channels[n][2][first:last+1] for n in r['chain']],axis=1)
            self.data.append(dict(row=r,clock=clock,worlds=worlds,box=box,bend=bend,free=free,ids=np.arange(start,len(initial)),projection=projection,original=original,seed=seed))
        self.initial,self.lower,self.upper=map(np.asarray,(initial,lower,upper))

    def rotations(self,x):
        x=np.asarray(x,float)
        if x.shape!=self.initial.shape or not np.isfinite(x).all() or np.any(x<self.lower) or np.any(x>self.upper):raise ValueError('Finite bends inside authored boxes required')
        values={n:self.channels[n][2].astype(float).copy() for n in self.nodes};angles=[]
        for d in self.data:
            bend=d['bend'].copy();bend[d['free']]=x[d['ids']];amount=lifts(d['box'],bend);r=d['row'];a,b=r['edit_keys']
            q=reach_rotations(d['worlds'],self.rig.parents,r['chain'],amount,r['up'],d['original'])
            # Exact frozen native boundaries, including source quaternion signs.
            q[[0,-1]]=d['original'][[0,-1]]
            for j,n in enumerate(r['chain']):values[n][a:b+1]=q[:,j]
            angles.append(np.rad2deg((Rotation.from_quat(d['original'].reshape(-1,4)).inv()*Rotation.from_quat(q.reshape(-1,4))).magnitude()).reshape(-1,3))
        return values,angles

    def world(self,values):
        local=self.local.copy();world=self.raw.copy()
        for node,q in values.items():
            clock=self.channels[node][1];matrix=sampled_rotations(clock,q,self.times)
            for mask,key in zip(self.endpoint_masks[node],(0,-1)):
                if mask.any():matrix[mask]=Rotation.from_quat(q[key]).as_matrix()
            exact=np.searchsorted(clock,self.times,side='left');valid=exact<len(clock);valid[valid]&=clock[exact[valid]].astype(float)==self.times[valid]
            matrix[valid]=Rotation.from_quat(q[exact[valid]]).as_matrix()
            local[:,node,:3,:3]=matrix
        done=set()
        def visit(n):
            if n in done:return
            parent=self.rig.parents[n]
            if parent>=0 and self.affected[parent]:visit(parent)
            world[:,n]=world[:,parent]@local[:,n] if parent>=0 else local[:,n];done.add(n)
        for n in np.flatnonzero(self.affected):visit(int(n))
        # Preserve the unmodified decoder at frozen/outside intervals exactly.
        for d in self.data:
            r=d['row'];branch=descendants(self.rig.parents,r['chain'][0]);free=np.ones(len(self.times),bool)
            for other in self.rows:
                if other['foot']==r['foot']:free&=(self.times<=other['edit_s'][0])|(self.times>=other['edit_s'][1])
            world[np.ix_(free,branch)]=self.raw[np.ix_(free,branch)]
        return world

    def residual(self,x):
        values,angles=self.rotations(x);world=self.world(values)
        rates=measures(features(world[self.rate_ids],self.rig.joints),self.caps.dt);parts=[]
        for actual,cap,floor in zip(rates,self.caps.caps,(.05,.5,.1,1.)):
            parts.append((np.maximum(0,actual[:,self.columns]-cap[:,self.columns]-self.caps.tolerance)/np.maximum(cap[:,self.columns],floor)).ravel())
        for d,angle in zip(self.data,angles):
            r=d['row'];mask=(self.times>=r['stance_s'][0])&(self.times<=r['stance_s'][1]);heights=d['projection'].evaluate(world[mask]).min(axis=1)
            parts.extend([np.maximum(0,.000125-heights)/.001,np.maximum(0,heights-r['maximum_height']+.000125)/.001])
            inside=(self.times>=r['edit_s'][0])&(self.times<=r['edit_s'][1]);node=r['chain'][-1]
            movement=np.linalg.norm(world[inside,node,:3,3]-self.raw[inside,node,:3,3],axis=1)
            parts.extend([np.maximum(0,movement-r['displacement'])/.001,np.maximum(0,angle-r['angle']).ravel()])
        return np.concatenate(parts)

    def dependencies(self,d):
        return zip(d['free'],d['ids'])

    def sparsity(self):
        """Every row is supported by its neighboring native keys and branch."""
        size=len(self.residual(self.initial));matrix=lil_matrix((size,len(self.initial)),dtype=int)
        uniform=self.uniform;offset=0
        for metric,order in enumerate((1,2,1,2)):
            count=len(uniform)-order
            for d in self.data:
                branch=descendants(self.rig.parents,d['row']['chain'][0]);columns=np.flatnonzero(branch[np.asarray(self.rig.joints)[self.columns]])
                for key,col in self.dependencies(d):
                    a,b=d['clock'][max(0,key-1)],d['clock'][min(len(d['clock'])-1,key+1)]
                    relevant=np.flatnonzero((uniform[:count]<=b)&(uniform[order:]>=a))
                    ids=offset+(relevant[:,None]*len(self.columns)+columns).ravel();matrix[ids,col]=1
            offset+=count*len(self.columns)
        for d in self.data:
            r=d['row'];stance=self.times[(self.times>=r['stance_s'][0])&(self.times<=r['stance_s'][1])]
            edit=self.times[(self.times>=r['edit_s'][0])&(self.times<=r['edit_s'][1])]
            for key,col in self.dependencies(d):
                a,b=d['clock'][max(0,key-1)],d['clock'][min(len(d['clock'])-1,key+1)]
                ids=np.flatnonzero((stance>=a)&(stance<=b));matrix[offset+ids,col]=1;matrix[offset+len(stance)+ids,col]=1
                ids=np.flatnonzero((edit>=a)&(edit<=b));matrix[offset+2*len(stance)+ids,col]=1
                matrix[offset+2*len(stance)+len(edit)+3*key+np.arange(3),col]=1
            offset+=2*len(stance)+len(edit)+3*len(d['clock'])
        assert offset==size
        return matrix.tocsr()


def propose(rig,reader,rows,path,acceleration_time=.05,reference_weight=.5,*,maximum_evaluations=80):
    if type(maximum_evaluations) is not int or not 1<=maximum_evaluations<=2000:raise ValueError('Choose 1–2000 joint-search evaluations')
    problem=SupportRateProblem(rig,reader,rows,acceleration_time,reference_weight)
    initial=problem.residual(problem.initial);fit=None
    if len(problem.initial):
        fit=least_squares(problem.residual,problem.initial,bounds=(problem.lower,problem.upper),jac_sparsity=problem.sparsity(),
            max_nfev=maximum_evaluations,ftol=1e-9,xtol=1e-9,gtol=1e-9,x_scale='jac',diff_step=1e-5)
    x=problem.initial if fit is None else fit.x;values,_=problem.rotations(x);final=problem.residual(x)
    export_rotations(rig.document,rig.binary,values,path)
    return [dict(method='joint_support_source_rate_search',variables=len(x),initial_squared_residual=float(initial@initial),
        final_squared_residual=float(final@final),evaluations=0 if fit is None else int(fit.nfev),
        success=True if fit is None else bool(fit.success),message='No free bend variables' if fit is None else str(fit.message),maximum_evaluations=maximum_evaluations,
        sample_times=len(problem.times),source_rate_tolerance=problem.caps.tolerance,
        scope='Bounded source-plane knee bends; native tangent/foot orientation retained. Proxy residual is not serialized acceptance.')]
