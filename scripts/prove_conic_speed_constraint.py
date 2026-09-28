"""Small diagnostic contrasting a tangent speed bound with a norm cone."""
import sys
import numpy as np
from scipy import sparse
from strep import ROOT,read,save,sha256,now


def run():
    output=ROOT/'reports/conic-speed-proof-v1.json'
    if output.exists():raise ValueError('Preserve proof')
    bootstrap=ROOT/'reports/conic-solver-bootstrap-v1.json';meta=read(bootstrap);vendor=ROOT/meta['vendor']
    for path,digest in meta['files'].items():
        if sha256(vendor/path)!=digest:raise ValueError('Vendored solver changed')
    sys.path.insert(0,str(vendor));import clarabel
    settings=clarabel.DefaultSettings();settings.verbose=False;settings.max_iter=100
    settings.tol_gap_abs=settings.tol_feas=settings.tol_gap_rel=1e-10
    if hasattr(settings,'max_threads'):settings.max_threads=1
    # Scalar z perturbs velocity perpendicular to an existing unit velocity.
    # The squared-norm constraint has zero derivative at z=0, yet requires z=0.
    A=sparse.csc_matrix([[1.],[-1.],[0.],[-1.],[0.]])
    b=np.array([1.,1.,1.,0.,1.])
    solver=clarabel.DefaultSolver(sparse.csc_matrix((1,1)),np.array([-1.]),A,b,
        [clarabel.NonnegativeConeT(2),clarabel.SecondOrderConeT(3)],settings)
    result=solver.solve();z=float(result.x[0]);residual=float(np.linalg.norm([z,1.])-1.)
    tangent_point=1.;tangent_margin=0.;true_margin=1.-np.linalg.norm([tangent_point,1.])
    passed=bool(np.isfinite(z) and abs(z)<1e-6 and residual<=1e-12 and true_margin<0)
    save(output,dict(at=now(),implementation_sha256=sha256(__file__),bootstrap_sha256=sha256(bootstrap),solver_version=clarabel.__version__,
        status=str(result.status),iterations=result.iterations,conic_coordinate=z,conic_speed_residual=residual,
        tangent_candidate=tangent_point,tangent_margin=tangent_margin,tangent_true_speed_margin=float(true_margin),passed=passed,
        scope='Known normalized one-variable boundary problem. AlmostSolved status retained; measured residual checked independently. Demonstrates tangent-bound weakness, not a tested character-motion correction or solver-convergence guarantee.',quality_approved=False))
    if not passed:raise ValueError('Conic speed diagnostic differs')
    print(read(output))


if __name__=='__main__':run()
