"""Fresh source certificate for older fixed-root trials, without rewriting them."""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_guarded_release import run as decoded_audit
from audit_release_normalized import run as normalized_audit

SCHEMA='strep-angular-source-v1'


def require_legacy_audit(audit,completion_hash,decoded_hash):
    if audit.get('study_completion_sha256')!=completion_hash or audit.get('decoded_audit_sha256')!=decoded_hash:
        raise ValueError('Legacy audit must bind exact completed source and decoded audit')
    if 'strict_checks' in audit:
        checks=audit['strict_checks']
        passed=audit.get('strict_checks_passed') is True and audit.get('original_full_checks_passed') is True
    elif 'envelope_checks' in audit:
        checks=audit['envelope_checks']
        passed=audit.get('failed_full_checks')==[] and audit.get('protected_parameters_unchanged') is True and audit.get('accepted_parameter_reconstruction') is True and audit.get('new_release_failures_relative_to_source')==[]
    else:raise ValueError('Unsupported legacy audit schema')
    if not passed or not checks or not all(v is True for v in checks.values()):raise ValueError('Every legacy preservation and original comparison must pass')


def certify(source,audit_path,output):
    if output.exists():raise ValueError('Preserve earlier source certificate')
    request=read(source/'request.json');spec=read(source/'take/spec.json');old_decoded=audit_path.parent/'decoded.json'
    require_legacy_audit(read(audit_path),sha256(source/'completion.json'),sha256(old_decoded))
    if read(old_decoded)['completion_sha256']!=sha256(source/'completion.json'):raise ValueError('Legacy decoded source differs')
    output.mkdir(parents=True);decoded_audit(source,output/'decoded.json');normal=normalized_audit(source,output/'normalized.json');decoded=read(output/'decoded.json')
    paths=[Path(request['held'])/'candidate/character.glb',source/'take/candidate/character.glb'];roots=[]
    for path in paths:
        rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
        roots.append(np.array([sampler.sample(float(np.float32(f/spec['fps'])))[spec['root_node']] for f in range(spec['frames'])]))
    root_error=float(np.abs(roots[1]-roots[0]).max());acc=np.linalg.norm(np.diff(roots[1][:,:3,3],n=2,axis=0)*spec['fps']**2,axis=1)
    prior=Path(request['prior'])/'verification.json';proof=source/'take/verification.json'
    limit=max(read(prior)['metrics']['candidate']['root_acceleration_max_m_s2'],read(proof)['metrics']['input']['root_acceleration_max_m_s2'])+1e-5
    checks=dict(**decoded['envelope_checks'],strict_normalized=normal['all_applicable_checks_passed'],original_comparisons_passed=not decoded['failed_full_checks'],source_root_matrices_preserved=root_error<=1e-12,
        original_root_limit_passed=bool(np.isfinite(acc).all() and acc.max()<=limit))
    inputs={str(p):sha256(p) for p in [source/'completion.json',source/'request.json',source/'envelope.json',source/'take/parameters.npz',*paths,audit_path,old_decoded,prior,proof,output/'decoded.json',output/'normalized.json']}
    save(output/'completion.json',dict(schema=SCHEMA,at=now(),source=str(source),completion_sha256=sha256(source/'completion.json'),request_sha256=sha256(source/'request.json'),
        implementation_sha256=sha256(__file__),inputs=inputs,checks=checks,all_source_checks_passed=all(checks.values()),decoded_audit=str(output/'decoded.json'),decoded_audit_sha256=sha256(output/'decoded.json'),
        root_matrix_error=root_error,root_envelope=dict(root_original_limit_m_s2=float(limit),root_safety_caps_m_s2=acc.tolist()),engine_actor_frames=decoded['engine_actor_frames'],quality_approved=False,
        scope='Fresh decoded/normalized/engine source verification for old fixed-root trial. Root safety caps equal measured source at each center; original comparison limit exactly matches existing compare(). No source mutation or fabricated repaired-root audit.'))
    print(dict(checks=checks,root_limit=limit,root_peak=float(acc.max())))
    if not all(checks.values()):raise ValueError('Source is ineligible; retained certificate records failed checks')


def validate(source,path):
    cert=read(path)
    if cert.get('schema')!=SCHEMA or cert.get('source')!=str(source) or cert['completion_sha256']!=sha256(source/'completion.json') or cert['request_sha256']!=sha256(source/'request.json'):
        raise ValueError('Source certificate binding differs')
    if cert.get('all_source_checks_passed') is not True or not cert.get('checks') or not all(v is True for v in cert['checks'].values()):raise ValueError('Source certificate did not pass')
    for name,digest in cert['inputs'].items():
        if sha256(name)!=digest:raise ValueError('Certified source artifact changed')
    decoded=Path(cert['decoded_audit'])
    if sha256(decoded)!=cert['decoded_audit_sha256']:raise ValueError('Decoded certificate changed')
    return read(decoded),decoded


def root_envelope(source,audit_path,envelope):
    fields={'root_original_limit_m_s2','root_safety_caps_m_s2'}
    if fields<=envelope.keys():return envelope
    if fields&envelope.keys():raise ValueError('Incomplete existing root envelope')
    validate(source,audit_path);cert=read(audit_path)
    return dict(envelope,**cert['root_envelope'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('audit',type=Path);p.add_argument('output',type=Path);a=p.parse_args();certify(a.source.resolve(),a.audit.resolve(),a.output.resolve())
