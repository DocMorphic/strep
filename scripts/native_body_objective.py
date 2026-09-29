"""Native reference-relative pose and added-speed inequalities for contact fitting.

These match two existing body review limits. Augmented penalties do not promise
feasibility; the independent body and export reviews remain authoritative.
"""
import math
import torch


class NativeBodyObjective:
    def __init__(self, references):
        if not isinstance(references, dict) or not references:
            raise ValueError('Named native joint reference tensors required')
        self.references = {}
        shape = None
        for name, positions in references.items():
            if not isinstance(name, str) or not name or not isinstance(positions, torch.Tensor):
                raise ValueError('Named native joint reference tensors required')
            if positions.ndim != 3 or positions.shape[0] < 2 or positions.shape[1] < 1 or positions.shape[2] != 3:
                raise ValueError('At least two frames of joint XYZ positions required')
            if positions.dtype != torch.float64 or not torch.isfinite(positions).all():
                raise ValueError('Finite float64 native references required')
            signature = (positions.shape, positions.device)
            if shape is not None and signature != shape:
                raise ValueError('Reference clocks, joints and devices must agree')
            shape = signature
            self.references[name] = positions.detach().clone()
        self.limits = (.22, 1.5)
        self.penalty = 10.
        self.multipliers = {name: [torch.zeros_like(p[..., 0]), torch.zeros_like(p[:-1, :, 0])]
                            for name, p in self.references.items()}
        self.last = None
        self.peaks = None

    def loss(self, positions):
        ref = next(iter(self.references.values()))
        if positions.shape != ref.shape or positions.dtype != ref.dtype or positions.device != ref.device:
            raise ValueError('Candidate must match native reference clock, joints, dtype and device')
        if not torch.isfinite(positions).all():
            raise ValueError('Finite candidate positions required')
        loss = positions.sum()*0
        self.last, self.peaks = {}, {}
        for name, reference in self.references.items():
            delta = positions-reference
            values = [torch.linalg.vector_norm(delta, dim=-1),
                      torch.linalg.vector_norm(torch.diff(delta, dim=0)*30, dim=-1)]
            residuals = [(value-limit)/limit for value, limit in zip(values, self.limits)]
            self.last[name] = [g.detach() for g in residuals]
            self.peaks[name] = [float(value.detach().max()) for value in values]
            for multiplier, g in zip(self.multipliers[name], residuals):
                loss = loss+((torch.relu(multiplier+self.penalty*g).square()-multiplier.square())/(2*self.penalty)).sum()
        return loss

    def advance_stage(self, growth):
        if self.last is None:
            raise ValueError('Evaluate accepted pose before updating body constraints')
        if type(growth) not in (int, float) or not math.isfinite(growth) or growth <= 0:
            raise ValueError('Positive finite penalty growth required')
        self.multipliers = {name: [torch.relu(m+self.penalty*g) for m, g in zip(ms, self.last[name])]
                            for name, ms in self.multipliers.items()}
        self.penalty *= growth

    def record(self):
        return dict(limits=list(self.limits), units=['m', 'm/s'], fps=30, penalty=self.penalty,
                    references=list(self.references), peaks=self.peaks,
                    maximum_normalized_violations=None if self.last is None else {
                        name: [float(g.relu().max()) for g in gs] for name, gs in self.last.items()},
                    reduction='sum over all reference, native frame and joint inequalities',
                    scope='Existing 22 cm pose and 1.5 m/s added-joint-speed screens relative to each immutable reference. '
                          'Augmented inequalities, not guaranteed feasibility. No support, export, anatomy or quality approval.')
