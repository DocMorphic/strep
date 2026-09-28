"""Conic proposals with stricter predicted foot bounds; actual limits unchanged."""
import argparse
from pathlib import Path
import shutil
import traceback
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from study_root_release_block import problem_for
from conic_root_descent import solve, affine_constraints
import numpy as np
from finalize_release_trial import finalize


def prepare(output,source,audit_path):
    if output.exists():raise ValueError('Preserve prior trial')
    old=read(source/'request.json');audit=read(audit_path);done=read(source/'completion.json')
    if audit['completion_sha256']!=sha256(source/'completion.json') or not audit['all_root_aware_checks_passed'] or audit['target_passed']:
        raise ValueError('Audited feasible source with unresolved root target required')
    if read(source/'pipeline.json')['status']!='complete':raise ValueError('Completed source required')
    for name,digest in done['files'].items():
        if sha256(source/name)!=digest:raise ValueError('Source artifact changed')
    envelope=read(source/'envelope.json');request=dict(old)
    request.update(at=now(),source_trial=str(source),independent_source_audit=str(audit_path),steps=12,trusts=[1e-4,1e-5,1e-6],proposal_buffers=dict(support_speed=1e-5,foot_acceleration=1e-3),
        method='At most12 conic descent steps, trust1e-4/1e-5/1e-6 and8fixed fractions each. Predicted movable foot-speed caps tightened by min(1e-5m/s,half cap), foot acceleration by min(1e-3m/s²,half cap), all other predicted caps unchanged. Actual acceptance and envelope.json caps unchanged. Norm constraints retain affine velocity/acceleration/edit vectors; floor and selected-hover constraints affine. Clarabel max100iterations/30s each, normalized tolerance1e-10, regularization1e-4 on scaled coordinates. Solved/AlmostSolved statuses permit proposals only; unchanged actual serialized strict constraints and geometry plus objective improvement decide acceptance.',quality_approved=False)
    request['inputs']=dict(old['inputs'])
    for path in [source/'request.json',source/'completion.json',source/'envelope.json',source/'take/parameters.npz',source/'take/candidate/character.glb',source/'take/solver.json',audit_path,ROOT/'reports/root-block-proposal-diagnostic-v1.json',ROOT/'reports/conic-root-rejection-diagnostic-v1.json']:
        request['inputs'][str(path)]=sha256(path)
    names=set(old['implementation'])|{'conic_root_descent.py','study_conic_root_descent.py','study_buffered_conic_root.py'}
    bootstrap=ROOT/'reports/conic-solver-bootstrap-v1.json';meta=read(bootstrap)
    request['inputs'][str(bootstrap)]=sha256(bootstrap)
    for name,digest in meta['files'].items():request['inputs'][str(Path(meta['vendor'])/name)]=digest
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request['implementation']={name:sha256(output/'implementation'/name) for name in sorted(names)}
    save(output/'request.json',request);save(output/'envelope.json',envelope)
    with threadpool_limits(limits=1):
        p=problem_for(request,envelope);x=p.initial[p.frames[:,None],p.free].ravel();first=p.evaluate(x);geometry=p.geometric_guard(first[5])
    if first[2].min()<-1e-8 or first[0]<=0 or not geometry:raise ValueError('Initial strict feasibility/objective differs')
    with threadpool_limits(limits=1):
        c,j,cones=affine_constraints(p,x)
        margins=np.r_[c,[(v['cap']**2-v['vector']@v['vector'])/v['scale']**2 for v in cones]]
        identity_error=float(np.abs(margins-first[2]).max())
        if identity_error>1e-9:raise ValueError('Conic representation differs from original constraints')
        base=affine_constraints(p,x,False);rng=np.random.default_rng(924);rows=[]
        for _ in range(3):
            d=rng.normal(size=len(x));d/=np.linalg.norm(d)
            minus,plus=[affine_constraints(p,x+sign*1e-6*d,False) for sign in [-1,1]]
            linear_error=float(np.abs((plus[0]-minus[0])/2e-6-base[1]@d).max())
            vector_error=max(float(np.abs((a['vector']-m['vector'])/2e-6-v['jacobian']@d).max()) for v,m,a in zip(base[2],minus[2],plus[2]))
            rows.append(dict(linear_error=linear_error,vector_error=vector_error))
        passed=max(max(r.values()) for r in rows)<=2e-4
    save(output/'conic-proof.json',dict(at=now(),passed=passed,original_margin_identity_error=identity_error,rows=rows,
        linear_rows=len(c),norm_cones=len(cones),variables=len(x),quality_approved=False,
        scope='Actual skin affine-vector derivative and original normalized constraint identity; no derivative of float quantization.'))
    if not passed:
        save(output/'pipeline.json',dict(at=now(),status='preparation_failed',quality_approved=False));raise ValueError('Actual conic derivative proof failed')
    save(output/'preflight.json',dict(at=now(),objective=first[0],minimum_constraint=float(first[2].min()),geometry=geometry,
        scope='Source strict constraints checked; new conic representation and vector derivative proof required before running.',quality_approved=False))
    save(output/'freeze.json',{name:sha256(output/name) for name in ['request.json','envelope.json','preflight.json','conic-proof.json']})
    save(output/'pipeline.json',dict(at=now(),status='prepared',quality_approved=False));print(read(output/'preflight.json'))


def run(output):
    request=read(output/'request.json');freeze=read(output/'freeze.json')
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Preserve previous run')
    p=psutil.Process();save(output/'runner.json',dict(at=now(),pid=p.pid,created=p.create_time()))
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    def validate():
        for name,digest in freeze.items():
            if sha256(output/name)!=digest:raise ValueError('Protocol changed')
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Input changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
    try:
        validate();envelope=read(output/'envelope.json')
        with threadpool_limits(limits=1):
            problem=problem_for(request,envelope);phase('fitting');values,solver=solve(problem,request['steps'],tuple(request['trusts']),lambda item:phase('fitting',**item),request['proposal_buffers'])
            phase('verifying_and_engine');result=finalize(output,request,problem.fitter,problem.initial,values,envelope,solver)
        validate();save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),**result,quality_approved=False));phase('complete',passed_development_screen=result['passed_development_screen'])
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path);p.add_argument('--source',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.command=='prepare':
        if not a.source or not a.audit:p.error('--source and --audit required')
        prepare(a.output.resolve(),a.source.resolve(),a.audit.resolve())
    else:run(a.output.resolve())
