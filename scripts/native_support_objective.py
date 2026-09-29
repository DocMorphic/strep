"""Optional augmented constraints matching native hand/foot support review.

Fixed reference patches are geometric contact candidates, not weight-bearing
annotations. No balance, force, anatomy or continuous-time claim is made.
"""
import math
import numpy as np
import torch
from floor_contact import Surface
from linear_skin_operator import LinearSkinOperator


class FixedPatchSupport:
    def __init__(self, reference, slide_allowance):
        a=np.asarray(reference,dtype=float)
        if a.ndim!=3 or a.shape[0]<2 or a.shape[1]<1 or a.shape[2]!=3 or not np.isfinite(a).all():
            raise ValueError('Finite native frame/vertex/XYZ reference required')
        if type(slide_allowance) not in (int,float) or not math.isfinite(slide_allowance) or slide_allowance<=0:
            raise ValueError('Positive finite slide allowance required')
        self.shape=a.shape
        heights=a[:,:,1].min(1)
        slow=np.linalg.norm(np.diff(a.mean(1)[:,[0,2]],axis=0),axis=1)*30<.35
        self.frames=np.flatnonzero((heights[:-1]<.03)&(heights[1:]<.03)&slow)
        self.patch=a[self.frames,:,1]<heights[self.frames,None]+.01
        self.enabled=len(self.frames)>=3
        self.allowances=(float(slide_allowance),.015)
        self.source=None;self.limits=None;self.last=None;self.peaks=None
        self.penalty=10.;self.multiplier=torch.zeros(2,dtype=torch.float64)
        if len(self.frames):
            values=self.measure(torch.tensor(a,dtype=torch.float64))
            self.source=values.detach().clone()
            self.limits=self.source+torch.tensor(self.allowances,dtype=torch.float64)

    def measure(self, vertices):
        if vertices.shape!=self.shape or vertices.dtype!=torch.float64 or vertices.device.type!='cpu' or not torch.isfinite(vertices).all():
            raise ValueError('Finite CPU float64 vertices matching reference required')
        if not len(self.frames):return vertices.sum()*0+torch.zeros(2,dtype=vertices.dtype)
        patch=torch.from_numpy(self.patch)
        a=vertices[self.frames];b=vertices[self.frames+1]
        speeds=torch.linalg.vector_norm((b-a)[...,[0,2]],dim=-1)*30
        slides=(speeds*patch).sum(1)/patch.sum(1)
        gaps=a[:,:,1].masked_fill(~patch,float('inf')).amin(1).clamp_min(0)
        return torch.stack([torch.quantile(slides,.95),torch.quantile(gaps,.95)])

    def loss(self, vertices):
        values=self.measure(vertices);self.peaks=values.detach()
        if not self.enabled:return values.sum()*0
        g=(values-self.limits)/torch.tensor(self.allowances,dtype=vertices.dtype)
        self.last=g.detach()
        return ((torch.relu(self.multiplier+self.penalty*g).square()-self.multiplier.square())/(2*self.penalty)).sum()

    def advance_stage(self,growth):
        if type(growth) not in (int,float) or not math.isfinite(growth) or growth<=0:
            raise ValueError('Positive finite penalty growth required')
        if not self.enabled:return
        if self.last is None:raise ValueError('Evaluate accepted support before updating multipliers')
        self.multiplier=torch.relu(self.multiplier+self.penalty*self.last);self.penalty*=growth

    def record(self):
        return dict(enabled=self.enabled,interval_frames=self.frames.tolist(),patch_sizes=self.patch.sum(1).tolist(),
                    source_p95=None if self.source is None else self.source.tolist(),
                    limits=None if self.limits is None else self.limits.tolist(),
                    candidate_p95=None if self.peaks is None else self.peaks.tolist(),
                    maximum_normalized_violations=None if self.last is None else self.last.relu().tolist(),
                    allowances=list(self.allowances),units=['m/s','m'],penalty=self.penalty)


class NativeSupportObjective:
    def __init__(self,references,skin):
        if not isinstance(references,dict) or not references or any(not isinstance(n,str) or not n for n in references):
            raise ValueError('Named native reference motions required')
        surface=Surface(skin)
        self.regions={name:np.asarray(ids) for name,ids in surface.regions.items()}
        selected=np.unique(np.concatenate(list(self.regions.values())))
        ids=surface.indices[selected];weights=surface.weights[selected]
        bind=np.einsum('vwij,vj->vwi',surface.inverse[ids],surface.points[selected])[...,:3]
        self.skin=LinearSkinOperator(torch.tensor(ids,dtype=torch.long),torch.tensor(weights,dtype=torch.float64),
                                    torch.tensor(bind,dtype=torch.float64),len(surface.inverse))
        self.groups={};self.frame_count=None
        for name,motion in references.items():
            rotations=np.asarray(motion['global_rot_mats']);positions=np.asarray(motion['posed_joints'])
            if rotations.ndim!=4 or rotations.shape[1:]!=(len(surface.inverse),3,3) or positions.shape!=rotations.shape[:2]+(3,) or not np.isfinite(rotations).all() or not np.isfinite(positions).all():
                raise ValueError('Matching finite native transforms required')
            if self.frame_count is not None and len(positions)!=self.frame_count:raise ValueError('Reference clocks differ')
            self.frame_count=len(positions)
            for region,vertices in self.regions.items():
                # Build masks with the independent review's NumPy skin path,
                # preserving strict low/slow comparisons and patch identities.
                source=np.array([surface.vertices(r,p,vertices) for r,p in zip(rotations,positions)])
                self.groups[(name,region)]=(np.searchsorted(selected,vertices),
                    FixedPatchSupport(source,.08 if region.endswith('Hand') else .02))

    def loss(self,rotations,positions):
        vertices=self.skin(rotations,positions)
        return sum(group.loss(vertices[:,ids]) for ids,group in self.groups.values())

    def advance_stage(self,growth):
        for _,group in self.groups.values():group.advance_stage(growth)

    def record(self):
        return dict(fps=30,groups=[dict(reference=name,region=region,**group.record()) for (name,region),(_,group) in self.groups.items()],
                    scope='Same fixed low/slow native hand/foot patches and p95 allowances as independent review, including outside authored intervals. '
                          'Augmented inequalities, not guaranteed feasibility or physical support. No export, balance or quality approval.')
