"""Warm native support repair with exact serialized, minimax step acceptance.

Linearized models propose directions. Their LP status is never a nonlinear
feasibility certificate; the independent native support job still selects clips.
"""
from pathlib import Path
import warnings
import numpy as np
from scipy.optimize import linprog, OptimizeWarning
from scipy.sparse import csc_matrix, csr_matrix, hstack, vstack, eye
from scipy.spatial.transform import Rotation
from native_support_orientation import SupportOrientationProblem
from native_leg_floor import export_rotations
from native_support_clock import NativeSupportSampler
from paired_temporal_neighbor import rotation_channels
from rig_asset import RigAsset
from native_support_peak_limits import limits, STRICT_PEAK_TOLERANCE
from sampled_motion_caps import features, measures
from strep import read, save, sha256


def signed_constraints(problem, values, world):
    """Same ordered rows as the parent residual, without clipping interior rows."""
    rates=measures(features(world[problem.rate_ids],problem.rig.joints),problem.caps.dt);parts=[]
    strict_limits=getattr(problem,'strict_rate_limits',None)
    for group,(actual,cap,floor) in enumerate(zip(rates,problem.caps.caps,(.05,.5,.1,1.))):
        excess=actual[:,problem.columns]-cap[:,problem.columns]-problem.caps.tolerance if strict_limits is None else actual[:,problem.columns]-strict_limits[group][:,problem.columns]
        parts.append((excess/np.maximum(cap[:,problem.columns],floor)).ravel())
    for d in problem.data:
        r=d['row'];a,b=r['edit_keys'];q=np.stack([values[n][a:b+1] for n in r['chain']],axis=1)
        angle=np.rad2deg((Rotation.from_quat(d['original'].reshape(-1,4)).inv()*Rotation.from_quat(q.reshape(-1,4))).magnitude()).reshape(-1,3)
        stance=(problem.times>=r['stance_s'][0])&(problem.times<=r['stance_s'][1]);heights=d['projection'].evaluate(world[stance]).min(axis=1)
        inside=(problem.times>=r['edit_s'][0])&(problem.times<=r['edit_s'][1]);node=r['chain'][-1]
        movement=np.linalg.norm(world[inside,node,:3,3]-problem.raw[inside,node,:3,3],axis=1)
        parts.extend([(.000125-heights)/.001,(heights-r['maximum_height']+.000125)/.001,
                      (movement-r['displacement'])/.001,(angle-r['angle']).ravel()])
    return np.concatenate(parts)


def colors(pattern):
    """Greedy structural coloring: no two same-color columns share a row."""
    pattern=csc_matrix(pattern);used=[set() for _ in range(pattern.shape[0])];groups=[]
    order=sorted(range(pattern.shape[1]),key=lambda j:(-(pattern.indptr[j+1]-pattern.indptr[j]),j))
    for col in order:
        rows=pattern.indices[pattern.indptr[col]:pattern.indptr[col+1]];forbidden=set()
        for row in rows:forbidden.update(used[row])
        color=0
        while color in forbidden:color+=1
        if color==len(groups):groups.append([])
        groups[color].append(col)
        for row in rows:used[row].add(color)
    return [np.asarray(g,int) for g in groups]


