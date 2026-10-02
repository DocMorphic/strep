"""Baked-TRS playback floor constraints and continuous witness derivatives.

Values model float32 export; derivatives use continuous pre-export channels.
Finite clocks, lowest-vertex branches and finite differences are not proofs.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from gltf_tools import local_matrix
from mesh_contact_clock import layout,validate_clock,validate_overrides


class MeshPlaybackFloor:
    def __init__(self,coupled,hz=120,contact_clock='authored-keys',contact_clock_overrides=None):
        self.contact_clock=validate_clock(contact_clock)
        self.coupled=coupled;self.f=coupled.fitter
        f=self.f;self.animated=sorted({c['target']['node'] for c in f.rig.document['animations'][0]['channels']}|set(f.nodes)|{f.spec['root_node']})
        self.reference=np.array([local_matrix(n) for n in f.rig.document['nodes']])
        self.clock=np.arange(len(f.values),dtype=np.float32)/30
        self.times=np.unique(np.concatenate([np.arange(int(np.floor(float(self.clock[-1])*hz))+1,dtype=float)/hz,
            self.clock.astype(float),(self.clock[:-1].astype(float)+self.clock[1:].astype(float))/2]))
        self.left=np.clip(np.searchsorted(self.clock,self.times,side='right')-1,0,len(self.clock)-2)
        self.right=self.left+1
        self.u=(self.times-self.clock[self.left].astype(float))/(self.clock[self.right]-self.clock[self.left]).astype(float)
        self.u[self.times>=self.clock[-1]]=1.
        width=max(nodes.shape[1] for nodes,points,weights in f.skin.parts)
        nodes=[];points=[];weights=[]
        for n,p,w in f.skin.parts:
            pad=width-n.shape[1]
            nodes.append(np.pad(n,((0,0),(0,pad))))
            points.append(np.pad(p,((0,0),(0,pad),(0,0))))
            weights.append(np.pad(w,((0,0),(0,pad))))
        self.nodes=np.concatenate(nodes);self.points=np.concatenate(points);self.weights=np.concatenate(weights)
        self.contact_clock_overrides=validate_overrides(contact_clock_overrides,len(f.spec['contacts']))
        self.contact_times,self.contact_groups=layout(f.spec,self.times,self.contact_clock,self.contact_clock_overrides)
        self.contact_indices=np.searchsorted(self.times,self.contact_times)
        if np.any(self.contact_indices>=len(self.times)) or not np.array_equal(self.times[self.contact_indices],self.contact_times):
            raise ValueError('Contact keys must belong to playback clock')
        self.bindings=np.zeros((len(f.spec['contacts']),len(f.order),4))
        for index,target in enumerate(f.spec['contacts']):
            ids=f.spec['patches'][target['patch']]['vertices']
            np.add.at(self.bindings[index],self.nodes[ids].ravel(),
                (self.points[ids]*self.weights[ids,:,None]/len(ids)).reshape(-1,4))
        self.targets=np.array([target['target_position_m'] for target in f.spec['contacts']])[self.contact_groups]
        self.direction=np.zeros(coupled.shape);self.direction[:,1]=1.;self.direction=self.direction.ravel()
        self.cached=None;self.data=None;self.cached_pair=None;self.cached_pair_step=None
        self.cached_contacts=None;self.cached_contact_pair=None;self.cached_contact_step=None

    def channels(self,values,quantized):
        """Batch the original world-root edit, then the encoder's localization."""
        f=self.f;shape=values.shape[:-1];local=np.broadcast_to(f.local.reshape((len(f.local),)+(1,)*(len(shape)-1)+f.local.shape[1:]),shape+f.local.shape[1:]).copy()
        delta=Rotation.from_rotvec(values[...,3:].reshape(-1,3)).as_matrix().reshape(shape+(len(f.nodes),3,3))
        local[...,f.nodes,:3,:3]=local[...,f.nodes,:3,:3]@delta
        world=np.empty_like(local)
        for node in f.order:
            parent=f.rig.parents[node]
            pw=np.broadcast_to(np.eye(4),shape+(4,4)) if parent<0 else world[...,parent,:,:]
            if node==f.spec['root_node']:
                local[...,node,:3,3]+=np.linalg.solve(pw[...,:3,:3],values[...,:3,None])[...,0]
            world[...,node,:,:]=pw@local[...,node,:,:]
        # Match encode/localize, including numerical localization of edited bones.
        local=world.copy()
        for node,parent in enumerate(f.rig.parents):
            if parent>=0:local[...,node,:,:]=np.linalg.inv(world[...,parent,:,:])@world[...,node,:,:]
        selected=np.take(local,self.animated,axis=-3)
        t=selected[...,:3,3]
        q=Rotation.from_matrix(selected[...,:3,:3].reshape(-1,3,3)).as_quat().reshape(shape+(len(self.animated),4))
        if quantized:t=t.astype(np.float32).astype(float);q=q.astype(np.float32).astype(float)
        return t,q

    def interpolate(self,lt,lq,rt,rq,u):
        shape=lt.shape[:-2];u=np.asarray(u).reshape((len(u),)+(1,)*(len(shape)-1)+(1,1))
        a=lq/np.linalg.norm(lq,axis=-1,keepdims=True);b=rq/np.linalg.norm(rq,axis=-1,keepdims=True)
        dot=np.sum(a*b,axis=-1,keepdims=True);b=b*np.where(dot<0,-1.,1.)
        angle=np.arccos(np.clip(np.abs(dot),0,1));small=angle<1e-6
        denom=np.where(small,1.,np.sin(angle))
        q=np.where(small,(1-u)*a+u*b,(np.sin((1-u)*angle)*a+np.sin(u*angle)*b)/denom)
        q/=np.linalg.norm(q,axis=-1,keepdims=True)
        local=np.broadcast_to(self.reference,shape+self.reference.shape).copy()
        translations=(1-u)*lt+u*rt
        rotations=Rotation.from_quat(q.reshape(-1,4)).as_matrix().reshape(shape+(len(self.animated),3,3))
        for index,node in enumerate(self.animated):
            local[...,node,:3,3]=translations[...,index,:]
            local[...,node,:3,:3]=rotations[...,index,:,:]
        world=np.empty_like(local)
        for node in self.f.order:
            parent=self.f.rig.parents[node]
            world[...,node,:,:]=local[...,node,:,:] if parent<0 else world[...,parent,:,:]@local[...,node,:,:]
        return world

    def heights(self,t,q):
        output=[]
        for start in range(0,len(self.times),32):
            sl=slice(start,start+32);a,b=self.left[sl],self.right[sl]
            world=self.interpolate(t[a],q[a],t[b],q[b],self.u[sl])
            output.append(np.einsum('svki,vki,vk->sv',world[:,self.nodes,1,:],self.points,self.weights))
        return np.concatenate(output)

    def evaluate(self,controls):
        if self.cached is None or not np.array_equal(controls,self.cached):
            values=self.coupled.parameters(controls);t,q=self.channels(values,True);height=self.heights(t,q)
            ids=np.argmin(height,axis=1);floor=1+height[np.arange(len(ids)),ids]/self.f.spec['screen']['floor_depth_m']
            self.data=(values,height,ids,floor);self.cached=np.asarray(controls).copy();self.cached_pair=None
            self.cached_contacts=None;self.cached_contact_pair=None
        return self.data

    def values(self,controls):return self.evaluate(controls)[3]

    def pair(self,controls,step=1e-5):
        if not np.isfinite(step) or step<=0:raise ValueError('Positive finite derivative step required')
        if self.cached is not None and np.array_equal(controls,self.cached) and self.cached_pair is not None and step==self.cached_pair_step:return self.cached_pair
        values,height,ids,floor=self.evaluate(controls);dim=values.shape[1]
        offset=np.concatenate([np.eye(dim)*step,-np.eye(dim)*step])
        pt,pq=self.channels(values[:,None,:]+offset[None,:,:],False)
        base_t,base_q=self.channels(values,False);derivatives=[]
        for side in ('left','right'):
            rows=[]
            for start in range(0,len(ids),16):
                sl=slice(start,start+16);a,b=self.left[sl],self.right[sl];witness=ids[sl]
                lt,lq,rt,rq=(pt[a],pq[a],base_t[b,None],base_q[b,None]) if side=='left' else (base_t[a,None],base_q[a,None],pt[b],pq[b])
                # Broadcast the unchanged endpoint across all signed perturbations.
                lt,rt=np.broadcast_arrays(lt,rt);lq,rq=np.broadcast_arrays(lq,rq)
                world=self.interpolate(lt,lq,rt,rq,self.u[sl])
                selected=world[np.arange(len(witness))[:,None,None],np.arange(2*dim)[None,:,None],self.nodes[witness,None,:],1,:]
                y=np.einsum('sdkj,skj,sk->sd',selected,self.points[witness],self.weights[witness])
                rows.append((y[:,:dim]-y[:,dim:])/(2*step*self.f.spec['screen']['floor_depth_m']))
            derivatives.append(np.concatenate(rows))
        jac=(self.coupled.basis[self.left,:,None]*derivatives[0][:,None,:]+
             self.coupled.basis[self.right,:,None]*derivatives[1][:,None,:]).reshape(len(ids),-1)
        self.cached_pair=(floor,jac)
        self.cached_pair_step=step
        return self.cached_pair

    def contact_points(self,t,q):
        points=[]
        for start in range(0,len(self.contact_times),32):
            sl=slice(start,start+32);samples=self.contact_indices[sl];a,b=self.left[samples],self.right[samples]
            world=self.interpolate(t[a],q[a],t[b],q[b],self.u[samples])
            points.append(np.einsum('snij,snj->si',world[:,:,:3,:],self.bindings[self.contact_groups[sl]]))
        return np.concatenate(points)

    def contact_values(self,controls):
        values=self.evaluate(controls)[0]
        if self.cached_contacts is None:
            t,q=self.channels(values,True);points=self.contact_points(t,q)
            self.cached_contacts=1-np.linalg.norm(points-self.targets,axis=1)/self.f.spec['screen']['contact_error_m']
        return self.cached_contacts

    def contact_pair(self,controls,step=1e-5):
        if not np.isfinite(step) or step<=0:raise ValueError('Positive finite derivative step required')
        contacts=self.contact_values(controls)
        if self.cached_contact_pair is not None and step==self.cached_contact_step:return self.cached_contact_pair
        values=self.data[0];dim=values.shape[1];offset=np.concatenate([np.eye(dim)*step,-np.eye(dim)*step])
        pt,pq=self.channels(values[:,None,:]+offset[None,:,:],False);t,q=self.channels(values,False)
        delta=self.contact_points(t,q)-self.targets;length=np.linalg.norm(delta,axis=1)
        direction=np.divide(-delta,length[:,None],out=np.zeros_like(delta),where=length[:,None]>1e-12)/self.f.spec['screen']['contact_error_m']
        derivatives=[]
        for side in ('left','right'):
            rows=[]
            for start in range(0,len(contacts),16):
                sl=slice(start,start+16);samples=self.contact_indices[sl];a,b=self.left[samples],self.right[samples]
                lt,lq,rt,rq=(pt[a],pq[a],t[b,None],q[b,None]) if side=='left' else (t[a,None],q[a,None],pt[b],pq[b])
                lt,rt=np.broadcast_arrays(lt,rt);lq,rq=np.broadcast_arrays(lq,rq)
                world=self.interpolate(lt,lq,rt,rq,self.u[samples])
                points=np.einsum('sdnij,snj->sdi',world[:,:,:,:3,:],self.bindings[self.contact_groups[sl]])
                derivative=(points[:,:dim]-points[:,dim:])/(2*step)
                rows.append(np.einsum('sdi,si->sd',derivative,direction[sl]))
            derivatives.append(np.concatenate(rows))
        a,b=self.left[self.contact_indices],self.right[self.contact_indices]
        jac=(self.coupled.basis[a,:,None]*derivatives[0][:,None,:]+self.coupled.basis[b,:,None]*derivatives[1][:,None,:]).reshape(len(contacts),-1)
        self.cached_contact_pair=(contacts,jac);self.cached_contact_step=step
        return self.cached_contact_pair

    def lift(self,controls,margin):
        values,height,_,floor=self.evaluate(controls);allowed=-self.f.spec['screen']['floor_depth_m']*(1-margin)
        bad=height<allowed
        if not np.any(bad):return None
        t,q=self.channels(values,False);base=self.heights(t,q)
        lifted=self.coupled.parameters(controls+self.direction)
        t,q=self.channels(lifted,False);slope=(self.heights(t,q)-base)[bad]
        if np.any(slope<=1e-10):return None
        # Verification after lifting remains mandatory; leave float32 roundoff room.
        return float(((allowed-height[bad])/slope).max())+2e-7
