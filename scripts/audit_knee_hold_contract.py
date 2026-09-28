"""Measure a proposed one-second knee hold without rewriting original contracts."""
import argparse
import copy
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from compare_reference_temporal_knee import verified_audit
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from strep import ROOT, now, read, save, sha256


def interval_metrics(points, target, sample_fps, contact_limit):
    points=np.asarray(points,float);target=np.asarray(target,float)
    if (points.ndim!=2 or points.shape[1]!=3 or len(points)<2 or target.shape!=(3,)
        or not np.isfinite(points).all() or not np.isfinite(target).all()
        or not np.isfinite(sample_fps) or sample_fps<=0
        or not np.isfinite(contact_limit) or contact_limit<=0):
        raise ValueError('Finite 3D tracks with two or more samples and positive rates/limits required')
    errors=np.linalg.norm(points-target,axis=1)
    speeds=np.linalg.norm(np.diff(points,axis=0),axis=1)*sample_fps
    horizontal=np.linalg.norm(np.diff(points[:,[0,2]],axis=0),axis=1)*sample_fps
    return dict(samples=len(points),contact_error_max_m=float(errors.max()),
        contact_error_p95_m=float(np.percentile(errors,95)),
        contact_samples_passed=int(np.sum(errors<=contact_limit)),
        contact_sample_fraction=float(np.mean(errors<=contact_limit)),
        all_contact_samples_passed=bool(np.all(errors<=contact_limit)),
        peak_speed_m_s=float(speeds.max()),speed_p95_m_s=float(np.percentile(speeds,95)),
        peak_horizontal_speed_m_s=float(horizontal.max()),
        horizontal_drift_from_first_max_m=float(np.linalg.norm((points-points[0])[:,[0,2]],axis=1).max()),
        vertical_range_m=float(np.ptp(points[:,1])))


def run(output):
    if output.exists():raise ValueError('Preserve earlier hold-contract audit')
    studies=[ROOT/'reports'/n for n in ('knee-contact-temporal-v1','knee-contact-reference-v1')]
    audits=[ROOT/'reports'/n for n in ('knee-contact-temporal-audit-v1','knee-contact-reference-audit-v1')]
    records=[verified_audit(a) for a in audits]
    if records[0]['case']!=records[1]['case']:raise ValueError('Require matched case')
    case=records[0]['case']
    request=ROOT/'reports/action-jobs/kneel-ending-guides-v1/takes'/case/'request.json'
    source=ROOT/'reports/kneel-body-clearance-v1/takes'/case/'soma.glb'
    # Verify both audits bind the exact source being compared.
    for r in records:
        if r['inputs'][str(source)]!=sha256(source):raise ValueError('Source changed')
    spec=copy.deepcopy(read(studies[1]/'spec.json'))
    for c in spec['contacts']:c.update(start_frame=60,end_frame_exclusive=90)
    spec['provenance']='New development authoring contract: retain center-frame knee patches/targets for requested 2..3 second pause. Fixed material patches are an experimental choice, not human-confirmed support labels. Original single-frame study remains unchanged.'
    # The prompt pause is a pre-existing timed segment, not selected from outputs.
    prompt=read(request)
    if ([s['duration_s'] for s in prompt['segments']] != [2,1,3]
        or prompt['segments'][1]['prompt'] != 'A person pauses upright on both knees.'):
        raise ValueError('Expected original 2..3 second upright knee-pause request')
    output.mkdir(parents=True)
    save(output/'proposed-spec.json',spec)
    files=[*[(a/'verification.json') for a in audits],source,request,studies[1]/'spec.json']
    save(output/'protocol.json',dict(at=now(),case=case,inputs={str(p):sha256(p) for p in files},
        implementation_sha256=sha256(Path(__file__)),request=prompt,
        contract='Fixed center-frame targets over frames [60,90), corresponding to the pre-existing one-second requested pause. This is an additional proposed contract, not a requirement claimed by previous solvers.',
        sample_step_frames=.125,quality_approved=False))
    frames=np.arange(60.,90.,.125);rows=[]
    with threadpool_limits(limits=1):
        for label,path in [('body_input',source),('limb_zero_prior',studies[0]/'candidate.glb'),('body_reference_prior',studies[1]/'candidate.glb')]:
            rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
            tracks={c['patch']:[] for c in spec['contacts']};floor=[]
            for frame in frames:
                points=rig.vertices(sampler.sample(float(frame/spec['fps'])))
                floor.append(max(0.,-float(points[:,1].min())))
                for name in tracks:tracks[name].append(points[spec['patches'][name]['vertices']].mean(0).tolist())
            stats={c['patch']:interval_metrics(tracks[c['patch']],c['target_position_m'],spec['fps']*8,spec['screen']['contact_error_m']) for c in spec['contacts']}
            for c in spec['contacts']:
                errors=np.linalg.norm(np.array(tracks[c['patch']])-c['target_position_m'],axis=1)
                stats[c['patch']]['worst_error_frame']=float(frames[np.argmax(errors)])
            save(output/f'{label}-tracks.json',dict(frames=frames.tolist(),tracks=tracks,floor_m=floor))
            rows.append(dict(variant=label,source=str(path),source_sha256=sha256(path),patches=stats,
                floor_max_m=max(floor),floor_samples_passed=all(d<=spec['screen']['floor_depth_m'] for d in floor),
                tracks_sha256=sha256(output/f'{label}-tracks.json'),
                held_contract_passed=all(s['all_contact_samples_passed'] for s in stats.values())))
    save(output/'verification.json',dict(at=now(),protocol_sha256=sha256(output/'protocol.json'),
        proposed_spec_sha256=sha256(output/'proposed-spec.json'),rows=rows,quality_approved=False,human_review=None,
        scope='Three existing full clips; 240 samples in proposed hold per clip. No new motion fitted. Constant material patches are a proposed contact authoring choice, not a semantic or force-balance judgment.'))
    print(rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    run(parser.parse_args().output.resolve())
