"""Verify the full frozen two-action/five-seed partner study population."""
import argparse
from pathlib import Path
from strep import ROOT,read,save,sha256,now
from study_breadth_partners_v2 import validate


def run(output):
    output=Path(output).resolve();spec=validate(output);data=read(output/'results.json');manifest=read(output/'manifest.json')
    if read(output/'pipeline.json')['status']!='complete':raise ValueError('Partner study not complete')
    if read(output/'runner.json')['status']!='stopped':raise ValueError('Partner worker has not stopped')
    ids=[r['id'] for r in data['rows']]
    if len(ids)!=len(set(ids)) or set(ids)!={s['id'] for s in spec['scenes']} or len(ids)!=spec['planned_pairs']:raise ValueError('Incomplete population')
    files={};rows=[];actor_frames=0;errors=[]
    def record(path):
        path=Path(path);files[str(path.relative_to(output))]=sha256(path)
    for entry in spec['scenes']:
        row=next(r for r in data['rows'] if r['id']==entry['id']);folder=output/entry['id'];scene=read(output/entry['scene'])['scene']
        if row['status']!='complete' or row['human_review'] is not None or row['quality_approved'] is not False:raise ValueError('Unexpected result status')
        point=read(folder/'point-audit.json');floor=read(folder/'floor-audit.json');collision=read(folder/'partner-surface-audit.json')
        if point!=row['point_metrics'] or floor['max_depth_m']!=row['floor_depth_m']:raise ValueError('Summary differs from audit')
        if collision['frames_checked']!=list(range(scene['frame_count'])):raise ValueError('Missing collision frames')
        pair=collision['pairs'][0]
        if pair['max_depth_m']!=row['partner_depth_max_m'] or pair['frames_over_tolerance']!=row['partner_frames_over_tolerance']:raise ValueError('Collision summary mismatch')
        if len(pair['frames'])!=scene['frame_count'] or any(len(f['directions'])!=2 for f in pair['frames']):raise ValueError('Missing bilateral frame evidence')
        group=output/'engine-groups'/entry['id']/'audit';engine=read(group/'verification.json');actual=read(group/'engine-output.json')
        if read(group/'pipeline.json')['status']!='complete' or engine!=row['engine'] or len(actual['scenes'])!=1:raise ValueError('Engine proof mismatch')
        if len(engine['checks'])!=2 or set(actual['scenes'][0]['actors'])!={'A','B'}:raise ValueError('Missing engine actors')
        for name,actor in scene['actors'].items():
            source=entry['sources'][name]
            for kind in ['motion','glb']:
                if sha256(source['original_'+kind])!=source['original_'+kind+'_sha256']:raise ValueError('Original source changed')
            if sha256(ROOT/actor['motion'])!=actor['source_sha256'] or sha256(output/actor['preview_glb'])!=manifest['assets'][actor['preview_glb']]['sha256']:raise ValueError('Scene input changed')
            check=next(c for c in engine['checks'] if c['actor']==name)
            if check['source_sha256']!=actor['source_sha256'] or check['glb_sha256']!=sha256(output/actor['preview_glb']) or check['frames']!=scene['frame_count']:raise ValueError('Engine input/clock mismatch')
            observed=actual['scenes'][0]['actors'][name]
            frames=actual['scenes'][0]['frames']
            if len(frames)!=scene['frame_count'] or len(observed['bone_names'])!=77 or any(len(f[name])!=77 for f in frames):raise ValueError('Engine population incomplete')
            if max(check['position_error_m'],check['rotation_element_error'])>1e-4:raise ValueError('Engine screen failed')
            actor_frames+=check['frames'];errors.append(check)
            record(output/actor['preview_glb'])
        for name in ['scene.json','point-audit.json','floor-audit.json','partner-surface-audit.json']:record(folder/name)
        for name in ['verification.json','engine-output.json','request.json']:record(group/name)
        rows.append(dict(id=entry['id'],case=entry['case'],seed=entry['seed'],requested_gap_max_m=point['requested_gap_max_m'],
            requested_point_frames_met=point['requested_frames_within_point_tolerance'],requested_frames=point['requested_frame_count'],
            timing_error_frames=point['nearest_within_tolerance_timing_error_frames'],normal_max_degrees=point['requested_normal_error_max_degrees'],
            penetration_max_m=pair['max_depth_m'],penetration_frames=pair['frames_over_tolerance']))
    for name in ['protocol.json','manifest.json','freeze.json','results.json','runner.json','pipeline.json']:record(output/name)
    result=dict(at=now(),pairs=len(rows),actors=spec['planned_actors'],actor_frames=actor_frames,all_bones=77,
        point_interval_passes=sum(r['requested_point_frames_met']==r['requested_frames'] for r in rows),
        penetration_diagnostic_passes=sum(r['penetration_max_m']<=spec['penetration_diagnostic_m'] for r in rows),
        max_engine_position_error_m=max(c['position_error_m'] for c in errors),max_engine_rotation_error=max(c['rotation_element_error'] for c in errors),
        rows=rows,files=files,implementation_sha256=sha256(__file__),quality_approved=False,human_reviews=0,
        scope='Complete fixed handshake/high-five development population: independently prompted actors with authored placement/contact timing. Hash-bound numerical/engine records, not independent semantic review or general partner capability.')
    save(output/'completion-verification.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);r=run(p.parse_args().output);print({k:v for k,v in r.items() if k not in ['rows','files']})
