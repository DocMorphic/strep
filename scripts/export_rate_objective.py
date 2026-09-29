"""Optional sampled global joint-rate ceilings relative to the original clip.

Augmented inequalities guide fitting, not hard feasibility guarantees. They do
not preserve per-joint dynamics or certify plausible motion. Audit the GLB.
"""
import math
import torch
from export_motion_sampling import joint_trajectory, motion_rates


class ExportRateObjective:
    def __init__(self, rotations, positions, parents, acceleration_margin_fraction=0.):
        margin=acceleration_margin_fraction
        if type(margin) not in (int,float) or not math.isfinite(margin) or not 0<=margin<1:
            raise ValueError('Acceleration margin fraction must be finite in [0, 1)')
        self.parents=parents
        with torch.no_grad():
            rates=motion_rates(joint_trajectory(rotations,positions,parents))
        self.reference_peaks=[rate.max().detach() for rate in rates]
        self.ceilings=[self.reference_peaks[0],self.reference_peaks[1]*(1-margin)]
        # Static references remain meaningful without division by zero.
        self.scales=[peak.clamp_min(1e-6) for peak in self.reference_peaks]
        self.multipliers=[torch.zeros_like(rate) for rate in rates]
        self.penalty=10.
        self.last=None
        self.margin=margin

    def loss(self, rotations, positions):
        rates=motion_rates(joint_trajectory(rotations,positions,self.parents))
        residuals=[(rate-limit)/scale for rate,limit,scale in zip(rates,self.ceilings,self.scales)]
        self.last=[g.detach() for g in residuals]
        self.peaks=[float(rate.detach().max()) for rate in rates]
        return sum(((torch.relu(m+self.penalty*g).square()-m.square())/(2*self.penalty)).sum()
                   for m,g in zip(self.multipliers,residuals))

    def advance_stage(self, growth):
        if self.last is None:raise ValueError('Evaluate accepted pose before advancing rate constraints')
        self.multipliers=[torch.relu(m+self.penalty*g) for m,g in zip(self.multipliers,self.last)]
        self.penalty*=growth

    def record(self):
        return dict(reference_peaks=[float(x) for x in self.reference_peaks],
                    ceilings=[float(x) for x in self.ceilings],units=['m/s','m/s2'],
                    acceleration_margin_fraction=self.margin,penalty=self.penalty,
                    sampled_peaks=getattr(self,'peaks',None),
                    max_normalized_violations=None if self.last is None else [float(g.relu().max()) for g in self.last],
                    subdivisions=4,fps=30,reduction='sum over all sample and joint inequalities',
                    scope='Original-source global peaks; proxy excludes export quantization. No per-joint, continuous-time, anatomical or quality guarantee.')
