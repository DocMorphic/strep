"""CPU float64 L-BFGS-B adapter with directly bounded physical root heights.

Rotation controls retain the caller's existing smooth bounded parameterization.
Only root coordinates receive box bounds here; contact feasibility is not implied.
"""
import numpy as np
import torch
import scipy
from scipy.optimize import minimize


class BoxRootOptimizer:
    def __init__(self, rotation, root, limit, iterations):
        self.parameters=[rotation,root]
        if any(not isinstance(p,torch.Tensor) or p.device.type!='cpu' or p.dtype!=torch.float64
               or not p.is_leaf or not p.requires_grad or not p.numel() or not torch.isfinite(p).all()
               for p in self.parameters):
            raise ValueError('Finite CPU float64 leaf parameters with gradients required')
        if root.ndim!=1 or type(limit) not in (int,float) or not np.isfinite(limit) or limit<=0:
            raise ValueError('Positive root limit and frame-wise root parameters required')
        if type(iterations) is not int or iterations<1:
            raise ValueError('Positive integer iteration budget required')
        if (root<0).any() or (root>limit).any():raise ValueError('Initial root exceeds bounds')
        self.limit=float(limit);self.rotation_count=rotation.numel();self.iterations=iterations
        self.bounds=[(None,None)]*rotation.numel()+[(0.,self.limit)]*root.numel()
        self.summary=None

    def zero_grad(self):
        for p in self.parameters:p.grad=None

    def assign(self, values):
        values=np.asarray(values,dtype=np.float64)
        if values.shape!=(sum(p.numel() for p in self.parameters),) or not np.isfinite(values).all():
            raise ValueError('Invalid optimizer coordinates')
        height=values[self.rotation_count:]
        if (height<0).any() or (height>self.limit).any():raise ValueError('Optimizer root exceeds bounds')
        offset=0
        with torch.no_grad():
            for p in self.parameters:
                p.copy_(torch.from_numpy(values[offset:offset+p.numel()].copy()).reshape(p.shape));offset+=p.numel()

    def step(self, closure):
        initial=np.concatenate([p.detach().numpy().reshape(-1) for p in self.parameters])
        def evaluate(values):
            self.assign(values)
            loss=closure()
            if loss.numel()!=1 or not torch.isfinite(loss):raise ValueError('Nonfinite fitting objective')
            if any(p.grad is None or not torch.isfinite(p.grad).all() for p in self.parameters):
                raise ValueError('Missing or nonfinite fitting gradient')
            gradient=np.concatenate([p.grad.detach().numpy().reshape(-1) for p in self.parameters])
            return float(loss.detach()),gradient
        result=minimize(evaluate,initial,jac=True,method='L-BFGS-B',bounds=self.bounds,
                        options=dict(maxiter=self.iterations,maxfun=max(40,self.iterations*40),maxls=40,
                                     maxcor=12,ftol=1e-11,gtol=1e-8))
        # A line search may leave tensors at a trial evaluation. Restore the
        # returned accepted point before the caller recomputes AL residuals.
        self.assign(result.x)
        gradient=np.asarray(result.jac,dtype=float).copy()
        if not np.isfinite(result.fun) or not np.isfinite(gradient).all():raise ValueError('Nonfinite optimizer result')
        height=result.x[self.rotation_count:];g=gradient[self.rotation_count:]
        g[((height<=0)&(g>0))|((height>=self.limit)&(g<0))]=0
        self.summary=dict(method='scipy-L-BFGS-B',scipy_version=scipy.__version__,success=bool(result.success),
                          status=int(result.status),message=str(result.message),iterations=int(result.nit),
                          evaluations=int(result.nfev),projected_gradient_inf=float(np.abs(gradient).max()),
                          root_bounds_m=[0.,self.limit],quality_approved=False)
        return float(result.fun)
