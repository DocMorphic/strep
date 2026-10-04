"""Complete incident-surface contact rows with shared batched skinning.

Every face incident to an authored group and every influence on its required
vertices is retained. This contact cache is never a whole-body collision audit.
"""
import copy
import numpy as np
from native_contact_norms import ContactNorms
from native_scene_norms import NormRows


class CachedContactNorms(ContactNorms):
    def __init__(self, problem, policy, digest, *, maximum_rows=20000, maximum_cache_bytes=256*1024**2):
        super().__init__(problem,copy.deepcopy(policy),digest,maximum_rows=maximum_rows)
        if type(maximum_cache_bytes) is not int or not 1024 <= maximum_cache_bytes <= 1024**3:
            raise ValueError('Explicit complete contact cache budget from 1 KiB to 1 GiB required')
        self.maximum_cache_bytes = maximum_cache_bytes
        self.clock = problem.times.copy(); self.plans = []; groups = {n:{} for n in problem.scene.actors}
        self.required_times = {n:set() for n in problem.scene.actors}; self.logical_queries = 0; self.point_rows = 0
        def grouped(name,ids,reduction):
            selected = [ids] if reduction=='centroid' else [[int(i)] for i in ids]
            keys=[]
            for selected_ids in selected:
                key=tuple(int(i) for i in selected_ids);keys.append(key)
                if key not in groups[name]:
                    groups[name][key]=np.flatnonzero(np.isin(self.faces[name],key).any(1))
            return keys
        for data in problem.rows:
            entry=data['entry'];row=entry['authored'];target=row['target'];name=row['actor']
            left=grouped(name,entry['ids'],row['reduction']);right=None
            actors={name}
            if target['space']=='actor':
                right=grouped(target['actor'],entry['target_ids'],target['reduction']);actors.add(target['actor'])
            for actor in actors:self.required_times[actor].update(int(i) for i in data['ids'])
            self.logical_queries+=len(actors)*len(data['times']);self.point_rows+=len(left)*len(data['times'])
            self.plans.append(dict(data=data,clock=data['times'].copy(),indices=data['ids'].copy(),left=left,right=right))
        if not self.point_rows or 3*self.point_rows>maximum_rows:
            raise ValueError('Complete contact norms exceed row budget; no subset returned')
        if self.logical_queries>self.budget:
            raise ValueError('Complete contact proposal exceeds explicit pose budget')
        self.patches={};required_bytes=0;largest_temporary_frame=0
        for name,group in groups.items():
            if not group:continue
            faces=np.unique(np.concatenate(list(group.values())))
            vertices=np.unique(np.r_[self.faces[name][faces].ravel(),np.concatenate([np.asarray(k,int) for k in group])])
            indices=np.array(sorted(self.required_times[name]),int)
            mapped=np.searchsorted(vertices,self.faces[name][faces]);local_groups={}
            for key,incident in group.items():
                local_groups[key]=dict(vertices=np.searchsorted(vertices,key),faces=np.searchsorted(faces,incident))
            required_bytes+=len(indices)*(len(vertices)*3*8+len(group)*(3*8+1))
            influences=problem.scene.actors[name]['skin'].nodes.shape[1]
            largest_temporary_frame=max(largest_temporary_frame,len(vertices)*influences*12*8+len(mapped)*32*8
                +len(vertices)*3*8+len(problem.scene.actors[name]['rig'].parents)*16*8)
            self.patches[name]=dict(vertices=vertices,faces=faces,mapped=mapped,groups=local_groups,indices=indices)
        if required_bytes+largest_temporary_frame>maximum_cache_bytes:
            raise ValueError('Complete contact cache exceeds explicit byte budget; no subset returned')
        self.required_cache_bytes=required_bytes
        self.batch_frames=max(1,min(64,(maximum_cache_bytes-required_bytes)//max(largest_temporary_frame,1)))

    def sample(self, worlds):
        problem=self.problem;scene=problem.scene
        if set(worlds)!=set(scene.actors):raise ValueError('Complete actor pose dictionary required')
        if not np.array_equal(self.clock,problem.times):raise ValueError('Original complete contact clock changed')
        for plan in self.plans:
            data=plan['data']
            if not np.array_equal(plan['clock'],data['times']) or not np.array_equal(plan['indices'],data['ids']):
                raise ValueError('Original contact row clock or pose indices changed')
            if not np.array_equal(problem.times[data['ids']],data['times']):raise ValueError('Exact contact clock missing')
        for name,actor in scene.actors.items():
            value=np.asarray(worlds[name],float)
            if value.shape!=(len(problem.times),len(actor['rig'].parents),4,4) or not np.isfinite(value).all():
                raise ValueError('Complete finite native pose population required')
        cache={}
        for name,patch in self.patches.items():
            indices=patch['indices'];positions=np.empty((len(indices),len(patch['vertices']),3))
            directions={k:np.empty((len(indices),3)) for k in patch['groups']};valid={k:np.empty(len(indices),bool) for k in patch['groups']}
            for start in range(0,len(indices),self.batch_frames):
                stop=min(start+self.batch_frames,len(indices))
                v=problem.skin_points(name,patch['vertices'],worlds,indices[start:stop],'vertices');positions[start:stop]=v
                triangle=v[:,patch['mapped']];cross=np.cross(triangle[:,:,1]-triangle[:,:,0],triangle[:,:,2]-triangle[:,:,0]);area=np.linalg.norm(cross,axis=2)
                for key,group in patch['groups'].items():
                    ids=group['faces'];summed=cross[:,ids].sum(1);length=np.linalg.norm(summed,axis=1);total=area[:,ids].sum(1)
                    coherence=np.divide(length,total,out=np.zeros_like(length),where=total>0)
                    available=(len(ids)>0)&np.all(area[:,ids]>self.limits['minimum_normal_area_m2'],axis=1)&(length>self.limits['minimum_normal_area_m2'])&(coherence>=self.limits['minimum_normal_coherence'])
                    directions[key][start:stop]=np.divide(summed,length[:,None],out=np.zeros_like(summed),where=available[:,None])
                    valid[key][start:stop]=available
            cache[name]=dict(positions=positions,directions=directions,valid=valid)
        def oriented(name,keys,indices):
            patch=self.patches[name];selected=np.searchsorted(patch['indices'],indices);data=cache[name]
            if not np.array_equal(patch['indices'][selected],indices):raise ValueError('Complete actor contact cache clock missing')
            if any(not data['valid'][k][selected].all() for k in keys):raise ValueError('Unavailable contact normal cannot guide a proposal')
            points=np.stack([data['positions'][selected][:,patch['groups'][k]['vertices']].mean(1) for k in keys],axis=1)
            normals=np.stack([data['directions'][k][selected] for k in keys],axis=1)
            return points,normals
        vectors=[];sides=[];identity=[]
        for plan in self.plans:
            data=plan['data'];entry=data['entry'];row=entry['authored'];target=row['target'];clock=data['times'];indices=data['ids']
            left,na=oriented(row['actor'],plan['left'],indices)
            if target['space']=='actor':right,nb=oriented(target['actor'],plan['right'],indices)
            else:
                nb=np.asarray(self.policy['contacts'][row['id']]['target_normal']['normals'],float);right=entry['target_ids']
                if target['space']=='object':
                    p,r=scene.object_poses(target['object'],clock);right=np.einsum('fij,vj->fvi',r,right)+p[:,None];nb=np.einsum('fij,vj->fvi',r,nb)
                else:right=np.broadcast_to(right,left.shape);nb=np.broadcast_to(nb,na.shape)
            delta=right-left;vectors.append((na+nb).reshape(-1,3))
            sides.append(np.stack([np.einsum('fvi,fvi->fv',na,delta),np.einsum('fvi,fvi->fv',-nb,delta)],axis=2).ravel())
            identity.extend(dict(contact=row['id'],time_s=float(t),point=k) for t in clock for k in range(left.shape[1]))
        vectors=np.concatenate(vectors);gaps=np.concatenate(sides)+self.limits['backface_allowance_m']
        if not np.isfinite(np.r_[vectors.ravel(),gaps]).all():raise ValueError('Complete finite contact rows required')
        chord=2*np.sin(np.deg2rad(self.limits['maximum_opposition_error_degrees'])/2)
        rows=NormRows(vectors,np.full(len(vectors),chord),np.full(len(vectors),max(chord,.001)))
        scene.check_inputs()
        return rows,gaps,dict(identity=identity,actor_pose_queries=self.logical_queries,original_references_and_clocks=True,
            maximum_norm_rows=self.maximum_rows,orientation_cap_chord=float(chord),backface_allowance_m=self.limits['backface_allowance_m'],
            computed_actor_poses=sum(len(p['indices']) for p in self.patches.values()),maximum_cache_bytes=self.maximum_cache_bytes,
            required_cache_bytes=self.required_cache_bytes,batch_frames=self.batch_frames,
            complete_incident_populations={n:dict(source_vertices=len(scene.actors[n]['skin'].nodes),required_vertices=len(p['vertices']),
                source_faces=len(self.faces[n]),required_incident_faces=len(p['faces'])) for n,p in self.patches.items()},
            whole_body_geometry_checked=False,quality_approved=False,release_approved=False)
