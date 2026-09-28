"""Audit foot release correction against the already-repaired source root."""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now
from verify_block_release import run as block_audit
from audit_release_normalized import run as normalized_audit
from angular_source import audited_source
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler


def run(folder,output):
    if output.exists():raise ValueError('Preserve existing audit')
    request=read(folder/'request.json');source=Path(request['source'])
    audited_source(source,Path(request['independent_source_audit']))
    reference=source/'take/candidate/character.glb'
    if request['root_reference']!=str(reference) or request['inputs'].get(str(reference))!=sha256(reference):raise ValueError('Root reference binding differs')
    output.mkdir(parents=True);block_audit(folder,output/'block');base=read(output/'block/completion.json')
    normalized=normalized_audit(folder,output/'normalized.json');spec=read(folder/'take/spec.json');envelope=read(folder/'envelope.json')
    roots=[]
    for path in [reference,folder/'take/candidate/character.glb']:
        rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
        roots.append(np.array([sampler.sample(float(np.float32(f/spec['fps'])))[spec['root_node']] for f in range(spec['frames'])]))
    error=float(np.abs(roots[1]-roots[0]).max());acceleration=np.diff(roots[1][:,:3,3],n=2,axis=0)*spec['fps']**2
    magnitude=np.linalg.norm(acceleration,axis=1);caps=np.asarray(envelope['root_safety_caps_m_s2']);margin=(caps**2-magnitude**2)/np.maximum(caps**2,1.)
    checks={k:v for k,v in base['envelope_checks'].items() if k!='held_root_acceleration_preserved'}
    checks.update(repaired_source_root_preserved=error<=1e-12,root_original_comparison_passed=bool(magnitude.max()<=envelope['root_original_limit_m_s2']),
        frozen_root_envelope_passed=bool(np.isfinite(margin).all() and margin.min()>=-1e-8),
        strict_normalized_foot_geometry_edits=normalized['all_applicable_checks_passed'],no_new_release_failures_relative_to_source=not base['new_release_failures_relative_to_source'])
    result=dict(at=now(),completion_sha256=sha256(folder/'completion.json'),implementation_sha256=sha256(__file__),
        block_audit_sha256=sha256(output/'block/completion.json'),decoded_audit=str(output/'block/decoded.json'),decoded_audit_sha256=sha256(output/'block/decoded.json'),
        normalized_audit_sha256=sha256(output/'normalized.json'),checks=checks,all_repaired_root_checks_passed=all(checks.values()),
        root_source_max_matrix_error=error,root_acceleration_max_m_s2=float(magnitude.max()),root_minimum_normalized_margin=float(margin.min()),
        failed_full_checks=base['failed_full_checks'],untouched_frames=base['untouched_frames'],untouched_decoded_max_matrix_error=base['untouched_decoded_max_matrix_error'],
        engine_actor_frames=base['engine_actor_frames'],quality_approved=False,
        scope='Preserve independently audited repaired root, not the earlier failing held root. Original-held diagnostic remains unmodified. All-frame strict constraints, corrected-root comparison, original full-screen and engine audit; no human or held-out quality claim.')
    save(output/'completion.json',result);print(result)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder.resolve(),a.output.resolve())
