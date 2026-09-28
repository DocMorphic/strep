"""Adjacent-edit proposal margins with the same actual serialized foot and root safeguards."""
import argparse
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from study_repaired_root_release import prepare as prepare_source
from study_block_release import problem_for as block_problem
from conic_root_descent import affine_constraints
from conic_buffer_schedule import solve
from finalize_release_trial import finalize


def problem_for(request,envelope):
    p=block_problem(request,envelope);p.root=p.fitter.spec['root_node']
    if any(i<3 for i in p.free):raise ValueError('Repaired root must be eliminated')
    return p


def prepare(output,source,audit):
    prepare_source(output,source,audit)
    save(output/'pipeline.json',dict(at=now(),status='preparing_conic',quality_approved=False))
    request=read(output/'request.json');envelope=read(output/'envelope.json')
    request.update(steps=12,trusts=[1e-4,1e-5,1e-6],proposal_buffers=dict(support_speed=1e-5,foot_acceleration=1e-3),
        method='Audited repaired-root source, root eliminated, worst release selected. At most12 conic descent steps, three fixed trusts and8fractions each. Predicted foot-speed/acceleration caps tighten by min(1e-5m/s or1e-3m/s²,half cap) for movable cones. Clarabel100iterations/30s,1e-10 tolerances,1e-4 scaled-coordinate regularization. Solved/AlmostSolved only propose; unchanged actual serialized guards and objective descent decide.')
    request['proposal_buffers']['adjacent_edit']=1e-6
    request['method'] += ' Additional movable adjacent-joint edit prediction buffer1e-6 radians; root columns remain eliminated; actual adjacent-edit radius unchanged.'
    request['proposal_schedule']=[dict(buffer_scale=scale,trust=trust) for scale in [1.,.1,0.] for trust in request['trusts']]
    request['method'] += ' Fixed fallback schedule: all three trusts at buffer scale1, then0.1, then0; stop on first actually accepted step. Maximum9proposals per step; actual acceptance never changes.'
    diagnostic=ROOT/'reports/conic-edit-margin-diagnostic-rig03-v1.json';request['inputs'][str(diagnostic)]=sha256(diagnostic)
    bootstrap=ROOT/'reports/conic-solver-bootstrap-v1.json';meta=read(bootstrap);request['inputs'][str(bootstrap)]=sha256(bootstrap)
    for name,digest in meta['files'].items():request['inputs'][str(Path(meta['vendor'])/name)]=digest
    for name in ['conic_root_descent.py','conic_buffer_schedule.py','study_edit_buffer_conic_foot.py','finalize_release_trial.py']:
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);request['implementation'][name]=sha256(output/'implementation'/name)
    save(output/'request.json',request)
    with threadpool_limits(limits=1):
        p=problem_for(request,envelope);x=p.initial[np.ix_(p.frames,p.free)].ravel();c,j,cones=affine_constraints(p,x);first=p.evaluate(x)
        # These cones add fixed-root constraints to the original foot problem.
        margins=np.r_[c,[(v['cap']**2-v['vector']@v['vector'])/v['scale']**2 for v in cones]]
        split=len(margins)-len(p.acceleration_indices);identity=float(np.abs(margins[:split]-first[2]).max())
        if identity>1e-9 or margins.min()<-1e-8:raise ValueError('Original or fixed-root constraints differ')
        base=affine_constraints(p,x,False);rng=np.random.default_rng(733);rows=[]
        for _ in range(3):
            d=rng.normal(size=len(x));d/=np.linalg.norm(d);minus,plus=[affine_constraints(p,x+s*1e-6*d,False) for s in [-1,1]]
            rows.append(dict(linear_error=float(np.abs((plus[0]-minus[0])/2e-6-base[1]@d).max()),
                vector_error=max(float(np.abs((a['vector']-m['vector'])/2e-6-v['jacobian']@d).max()) for v,m,a in zip(base[2],minus[2],plus[2]))))
    passed=max(max(r.values()) for r in rows)<=2e-4
    save(output/'conic-proof.json',dict(at=now(),passed=passed,original_margin_identity_error=identity,minimum_margin=float(margins.min()),rows=rows,
        variables=len(x),linear_rows=len(c),norm_cones=len(cones),quality_approved=False))
    if not passed:
        save(output/'pipeline.json',dict(at=now(),status='preparation_failed',quality_approved=False));raise ValueError('Conic derivative proof failed')
    save(output/'freeze.json',dict(request_sha256=sha256(output/'request.json'),envelope_sha256=sha256(output/'envelope.json'),
        derivative_sha256=sha256(output/'derivative-proof.json'),conic_sha256=sha256(output/'conic-proof.json')))
    save(output/'pipeline.json',dict(at=now(),status='prepared',quality_approved=False));print(read(output/'conic-proof.json'))


def run(output):
    request=read(output/'request.json');freeze=read(output/'freeze.json')
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Preserve prior run')
    p=psutil.Process();save(output/'runner.json',dict(at=now(),pid=p.pid,created=p.create_time()))
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    def validate():
        for name,key in [('request.json','request_sha256'),('envelope.json','envelope_sha256'),('derivative-proof.json','derivative_sha256'),('conic-proof.json','conic_sha256')]:
            if sha256(output/name)!=freeze[key]:raise ValueError('Frozen protocol changed')
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Source changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
    try:
        validate();envelope=read(output/'envelope.json')
        with threadpool_limits(limits=1):
            p=problem_for(request,envelope);phase('fitting');values,solver=solve(p,request['steps'],tuple(request['trusts']),lambda item:phase('fitting',**item),request['proposal_buffers'],request['proposal_schedule'])
            phase('verifying_and_engine');result=finalize(output,request,p.fitter,p.initial,values,envelope,solver)
        validate();save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),**result,quality_approved=False));phase('complete',passed_development_screen=result['passed_development_screen'])
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path);p.add_argument('--source',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.command=='prepare':
        if not a.source or not a.audit:p.error('--source and --audit required')
        prepare(a.output.resolve(),a.source.resolve(),a.audit.resolve())
    else:run(a.output.resolve())
