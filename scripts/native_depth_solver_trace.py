"""Observe raw phase points without changing the existing depth-direction code.

The owner function keeps its code object, defaults, data and phase checks. A
private globals dictionary supplies a transparent solver proxy; original module
globals and solution objects are untouched. Captured points remain unapproved.
"""
import types
import numpy as np
import native_partner_depth_restore as owner


def direction(*args,**kwargs):
    """Return the unchanged direction tuple plus raw bounded phase observations.

    Failed/nonfinite points are recorded as unavailable. Consumers must still
    project and fully validate a point before using it for any new experiment.
    Capturing a rejected solution does not authorize replacing the selected one.
    """
    original=owner.direction;module=original.__globals__['solver_module']();records=[]
    class Solver:
        def __init__(self,solver):self.solver=solver
        def solve(self):
            solution=self.solver.solve();point=getattr(solution,'x',None)
            point=np.asarray(point,float).copy() if point is not None else None
            finite=bool(point is not None and point.ndim==1 and np.isfinite(point).all())
            records.append(dict(solve_index=len(records),status=str(solution.status),
                finite_point=finite,point=point.tolist() if finite else None,
                iterations=getattr(solution,'iterations',None),quality_approved=False,release_approved=False))
            return solution
    class Module:
        def __getattr__(self,name):return getattr(module,name)
        @staticmethod
        def DefaultSolver(*inputs):return Solver(module.DefaultSolver(*inputs))
    isolated=dict(original.__globals__,solver_module=lambda:Module())
    observed=types.FunctionType(original.__code__,isolated,original.__name__,original.__defaults__,original.__closure__)
    observed.__kwdefaults__=original.__kwdefaults__.copy() if original.__kwdefaults__ is not None else None
    delta,info,reduction=observed(*args,**kwargs)
    return delta,info,reduction,records
