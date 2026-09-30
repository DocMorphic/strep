"""Constrained local GLB edits with fixed contact/boundary keys and joint-rate caps."""
import copy
import time
import numpy as np
from scipy.optimize import minimize,least_squares
from scipy.spatial.transform import Rotation, Slerp
from gltf_tools import local_matrix, hierarchy, append_accessor, write_glb
from paired_temporal_neighbor import rotation_channels
from rig_clip_import import AnimationSampler


def world_from_local(local,parents):
    result=np.empty_like(local);done=set();visiting=set()
    def visit(node):
        if node in visiting:raise ValueError('Cyclic node hierarchy')
        if node not in done:
            visiting.add(node);parent=parents[node]
            if parent<0:result[:,node]=local[:,node]
            else:visit(parent);result[:,node]=result[:,parent]@local[:,node]
            visiting.remove(node);done.add(node)
    for node in range(len(parents)):visit(node)
    return result


def joint_rates(positions,frames):
    return [(frames[:-1]+frames[1:])/2,np.linalg.norm(np.diff(positions,axis=0)*120,axis=-1)], \
           [frames[1:-1],np.linalg.norm(np.diff(positions,n=2,axis=0)*14400,axis=-1)]


class GuardedEdit:
    def __init__(self,document,binary,names,free_frames,frames,windows,limit_degrees=5.):
        self.document,self.binary=document,binary;self.parents=hierarchy(document)
        self.frames=np.asarray(frames,dtype=float);self.free=np.asarray(free_frames,dtype=int);self.limit=np.deg2rad(limit_degrees)
        if len(self.frames)<3 or not np.allclose(np.diff(self.frames),.25) or len(set(free_frames))!=len(free_frames):
            raise ValueError('Distinct editable keys and quarter-frame sample clock required')
        if not np.isfinite(self.limit) or self.limit<=0:raise ValueError('Positive finite rotation limit required')
        lookup={n['name']:i for i,n in enumerate(document['nodes']) if 'name' in n}
        self.nodes=[lookup[n] for n in names];self.joints=document['skins'][0]['joints'];self.channels=rotation_channels(document,binary)
        self.affected=[]
        for index,node in enumerate(self.joints):
            parent=self.parents[node]
            while parent>=0:
                if parent in self.nodes:self.affected.append(index);break
                parent=self.parents[parent]
        self.local=np.tile(np.array([local_matrix(n) for n in document['nodes']]),(len(self.frames),1,1,1))
        sampler=AnimationSampler(document,binary,0);scales={}
        sampled={}
        for node,path,clock,values,mode in sampler.channels:
            sampled[node,path]=np.array([sampler.value(path,clock,values,mode,t/30) for t in self.frames])
        for node in range(len(self.parents)):
            if 'matrix' in document['nodes'][node]:continue
            scale=sampled.get((node,'scale'),np.tile(document['nodes'][node].get('scale',[1,1,1]),(len(self.frames),1)))
            scales[node]=scale
            if (node,'rotation') in sampled:self.local[:,node,:3,:3]=Rotation.from_quat(sampled[node,'rotation']).as_matrix()*scale[:,None,:]
            if (node,'translation') in sampled:self.local[:,node,:3,3]=sampled[node,'translation']
        self.scales=scales;self.reference_world=np.array([sampler.sample(t/30) for t in self.frames])
        np.testing.assert_allclose(world_from_local(self.local,self.parents),self.reference_world,atol=1e-12,rtol=0)
        for node in self.nodes:
            _,clock,q=self.channels[node]
            if min(self.free)<0 or max(self.free)>=len(clock):raise ValueError('Editable key outside channel')
            np.testing.assert_array_equal(clock,np.arange(len(clock),dtype=np.float32)/30)
        self.reference=self.reference_world[:,self.joints][:,:,:3,3];self.windows=windows
        self.caps=self.peaks(self.reference);self.normalizer=np.maximum(self.caps,np.tile([.01]*len(self.affected)+[1.]*len(self.affected),len(windows)))
        self.base_energy=max(self.energy(self.reference),1e-12);self.size=len(self.free)*len(self.nodes)*3
        np.testing.assert_allclose(self.positions(np.zeros(self.size)),self.reference,atol=1e-12,rtol=0)

    def quaternions(self,parameters,quantize=False):
        angles=np.asarray(parameters).reshape(len(self.free),len(self.nodes),3)*self.limit;result={}
        for j,node in enumerate(self.nodes):
            q=self.channels[node][2].astype(float).copy()
            edited=(Rotation.from_quat(q[self.free])*Rotation.from_rotvec(angles[:,j])).as_quat()
            edited*=np.where(np.sum(edited*q[self.free],axis=1)<0,-1,1)[:,None]
            unchanged=np.all(angles[:,j]==0,axis=1);edited[unchanged]=q[self.free[unchanged]]
            q[self.free]=edited.astype(np.float32) if quantize else edited;result[node]=q
        return result

    def positions(self,parameters):
        local=self.local.copy()
        for node,q in self.quaternions(parameters).items():
            clock=self.channels[node][1].astype(float)
            rotations=Slerp(clock,Rotation.from_quat(q))(self.frames/30).as_matrix()
            local[:,node,:3,:3]=rotations*self.scales[node][:,None,:]
        world=world_from_local(local,self.parents)
        return world[:,self.joints][:,:,:3,3]

    def peaks(self,positions):
        rates=joint_rates(positions,self.frames)
        return np.concatenate([values[(clock>=start)&(clock<=end)][:,self.affected].max(0)
                               for start,end in self.windows.values() for clock,values in rates])

    def energy(self,positions):
        clock,acceleration=joint_rates(positions,self.frames)[1]
        start,end=self.windows['event'];return float(np.square(acceleration[(clock>=start)&(clock<=end)]).sum())

    def evaluate(self,parameters,reserve=False):
        positions=self.positions(parameters)
        rates=joint_rates(positions,self.frames);slacks=[];offset=0
        # Keep each inequality smooth instead of switching the peak sample
        # inside a max(). Caps still come from the same source joint peaks.
        for start,end in self.windows.values():
            for metric,(clock,values) in enumerate(rates):
                count=len(self.affected);caps=self.caps[offset:offset+count];scale=self.normalizer[offset:offset+count]
                if reserve:caps=caps-np.minimum(caps*1e-4,1e-5 if metric==0 else 1e-3)
                slacks.append(((caps-values[(clock>=start)&(clock<=end)][:,self.affected])/scale+1e-9).ravel());offset+=count
        slack=np.concatenate(slacks)
        norms=np.sum(np.asarray(parameters).reshape(-1,3)**2,axis=1)
        return self.energy(positions)/self.base_energy+1e-5*float(np.sum(norms)),np.r_[slack,1-norms]

    def fit(self,max_iterations=60,max_seconds=90,initial_parameters=None):
        initial=np.zeros(self.size) if initial_parameters is None else np.asarray(initial_parameters,dtype=float)
        if initial.shape!=(self.size,) or not np.isfinite(initial).all():raise ValueError('Finite matching starting parameters required')
        best=np.zeros(self.size);best_loss=1.;evaluations=0;cached=None;value=None;history=[];started=time.monotonic()
        class Deadline(Exception):pass
        def pair(x):
            nonlocal cached,value,best,best_loss,evaluations
            if time.monotonic()-started>max_seconds:raise Deadline()
            if cached is None or not np.array_equal(x,cached):
                value=self.evaluate(x);cached=x.copy();evaluations+=1
            return value
        def callback(x):
            nonlocal best,best_loss
            cost,slack=pair(x);history.append(dict(iteration=len(history)+1,cost=float(cost),minimum_slack=float(slack.min())))
            if slack.min()>=0 and cost<best_loss:best=x.copy();best_loss=float(cost)
            if len(history)%10==0:print(history[-1],flush=True)
        try:
            result=minimize(lambda x:pair(x)[0],initial,method='SLSQP',bounds=[(-1.,1.)]*self.size,
                constraints=[dict(type='ineq',fun=lambda x:pair(x)[1])],callback=callback,
                options=dict(maxiter=max_iterations,ftol=1e-9,eps=1e-6))
            status=dict(success=bool(result.success),message=str(result.message),iterations=int(result.nit),final_cost=float(result.fun),final_parameters=result.x.tolist())
        except Deadline:status=dict(success=False,message='Wall-clock resource limit',iterations=len(history),final_cost=None)
        return best,dict(**status,evaluations=evaluations,seconds=time.monotonic()-started,best_feasible_cost=best_loss,history=history)

    def restore(self,initial_parameters,max_evaluations=80,max_seconds=90):
        initial=np.asarray(initial_parameters,dtype=float)
        if initial.shape!=(self.size,) or not np.isfinite(initial).all():raise ValueError('Finite matching starting parameters required')
        started=time.monotonic();best=initial.copy();best_cost=np.inf;calls=0
        class Deadline(Exception):pass
        def residual(x):
            nonlocal best,best_cost,calls
            if time.monotonic()-started>max_seconds:raise Deadline()
            slack=self.evaluate(x,reserve=True)[1];r=np.maximum(-slack,0);cost=float(r@r);calls+=1
            if cost<best_cost:best=x.copy();best_cost=cost
            return r
        try:
            result=least_squares(residual,initial,bounds=(-1,1),jac='3-point',tr_solver='lsmr',
                max_nfev=max_evaluations,ftol=1e-12,xtol=1e-12,gtol=1e-12)
            parameters=result.x;status=dict(success=bool(result.success),message=str(result.message),evaluations=int(result.nfev),optimality=float(result.optimality))
        except Deadline:
            parameters=best;status=dict(success=False,message='Wall-clock restoration limit',evaluations=None,optimality=None)
        cost,slack=self.evaluate(parameters);reserved=self.evaluate(parameters,reserve=True)[1]
        return parameters,dict(**status,seconds=time.monotonic()-started,residual_calls=calls,final_parameters=parameters.tolist(),
            motion_cost=float(cost),minimum_original_slack=float(slack.min()),minimum_reserved_slack=float(reserved.min()),
            reserve='Fit only: min(1e-4 * source cap, 1e-5 m/s or 1e-3 m/s2); final decoded checks retain original caps and 1e-5 reporting tolerance.')

    def export(self,parameters,path):
        doc=copy.deepcopy(self.document);payload=bytearray(self.binary)
        for node,q in self.quaternions(parameters,quantize=True).items():
            index=self.channels[node][0];doc['animations'][0]['samplers'][index]['output']=append_accessor(doc,payload,q,'VEC4')
        write_glb(path,doc,payload)