def colored_jacobian(function,x,lower,upper,pattern,groups=None,step=1e-5):
    """Bound-aware absolute forward differences for the supplied constraint model."""
    x,lower,upper=map(lambda a:np.asarray(a,float),(x,lower,upper));pattern=csc_matrix(pattern)
    if x.ndim!=1 or lower.shape!=x.shape or upper.shape!=x.shape or not np.isfinite([x,lower,upper]).all() or np.any(x<lower) or np.any(x>upper) or np.any(lower>=upper) or not np.isfinite(step) or step<=0:
        raise ValueError('Finite free controls inside ordered boxes and positive difference step required')
    base=np.asarray(function(x),float)
    if base.ndim!=1 or pattern.shape!=(len(base),len(x)) or not np.isfinite(base).all():raise ValueError('Finite matching constraint rows and structural graph required')
    groups=colors(pattern) if groups is None else groups
    width=upper-lower;h=np.minimum(step,width/4);forward=upper-x>=x-lower
    h=np.where(forward,np.minimum(h,upper-x),-np.minimum(h,x-lower))
    if np.any(h==0):raise ValueError('No finite-difference room inside control boxes')
    data=np.zeros(pattern.nnz)
    for group in groups:
        z=x.copy();z[group]+=h[group];sample=np.asarray(function(z),float)
        if sample.shape!=base.shape or not np.isfinite(sample).all():raise ValueError('Constraint population changed during differences')
        difference=sample-base
        for col in group:
            a,b=pattern.indptr[col:col+2];data[a:b]=difference[pattern.indices[a:b]]/h[col]
    return csc_matrix((data,pattern.indices.copy(),pattern.indptr.copy()),shape=pattern.shape)


def direction(x,g,j,lower,upper,trust=.0002):
    """Minimize linearized worst excess, then minimize its L1 coordinate step."""
    x,g,lower,upper=map(lambda a:np.asarray(a,float),(x,g,lower,upper));j=csr_matrix(j);n=len(x)
    if x.ndim!=1 or g.ndim!=1 or lower.shape!=x.shape or upper.shape!=x.shape or j.shape!=(len(g),n) or not np.isfinite([x,lower,upper]).all() or not np.isfinite(g).all() or not np.isfinite(j.data).all() or np.any(x<lower) or np.any(x>upper) or not np.isfinite(trust) or trust<=0:
        raise ValueError('Finite constraints/derivatives and bounded controls required')
    lo=np.maximum(-1.,(lower-x)/trust);hi=np.minimum(1.,(upper-x)/trust)
    matrix=hstack([j*trust,csr_matrix(-np.ones((len(g),1)))],format='csr')
    options=dict(primal_feasibility_tolerance=1e-9,dual_feasibility_tolerance=1e-9,time_limit=20.,threads=1)
    with warnings.catch_warnings():
        # SciPy forwards this known HiGHS option but emits a generic notice.
        warnings.filterwarnings('ignore',message='Unrecognized options detected:.*threads.*',category=OptimizeWarning)
        fit=linprog(np.r_[np.zeros(n),1.],A_ub=matrix,b_ub=-g,bounds=list(zip(lo,hi))+[(0.,None)],method='highs',options=options)
        record=dict(success=bool(fit.success),status=int(fit.status),message=str(fit.message),trust_radians=float(trust))
        if not fit.success:return None,record
        # The second LP retains the first LP's optimum (within 1e-10 normalized
        # numerical slack), while avoiding a gratuitous box-corner direction.
        identity=eye(n,format='csr');zero=csr_matrix((n,1));slack=csr_matrix((len(g),n))
        second=vstack([hstack([matrix,slack]),hstack([identity,zero,-identity]),hstack([-identity,zero,-identity])],format='csr')
        target=max(0.,float(fit.x[-1]))+1e-10
        sparse_fit=linprog(np.r_[np.zeros(n+1),np.ones(n)],A_ub=second,b_ub=np.r_[-g,np.zeros(2*n)],
            bounds=list(zip(lo,hi))+[(0.,target)]+[(0.,1.)]*n,method='highs',options=options)
    selected=sparse_fit if sparse_fit.success else fit
    delta=selected.x[:n]*trust
    record.update(linearized_worst_excess=float(fit.x[-1]),l1_phase_success=bool(sparse_fit.success),
        maximum_parameter_step=float(abs(delta).max(initial=0)),predicted_worst_excess=float(max(0.,(g+j@delta).max())))
    return delta,record


def merit(g):
    g=np.asarray(g,float)
    if g.ndim!=1 or not np.isfinite(g).all():raise ValueError('Finite serialized constraint vector required')
    positive=np.maximum(0,g)
    return float(positive.max(initial=0)),float(positive@positive)


