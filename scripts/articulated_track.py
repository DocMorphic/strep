"""Explicit bounded local-rotation/root edits on a complete supplied clock.

This authors controls, not anatomy or feasible motion. The caller uses its rig's
FK and retains independent raw/saved contact, geometry and motion gates.
"""
import torch


class ArticulatedTrack:
    def __init__(self,local_rotations,root_positions,basis,joints,rotation_limits_radians,*,fixed_frames,maximum_root_translation_m=0.,root_basis=None,root_fixed_frames=None):
        tensors=[local_rotations,root_positions,basis,rotation_limits_radians]
        if (any(not isinstance(v,torch.Tensor) or v.dtype not in (torch.float32,torch.float64) for v in tensors)
                or any(v.dtype!=local_rotations.dtype or v.device!=local_rotations.device or not torch.isfinite(v).all() for v in tensors)):
            raise ValueError('Finite same-device/dtype floating source, basis and limits required')
        if local_rotations.ndim!=4 or local_rotations.shape[-2:]!=(3,3):raise ValueError('Complete frame/joint local rotation matrices required')
        frames,count=local_rotations.shape[:2]
        if not 3<=frames<=300 or not 1<=count<=256 or root_positions.shape!=(frames,3) or root_positions.abs().max()>1e4:
            raise ValueError('Bounded complete source clock and root track required')
        if basis.ndim!=2 or basis.shape[0]!=frames or not 1<=basis.shape[1]<=8 or torch.any(basis<0) or torch.any(basis.sum(1)>1) or torch.any(basis.abs().sum(0)==0):
            raise ValueError('Complete nonempty convex temporal basis with1-8 columns required; no clipping')
        if (not isinstance(joints,(list,tuple)) or not 1<=len(joints)<=16 or any(type(j) is not int or not 0<=j<count for j in joints)
                or len(set(joints))!=len(joints) or rotation_limits_radians.shape!=(len(joints),)
                or torch.any(rotation_limits_radians<=0) or torch.any(rotation_limits_radians>torch.pi/2)):
            raise ValueError('Explicit distinct supplied-rig joints and rotation budgets up to90degrees required')
        if (not isinstance(fixed_frames,torch.Tensor) or fixed_frames.dtype!=torch.bool or fixed_frames.device!=basis.device
                or fixed_frames.shape!=(frames,) or torch.any(basis[fixed_frames]!=0)):
            raise ValueError('Every declared protected frame must have exactly zero temporal support')
        if type(maximum_root_translation_m) not in (int,float) or not 0<=maximum_root_translation_m<=.22:
            raise ValueError('Explicit finite root edit budget up to22cm required')
        if maximum_root_translation_m==0 and (root_basis is not None or root_fixed_frames is not None):raise ValueError('Disabled root cannot receive an unused temporal permission')
        root_basis=basis if root_basis is None else root_basis;root_fixed_frames=fixed_frames if root_fixed_frames is None else root_fixed_frames
        if (not isinstance(root_basis,torch.Tensor) or root_basis.shape!=basis.shape or root_basis.dtype!=basis.dtype or root_basis.device!=basis.device
                or not torch.isfinite(root_basis).all() or torch.any(root_basis<0) or torch.any(root_basis.sum(1)>1) or torch.any(root_basis.sum(0)==0)):
            raise ValueError('Explicit complete convex root basis on the original clock required')
        if (not isinstance(root_fixed_frames,torch.Tensor) or root_fixed_frames.dtype!=torch.bool or root_fixed_frames.device!=basis.device
                or root_fixed_frames.shape!=(frames,) or torch.any(root_basis[root_fixed_frames]!=0)):
            raise ValueError('Root temporal support must preserve its explicitly declared protected frames')
        eye=torch.eye(3,dtype=local_rotations.dtype,device=local_rotations.device)
        if (local_rotations.mT@local_rotations-eye).abs().max()>1e-4 or (torch.linalg.det(local_rotations)-1).abs().max()>1e-4:
            raise ValueError('Source local rotations must already be consistent with SO3; no repair inferred')
        self._local=local_rotations.detach().clone();self._root=root_positions.detach().clone();self._basis=basis.detach().clone()
        self._limits=rotation_limits_radians.detach().clone();self._fixed=fixed_frames.detach().clone();self.joints=tuple(joints)
        self._root_basis=root_basis.detach().clone();self._root_fixed=root_fixed_frames.detach().clone()
        self.maximum_root_translation_m=float(maximum_root_translation_m);self.groups=len(joints)+(maximum_root_translation_m>0)
        self.shape=(basis.shape[1],self.groups,3);self.size=basis.shape[1]*self.groups*3;self.frames=frames;self._lookup={j:i for i,j in enumerate(joints)}

    def _controls(self,controls):
        if (not isinstance(controls,torch.Tensor) or controls.dtype!=self._local.dtype or controls.device!=self._local.device
                or controls.shape!=(self.size,) or not torch.isfinite(controls).all() or controls.abs().max()>2):
            raise ValueError('Complete bounded normalized control vector on the source dtype/device required')
        return controls.reshape(self.shape)

    def vectors(self,controls):
        control=self._controls(controls);values=torch.einsum('fk,kgc->fgc',self._basis,control)
        if self.maximum_root_translation_m>0:
            root=torch.einsum('fk,kc->fc',self._root_basis,control[:,-1]);values=torch.cat([values[:,:-1],root[:,None]],1)
        return values

    def assess(self,controls):
        raw=self._controls(controls);values=self.vectors(controls)
        knots=torch.linalg.vector_norm(raw,dim=-1);frames=torch.linalg.vector_norm(values,dim=-1)
        return dict(all_declared_bounds_pass=bool(torch.all(frames<=1)),all_knot_balls_pass=bool(torch.all(knots<=1)),
            maximum_frame_normalized_norm=float(frames.max().detach()),maximum_knot_normalized_norm=float(knots.max().detach()),
            frames=self.frames,protected_frames=int(self._fixed.sum()),root_protected_frames=self.frames if self.maximum_root_translation_m==0 else int(self._root_fixed.sum()),complete_frame_group_vectors=values.numel()//3,
            added_physical_tolerance=0.,quality_approved=False,release_approved=False)

    def __call__(self,controls):
        values=self.vectors(controls)
        if torch.any(torch.linalg.vector_norm(values,dim=-1)>1):raise ValueError('Declared per-frame vector edit budget exceeded; no normalization or clipping')
        vector=values[:,:len(self.joints)]*self._limits[None,:,None];x,y,z=vector.unbind(-1);zero=torch.zeros_like(x)
        skew=torch.stack([zero,-z,y,z,zero,-x,-y,x,zero],-1).reshape(*vector.shape[:-1],3,3)
        delta=torch.matrix_exp(skew);local=torch.stack([self._local[:,j] if j not in self._lookup else self._local[:,j]@delta[:,self._lookup[j]] for j in range(self._local.shape[1])],1)
        local=torch.where(self._fixed[:,None,None,None],self._local,local)
        root=self._root if self.maximum_root_translation_m==0 else self._root+values[:,-1]*self.maximum_root_translation_m
        root=torch.where(self._root_fixed[:,None],self._root,root)
        return local,root
