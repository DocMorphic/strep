"""Foot-release blocks initialized from an independently audited root repair."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from study_block_release import problem_for,run
from select_release_block import select_block
from check_piecewise_derivative import check_direction


def audited_source(source,audit_path):
    done=read(source/'completion.json');audit=read(audit_path)
    if audit['completion_sha256']!=sha256(source/'completion.json') or done['request_sha256']!=sha256(source/'request.json'):
        raise ValueError('Independent audit must bind this exact completed source')
    if read(source/'pipeline.json')['status']!='complete':raise ValueError('Completed source required')
    for name,digest in done['files'].items():
        if sha256(source/name)!=digest:raise ValueError('Source output changed')
    if 'all_root_aware_checks_passed' in audit:
        passed=audit['all_root_aware_checks_passed'];release_audit=audit_path.parent/'fixed-root-diagnostic.json'
        digest=audit['fixed_root_diagnostic_sha256']
    else:
        passed=audit['all_repaired_root_checks_passed'];release_audit=Path(audit['decoded_audit']);digest=audit['decoded_audit_sha256']
    if not passed or sha256(release_audit)!=digest:raise ValueError('Passing source guards and bound release measurements required')
    decoded=read(release_audit)
    if decoded['completion_sha256']!=sha256(source/'completion.json'):raise ValueError('Release audit belongs to another source')
    if any(not name.endswith('_every_release_acceleration_no_worse') for name in decoded['failed_full_checks']):
        raise ValueError('Root repair and every non-release original check must already pass')
    return decoded,release_audit


def prepare(output,source,audit_path):
    if output.exists():raise ValueError('Preserve previous study')
    decoded,release_audit=audited_source(source,audit_path);original=read(source/'request.json');spec=read(source/'take/spec.json')
    if spec['fps']!=30:raise ValueError('Current encoder requires30fps')
    envelope=read(source/'envelope.json');envelope['protected_columns']=sorted(set(envelope['protected_columns'])|{0,1,2})
    root_limit=envelope['root_original_limit_m_s2']
    envelope['root_safety_caps_m_s2']=np.minimum(envelope['root_safety_caps_m_s2'],root_limit).tolist()
    dynamics=read(source/'take/release-dynamics.json');caps=np.asarray(envelope['safety_caps_m_s2']);releases=[]
    for index,side in enumerate(spec['patches']):
        tracks=[dynamics[v]['feet'][side]['releases'] for v in ['input','prior','candidate']]
        if len({len(t) for t in tracks})!=1:raise ValueError('Release population differs')
        for raw,prior,current in zip(*tracks):
            if len({r['release_frame'] for r in [raw,prior,current]})!=1:raise ValueError('Release clocks differ')
            limit=max(raw['acceleration_max_m_s2'],prior['acceleration_max_m_s2'])+1e-5
            protection=max(limit,current['acceleration_max_m_s2']);centers=current['acceleration_frames']
            caps[np.asarray(centers)-1,index]=np.minimum(caps[np.asarray(centers)-1,index],protection)
            releases.append(dict(side=side,release_frame=current['release_frame'],centers=centers,original_limit_m_s2=limit,frozen_protection_m_s2=protection))
    envelope['safety_caps_m_s2']=caps.tolist();envelope['release_protection']=releases
    selection=select_block(decoded['events'],releases,spec['frames'])
    target=dict(centers=selection['centers'],side_index=list(spec['patches']).index(selection['side']),limit_m_s2=selection['limit_m_s2'],release_frame=selection['release_frame'])
    names=set(original['implementation'])|{'study_repaired_root_release.py'};inputs=dict(original['inputs'])
    for path in [source/'request.json',source/'completion.json',source/'envelope.json',source/'take/parameters.npz',source/'take/fit-summary.json',source/'take/release-dynamics.json',source/'take/candidate/character.glb',audit_path,release_audit]:
        inputs[str(path)]=sha256(path)
    request=dict(at=now(),case=original['case'],held=original['held'],prior=original['prior'],source=str(source),source_audit=str(release_audit),
        independent_source_audit=str(audit_path),frames=selection['frames'],selection=selection,target=target,
        protected_nodes=original['protected_nodes'],maxiter=80,inputs=inputs,root_reference=str(source/'take/candidate/character.glb'),
        method='One automatically selected coupled foot-release block from independently audited root-repaired source. Root coordinates eliminated; preserve corrected root, protected joint, all original surface/dynamics/edit guards. Existing root and release caps may tighten to resolved source limits but never loosen. One80iteration SLSQP proposal and8fixed safeguard fractions.',
        acceptance='Original full comparison unchanged. Compare root preservation to audited repaired source, retaining original-held root diagnostic separately. All missing human/held-out evidence remains missing.',quality_approved=False)
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request['implementation']={name:sha256(output/'implementation'/name) for name in sorted(names)}
    save(output/'request.json',request);save(output/'envelope.json',envelope)
    with threadpool_limits(limits=1):
        problem=problem_for(request,envelope);x=problem.initial[np.ix_(problem.frames,problem.free)].ravel();rows=[];rng=np.random.default_rng(733)
        def signature(y):
            values=problem.values(y);active=[]
            for frame in problem.frames:
                positions=problem.fitter.surface_jacobian(int(frame),values[frame])[0]
                active.extend(int(ids[np.argmin(positions[ids,1])]) for side,ids in enumerate(problem.patches) if envelope['active_frames'][frame][side])
            return active
        for _ in range(3):
            d=rng.normal(size=len(x));d/=np.linalg.norm(d);rows.append(check_direction(lambda y:problem.evaluate(y,False),signature,x,d))
        first=problem.evaluate(x);geometry=problem.geometric_guard(problem.initial)
    valid=all(r['passed'] for r in rows) and first[2].min()>=-1e-7 and geometry
    proof=dict(at=now(),rows=rows,passed=bool(valid),initial_objective=first[0],initial_minimum_constraint=float(first[2].min()),geometry=geometry,variables=len(x),constraints=len(first[2]),quality_approved=False)
    save(output/'derivative-proof.json',proof)
    if not valid:
        save(output/'pipeline.json',dict(at=now(),status='preparation_failed',quality_approved=False));raise ValueError('Preflight failed; evidence retained')
    save(output/'freeze.json',dict(request_sha256=sha256(output/'request.json'),envelope_sha256=sha256(output/'envelope.json'),derivative_sha256=sha256(output/'derivative-proof.json')))
    save(output/'pipeline.json',dict(at=now(),status='prepared',quality_approved=False));print(proof)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path);p.add_argument('--source',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    if a.command=='prepare':
        if not a.source or not a.audit:p.error('--source and --audit required')
        prepare(a.output.resolve(),a.source.resolve(),a.audit.resolve())
    else:run(a.output.resolve())