def constraint_model(problem,x,*,quantized=False):
    """Finite-difference proxy; round stored keys before float64 interpolation."""
    values,_=problem.rotations(x)
    native=getattr(problem,'native_roundtrip',False)
    if quantized or native:values={n:q.astype(np.float32).astype(float) for n,q in values.items()}
    raw=signed_constraints(problem,values,problem.world(values))
    if not native:return raw
    from native_support_roundtrip import preview_values
    forwarded=preview_values(values,problem.channels)
    return np.r_[raw,signed_constraints(problem,forwarded,problem.world(forwarded))]


def restore(problem,start,evaluate,*,iterations=8,trust=.0002,observe=None,quantized=False):
    """Keep only strictly improved serialized minimax scores; retain every probe."""
    if type(iterations) is not int or not 1<=iterations<=32 or type(trust) not in (int,float) or not np.isfinite(trust) or not 0<trust<=.001:
        raise ValueError('Choose 1–32 repair iterations and up to .001 radians trust')
    if type(quantized) is not bool:raise ValueError('Explicit quantized difference mode required')
    x=np.asarray(start,float).copy();problem.rotations(x);current=np.asarray(evaluate(x,'start'),float);initial=merit(current)
    pattern=problem.sparsity();groups=colors(pattern);history=[];reason='iteration_budget'
    def model(z):return constraint_model(problem,z,quantized=quantized)
    difference_step=1e-7 if quantized else 1e-5
    minimum_trust=1e-9 if quantized else 1e-7
    radius=float(trust)
    for iteration in range(1,iterations+1):
        before=merit(current)
        if before[0]==0:reason='sampled_constraints_satisfied';break
        jac=colored_jacobian(model,x,problem.lower,problem.upper,pattern,groups,step=difference_step)
        delta,info=direction(x,current,jac,problem.lower,problem.upper,radius)
        info.update(iteration=iteration,before_merit=list(before),probes=[]);chosen=None
        if delta is not None:
            for backoff in range(10):
                fraction=.5**backoff;z=np.clip(x+delta*fraction,problem.lower,problem.upper)
                g=np.asarray(evaluate(z,f'{iteration}-{backoff}'),float);score=merit(g)
                acceptable=score[0]<before[0]-1e-12 or abs(score[0]-before[0])<=1e-12 and score[1]<before[1]-1e-15
                info['probes'].append(dict(fraction=fraction,merit=list(score),accepted=bool(acceptable)))
                if acceptable:chosen=fraction;x=z;current=g;break
        info.update(selected_fraction=chosen,after_merit=list(merit(current)));history.append(info)
        if observe:observe(info)
        if chosen is None:
            radius*=.25
            if radius<minimum_trust:reason='serialized_line_search_stalled';break
    return x,dict(initial_merit=list(initial),final_merit=list(merit(current)),history=history,
        reason=reason,iterations=len(history),maximum_iterations=iterations,trust_radians=trust,
        structural_colors=len(groups),difference_step_radians=difference_step,minimum_trust_radians=minimum_trust,
        difference_model='float32_keys_float64_interpolation' if quantized else 'smooth_float64',
        sampled_proxy_feasible=merit(current)[0]==0,quality_approved=False)


def check_controls(problem,controls):
    if controls.get('schema')!='strep-native-support-orientation-controls-v1':raise ValueError('Orientation controls schema required')
    for name in ('lower','upper'):
        if not np.array_equal(controls.get(name),getattr(problem,name)):raise ValueError('Warm control boxes differ from frozen source/draft')
    if len(controls.get('intervals',[]))!=len(problem.data):raise ValueError('Warm interval population differs')
    for d,c in zip(problem.data,controls['intervals']):
        expected=dict(id=d['row']['id'],chain=d['row']['chain'],clock_s=d['clock'].tolist(),edit_keys=d['row']['edit_keys'],
            bend_ids=d['ids'].tolist(),swivel_ids=d['swivel_ids'].tolist(),orientation_ids=d['orientation_ids'].tolist())
        if c!=expected:raise ValueError('Warm native interval/control indices differ')
    x=np.asarray(controls['parameters'],float);problem.rotations(x);return x


