"""Bind experimental region decisions to retained inputs, exports and audits."""
import argparse
import hashlib
import shutil
from pathlib import Path
from strep import ROOT,read,save,sha256,now


def run(export,study):
    export=Path(export).resolve();study=Path(study).resolve()
    if (export/'completion-verification.json').exists():raise ValueError('Preserve completion evidence')
    for folder in [study,export]:
        if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Experiment still incomplete')
        request=read(folder/'request.json')
        for name,digest in request['implementation'].items():
            if sha256(folder/'implementation'/name)!=digest:raise ValueError('Implementation snapshot changed')
    manifest=read(export/'manifest.json')
    for path,entry in manifest['assets'].items():
        if sha256(export/path)!=entry['sha256']:raise ValueError('GLB changed')
    verify=read(export/'region-verification.json');request=read(study/'request.json')
    if verify['request_sha256']!=sha256(study/'request.json') or verify['region_sha256']!=sha256(study/'palm-region.json'):raise ValueError('Region specification changed')
    engine=read(export/'engine-audit/verification.json')
    if len(engine['checks'])!=4 or any(c['frames']!=150 for c in engine['checks']):raise ValueError('Missing paired engine population')
    expected={entry['sha256'] for entry in manifest['assets'].values()}
    if {c['glb_sha256'] for c in engine['checks']}!=expected:raise ValueError('Engine GLB mismatch')
    source=ROOT/'reports/breadth-partners-v2/SOMA-preview-LICENSE.txt'
    for folder in [study,export]:
        if not (folder/source.name).exists():shutil.copyfile(source,folder/source.name)
    verifier=ROOT/'scripts/verify_palm_region.py';snapshot=verifier.read_bytes()
    reconstructed=False
    if hashlib.sha256(snapshot).hexdigest()!=verify['verifier_sha256']:
        # V1 ran before explicit aggregate booleans were added. Reconstruct only
        # that known revision, and require its original recorded content hash.
        text=snapshot.decode('utf-8')
        newer="orientation_screen_passed=region['opposing_normal_degrees']<=screen['opposing_normal_max_degrees'],\n            penetration_screen_passed=max(c['max_depth_m'] for c in collision)<=screen['max_event_penetration_m'])\n        result[variant]['event_screens_passed']=all(result[variant][k] for k in ['region_area_screen_passed','orientation_screen_passed','penetration_screen_passed'])"
        older="orientation_screen_passed=region['opposing_normal_degrees']<=screen['opposing_normal_max_degrees'])"
        snapshot=text.replace(newer,older).encode('utf-8');reconstructed=True
    if hashlib.sha256(snapshot).hexdigest()!=verify['verifier_sha256']:raise ValueError('Cannot recover matching verifier source')
    (export/'region-verifier.py').write_bytes(snapshot)
    candidate=verify['variants']['candidate'];screen=verify['screen']
    passed=dict(region_area=candidate['region_area_screen_passed'],opposing_normals=candidate['orientation_screen_passed'],
        penetration=max(c['max_depth_m'] for c in candidate['collision'])<=screen['max_event_penetration_m'])
    history=read(study/'history.json')['iterations']
    files={str(p.relative_to(export)):sha256(p) for p in export.rglob('*') if p.is_file() and 'project' not in p.relative_to(export).parts}
    result=dict(at=now(),source_study=str(study),request_sha256=sha256(study/'request.json'),history_sha256=sha256(study/'history.json'),
        files=files,verifier_source_reconstructed_and_hash_matched=reconstructed,screen=screen,event_screens=passed,
        event_screens_passed=all(passed.values()),event_depth_m=max(c['max_depth_m'] for c in candidate['collision']),
        contact_solver_max_distance_m=max(max(d['distances_m']) for d in history[-1]['contact']),
        iterations=len(history)-1,solver_success_flags=[h['solver_success'] for h in history[1:]],
        all_context_preservation=read(export/'preservation.json'),engine_actor_frames=sum(c['frames'] for c in engine['checks']),
        continuous_or_whole_window_collision_approved=False,human_approved=False,quality_approved=False,
        scope='Observed development event only; changed region intent is explicit, original center-point failures retained. Event numerical passes alone do not qualify an interaction.')
    save(export/'completion-verification.json',result);print({k:result[k] for k in ['event_screens','event_depth_m','contact_solver_max_distance_m','iterations','engine_actor_frames']})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('export',type=Path);p.add_argument('study',type=Path);a=p.parse_args();run(a.export,a.study)
