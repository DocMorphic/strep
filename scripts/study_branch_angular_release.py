"""Frozen per-joint angular repair from a passing root/contact development clip."""
import argparse
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from angular_source import audited_source
from angular_branch_proof import prove
from legacy_angular_source import root_envelope
from study_block_release import problem_for as foot_problem
from angular_release_block import AngularBlockProblem,rotation_steps
from projected_angular_conic import affine_constraints,solve
from finalize_release_trial import finalize


def decoded_rotations(path,nodes,count,fps):
    rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
    world=np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)])
    return localize(world,rig.parents)[:,nodes,:3,:3]


def problem_for(request,envelope):
    internal=dict(request,target=dict(centers=[request['frames'][0]+1],side_index=0,limit_m_s2=0.))
    return AngularBlockProblem(foot_problem(internal,envelope),envelope['angular'])


def prepare(output,source,audit):
    if output.exists():raise ValueError('Preserve prior trial')
    decoded,release_audit=audited_source(source,audit)
    if decoded['failed_full_checks']:raise ValueError('Every original root/contact comparison must already pass')
    original=read(source/'request.json');spec=read(source/'take/spec.json');nodes=[j['node'] for j in spec['edit_joints'].values()]
    paths=[source/'take/input/character.glb',Path(original['prior'])/'candidate/character.glb',source/'take/candidate/character.glb']
    rotations=[decoded_rotations(path,nodes,spec['frames'],spec['fps']) for path in paths]
    angles=[rotation_steps(r) for r in rotations]
    # A new development comparison, not a physiological speed limit or revised old verdict.
    reference=np.maximum(angles[0].max(axis=0),angles[1].max(axis=0))+np.radians(1e-5)
    excess=angles[2]-reference[None];edge,joint=np.unravel_index(np.argmax(excess),excess.shape)
    if excess[edge,joint]<=0:raise ValueError('No per-joint peak regression to repair')
    target=dict(end_frame=int(edge+1),joint_index=int(joint),node=int(nodes[joint]),role=list(spec['edit_joints'])[joint],limit_radians=float(reference[joint]))
    frames=list(range(max(0,edge-2),min(spec['frames'],edge+4)))
    envelope=root_envelope(source,audit,read(source/'envelope.json'));envelope['protected_columns']=sorted(set(envelope['protected_columns'])|{0,1,2})
    caps=np.asarray(envelope['safety_caps_m_s2']);dynamics=read(source/'take/release-dynamics.json')['candidate']
    for side_index,side in enumerate(spec['patches']):
        for release in dynamics['feet'][side]['releases']:
            event=next(e for e in decoded['events'] if (e['side'],e['release_frame'])==(side,release['release_frame']))
            caps[np.asarray(release['acceleration_frames'])-1,side_index]=np.minimum(caps[np.asarray(release['acceleration_frames'])-1,side_index],event['limit_m_s2'])
    envelope['safety_caps_m_s2']=caps.tolist()
    envelope['angular']=dict(nodes=nodes,reference_global_caps_radians=reference.tolist(),safety_caps_radians=np.maximum(angles[2],reference[None]).tolist(),target=target,
        policy='Each edited joint global reference peak is max(raw, prior) plus1e-5degrees. Per-edge safety cap is max(source edge, reference peak), so existing regressions may improve but cannot grow. Largest excess selects the target before fitting. No retroactive changes to old study decisions.')
    names=set(original['implementation'])|{'legacy_angular_source.py','study_repaired_root_release.py','conic_root_descent.py','root_release_block.py','finalize_release_trial.py','study_block_release.py','angular_source.py','study_branch_angular_release.py','angular_branch_proof.py','check_piecewise_derivative.py','angular_release_block.py','angular_conic_descent.py','projected_angular_conic.py'}
    inputs=dict(original['inputs'])
    for path in [*paths,source/'request.json',source/'completion.json',source/'envelope.json',source/'take/parameters.npz',source/'take/release-dynamics.json',audit,release_audit]:inputs[str(path)]=sha256(path)
    bootstrap=ROOT/'reports/conic-solver-bootstrap-v1.json';meta=read(bootstrap);inputs[str(bootstrap)]=sha256(bootstrap)
    for name,digest in meta['files'].items():inputs[str(Path(meta['vendor'])/name)]=digest
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in sorted(names):shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),case=original.get('case',Path(original['prior']).name),held=original['held'],prior=original['prior'],source=str(source),source_audit=str(release_audit),independent_source_audit=str(audit),
        root_reference=str(paths[2]),protected_nodes=original['protected_nodes'],frames=frames,angular_target=target,inputs=inputs,
        implementation={n:sha256(output/'implementation'/n) for n in sorted(names)},steps=12,trusts=[.01,.001,.0001],
        proposal_buffers=dict(support_speed=1e-5,foot_acceleration=1e-3,adjacent_edit=1e-6,angular_step=1e-6),
        proposal_schedule=[dict(buffer_scale=scale,trust=trust) for scale in [1.,.1,0.] for trust in [.01,.001,.0001]],
        method='At most12 accepted conic angular-descent steps; fixed scale/trust schedule and8fractions. Chordal rotation-matrix norm is exactly monotonic in local relative angle from0to pi. Root eliminated; original contact/root/edit constraints plus new per-joint step safety caps. Angular target objective is squared chord excess times(180/pi)^2. Actual serialized acceptance>=-1e-8, geometry and objective descent remain mandatory. Trusts include larger steps for the measured1.55degree joint regression but never widen original absolute/adjacent limits.',quality_approved=False)
    diagnostic=ROOT/'reports/angular-backpedal-branch-diagnostic-v1.json';request['inputs'][str(diagnostic)]=sha256(diagnostic)
    request['method'] += ' Derivative preflight checks the same seeded directions at1e-6, retrying1e-7 only if the hover minimum branch changes. Both perturbations must share the base branch; unchanged2e-4error limit applies to objective, constraint and vector derivatives.'
    request['method'] += ' Solved/AlmostSolved finite deltas are clipped into the intersection of the frozen trust and original absolute-coordinate box before prediction/actual evaluation. Raw deltas and projection differences retained. No feasibility tolerance changes.'
    request['inputs'][str(source/'take/solver.json')]=sha256(source/'take/solver.json')
    save(output/'request.json',request);save(output/'envelope.json',envelope)
    with threadpool_limits(limits=1):
        p=problem_for(request,envelope);x=p.initial[np.ix_(p.frames,p.free)].ravel();first=p.evaluate(x);c,j,cones=affine_constraints(p,x)
        margin=np.r_[c,[(v['cap']**2-v['vector']@v['vector'])/v['scale']**2 for v in cones]];identity=float(np.abs(margin-first[2]).max())
        rows=prove(p,x,affine_constraints)
        geometry=p.geometric_guard(p.initial)
    passed=identity<1e-9 and first[2].min()>=-1e-8 and geometry and all(r['passed'] for r in rows)
    proof=dict(at=now(),passed=bool(passed),rows=rows,initial_objective=first[0],initial_minimum_constraint=float(first[2].min()),geometry=geometry,variables=len(x),constraints=len(first[2]),original_margin_identity_error=identity,quality_approved=False)
    save(output/'derivative-proof.json',proof);save(output/'conic-proof.json',proof)
    save(output/'freeze.json',dict(request_sha256=sha256(output/'request.json'),envelope_sha256=sha256(output/'envelope.json'),derivative_sha256=sha256(output/'derivative-proof.json'),conic_sha256=sha256(output/'conic-proof.json')))
    save(output/'pipeline.json',dict(at=now(),status='prepared' if passed else 'preparation_failed',quality_approved=False));print(proof)
    if not passed:raise ValueError('Angular preflight failed; evidence retained')


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