def seed_inputs(folder,source,spec_path,root):
    """Bind a completed four-trial source-matched study, including its archive."""
    folder=Path(folder).resolve()
    if folder.parent!=Path(root).resolve()/'reports':raise ValueError('Choose an immediate completed reports study for warm controls')
    request_path=folder/'request.json';result_path=folder/'result.json'
    request,result=read(request_path),read(result_path)
    if read(folder/'pipeline.json').get('status')!='complete' or result.get('status')!='complete':raise ValueError('Completed warm study required')
    method=request.get('proposal_method')
    if method not in ('joint_support_source_rate_orientation_search','serialized_native_support_feasibility_repair','serialized_native_support_coordinate_repair','serialized_native_support_roundtrip_repair') or len(result.get('trials',[]))!=4:
        raise ValueError('Four orientation-search or serialized-repair trials required')
    if request.get('spec')!=read(spec_path) or request['spec']['glb_sha256']!=sha256(source):raise ValueError('Warm study source/draft differs')
    bindings=dict(request['inputs'])
    def bind(path,digest):
        name=str(path)
        if name in bindings and bindings[name]!=digest:raise ValueError('Conflicting warm study evidence hashes')
        bindings[name]=digest
    for path in (request_path,result_path,folder/'pipeline.json'):bind(path,sha256(path))
    for name,h in request['implementation'].items():
        if Path(name).name!=name or Path(name).suffix!='.py':raise ValueError('Warm implementation filename required')
        bind(folder/'implementation'/name,h)
    for name,h in result['outputs'].items():
        if Path(name).name!=name:raise ValueError('Warm output filename required')
        bind(folder/name,h)
    seeds=[]
    for i,t in enumerate(result['trials']):
        if t.get('trial')!=i or t.get('status')!='complete' or len(t.get('proposal',[]))!=1:raise ValueError('Completed ordered warm trials required')
        p=t['proposal'][0];name=f'trial-{i}.controls.json'
        if p.get('controls_file')!=name or p.get('method')!=method:raise ValueError('Source-bound orientation controls and matching proposal method required')
        control=folder/name;bind(control,p['controls_sha256'])
        glb=folder/f'trial-{i}.glb';bind(glb,t['sha256'])
        if read(control).get('proposal_sha256')!=t['sha256']:raise ValueError('Warm control/proposal binding differs')
        seeds.append(control)
    for name,h in bindings.items():
        if sha256(name)!=h:raise ValueError('Warm study evidence hash differs')
    return seeds,bindings


