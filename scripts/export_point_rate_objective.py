"""Sampled per-material-point motion ceilings for authored stationary contacts.

Separate source ceilings cover approach, hold and release. These are augmented
inequalities, not guaranteed feasibility, force support or anatomical limits.
"""
import numpy as np
import torch
from contact_spec import validate
from support_contact import regions
from floor_contact import Surface
from linear_skin_operator import LinearSkinOperator
from export_motion_sampling import joint_trajectory, motion_rates


class ExportPointRateObjective:
    def __init__(self, rotations, positions, parents, skin, spec, window=None):
        frames=len(positions)
        validate(spec,frames,regions(skin))
        if window is None:window=[0,frames-1]
        if (not isinstance(window,(list,tuple)) or len(window)!=2 or
            any(type(x)!=int for x in window) or not 0<=window[0]<window[1]<frames):
            raise ValueError('Ordered integer rate-guard window required')
        self.parents=parents; self.rows=[]; self.points=[]
        for name,entry in spec['regions'].items():
            if entry['mode']!='explicit':continue
            for pin in entry['segments']:
                if pin['space']!='world' or 'vertex_id' not in pin:
                    raise ValueError('Point-rate guard requires fixed material vertices with stationary world targets')
                a,b=pin['start_frame'],pin['end_frame']
                if not window[0]<=a<b<=window[1]:
                    raise ValueError('Nonempty pin interval must lie inside the rate-guard window')
                j=len(self.points);self.points.append(pin['vertex_id'])
                for phase,start,end in [('approach',window[0],a),('hold',a,b),('release',b,window[1])]:
                    if start==end:continue
                    self.rows.append(dict(region=name,vertex_id=pin['vertex_id'],point=j,phase=phase,
                                         first_frame=start,last_frame=end))
        if not self.points:raise ValueError('At least one explicit stationary material-point interval required')
        surface=Surface(skin);ids=skin['lbs_indices'][self.points]
        bind=np.einsum('vwij,vj->vwi',surface.inverse[ids],surface.points[self.points])[...,:3]
        tensor=lambda x:torch.as_tensor(x,dtype=rotations.dtype,device=rotations.device)
        self.skin=LinearSkinOperator(torch.as_tensor(ids,dtype=torch.long,device=rotations.device),
            tensor(skin['lbs_weights'][self.points]),tensor(bind),positions.shape[1])
        self.masks=[]
        # Classify each finite-difference stencil by its center, so stencils
        # crossing phase boundaries are still constrained (sometimes twice).
        for row in self.rows:
            self.masks.append([((torch.arange((frames-1)*4+1-order,device=rotations.device)+order/2)/4>=row['first_frame']) &
                               ((torch.arange((frames-1)*4+1-order,device=rotations.device)+order/2)/4<=row['last_frame'])
                               for order in [1,2]])
        with torch.no_grad():source=self.rates(rotations,positions)
        self.ceilings=[[r[mask,row['point']].max().detach() for r,mask in zip(source,masks)]
                       for row,masks in zip(self.rows,self.masks)]
        self.scales=[[c.clamp_min(1e-6) for c in row] for row in self.ceilings]
        self.multipliers=[[torch.zeros(int(mask.sum()),dtype=rotations.dtype,device=rotations.device)
                           for mask in masks] for masks in self.masks]
        self.penalty=10.;self.last=None

    def rates(self,rotations,positions):
        r,p=joint_trajectory(rotations,positions,self.parents,return_rotations=True)
        return motion_rates(self.skin(r,p))

    def loss(self,rotations,positions):
        rates=self.rates(rotations,positions);residuals=[];peaks=[];terms=[]
        for row,masks,ceilings,scales,multipliers in zip(self.rows,self.masks,self.ceilings,self.scales,self.multipliers):
            selected=[r[mask,row['point']] for r,mask in zip(rates,masks)]
            gs=[(r-c)/s for r,c,s in zip(selected,ceilings,scales)]
            terms.extend(((torch.relu(m+self.penalty*g).square()-m.square())/(2*self.penalty)).sum()
                         for g,m in zip(gs,multipliers))
            residuals.append([g.detach() for g in gs]);peaks.append([float(r.detach().max()) for r in selected])
        self.last=residuals;self.peaks=peaks
        return sum(terms)

    def advance_stage(self,growth):
        if self.last is None:raise ValueError('Evaluate accepted point rates before updating multipliers')
        self.multipliers=[[torch.relu(m+self.penalty*g) for m,g in zip(ms,gs)]
                          for ms,gs in zip(self.multipliers,self.last)]
        self.penalty*=growth

    def record(self):
        rows=[]
        for i,row in enumerate(self.rows):
            rows.append(dict(**row,reference_ceilings=[float(c) for c in self.ceilings[i]],
                sampled_peaks=None if self.last is None else self.peaks[i],
                maximum_normalized_violations=None if self.last is None else [float(g.relu().max()) for g in self.last[i]]))
        return dict(rows=rows,units=['m/s','m/s2'],subdivisions=4,fps=30,penalty=self.penalty,
            scope='Each authored fixed material point has separate original-source speed/acceleration maxima for approach, hold and release. All eight skin influences, differentiable export interpolation; quantization excluded. Not hard feasibility, angular limits, sole support, force or quality approval.')
