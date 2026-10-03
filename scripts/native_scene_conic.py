"""Optional vector-norm minimax proposals with independent decoded acceptance."""
import hashlib
from pathlib import Path
import numpy as np
from scipy import sparse
from native_scene_norms import NormRows, linearize
from native_support_feasibility import merit

VERSION = '0.11.1'


def solver_module():
    try:import clarabel
    except ImportError as exc:
        raise RuntimeError('Vector proposals require requirements-scene-proposals.txt in the selected Python environment') from exc
    if clarabel.__version__ != VERSION:raise ValueError('Native scene proposal solver must be Clarabel '+VERSION)
    return clarabel


def solver_identity():
    module = solver_module(); folder = Path(module.__file__).parent
    files = sorted(p for p in folder.rglob('*') if p.is_file() and p.suffix in ('.py','.pyd','.so'))
    if not files:raise ValueError('Installed proposal solver files unavailable')
    return dict(version=module.__version__,files_sha256={p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files})


def direction(system, jacobian, value, lower, upper, trust, *, hard_rows=0):
    value,lower,upper = [np.asarray(a,float) for a in (value,lower,upper)]
    if value.ndim!=1:raise ValueError('One-dimensional vector controls required')
    n = len(value)
    if type(hard_rows) is not int or not 0<=hard_rows<=len(system.vectors):raise ValueError('Valid protected norm row prefix required')
    if sparse.issparse(jacobian):jacobian = sparse.csr_matrix(jacobian)
    else:
        jacobian = np.asarray(jacobian,float)
        if jacobian.shape!=(*system.vectors.shape,n):raise ValueError('Matching dense vector Jacobian required')
        jacobian = sparse.csr_matrix(jacobian.reshape(system.vectors.size,n))
    if (not n or lower.shape!=value.shape or upper.shape!=value.shape
            or jacobian.shape!=(system.vectors.size,n)
            or any(not np.isfinite(a).all() for a in (value,lower,upper,jacobian.data))
            or np.any(lower>=upper) or np.any(value<lower) or np.any(value>upper)
            or type(trust) not in (int,float) or not np.isfinite(trust) or trust<=0):
        raise ValueError('Finite matching vector model, ordered boxes and positive trust required')
    solver = solver_module(); lo = np.maximum(-1.,(lower-value)/trust); hi = np.minimum(1.,(upper-value)/trust)
    # Unknowns are a normalized trust-box step and nonnegative worst excess t.
    mats = [sparse.hstack([sparse.eye(n),sparse.csc_matrix((n,1))]),
        sparse.hstack([-sparse.eye(n),sparse.csc_matrix((n,1))]),
        sparse.csc_matrix(np.r_[np.zeros(n),-1.][None])]
    rhs = [hi,-lo,np.zeros(1)]; cones = [solver.NonnegativeConeT(2*n+1)]
    jacobian.eliminate_zeros()
    counts = np.diff(jacobian.indptr).reshape(-1,3).sum(axis=1)
    maximum_step = np.maximum(abs(lo),abs(hi))*trust
    radius = np.asarray(abs(jacobian)@maximum_step).reshape(system.vectors.shape)
    upper_norm = np.linalg.norm(abs(system.vectors)+radius,axis=1)
    reserve = 64*(n+4)*np.finfo(float).eps*np.maximum.reduce([upper_norm,abs(system.caps),np.ones(len(system.caps))])
    # Omit a variable cone only when every affine vector in the entire trust
    # box is within its original cap, with a conservative arithmetic reserve.
    box_passing = (counts>0)&np.isfinite(upper_norm)&(upper_norm+reserve<=system.caps)
    active = np.flatnonzero((counts>0)&~box_passing); fixed_mask = counts==0
    fixed_residual = system.residual()[fixed_mask]; fixed = fixed_residual[fixed_residual>0]
    if np.any(system.residual()[:hard_rows][counts[:hard_rows]==0]>0):
        return None,dict(status='FixedProtectedConflict',protected_norm_rows=hard_rows,
            scope='Fixed failed protected affine row; no decoded feasibility claim.')
    omitted = int((fixed_residual<=0).sum())
    if len(active):
        selected_rows = (3*active[:,None]+np.arange(3)).ravel()
        derivative = jacobian[selected_rows].multiply((-trust/np.repeat(system.scales[active],3))[:,None]).tocoo()
        mapped_rows = 4*(derivative.row//3)+1+derivative.row%3
        matrix = sparse.csc_matrix((np.r_[derivative.data,-(active>=hard_rows).astype(float)],
            (np.r_[mapped_rows,4*np.arange(len(active))],np.r_[derivative.col,np.full(len(active),n)])),shape=(4*len(active),n+1))
        # Each consecutive four-row group is one full, unsimplified norm cone.
        bound = np.c_[system.caps[active],system.vectors[active]]/system.scales[active,None]
        mats.append(matrix); rhs.append(bound.ravel()); cones.extend(solver.SecondOrderConeT(4) for _ in active)
    if len(fixed):
        mats.append(sparse.csc_matrix(np.r_[np.zeros(n),-1.][None])); rhs.append(np.array([-float(fixed.max())]))
        cones.append(solver.NonnegativeConeT(1))
    matrix = sparse.vstack(mats,format='csc'); bound = np.concatenate(rhs)
    settings = solver.DefaultSettings(); settings.verbose=False; settings.max_iter=100; settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-9
    if hasattr(settings,'max_threads'):settings.max_threads=1
    objective = np.r_[np.zeros(n),1.]
    first = solver.DefaultSolver(sparse.csc_matrix((n+1,n+1)),objective,matrix,bound,cones,settings).solve()
    info = dict(status=str(first.status),iterations=first.iterations,trust_control_fraction=float(trust),
        solver_version=solver.__version__,norm_rows=len(system.vectors),active_cones=len(active),
        protected_norm_rows=hard_rows,
        fixed_failed_rows=len(fixed),omitted_fixed_passing_rows=omitted,
        omitted_affine_box_passing_rows=int(box_passing.sum()),
        affine_box_bound='norm(abs(vector) + abs(J) @ maximum_absolute_step) plus arithmetic reserve',
        scope='Affine vector-norm proposal only; decoded constraints still decide acceptance.')
    if str(first.status) not in ('Solved','AlmostSolved'):return None,info
    point = np.asarray(first.x)
    if not np.isfinite(point).all():return None,dict(info,invalid_solution=True)
    optimum = max(0.,float(point[-1]))
    # Remove gratuitous controls while retaining the first minimax optimum.
    second_matrix = sparse.vstack([matrix,sparse.csc_matrix(np.r_[np.zeros(n),1.][None])],format='csc')
    second_bound = np.r_[bound,optimum+1e-9]
    second = solver.DefaultSolver(sparse.diags(np.r_[np.ones(n),0.],format='csc'),np.zeros(n+1),
        second_matrix,second_bound,cones+[solver.NonnegativeConeT(1)],settings).solve()
    info.update(minimum_norm_phase_status=str(second.status),affine_optimum=optimum)
    if str(second.status) in ('Solved','AlmostSolved') and np.isfinite(second.x).all():point = np.asarray(second.x)
    delta = point[:n]*trust
    if (np.any(delta<lo*trust-1e-9) or np.any(delta>hi*trust+1e-9)
            or not np.isfinite(delta).all()):return None,dict(info,invalid_solution=True)
    delta = np.clip(value+delta,lower,upper)-value
    info.update(maximum_control_step=float(abs(delta).max()),predicted_norm_merit=list(merit(system.residual(jacobian,delta))))
    return delta,info


def optimize(problem,evaluate,iterations,trust,*,difference_step=.001,difference_source='stored',storage_cells=0,protect_source_rows=False,restoration_steps=0,
        protect_contact_rows=False,anchor_worlds=None):
    if type(protect_contact_rows) is not bool or protect_contact_rows and not protect_source_rows:
        raise ValueError('Individual native contact protection requires source protection')
    if anchor_worlds is not None and not callable(anchor_worlds):raise ValueError('Callable decoded anchor required')
    value = problem.initial.copy(); current_label='start';current = evaluate(value,current_label); history = []; radius = trust
    for iteration in range(1,iterations+1):
        before = merit(current)
        if before[0]==0:break
        options={} if anchor_worlds is None else dict(base_worlds=anchor_worlds(value,current_label))
        system,jacobian,differences = linearize(problem,value,step=difference_step,difference_source=difference_source,**options)
        # Algebraic refactoring may differ in final floating-point subtraction;
        # it must describe the same ordered constraints before proposing a step.
        np.testing.assert_allclose(system.residual(),problem.model(value) if anchor_worlds is None else current,atol=1e-9,rtol=1e-12)
        hard=problem.protected_rows if protect_source_rows else 0
        contact_before=None
        if protect_contact_rows:
            from native_contact_norms import protect_rows,row_regression
            contact_before=np.asarray(current[hard:],float)
            if np.any(np.asarray(current[:hard])>0):raise ValueError('Original source conditions must pass before contact protection')
            system,jacobian,guard_identity=protect_rows(system,jacobian,hard,contact_before)
            hard=guard_identity['hard_rows'];differences['native_contact_protection']=guard_identity
        delta,info = direction(system,jacobian,value,problem.lower,problem.upper,radius,
            hard_rows=hard)
        accepted = None; probes = []; storage_info = None; repairs=[]
        def acceptable(g):
            score=merit(g)
            protected=not protect_source_rows or np.all(g[:problem.protected_rows]<=0)
            if protect_contact_rows:protected=bool(protected and np.all(row_regression(contact_before,g[problem.protected_rows:])<=0))
            improved=score[0]<before[0]-1e-12 or abs(score[0]-before[0])<=1e-12 and score[1]<before[1]-1e-15
            return score,bool(protected),bool(protected and improved)
        def observation(g):
            extra=dict(source_rows_pass=bool(not protect_source_rows or np.all(g[:problem.protected_rows]<=0)))
            if protect_contact_rows:
                regression=row_regression(contact_before,g[problem.protected_rows:])
                extra.update(native_contact_rows_nonregressing=bool(np.all(regression<=0)),
                    maximum_native_contact_row_regression=float(max(0.,regression.max())))
            return extra
        def protected_residual(g):
            if not protect_contact_rows:return g
            return np.r_[g[:problem.protected_rows],row_regression(contact_before,g[problem.protected_rows:]),g[problem.protected_rows:]]
        if delta is not None:
            for backoff in range(10):
                fraction = .5**backoff; other = np.clip(value+fraction*delta,problem.lower,problem.upper)
                label=f'{iteration}-{backoff}';g = evaluate(other,label); score,protected,passed = acceptable(g)
                probes.append(dict(fraction=fraction,merit=list(score),**observation(g),accepted=passed))
                if passed:value=other;current=g;current_label=label;accepted=fraction;break
                if restoration_steps and protect_source_rows and backoff==0 and not protected:
                    from native_scene_restore import tighten
                    reserve=None;repair_delta=delta;repair_g=g
                    for repair in range(restoration_steps):
                        tightened,reserve,margin=tighten(system,jacobian,repair_delta,protected_residual(repair_g),hard,reserve)
                        repaired,repair_info=direction(tightened,jacobian,value,problem.lower,problem.upper,radius,hard_rows=hard)
                        record=dict(index=repair,margin=margin,conic_step=repair_info,available=repaired is not None)
                        repairs.append(record)
                        if repaired is None:break
                        other=np.clip(value+repaired,problem.lower,problem.upper)
                        label=f'{iteration}-restore-{repair}';repair_g=evaluate(other,label);score,protected,passed=acceptable(repair_g)
                        record.update(merit=list(score),**observation(repair_g),accepted=passed)
                        probes.append(dict(kind='decoded-restoration',index=repair,fraction=1.,merit=list(score),**observation(repair_g),accepted=passed))
                        if passed:value=other;current=repair_g;current_label=label;accepted=1.;break
                        if protected:break  # No decoded protected defect left to restore.
                        repair_delta=repaired
                    if accepted is not None:break
                if storage_cells and backoff==0:
                    from native_scene_storage import fractions
                    try:
                        cells,storage_info=fractions(problem.edits,value,delta,maximum_cells=storage_cells)
                    except ValueError as exc:
                        cells=[];storage_info=dict(available=False,error=str(exc),maximum_cells=storage_cells)
                    for index,entry in enumerate(cells):
                        other=np.clip(value+entry['fraction']*delta,problem.lower,problem.upper)
                        label=f'{iteration}-storage-{index}';g=evaluate(other,label);score,protected,passed=acceptable(g)
                        probes.append(dict(**entry,kind='translation-storage-cell',merit=list(score),**observation(g),accepted=passed))
                        if passed:value=other;current=g;current_label=label;accepted=entry['fraction'];break
                    if accepted is not None:break
        history.append(dict(iteration=iteration,before=list(before),after=list(merit(current)),
            selected_fraction=accepted,probes=probes,conic_step=info,differences=differences,storage_cells=storage_info,decoded_restorations=repairs))
        print(iteration,history[-1]['after'],flush=True)
        if accepted is None:
            radius *= .25
            if radius<1e-8:break
    return value,dict(history=history,maximum_iterations=iterations,trust_control_fraction=trust,
        final_merit=list(merit(current)),proposal_model='affine-vector-norms',solver_version=VERSION,
        difference_source=difference_source,maximum_storage_cells=storage_cells,protect_source_rows=protect_source_rows,
        maximum_restoration_steps=restoration_steps,
        native_contact_rows_individually_protected=protect_contact_rows,decoded_base_anchor=anchor_worlds is not None,
        quantized_native_keys=True,conservative_dense_dependencies=True)
