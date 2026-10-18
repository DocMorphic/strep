"""Complete authored primitive/contact energy and metric observations.

Native SOMA scene wiring and sampled vertex metrics; full mesh/partner,
continuous collision, physics, semantic and human gates remain separate.
"""
import torch
from object_geometry import Geometry
from linear_skin_operator import LinearSkinOperator


class AuthoredSkinSceneEnergy:
    def __init__(self,decode,skin,plan,*,frame_chunk=4):
        if (not callable(decode) or not isinstance(skin,LinearSkinOperator) or plan.get('schema')!='strep-authored-scene-guidance-v1'
                or plan.get('vertices')!=skin.operator.shape[0] or len(plan.get('joint_names',[]))!=skin.joint_count
                or type(frame_chunk) is not int or not 1<=frame_chunk<=16 or type(plan.get('frames')) is not int or not 3<=plan['frames']<=300
                or len(plan['primitives'])>16 or len(plan['contacts'])>64):
            raise ValueError('Complete bounded compiled scene, decoder and exact native skin required')
        self.decode=decode;self.skin=skin;self.frames=plan['frames'];self.chunk=frame_chunk;self.objects=[];self.contacts=[]
        def fixed(value,shape):
            v=torch.tensor(value,dtype=skin.operator.dtype,device=skin.operator.device)
            if v.shape!=shape or not torch.isfinite(v).all():raise ValueError('Complete finite compiled track required')
            return v
        self.floor=(fixed(plan['floor_normal'],(3,)),float(plan['floor_offset_m']))
        if abs(float(torch.linalg.vector_norm(self.floor[0]))-1)>1e-5:raise ValueError('Unit floor normal required')
        for obj in plan['primitives']:
            geometry=Geometry.parse(obj['geometry']);p=fixed(obj['positions_m'],(self.frames,3));r=fixed(obj['rotations'],(self.frames,3,3))
            if (r.mT@r-torch.eye(3,device=r.device,dtype=r.dtype)).abs().max()>1e-5 or (torch.linalg.det(r)-1).abs().max()>1e-5:raise ValueError('Proper complete primitive rotations required')
            self.objects.append((geometry,p,r))
        for c in plan['contacts']:
            a,b=c['start_frame'],c['end_frame'];vertex=c['vertex']
            if type(a) is not int or type(b) is not int or not 0<=a<=b<self.frames or type(vertex) is not int or not 0<=vertex<skin.operator.shape[0]:raise ValueError('Complete contact interval and exact vertex required')
            item=dict(a=a,b=b,vertex=vertex,targets=fixed(c['targets_m'],(b-a+1,3)))
            if 'normal_directions' in c:
                normal=fixed(c['normal_directions'],(b-a+1,3));faces=torch.tensor(c['normal_faces'],device=skin.operator.device)
                if (torch.linalg.vector_norm(normal,dim=-1)-1).abs().max()>1e-5 or faces.dtype!=torch.long or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces) or faces.min()<0 or faces.max()>=skin.operator.shape[0]:raise ValueError('Unit normals and complete adjacent triangle identities required')
                item.update(normal=normal,faces=faces)
            if 'tangent_directions' in c:
                tangent=fixed(c['tangent_directions'],(b-a+1,3));hand=c['hand_joint'];knuckles=c['knuckle_joints']
                if 'normal' not in item or (torch.linalg.vector_norm(tangent,dim=-1)-1).abs().max()>1e-5 or type(hand) is not int or not 0<=hand<skin.joint_count or len(knuckles)!=4 or any(type(k) is not int or not 0<=k<skin.joint_count for k in knuckles):raise ValueError('Complete hand tangent mapping required')
                item.update(tangent=tangent,hand=hand,knuckles=knuckles)
            self.contacts.append(item)

    def motion(self,features):
        if features.ndim!=3 or features.shape[:2]!=(1,self.frames) or features.dtype!=self.skin.operator.dtype or features.device!=self.skin.operator.device:raise ValueError('One complete matching actor feature clock required')
        motion=self.decode(features);r=motion['global_rot_mats'];p=motion['posed_joints']
        if r.shape!=(1,self.frames,self.skin.joint_count,3,3) or p.shape!=(1,self.frames,self.skin.joint_count,3):raise ValueError('Exact complete decoded skin skeleton required')
        return r[0],p[0]

    @staticmethod
    def depth(v,geometry,p,r):
        local=torch.einsum('fvi,fij->fvj',v-p[:,None,:],r)
        if geometry.shape=='box':return torch.relu((v.new_tensor(geometry.dimensions)/2-local.abs()).amin(-1))
        if geometry.shape=='sphere':return torch.relu(geometry.dimensions[0]-torch.linalg.vector_norm(local,dim=-1))
        q=torch.stack([torch.linalg.vector_norm(local[...,[0,2]],dim=-1)-geometry.dimensions[0],local[...,1].abs()-geometry.dimensions[1]/2],-1)
        return torch.relu(-torch.linalg.vector_norm(torch.relu(q),dim=-1)-torch.minimum(q.amax(-1),q.new_tensor(0.)))

    def contact_rows(self,v,r,p,c,start,stop):
        a=max(start,c['a']);b=min(stop,c['b']+1)
        if a>=b:return None
        interval=slice(a-start,b-start);target_slice=slice(a-c['a'],b-c['a']);position=torch.linalg.vector_norm(v[interval,c['vertex']]-c['targets'][target_slice],dim=-1)
        result=dict(position=position)
        if 'normal' in c:
            # Match the source normal convention: remove the root translation
            # before LBS so rounded weight sums do not perturb tiny triangles.
            centered=self.skin(r[interval],p[interval]-p[interval,:1]);tri=centered[:,c['faces']]
            normal=torch.cross(tri[:,:,1]-tri[:,:,0],tri[:,:,2]-tri[:,:,0],dim=-1).sum(1);length=torch.linalg.vector_norm(normal,dim=-1);normal=normal/length.clamp_min(1e-12)[:,None]
            result.update(normal=(1-(normal*c['normal'][target_slice]).sum(-1).clamp(-1,1)),normal_degenerate=(length<1e-12).to(v.dtype))
            if 'tangent' in c:
                tangent=p[interval][:,c['knuckles']].mean(1)-p[interval,c['hand']];tangent=tangent-normal*(tangent*normal).sum(-1,keepdim=True)
                length=torch.linalg.vector_norm(tangent,dim=-1);tangent=tangent/length.clamp_min(1e-12)[:,None]
                result.update(tangent=1-(tangent*c['tangent'][target_slice]).sum(-1).clamp(-1,1),tangent_degenerate=(length<1e-12).to(v.dtype))
        return result

    def __call__(self,features):
        from torch.utils.checkpoint import checkpoint
        r,p=self.motion(features);total=features.sum()*0;count=self.frames*self.skin.operator.shape[0]
        for start in range(0,self.frames,self.chunk):
            stop=min(start+self.chunk,self.frames)
            def energy(rot,pos,start=start,stop=stop):
                v=self.skin(rot,pos);value=torch.relu(self.floor[1]-v@self.floor[0]).square().sum()/count
                for geometry,op,orr in self.objects:value=value+self.depth(v,geometry,op[start:stop],orr[start:stop]).square().sum()/count
                for c in self.contacts:
                    rows=self.contact_rows(v,rot,pos,c,start,stop)
                    if rows is not None:
                        length=c['b']-c['a']+1;value=value+rows['position'].square().sum()/length
                        for name in ['normal','tangent']:
                            if name in rows:value=value+rows[name].square().sum()/length
                return value
            total=total+checkpoint(energy,r[start:stop],p[start:stop],use_reentrant=False,preserve_rng_state=False)
        return total

    def metrics(self,features):
        with torch.no_grad():
            r,p=self.motion(features);floor=[];objects=[[] for _ in self.objects];contact=[{} for _ in self.contacts];speed=[];acceleration=[];previous=None
            for start in range(0,self.frames,self.chunk):
                stop=min(start+self.chunk,self.frames);v=self.skin(r[start:stop],p[start:stop]);depth=torch.relu(self.floor[1]-v@self.floor[0])
                floor.append(torch.stack([depth.amax(-1),(depth>0).sum(-1),depth.square().sum(-1)],0))
                for i,(geometry,op,orr) in enumerate(self.objects):
                    d=self.depth(v,geometry,op[start:stop],orr[start:stop]);objects[i].append(torch.stack([d.amax(-1),(d>0).sum(-1),d.square().sum(-1)],0))
                for i,c in enumerate(self.contacts):
                    rows=self.contact_rows(v,r[start:stop],p[start:stop],c,start,stop)
                    if rows is not None:
                        for name,value in rows.items():contact[i].setdefault(name,[]).append(value)
                track=v if previous is None else torch.cat([previous,v],0)
                velocity=torch.linalg.vector_norm(torch.diff(track,dim=0)*30,dim=-1).amax(-1)
                speed.append(velocity if previous is None else velocity[-len(v):])
                acc=torch.linalg.vector_norm(torch.diff(track,n=2,dim=0)*900,dim=-1).amax(-1)
                if len(acc):acceleration.append(acc)
                previous=track[-2:]
            result={'floor':torch.cat(floor,1),'skin_speed_m_s':torch.cat(speed),'skin_acceleration_m_s2':torch.cat(acceleration),
                'joint_speed_m_s':torch.linalg.vector_norm(torch.diff(p,dim=0)*30,dim=-1).amax(-1),
                'joint_acceleration_m_s2':torch.linalg.vector_norm(torch.diff(p,n=2,dim=0)*900,dim=-1).amax(-1)}
            if objects:result['objects']=torch.stack([torch.cat(items,1) for items in objects])
            # Contact rows stay in declaration order, each complete interval in
            # increasing frame order, independent of activation chunk size.
            for name in ['position','normal','tangent','normal_degenerate','tangent_degenerate']:
                values=[torch.cat(c[name]) for c in contact if name in c]
                if values:result['contact_'+name]=torch.cat(values)
            return {name:value.detach().cpu().numpy().copy() for name,value in result.items()}
