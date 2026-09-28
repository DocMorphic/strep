"""Independent terminal artifact and contact-pose checks for a refined partner trial."""
import argparse
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from compare_partner_paths import full_curve


def run(study,output):
    if output.exists():raise ValueError('Preserve earlier verification')
    status=read(study/'pipeline.json')['status']
    if status not in ('complete','complete_no_candidate'):raise ValueError('Wait for terminal study before verifying')
    request=read(study/'request.json');done=read(study/'completion.json');warm=Path(request['warm'])
    for path,digest in request['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Input identity changed')
    for name,digest in request['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Frozen implementation changed')
    if not done['accepted']:
        if sha256(study/'history.json')!=done['history_sha256']:raise ValueError('Rejected history changed')
        save(output,dict(at=now(),exported=False,completion_sha256=sha256(study/'completion.json'),quality_approved=False));return
    export=study/'export';complete=read(export/'completion.json')
    if sha256(export/'completion.json')!=done['export_completion_sha256'] or sha256(study/'parameters.json')!=done['parameters_sha256'] or sha256(study/'comparison.json')!=done['comparison_sha256']:raise ValueError('Terminal evidence changed')
    for name,key in [('manifest.json','manifest_sha256'),('source-evidence.json','source_evidence_sha256'),('engine-audit/verification.json','engine_sha256'),('geometry-summary.json','geometry_summary_sha256')]:
        if sha256(export/name)!=complete[key]:raise ValueError('Export evidence changed')
    manifest=read(export/'manifest.json')
    for name,item in manifest['assets'].items():
        path=(export/name).resolve()
        if not path.is_relative_to(export) or sha256(path)!=item['sha256']:raise ValueError('Export asset changed')
    checks=read(export/'engine-audit/verification.json')['checks']
    expected={(variant+'-seed-1301',actor) for variant in ['raw','candidate'] for actor in ['A','B']}
    if len(checks)!=4 or {(c['scene_id'],c['actor']) for c in checks}!=expected or complete['engine_actor_frames']!=600:raise ValueError('Incomplete engine proof')
    if complete['samples_per_scene']!=299 or complete['scenes']!=2:raise ValueError('Incomplete geometry clock')
    evidence=read(export/'source-evidence.json')
    for name,key in [('parameters.json','parameters_sha256'),('initial-parameters.json','initial_parameters_sha256'),('history.json','history_sha256')]:
        if sha256(study/name)!=evidence[key]:raise ValueError('Export source evidence changed')
    geometry=read(export/'geometry-summary.json')['rows']
    if len(geometry)!=2 or {row['variant'] for row in geometry}!={'raw','candidate'}:raise ValueError('Incomplete geometry scenes')
    for row in geometry:
        path=export/'geometry'/row['variant']/'samples.json'
        if sha256(path)!=row['samples_sha256']:raise ValueError('Geometry samples changed')
        curve=full_curve(read(path)['rows'])
        if curve['max_depth_m']!=row['max_depth_m'] or curve['floor_max_m']!=row['floor_max_depth_m'] or curve['failed_frames']!=row['collision_failed_frames']:raise ValueError('Geometry summary differs from samples')
    for check in checks:
        prefix='assets/'+check['actor']+'/'+check['scene_id'].split('-')[0]+'/'
        if check['frames']!=150 or check['glb_sha256']!=manifest['assets'][prefix+'character.glb']['sha256'] or check['source_sha256']!=manifest['assets'][prefix+'motion.npz']['sha256']:raise ValueError('Engine actor identity or clock changed')
    before=full_curve(read(warm/'export/geometry/candidate/samples.json')['rows']);after=full_curve(read(export/'geometry/candidate/samples.json')['rows'])
    warm_complete=read(warm/'export/completion.json')
    warm_summary=warm/'export/geometry-summary.json'
    if sha256(warm_summary)!=warm_complete['geometry_summary_sha256']:raise ValueError('Warm geometry evidence changed')
    for row in read(warm_summary)['rows']:
        if sha256(warm/'export/geometry'/row['variant']/'samples.json')!=row['samples_sha256']:raise ValueError('Warm samples changed')
    raw=full_curve(read(export/'geometry/raw/samples.json')['rows'])
    if raw!=full_curve(read(warm/'export/geometry/raw/samples.json')['rows']):raise ValueError('Raw baseline changed')
    comparison=read(study/'comparison.json')
    if comparison['before']!=before or comparison['after']!=after or comparison['raw']!=raw:raise ValueError('Published comparison differs from curves')
    cap_pass=all(new<=max(.005,old)+(1e-9 if old>.005 else 0) for old,new in zip(before['body_depth_m'],after['body_depth_m']))
    if cap_pass!=done['full_clock_cap_pass']:raise ValueError('Full-clock outcome differs')
    events=[]
    for actor in ['A','B']:
        poses=[]
        for folder in [warm/'export',export]:
            rig=RigAsset.load(folder/'assets'/actor/'candidate/character.glb');sampler=AnimationSampler(rig.document,rig.binary,0)
            poses.append(rig.vertices(sampler.sample(float(np.float32(75/30)))))
        error=float(np.abs(poses[1]-poses[0]).max());events.append(dict(actor=actor,event_mesh_max_error_m=error))
        if error>1e-6:raise ValueError('Exported contact event changed')
        bounds=read(export/(actor+'-decoded-bounds.json'))
        if not bounds['bounds']['passed'] or bounds['bounds']['samples']!=299:raise ValueError('Missing decoded motion bounds')
    save(output,dict(at=now(),exported=True,completion_sha256=sha256(study/'completion.json'),full_clock_cap_pass=cap_pass,
        before_peak_m=before['max_depth_m'],after_peak_m=after['max_depth_m'],floor_curve_unchanged=before['floor_depth_m']==after['floor_depth_m'],
        raw_peak_m=raw['max_depth_m'],verifier_sha256=sha256(__file__),
        event_checks=events,engine_actor_frames=600,failed_samples=len(after['failed_frames']),quality_approved=False,
        scope='Terminal input/export identities, full299-sample comparison, engine clock and separately decoded contact skin. No continuous collision, anatomy or human approval.'))
    print(dict(full_clock_cap_pass=cap_pass,before_peak_m=before['max_depth_m'],after_peak_m=after['max_depth_m']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study.resolve(),a.output.resolve())
