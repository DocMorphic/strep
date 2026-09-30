"""CPU float64 Jacobian products without materializing a dense Jacobian.

A differentiable pullback provides Jv by differentiating with respect to an
auxiliary cotangent. J^T w uses the original graph. No finite differences are
used by the operator; callers remain responsible for smoothness and acceptance.
"""
import numpy as np
import torch
from scipy.sparse.linalg import LinearOperator


class TorchJacobianOperator(LinearOperator):
    def __init__(self,function,point,guard=None):
        point=np.asarray(point,dtype=float)
        if point.ndim!=1 or not len(point) or not np.isfinite(point).all():raise ValueError('Finite nonempty point required')
        self.guard=guard;self.products=dict(forward=0,transpose=0)
        self.check()
        self.variable=torch.tensor(point.copy(),dtype=torch.float64,requires_grad=True)
        self.output=function(self.variable)
        if not isinstance(self.output,torch.Tensor) or self.output.ndim!=1 or not self.output.numel() or self.output.dtype!=torch.float64 or self.output.device.type!='cpu' or not torch.isfinite(self.output).all():
            raise ValueError('Finite nonempty CPU float64 residual vector required')
        self.cotangent=torch.zeros_like(self.output,requires_grad=True)
        self.pullback=None
        if self.output.requires_grad:
            self.pullback=torch.autograd.grad(self.output,self.variable,grad_outputs=self.cotangent,
                create_graph=True,retain_graph=True,allow_unused=True)[0]
        super().__init__(dtype=np.dtype('float64'),shape=(len(self.output),len(point)))
        self.check()

    def check(self):
        if self.guard is not None:self.guard()

    @property
    def values(self):return self.output.detach().numpy().copy()

    def vector(self,value,size):
        a=np.asarray(value,dtype=float).reshape(-1)
        if a.shape!=(size,) or not np.isfinite(a).all():raise ValueError('Finite vector with matching dimension required')
        return torch.tensor(a.copy(),dtype=torch.float64)

    def _matvec(self,value):
        self.check();v=self.vector(value,self.shape[1]);self.products['forward']+=1
        result=None
        if self.pullback is not None and self.pullback.requires_grad:
            result=torch.autograd.grad(self.pullback,self.cotangent,grad_outputs=v,retain_graph=True,allow_unused=True)[0]
        out=np.zeros(self.shape[0]) if result is None else result.detach().numpy().copy()
        if not np.isfinite(out).all():raise ValueError('Nonfinite forward Jacobian product')
        self.check();return out

    def _rmatvec(self,value):
        self.check();v=self.vector(value,self.shape[0]);self.products['transpose']+=1
        result=None
        if self.output.requires_grad:
            result=torch.autograd.grad(self.output,self.variable,grad_outputs=v,retain_graph=True,allow_unused=True)[0]
        out=np.zeros(self.shape[1]) if result is None else result.detach().numpy().copy()
        if not np.isfinite(out).all():raise ValueError('Nonfinite transpose Jacobian product')
        self.check();return out

    def _matmat(self,values):
        values=np.asarray(values)
        return np.column_stack([self._matvec(v) for v in values.T])
