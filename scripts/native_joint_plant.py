"""Joint native rotation model for contact, support and source-rate constraints.

Free interior leg keys preserve all translations, other joints and boundaries.
Proposal constraints never replace independently decoded acceptance.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.sparse import lil_matrix,vstack
from native_support_rates import SupportRateProblem
from native_support_skin import NativeSupportSkin
from native_support_roundtrip import preview_values
from native_foot_plant import patch_geometry
from native_leg_floor import foot_region
from contact_rate_path import ProjectedSkin
from paired_temporal_neighbor import rotation_channels
from sampled_motion_caps import features,measures,SampledMotionCaps
from native_engine_clock import audit_clock
from elbow_swivel import descendants


class JointPlantProblem(SupportRateProblem):
    """Direct local rotation vectors; no precomputed ankle-only reach corridor."""
    native_roundtrip=False
    def __init__(self,rig,reader,rows,limits,seed_reader):
        self.rig,self.reader,self.rows,self.limits=rig,reader,rows,limits
        self.channels=rotation_channels(rig.document,rig.binary)
        self.uniform=np.arange(int(np.floor(reader.duration*120))+1)/120
        if len(self.uniform)<3:raise ValueError('At least three native rate samples required')
        self.contact_clocks=[]
        for r in rows:
            a,b=r['stance_s'];u=np.arange(int(np.floor(a*120)),int(np.ceil(b*120))+1)/120
            self.contact_clocks.append(np.unique(np.r_[a,u[(u>a)&(u<b)],b]))
        declared=self.uniform.tolist()+[t for r in rows for t in r['stance_s']+r['edit_s']]
        declared.extend(t for clock in self.contact_clocks for t in clock)
        self.times=audit_clock(reader.duration,[c[2] for c in reader.channels],declared,rows[0]['stance_s'][0])
        self.raw=np.array([reader.sample(float(t)) for t in self.times]);self.rate_ids=np.searchsorted(self.times,self.uniform)
        self.caps=SampledMotionCaps(features(self.raw[self.rate_ids],rig.joints),self.uniform,np.linspace(0,self.uniform[-1],5))
        self.local=self.raw.copy()
        for node,parent in enumerate(rig.parents):
            if parent>=0:self.local[:,node]=np.linalg.inv(self.raw[:,parent])@self.raw[:,node]
        self.nodes=sorted({n for r in rows for n in r['chain']});self.affected=np.zeros(len(rig.parents),bool)
        for r in rows:self.affected|=descendants(rig.parents,r['chain'][0])
        self.columns=np.flatnonzero(self.affected[rig.joints])
        self.endpoint_masks={n:tuple(np.fromiter((compare(float(t),clock[key]) for t in self.times),bool,len(self.times))
            for compare,key in ((np.less_equal,0),(np.greater_equal,-1))) for n,(_,clock,_) in self.channels.items() if n in self.nodes}
        self.data=[];initial=[];lower=[];upper=[];skin=NativeSupportSkin(rig)
        seed={node:values for node,kind,clock,values,mode in seed_reader.channels if kind=='rotation'}
        for r,contact_clock in zip(rows,self.contact_clocks):
            first,last=r['edit_keys'];clock=r['clock'][first:last+1]
            original=np.stack([self.channels[n][2][first:last+1] for n in r['chain']],axis=1)
            warm=np.stack([seed[n][first:last+1] for n in r['chain']],axis=1)
            vectors=(Rotation.from_quat(original.reshape(-1,4)).inv()*Rotation.from_quat(warm.reshape(-1,4))).as_rotvec().reshape(len(clock),3,3)
            vectors[np.all(original==warm,axis=2)]=0
            free=np.arange(1,len(clock)-1);start=len(initial);initial.extend(vectors[free].ravel())
            # Component boxes include the full authored rotation ball. The
            # separate radial angle constraints reject its excessive corners.
            bound=np.deg2rad(r['angle']);lower.extend(np.full(9*len(free),-bound));upper.extend(np.full(9*len(free),bound))
            region=foot_region(skin,rig.parents,r['chain'][-1])
            points,anchor,patch,refs=patch_geometry(rig,reader,r)
            ids=np.arange(start,len(initial)).reshape(len(free),3,3)
            self.data.append(dict(row=r,clock=clock,original=original,free=free,ids=ids,
                projection=ProjectedSkin(skin,region,r['up'],r['offset']),
                patch_projections=[ProjectedSkin(skin,region[patch],axis) for axis in np.eye(3)],
                anchor=anchor[patch],patch_vertex_references=refs,patch_vertices=len(patch),
                contact_ids=np.searchsorted(self.times,contact_clock),contact_clock=contact_clock,
                stance=np.flatnonzero((self.times>=r['stance_s'][0])&(self.times<=r['stance_s'][1])),
                inside=np.flatnonzero((self.times>=r['edit_s'][0])&(self.times<=r['edit_s'][1]))))
        self.initial,self.lower,self.upper=map(lambda a:np.asarray(a,float),(initial,lower,upper))
        self.rotations(self.initial)

    def rotations(self,x):
        x=np.asarray(x,float)
        if x.shape!=self.initial.shape or not np.isfinite(x).all() or np.any(x<self.lower) or np.any(x>self.upper):
            raise ValueError('Finite joint rotation controls inside component boxes required')
        values={n:self.channels[n][2].astype(float).copy() for n in self.nodes};angles=[]
        for d in self.data:
            r=d['row'];a,b=r['edit_keys'];vectors=np.zeros((len(d['clock']),3,3));vectors[d['free']]=x[d['ids']]
            q=d['original'].astype(float).copy();active=np.any(vectors!=0,axis=2)
            if active.any():
                q[active]=(Rotation.from_quat(q[active])*Rotation.from_rotvec(vectors[active])).as_quat()
                q[active]*=np.where(np.sum(q[active]*d['original'][active],axis=1)<0,-1.,1.)[:,None]
            for j,node in enumerate(r['chain']):values[node][a:b+1]=q[:,j]
            angles.append(np.rad2deg(np.linalg.norm(vectors,axis=2)))
        return values,angles

    def core_constraints(self,values,world):
        # Per-joint measures are independent. Final export audits still cover
        # all joints; this subset avoids repeated work for frozen branches.
        rates=measures(features(world[self.rate_ids],np.asarray(self.rig.joints)[self.columns]),self.caps.dt)
        parts=[]
        for actual,cap,floor in zip(rates,self.caps.caps,(.05,.5,.1,1.)):
            parts.append(((actual-cap[:,self.columns]-self.caps.tolerance)/np.maximum(cap[:,self.columns],floor)).ravel())
        for d in self.data:
            r=d['row'];a,b=r['edit_keys'];q=np.stack([values[n][a:b+1] for n in r['chain']],axis=1)
            angle=np.rad2deg((Rotation.from_quat(d['original'].reshape(-1,4)).inv()*Rotation.from_quat(q.reshape(-1,4))).magnitude()).reshape(-1,3)
            heights=d['projection'].evaluate(world[d['stance']]).min(axis=1)
            shift=np.linalg.norm(world[d['inside'],r['chain'][-1],:3,3]-self.raw[d['inside'],r['chain'][-1],:3,3],axis=1)
            parts.extend([(r['clearance']-heights)/.001,(heights-r['maximum_height'])/.001,
                          (shift-r['displacement'])/.001,(angle-r['angle']).ravel()/max(r['angle'],.01)])
        return np.concatenate(parts)

    def contact_constraints(self,world):
        parts=[]
        for d in self.data:
            r=d['row'];up=r['up'];world= np.asarray(world)
            points=np.stack([p.evaluate(world[d['contact_ids']]) for p in d['patch_projections']],axis=2)
            error=points-d['anchor'];error-=(error@up)[...,None]*up
            velocity=np.diff(points,axis=0)/np.diff(d['contact_clock'])[:,None,None]
            velocity-=(velocity@up)[...,None]*up;limit=self.limits[r['id']]
            parts.extend([((np.linalg.norm(error,axis=2)-limit['anchor'])/max(limit['anchor'],.0001)).ravel(),
                          ((np.linalg.norm(velocity,axis=2)-limit['speed'])/max(limit['speed'],.001)).ravel()])
        return np.concatenate(parts)

    def constraints(self,values,world):return np.r_[self.core_constraints(values,world),self.contact_constraints(world)]

    def model(self,x,*,quantized=False,native_roundtrip=False):
        values,_=self.rotations(x)
        if quantized or native_roundtrip:values={n:q.astype(np.float32).astype(float) for n,q in values.items()}
        raw=self.constraints(values,self.world(values))
        if not native_roundtrip:return raw
        forwarded=preview_values(values,self.channels)
        return np.r_[raw,self.constraints(forwarded,self.world(forwarded))]

    def native_constraint_model(self,x,*,quantized=False):
        return self.model(x,quantized=quantized,native_roundtrip=self.native_roundtrip)

    def dependencies(self,d):
        return ((int(key),int(col)) for key,cols in zip(d['free'],d['ids']) for col in cols.ravel())

    def sparsity(self,*,native_roundtrip=None):
        if native_roundtrip is None:native_roundtrip=self.native_roundtrip
        values,_=self.rotations(self.initial);world=self.world(values)
        size=len(self.constraints(values,world));matrix=lil_matrix((size,len(self.initial)),dtype=int);offset=0
        for order in (1,2,1,2):
            count=len(self.uniform)-order
            for d in self.data:
                branch=descendants(self.rig.parents,d['row']['chain'][0]);joints=np.flatnonzero(branch[np.asarray(self.rig.joints)[self.columns]])
                for key,col in self.dependencies(d):
                    a,b=d['clock'][key-1],d['clock'][key+1]
                    relevant=np.flatnonzero((self.uniform[:count]<=b)&(self.uniform[order:]>=a))
                    matrix[offset+(relevant[:,None]*len(self.columns)+joints).ravel(),col]=1
            offset+=count*len(self.columns)
        for d in self.data:
            stance=self.times[d['stance']];inside=self.times[d['inside']]
            for key,col in self.dependencies(d):
                a,b=d['clock'][key-1],d['clock'][key+1]
                ids=np.flatnonzero((stance>=a)&(stance<=b));matrix[offset+ids,col]=1;matrix[offset+len(stance)+ids,col]=1
                ids=np.flatnonzero((inside>=a)&(inside<=b));matrix[offset+2*len(stance)+ids,col]=1
                matrix[offset+2*len(stance)+len(inside)+3*key+np.arange(3),col]=1
            offset+=2*len(stance)+len(inside)+3*len(d['clock'])
        for d in self.data:
            clock=d['contact_clock'];p=d['patch_vertices'];m=len(clock)
            for key,col in self.dependencies(d):
                a,b=d['clock'][key-1],d['clock'][key+1]
                ids=np.flatnonzero((clock>=a)&(clock<=b));matrix[offset+(ids[:,None]*p+np.arange(p)).ravel(),col]=1
                ids=np.flatnonzero((clock[:-1]<=b)&(clock[1:]>=a));matrix[offset+m*p+(ids[:,None]*p+np.arange(p)).ravel(),col]=1
            offset+=(2*m-1)*p
        assert offset==size
        result=matrix.tocsr()
        return vstack([result,result],format='csr') if native_roundtrip else result
