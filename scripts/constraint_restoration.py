"""Experimental bounded minimax steps with nonlinear constraint acceptance.

Residuals are normalized inequalities g(x) <= 0. A linear model proposes a
step; only the complete nonlinear residual vector can accept it. This neither
proves infeasibility on failure nor covers constraints omitted by the caller.
"""
import numpy as np
import torch
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, hstack, vstack, eye


def minimax_step(x, residuals, jacobian, lower, upper, trust):
    x, g, j, lo, hi, trust = [np.asarray(a, dtype=float) for a in
                              (x, residuals, jacobian, lower, upper, trust)]
    if (x.ndim != 1 or not x.size or g.ndim != 1 or not g.size or
            j.shape != (g.size, x.size) or any(a.shape != x.shape for a in [lo, hi, trust])):
        raise ValueError('Matching coordinates, constraints, Jacobian and step bounds required')
    if (not all(np.isfinite(a).all() for a in [x, g, j, trust]) or
            np.isnan(lo).any() or np.isnan(hi).any() or (lo > hi).any() or
            (trust <= 0).any() or (x < lo).any() or (x > hi).any()):
        raise ValueError('Finite residuals, positive trust and in-bound coordinates required')
    bounds = list(zip(np.maximum(-1., (lo-x)/trust), np.minimum(1., (hi-x)/trust)))
    # Dimensionless step z, common nonnegative violation t. Passing rows get
    # no elastic slack, so the model cannot trade them for failed rows.
    a = hstack([csr_matrix(j*trust), csr_matrix(-(g > 0).astype(float)[:, None])], format='csr')
    fit = linprog(np.r_[np.zeros(x.size), 1.], A_ub=a, b_ub=-g,
                  bounds=bounds+[(0., None)], method='highs')
    record = dict(success=bool(fit.success), status=int(fit.status), message=str(fit.message))
    if not fit.success:
        return None, record
    # Among steps achieving that violation, choose the smallest scaled L-inf
    # change. The tiny LP reserve is NOT a nonlinear acceptance tolerance.
    target = max(0., float(fit.x[-1]))
    identity = eye(x.size, format='csr')
    a2 = vstack([hstack([csr_matrix(j*trust), csr_matrix((g.size, 1))]),
                 hstack([identity, csr_matrix(-np.ones((x.size, 1)))]),
                 hstack([-identity, csr_matrix(-np.ones((x.size, 1)))])], format='csr')
    b2 = np.r_[-g+(g > 0)*(target+1e-10), np.zeros(2*x.size)]
    small = linprog(np.r_[np.zeros(x.size), 1.], A_ub=a2, b_ub=b2,
                    bounds=bounds+[(0., 1.)], method='highs')
    z = (small.x if small.success else fit.x)[:-1]
    proposed = np.clip(x+z*trust, lo, hi)
    step = proposed-x
    record.update(predicted_maximum_violation=max(0., float((g+j@step).max())),
                  minimum_step_solve=bool(small.success), scaled_step_inf=float(np.max(np.abs(step/trust))))
    return step, record


def restore(parameters, residuals, lower, upper, trust, *, steps=3, backtracks=10, progress=None):
    """Update leaf tensors only with accepted bounded nonlinear improvements."""
    if type(steps) is not int or not 1 <= steps <= 20 or type(backtracks) is not int or not 1 <= backtracks <= 20:
        raise ValueError('Bounded positive iteration and backtracking counts required')
    if not parameters or any(not isinstance(p, torch.Tensor) or not p.is_leaf or not p.requires_grad or
                             p.device.type != 'cpu' or p.dtype != torch.float64 or not p.numel()
                             for p in parameters):
        raise ValueError('CPU float64 leaf parameters with gradients required')
    def pack():
        return np.concatenate([p.detach().numpy().reshape(-1) for p in parameters])
    def assign(x):
        offset = 0
        with torch.no_grad():
            for p in parameters:
                p.copy_(torch.from_numpy(x[offset:offset+p.numel()].copy()).reshape(p.shape))
                offset += p.numel()
    def evaluate():
        g = residuals()
        if not isinstance(g, torch.Tensor) or g.ndim != 1 or not g.numel() or not torch.isfinite(g).all():
            raise ValueError('Complete finite one-dimensional constraint tensor required')
        return g
    initial = pack(); accepted = initial.copy(); history = []
    lower, upper, trust = [np.asarray(a, dtype=float) for a in [lower, upper, trust]]
    if (any(a.shape != initial.shape for a in [lower, upper, trust]) or
            not np.isfinite(initial).all() or not np.isfinite(trust).all() or
            np.isnan(lower).any() or np.isnan(upper).any() or (lower > upper).any() or
            (trust <= 0).any() or (initial < lower).any() or (initial > upper).any()):
        raise ValueError('Positive trust and initially bounded finite parameters required')
    try:
        for iteration in range(steps):
            g = evaluate(); before = g.detach().numpy().copy()
            peak = max(0., float(before.max()))
            if peak == 0.:
                break
            jacobian = []
            for value in g:
                gradients = (torch.autograd.grad(value, parameters, retain_graph=True, allow_unused=True)
                             if value.requires_grad else [None]*len(parameters))
                jacobian.append(np.concatenate([np.zeros(p.numel()) if grad is None else
                    grad.detach().numpy().reshape(-1) for p, grad in zip(parameters, gradients)]))
            step, record = minimax_step(accepted, before, jacobian, lower, upper, trust)
            record.update(iteration=iteration+1, before_maximum_violation=peak, trials=[])
            selected = None
            if step is not None:
                for attempt in range(backtracks):
                    fraction = .5**attempt; candidate = np.clip(accepted+fraction*step, lower, upper)
                    assign(candidate)
                    with torch.no_grad():
                        after = evaluate().numpy().copy()
                    if after.shape != before.shape:
                        raise ValueError('Constraint layout changed during restoration')
                    worst = max(0., float(after.max()))
                    new_failures = int(np.count_nonzero((before <= 0) & (after > 0)))
                    improves = worst == 0. or worst < peak-1e-10
                    ok = bool(improves and not new_failures)
                    record['trials'].append(dict(fraction=fraction, maximum_violation=worst,
                                                  new_failures=new_failures, accepted=ok))
                    if ok:
                        accepted = candidate; selected = fraction; break
            assign(accepted)
            record['selected_fraction'] = selected; history.append(record)
            if progress:
                progress(record)
            if selected is None:
                break
        with torch.no_grad():
            final = evaluate().numpy().copy()
    finally:
        # Rejected probes and exceptions must not leave a trial in live tensors.
        assign(accepted)
    return dict(history=history, steps_requested=steps,
                maximum_parameter_change=float(np.abs(accepted-initial).max()),
                final_maximum_violation=max(0., float(final.max())),
                proxy_feasible=bool((final <= 0).all()), quality_approved=False)
