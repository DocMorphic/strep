"""Decoded SOMA skin energy for experimental clean-prediction guidance.

Every supplied frame/vertex/object is evaluated. Convex half-space interiors
provide a penetration surrogate, not exact mesh distance or collision approval.
"""
import torch
from linear_skin_operator import LinearSkinOperator


class SkinSceneEnergy:
    def __init__(self,decode,skin,*,planes=(),convex_objects=(),contacts=(),frame_chunk=4):
        if not callable(decode) or not isinstance(skin,LinearSkinOperator) or type(frame_chunk) is not int or not 1<=frame_chunk<=16:
            raise ValueError('Explicit decoder, complete sparse skin and bounded frame chunk required')
        if not planes and not convex_objects and not contacts:raise ValueError('An explicit nonempty scene energy required')
        if len(planes)>16 or len(convex_objects)>16 or len(contacts)>64:raise ValueError('Complete scene term budget exceeded; split explicitly, never drop terms')
        self.decode=decode;self.skin=skin;self.frame_chunk=frame_chunk
        self.planes=[];self.objects=[];self.contacts=[]
        def frozen(value,shape,label):
            if (not isinstance(value,torch.Tensor) or tuple(value.shape)!=shape or value.requires_grad
                    or value.dtype!=skin.operator.dtype or value.device!=skin.operator.device or not torch.isfinite(value).all()):
                raise ValueError('Frozen matching '+label+' required')
            return value.detach().clone()
        for normal,offset in planes:
            normal=frozen(normal,(3,),'unit plane normal')
            if abs(float(torch.linalg.vector_norm(normal))-1)>1e-5 or type(offset) not in (int,float) or not -10000<=offset<=10000:raise ValueError('Finite unit plane and offset required')
            self.planes.append((normal,float(offset)))
        frames=None
        for normals,offsets in convex_objects:
            if not isinstance(normals,torch.Tensor) or normals.ndim!=3 or not 4<=normals.shape[1]<=128:raise ValueError('Complete frame/face convex plane tracks required')
            n,k,_=normals.shape;normals=frozen(normals,(n,k,3),'convex normals');offsets=frozen(offsets,(n,k),'convex offsets')
            if n<1 or (frames is not None and n!=frames) or torch.any(abs(torch.linalg.vector_norm(normals,dim=-1)-1)>1e-5):raise ValueError('Aligned complete unit-normal object clock required')
            frames=n;self.objects.append((normals,offsets))
        for ids,targets in contacts:
            if not isinstance(ids,torch.Tensor) or ids.dtype!=torch.long or ids.ndim!=1 or not len(ids) or ids.device!=skin.operator.device or ids.min()<0 or ids.max()>=skin.operator.shape[0] or len(torch.unique(ids))!=len(ids):raise ValueError('Distinct in-range contact vertex identities required')
            if not isinstance(targets,torch.Tensor) or targets.ndim!=3:raise ValueError('Complete contact target clock required')
            n=len(targets);targets=frozen(targets,(n,len(ids),3),'contact targets')
            if n<1 or (frames is not None and n!=frames):raise ValueError('Aligned complete contact clock required')
            frames=n;self.contacts.append((ids.detach().clone(),targets))
        self.frames=frames

    def __call__(self,features):
        from torch.utils.checkpoint import checkpoint
        if (features.ndim!=3 or len(features)!=1 or not 1<=features.shape[1]<=300
                or features.dtype!=self.skin.operator.dtype or features.device!=self.skin.operator.device
                or self.frames is not None and features.shape[1]!=self.frames):
            raise ValueError('One complete bounded scene actor clock and matching dtype/device required')
        motion=self.decode(features);r=motion['global_rot_mats'];p=motion['posed_joints'];n=features.shape[1]
        if r.shape!=(1,n,self.skin.joint_count,3,3) or p.shape!=(1,n,self.skin.joint_count,3):raise ValueError('Decoder must produce the complete matching skinned skeleton')
        total=features.sum()*0;vertices=self.skin.operator.shape[0]
        for start in range(0,n,self.frame_chunk):
            stop=min(start+self.frame_chunk,n)
            objects=tuple((a[start:stop],b[start:stop]) for a,b in self.objects)
            contacts=tuple((ids,target[start:stop]) for ids,target in self.contacts)
            def energy(rot,pos,objects=objects,contacts=contacts):
                v=self.skin(rot,pos);value=v.sum()*0
                for normal,offset in self.planes:value=value+torch.relu(offset-v@normal).square().sum()/(n*vertices)
                for normals,offsets in objects:
                    depth=torch.relu((offsets[:,None,:]-torch.einsum('fvi,fki->fvk',v,normals)).amin(-1))
                    value=value+depth.square().sum()/(n*vertices)
                for ids,target in contacts:value=value+(v[:,ids]-target).square().sum()/(n*len(ids))
                return value
            total=total+checkpoint(energy,r[0,start:stop],p[0,start:stop],use_reentrant=False,preserve_rng_state=False)
        return total
