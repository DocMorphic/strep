"""Coupled existing-key curve model with immutable original motion limits.

Complete norm rows and floor clocks are retained. Minimum vertex witnesses guide
proposals; only separately decoded complete geometry can retain a new clip.
"""
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.spatial.transform import Rotation
from audit_native_key_initializer import bound,require
from native_key_contact_initializer import prepare,encode
from native_scene_contacts import SceneContacts
from native_scene_geometry import policy_for,faces_for
from native_scene_norms import NormRows,rate_vectors
from native_surface_lift import lift
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from sampled_motion_caps import features,SampledMotionCaps
from timed_rotation_edit import sampled_rotations
from bounded_pose_ik import hierarchy_order
from strep import read,sha256


class KeyIntervalModel:
    def __init__(self,producer,result_digest,request_digest,active_keys):
        self.producer=Path(producer).resolve()
        result,saved,request,pins,methods,contacts,policy=bound(self.producer,result_digest,request_digest)
        self.pins=dict(pins);self.pins.update({str(self.producer/'result.json'):result_digest,str(self.producer/'request.json'):request_digest})
        self.methods=dict(methods);self.request=request;self.spec=read(contacts);self.digest=sha256(contacts)
        self.scene=SceneContacts(self.spec,contacts.parent);self.policy=policy
        self.name,self.nodes,self.degrees,self.clock,self.channels=prepare(self.scene,request,self.digest,policy)
        self.actor=self.scene.actors[self.name];self.rig=self.actor['rig'];self.skin=self.actor['skin'];self.parents=self.rig.parents
        with np.load(self.producer/'key-controls.npz',allow_pickle=False) as data:
            np.testing.assert_array_equal(data['times_s'],self.clock);self.seed=data['controls'].copy()
        require(self.seed.shape==(len(self.clock),len(self.nodes),3) and np.isfinite(self.seed).all()
            and np.all(np.linalg.norm(self.seed,axis=-1)<=1),'Complete bounded original-key initialization required')
        require(isinstance(active_keys,list) and bool(active_keys) and all(type(i) is int for i in active_keys)
            and active_keys==sorted(set(active_keys)) and np.all(np.diff(active_keys)==1),'Explicit contiguous complete active-key interval required')
        require(all(0<i<len(self.clock)-1 and self.clock[i] not in request['frozen_times_s']
            and request['window_s'][0]<self.clock[i]<request['window_s'][1] for i in active_keys),'Frozen/outside-window key cannot become editable')
        self.active=np.asarray(active_keys,int);self.size=len(active_keys)*len(self.nodes)*3
        require(self.size<=768,'Complete interval exceeds 768 control components; no variables discarded')
        self.initial=self.seed[self.active].ravel().copy();self.lower=np.full(self.size,-1.);self.upper=np.full(self.size,1.)
        self.geometry_times,_,_=policy_for(policy,self.scene,self.digest)
        self.uniform=np.arange(int(np.floor(self.scene.duration*120))+1)/120
        native=[c[2] for a in self.scene.actors.values() for c in a['sampler'].channels]+[o['times'] for o in self.scene.objects.values()]
        self.contact_rows=[];clocks=[self.geometry_times,self.uniform,self.clock,*native]
        from engine_contact_sampling import frame_populations
        for entry in self.scene.rows:
            row=entry['authored'];a,b=row['interval_s'];pops=frame_populations([a,b]) if row['mode']=='hold' else []
            clock=np.unique(np.concatenate([np.array([a,b]),*native,*[p['times_s'] for p in pops]]));clock=clock[(clock>=a)&(clock<=b)]
            self.contact_rows.append(dict(entry=entry,times=clock,populations=pops));clocks.append(clock)
        self.times=np.unique(np.concatenate(clocks));self.rate_ids=np.searchsorted(self.times,self.uniform);self.geometry_ids=np.searchsorted(self.times,self.geometry_times)
        self.source_world=np.asarray([self.actor['sampler'].sample(float(t)) for t in self.times]);self.local=self.source_world.copy()
        for n,p in enumerate(self.parents):
            if p>=0:self.local[:,n]=np.linalg.solve(self.source_world[:,p],self.source_world[:,n])
        self.order=hierarchy_order(self.parents);self.affected=np.zeros(len(self.parents),bool)
        for n in range(len(self.parents)):
            current=n
            while current>=0:
                if current in self.nodes:self.affected[n]=True;break
                current=self.parents[current]
        self.rate=SampledMotionCaps(features(self.source_world[self.rate_ids],self.rig.joints),self.uniform,np.linspace(0,self.scene.duration,5),tolerance=1e-5)
        self.original_caps=tuple(c.copy() for c in self.rate.caps)
        self.rate_count=sum(c.size for c in self.rate.caps);self.used=np.unique(faces_for(self.rig)[0]);self.caps_rad=np.radians(self.degrees)
        candidate=self.producer/'character.glb';require(sha256(candidate)==result['glb_sha256'],'Initial candidate binding changed')
        self.pins[str(candidate)]=result['glb_sha256'];self.pins[str(self.producer/'key-controls.npz')]=sha256(self.producer/'key-controls.npz')
        candidate_rig=RigAsset.load(candidate);reader=NativeSupportSampler(candidate_rig.document,candidate_rig.binary,result['output_animation_index'])
        values=self.quaternions(self.initial,quantized=True)
        for node,value in zip(self.nodes,values):
            expected=next(c[3] for c in reader.channels if c[:2]==(node,'rotation'))
            np.testing.assert_array_equal(value,expected)
        self.initial_world=np.asarray([reader.sample(float(t)) for t in self.times])
        np.testing.assert_allclose(self.worlds(self.initial),self.initial_world,atol=1e-12,rtol=0)
        for row in self.contact_rows:row['ids']=np.searchsorted(self.times,row['times'])
        self.check()

    def check(self):
        self.scene.check_inputs()
        require(all(sha256(p)==h for p,h in self.pins.items()),'Original interval inputs changed')
        require(self.rate.tolerance==1e-5 and all(np.array_equal(a,b) for a,b in zip(self.original_caps,self.rate.caps)), 'Original source-rate caps changed')

    def controls(self,value):
        value=np.asarray(value,float)
        require(value.shape==(self.size,) and np.isfinite(value).all() and np.all(value>=self.lower) and np.all(value<=self.upper),'Finite original-box interval controls required')
        full=self.seed.copy();full[self.active]=value.reshape(len(self.active),len(self.nodes),3);return full

    def quaternions(self,value,*,quantized):
        full=self.controls(value);result=[]
        for k,(channel,cap) in enumerate(zip(self.channels,self.caps_rad)):
            values=channel[3].copy();active=np.any(full[:,k]!=0,axis=1)
            if np.any(active):
                q=(Rotation.from_quat(values[active])*Rotation.from_rotvec(full[active,k]*cap)).as_quat()
                q[np.sum(q*values[active],axis=1)<0]*=-1;values[active]=q
            result.append(values.astype(np.float32).astype(float) if quantized else values)
        return result

    def worlds(self,value,*,quantized=True):
        local=self.local.copy();world=self.source_world.copy()
        for node,channel,values in zip(self.nodes,self.channels,self.quaternions(value,quantized=quantized)):
            matrices=sampled_rotations(channel[2],values,self.times)
            ids=np.searchsorted(channel[2],self.times);safe=np.minimum(ids,len(channel[2])-1);exact=(ids<len(channel[2]))&(channel[2][safe]==self.times)
            matrices[exact]=Rotation.from_quat(values[safe[exact]]).as_matrix();local[:,node,:3,:3]=matrices
        for n in self.order:
            if self.affected[n]:world[:,n]=world[:,self.parents[n]]@local[:,n] if self.parents[n]>=0 else local[:,n]
        return world

    def points(self,worlds,ids,stamps):
        skin=self.skin;points=np.einsum('fvkij,vkj,vk->fvi',worlds[stamps[:,None,None],skin.nodes[ids][None],:3,:],skin.points[ids],skin.weights[ids])
        p,r=self.actor['placement'];return points@r.T+p

    def rows(self,value,worlds=None):
        require(self.rate.tolerance==1e-5 and len(self.rate.caps)==len(self.original_caps) and all(np.array_equal(a,b) for a,b in zip(self.original_caps,self.rate.caps)), 'Original source-rate caps changed')
        self.controls(value);worlds=self.worlds(value) if worlds is None else worlds;vectors=[];caps=[];scales=[]
        def add(vector,cap,scale):
            v=np.asarray(vector,float).reshape(-1,3);vectors.append(v);caps.append(np.broadcast_to(cap,(len(v),)).copy());scales.append(np.broadcast_to(scale,(len(v),)).copy())
        for node,cap in zip(self.nodes,self.caps_rad):
            parent=self.parents[node];local=np.linalg.solve(worlds[:,parent],worlds[:,node])
            delta=Rotation.from_matrix(self.local[:,node,:3,:3].swapaxes(-1,-2)@local[:,:3,:3]).as_rotvec();add(delta,cap,cap)
        add(worlds[:,self.rig.joints,:3,3]-self.source_world[:,self.rig.joints,:3,3],self.request['maximum_joint_displacement_m'],self.request['maximum_joint_displacement_m'])
        for data in self.contact_rows:
            entry=data['entry'];row=entry['authored'];target=row['target'];ids=data['ids'];clock=data['times']
            def actor_points(name,refs,reduction):
                points=self.points(worlds,refs,ids) if name==self.name else self.scene.actor_points(name,refs,clock)
                return points.mean(1,keepdims=True) if reduction=='centroid' else points
            left=actor_points(row['actor'],entry['ids'],row['reduction'])
            if target['space']=='actor':right=actor_points(target['actor'],entry['target_ids'],target['reduction'])
            elif target['space']=='world':right=np.repeat(entry['target_ids'][None],len(ids),axis=0)
            else:
                p,r=self.scene.object_poses(target['object'],clock);right=np.einsum('fij,vj->fvi',r,entry['target_ids'])+p[:,None]
            error=left-right
            if target['space']=='object':error=np.einsum('fvi,fij->fvj',error,r)
            limit=row['limits']['position_m'];add(error,limit,max(limit,.0001))
            for pop in data['populations']:
                if len(pop['times_s'])<2:add(np.zeros((1,3)),-1.,1.);continue
                stamps=np.searchsorted(clock,pop['times_s']);limit=row['limits']['relative_speed_m_s'];add(np.diff(error[stamps],axis=0)*pop['rate_hz'],limit,max(limit,.001))
        self.edit_count=sum(len(v) for v in vectors)
        for vector,cap in zip(rate_vectors(features(worlds[self.rate_ids],self.rig.joints),self.rate.dt),self.rate.caps):add(vector,(cap+self.rate.tolerance).ravel(),np.maximum(cap,.001).ravel())
        return NormRows(np.concatenate(vectors),np.concatenate(caps),np.concatenate(scales))

    def floor(self,worlds):
        points=[]
        for start in range(0,len(self.geometry_ids),32):points.append(self.points(worlds,self.used,self.geometry_ids[start:start+32]))
        points=np.concatenate(points);witnesses=[];gaps=[]
        for plane in self.policy['planes'].values():
            distance=points@np.asarray(plane['normal_world'])-plane['offset_m'];ids=np.argmin(distance,axis=1)
            witnesses.append(self.used[ids]);gaps.append(distance[np.arange(len(ids)),ids]+self.policy['limits']['penetration_m'])
        require(bool(gaps),'Explicit complete plane guidance required')
        return np.concatenate(gaps),np.asarray(witnesses)

    def witness_gaps(self,worlds,witnesses):
        gaps=[]
        for plane,vertices in zip(self.policy['planes'].values(),witnesses):
            skin=self.skin;nodes=skin.nodes[vertices];points=np.einsum('fkij,fkj,fk->fi',worlds[self.geometry_ids[:,None],nodes,:3,:],skin.points[vertices],skin.weights[vertices])
            p,r=self.actor['placement'];points=points@r.T+p
            gaps.append(points@np.asarray(plane['normal_world'])-plane['offset_m']+self.policy['limits']['penetration_m'])
        return np.concatenate(gaps)

    def linearize(self,value,worlds,trust,*,step=.001,maximum_nonzeros=60000000):
        self.check()
        value=np.asarray(value,float);base=self.rows(value,worlds);gaps,witnesses=self.floor(worlds)
        proxy_world=self.worlds(value,quantized=False);proxy=self.rows(value,proxy_world);proxy_gaps=self.witness_gaps(proxy_world,witnesses)
        np.testing.assert_array_equal(base.caps,proxy.caps);np.testing.assert_array_equal(base.scales,proxy.scales)
        data=[];indices=[];pointers=[0];gdata=[];gindices=[];gpointers=[0]
        require(type(step) in (int,float) and np.isfinite(step) and 1e-6<=step<=.01,'Bounded interval finite-difference step required')
        for column in range(self.size):
            h=step if self.upper[column]-value[column]>=value[column]-self.lower[column] else -step
            h=np.copysign(min(abs(h),self.upper[column]-value[column] if h>0 else value[column]-self.lower[column]),h)
            require(h!=0,'No finite-difference room');other=value.copy();other[column]+=h;w=self.worlds(other,quantized=False);rows=self.rows(other,w)
            np.testing.assert_array_equal(rows.caps,base.caps);np.testing.assert_array_equal(rows.scales,base.scales)
            derivative=((rows.vectors-proxy.vectors)/h).ravel();ids=np.flatnonzero(derivative);gd=(self.witness_gaps(w,witnesses)-proxy_gaps)/h;gids=np.flatnonzero(gd)
            require(pointers[-1]+len(ids)+gpointers[-1]+len(gids)<=maximum_nonzeros,'Complete interval Jacobian exceeds resource budget; no entries dropped')
            data.extend(derivative[ids]);indices.extend(ids);pointers.append(len(data));gdata.extend(gd[gids]);gindices.extend(gids);gpointers.append(len(gdata))
        jac=sparse.csc_matrix((data,indices,pointers),shape=(base.vectors.size,self.size));gjac=sparse.csc_matrix((gdata,gindices,gpointers),shape=(len(gaps),self.size))
        floors,fjac,identity=lift(gaps,gjac,value,self.lower,self.upper,trust,clearance=0.,scale=max(self.policy['limits']['penetration_m'],.001))
        # Every original rate and sampled floor row receives a separate hard
        # no-worsening bound. Original caps remain in the minimax soft suffix.
        start=self.edit_count;rate_ids=np.arange(start,len(base.caps));order=np.r_[np.arange(start),rate_ids,rate_ids]
        cap=base.caps[order].copy();cap[start:start+len(rate_ids)]=np.maximum(base.caps[rate_ids],np.linalg.norm(base.vectors[rate_ids],axis=1))
        vector=base.vectors[order];scale=base.scales[order];derivative=jac[(3*order[:,None]+np.arange(3)).ravel()]
        protected_floor=np.maximum(floors.caps,np.linalg.norm(floors.vectors,axis=1))
        # Insert protected planes before the soft original-rate suffix.
        hard=start+len(rate_ids)
        system=NormRows(np.r_[vector[:hard],floors.vectors,vector[hard:],floors.vectors],np.r_[cap[:hard],protected_floor,cap[hard:],floors.caps],np.r_[scale[:hard],floors.scales,scale[hard:],floors.scales])
        derivative=sparse.vstack([derivative[:3*hard],fjac,derivative[3*hard:],fjac],format='csc')
        self.check()
        return system,derivative,dict(hard_rows=hard+len(gaps),edit_rows=start,original_rate_rows=len(rate_ids),complete_floor_rows=len(gaps),
            sparse_nonzeros=derivative.nnz,controls=self.size,witnesses=witnesses.tolist(),conversion=identity,difference_step=step,
            original_caps_unchanged=True,scope='Decoded vector/gap anchoring, continuous differences and full rowwise no-worsening protection. Rebuilt full minima and independently decoded geometry remain necessary.')

    def export(self,value,path):
        return encode(self.rig,self.actor['animation_index'],self.nodes,self.channels,self.controls(value),self.degrees,path)