def propose(rig,reader,rows,path,tau=.05,mu=.5,*,controls_path,iterations=8,trust=.0002,quantized=False,coordinates=False,strict_peaks=False,native_roundtrip=False):
    if type(coordinates) is not bool:raise ValueError('Explicit coordinate repair mode required')
    if type(strict_peaks) is not bool:raise ValueError('Explicit strict peak repair mode required')
    if type(native_roundtrip) is not bool:raise ValueError('Explicit native roundtrip repair mode required')
    controls_path=Path(controls_path);controls=read(controls_path)
    if controls.get('acceleration_time_s')!=tau or controls.get('reference_weight_per_s2')!=mu or controls.get('orientation_limit_degrees')!=1. or controls.get('swivel_limit_degrees')!=5.:
        raise ValueError('Warm seed settings differ from requested trial')
    problem_type=SupportOrientationProblem
    if native_roundtrip:
        from native_support_roundtrip import SupportRoundtripProblem
        problem_type=SupportRoundtripProblem
    problem=problem_type(rig,reader,rows,tau,mu);start=check_controls(problem,controls);path=Path(path);prefix=path.stem
    if strict_peaks:
        source_rates=measures(features(problem.raw[problem.rate_ids],problem.rig.joints),problem.caps.dt)
        problem.strict_rate_limits=limits(source_rates,problem.caps)
    probes=[]
    def evaluate(x,label):
        values,_=problem.rotations(x);file=path.with_name(prefix+'.repair-'+label+'.glb')
        if file.exists():raise ValueError('Choose a fresh serialized repair probe')
        export_rotations(rig.document,rig.binary,values,file)
        if label=='start' and sha256(file)!=controls['proposal_sha256']:raise ValueError('Warm controls do not reproduce their original GLB')
        actual=RigAsset.load(file);s=NativeSupportSampler(actual.document,actual.binary,0)
        world=np.array([s.sample(float(t)) for t in problem.times]);channels=rotation_channels(actual.document,actual.binary)
        g=signed_constraints(problem,{n:channels[n][2] for n in problem.nodes},world)
        record=dict(label=label,file=file.name,sha256=sha256(file),raw_merit=list(merit(g)))
        if native_roundtrip:
            from native_support_roundtrip import preview_values
            forwarded=preview_values({n:channels[n][2] for n in problem.nodes},problem.channels)
            preview=file.with_name(file.stem+'.preview.glb')
            export_rotations(rig.document,rig.binary,forwarded,preview)
            converted=RigAsset.load(preview);decoder=NativeSupportSampler(converted.document,converted.binary,0)
            preview_world=np.array([decoder.sample(float(t)) for t in problem.times])
            preview_channels=rotation_channels(converted.document,converted.binary)
            native_g=signed_constraints(problem,{n:preview_channels[n][2] for n in problem.nodes},preview_world)
            record.update(preview_file=preview.name,preview_sha256=sha256(preview),preview_merit=list(merit(native_g)),
                          raw_constraints_pass=bool(np.all(g<=0)),preview_constraints_pass=bool(np.all(native_g<=0)))
            g=np.r_[g,native_g]
        record['merit']=list(merit(g));probes.append(record)
        save(file.with_suffix('.json'),dict(record,controls=x.tolist(),quality_approved=False))
        return g
    def observe(row):
        save(path.with_suffix('.repair-progress.json'),dict(history=row,probes=probes,quality_approved=False))
        print(dict(trial=prefix,repair_iteration=row['iteration'],merit=row['after_merit'],
            selection=row.get('selected_screen_index') if coordinates else row['selected_fraction']),flush=True)
    if coordinates:
        from native_support_coordinates import restore as coordinate_restore
        x,report=coordinate_restore(problem,start,evaluate,iterations=iterations,trust=trust,observe=observe)
    else:
        x,report=restore(problem,start,evaluate,iterations=iterations,trust=trust,observe=observe,quantized=quantized or native_roundtrip)
    if native_roundtrip:
        evaluate(x,'final')
        report.update(native_roundtrip_constraints_pass=probes[-1]['preview_constraints_pass'],
                      serialized_raw_constraints_pass=probes[-1]['raw_constraints_pass'],
                      native_roundtrip=True,constraint_population='Raw GLB plus editable FP32-matrix preview model; actual NPZ/preview conversion still independent')
    values,_=problem.rotations(x);export_rotations(rig.document,rig.binary,values,path)
    final_controls=dict(controls,parameters=x.tolist(),proposal_sha256=sha256(path),
        scope='Repaired orientation controls; source/draft and independent serialized acceptance remain separate')
    saved=path.with_suffix('.controls.json');save(saved,final_controls)
    return [dict(report,method='serialized_native_support_roundtrip_repair' if native_roundtrip else 'serialized_native_support_coordinate_repair' if coordinates else 'serialized_native_support_feasibility_repair',variables=len(x),
        warm_controls_sha256=sha256(controls_path),controls_file=saved.name,controls_sha256=sha256(saved),
        strict_peak_limits=strict_peaks,absolute_peak_tolerance=STRICT_PEAK_TOLERANCE if strict_peaks else None,
        maximum_parameter_change=float(abs(x-start).max(initial=0)),probes=probes)]
