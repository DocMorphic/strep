"""Chunked exact reverse-mode rows, without reducing the constraint population.

PyTorch's batched VJP backend is experimental; benchmark before adopting it.
The chunk cap bounds batched graph intermediates, not total process memory.
"""
import torch


def row_jacobian(values,variable,chunk=16):
    if (not isinstance(values,torch.Tensor) or not isinstance(variable,torch.Tensor)
            or values.ndim!=1 or variable.ndim!=1 or not len(values) or not len(variable)
            or values.dtype!=torch.float64 or variable.dtype!=torch.float64
            or values.device!=variable.device or not values.requires_grad or not variable.requires_grad
            or not torch.isfinite(values).all() or not torch.isfinite(variable).all()
            or type(chunk) is not int or not 1<=chunk<=32):
        raise ValueError('Finite connected double-precision rows and controls with bounded chunk required')
    rows=[]
    for start in range(0,len(values),chunk):
        stop=min(start+chunk,len(values))
        basis=torch.zeros((stop-start,len(values)),dtype=values.dtype,device=values.device)
        basis[torch.arange(stop-start),torch.arange(start,stop)]=1
        derivative,=torch.autograd.grad(values,variable,grad_outputs=basis,
            is_grads_batched=True,retain_graph=True)
        if derivative.shape!=(stop-start,len(variable)) or not torch.isfinite(derivative).all():
            raise ValueError('Complete finite derivative rows required')
        rows.append(derivative.detach())
    return torch.cat(rows).cpu().numpy()
