"""Independently recompute completed minimax export evidence and full curves."""
import argparse
from pathlib import Path
from strep import read,save,sha256,now,ROOT
from compare_partner_paths import full_curve


def load_export(folder):
    done=read(folder/'completion.json')
    # The conditional wrapper owns the terminal state; the inner exporter
    # leaves its progress file at the last geometry sample.
    if read(folder.parent/'pipeline.json')['status']!='complete':raise ValueError('Incomplete export wrapper')
    for name,key in [('manifest.json','manifest_sha256'),('source-evidence.json','source_evidence_sha256'),
                     ('engine-audit/verification.json','engine_sha256'),('geometry-summary.json','geometry_summary_sha256')]:
        if sha256(folder/name)!=done[key]:raise ValueError('Completion hash mismatch')
    if (done['engine_actor_frames'],done['samples_per_scene'],done['scenes'])!=(600,299,2):raise ValueError('Incomplete export population')
    manifest=read(folder/'manifest.json')
    for name,item in manifest['assets'].items():
        path=(folder/name).resolve()
        if not path.is_relative_to(folder) or sha256(path)!=item['sha256']:raise ValueError('Asset changed or escaped')
    engine=read(folder/'engine-audit/verification.json')['checks']
    if len(engine)!=4 or {(c['scene_id'],c['actor']) for c in engine}!={(v+'-seed-1301',a) for v in ['raw','candidate'] for a in ['A','B']}:
        raise ValueError('Engine population differs')
    for row in engine:
        v=row['scene_id'].split('-')[0];prefix='assets/'+row['actor']+'/'+v+'/'
        if row['frames']!=150 or row['source_sha256']!=manifest['assets'][prefix+'motion.npz']['sha256'] or row['glb_sha256']!=manifest['assets'][prefix+'character.glb']['sha256']:
            raise ValueError('Engine source or clock differs')
        if row['position_error_m']>1e-5 or row['rotation_element_error']>1e-5:raise ValueError('Engine transforms disagree')
    for actor in ['A','B']:
        if not read(folder/(actor+'-integer-bounds.json'))['passed']:raise ValueError('Integer bounds failed')
        bounds=read(folder/(actor+'-decoded-bounds.json'))['bounds']
        if not bounds['passed'] or bounds['samples']!=299:raise ValueError('Decoded bounds failed')
    variants={}
    for row in read(folder/'geometry-summary.json')['rows']:
        path=folder/'geometry'/row['variant']/'samples.json'
        if sha256(path)!=row['samples_sha256']:raise ValueError('Samples changed')
        samples=read(path)['rows'];curve=full_curve(samples)
        if curve['max_depth_m']!=row['max_depth_m'] or curve['floor_max_m']!=row['floor_max_depth_m'] or curve['failed_frames']!=row['collision_failed_frames']:
            raise ValueError('Published full curve differs')
        if samples[150]!=row['event']:raise ValueError('Published event differs from full curve')
        variants[row['variant']]=dict(curve=curve,event=row['event'])
    if set(variants)!={'raw','candidate'}:raise ValueError('Missing variant')
    return dict(variants=variants,manifest=manifest,engine=engine,completion_sha256=sha256(folder/'completion.json'))


def run(folder,output):
    folder,output=folder.resolve(),output.resolve()
    if output.exists():raise ValueError('Preserve prior verification')
    request,done=read(folder/'request.json'),read(folder/'completion.json');study=Path(request['study'])
    for path,digest in [(study/'request.json',request['study_request_sha256']),
        (study/'completion.json',done['minimax_completion_sha256']),
        (folder/'export/completion.json',done['export_completion_sha256']),
        (folder/'event-preservation.json',done['event_preservation_sha256'])]:
        if sha256(path)!=digest:raise ValueError('Wrapper provenance changed')
    for name,digest in request['implementation'].items():
        if sha256(folder/'implementation'/name)!=digest:raise ValueError('Implementation snapshot changed')
    adapter=folder/'export-input';evidence=read(folder/'export/source-evidence.json')
    for name,key in [('parameters.json','parameters_sha256'),('initial-parameters.json','initial_parameters_sha256'),('history.json','history_sha256')]:
        if sha256(adapter/name)!=evidence[key]:raise ValueError('Export input changed')
    for name in ['parameters.json','history.json']:
        if sha256(adapter/name)!=sha256(study/name):raise ValueError('Adapter differs from completed minimax')
    original=ROOT/'reports/seeded-dynamic-witness-validation-v1/export'
    old,new=load_export(original),load_export(folder/'export')
    if old['variants']['raw']!=new['variants']['raw']:raise ValueError('Raw geometry baseline changed')
    for actor in ['A','B']:
        for name in ['character.glb','motion.npz']:
            key='assets/'+actor+'/raw/'+name
            if old['manifest']['assets'][key]!=new['manifest']['assets'][key]:raise ValueError('Raw assets changed')
    locked=read(folder/'event-preservation.json')
    if {r['actor'] for r in locked['rows']}!={'A','B'}:raise ValueError('Missing event actor')
    for row in locked['rows']:
        key='assets/'+row['actor']+'/candidate/character.glb'
        if row['source_sha256']!=old['manifest']['assets'][key]['sha256'] or row['candidate_sha256']!=new['manifest']['assets'][key]['sha256'] or row['max_vertex_error_m']>1e-6:
            raise ValueError('Event proof source or tolerance differs')
    a,b=old['variants']['candidate']['curve'],new['variants']['candidate']['curve']
    raw=new['variants']['raw']['curve']
    changes=dict(old_to_new_peak_m=b['max_depth_m']-a['max_depth_m'],raw_to_new_peak_m=b['max_depth_m']-raw['max_depth_m'],
        worsened_vs_previous_frames=[f for f,x,y in zip(a['frames'],a['body_depth_m'],b['body_depth_m']) if y>x+1e-8],
        newly_failing_vs_previous_frames=[f for f,x,y in zip(a['frames'],a['body_depth_m'],b['body_depth_m']) if x<=.005<y],
        full_body_screen_pass=b['max_depth_m']<=.005,full_floor_screen_pass=b['floor_max_m']<=.005)
    output.mkdir(parents=True)
    save(output/'curves.json',dict(raw=raw,previous=a,minimax=b))
    rows=[dict(method=name,peak_m=curve['max_depth_m'],peak_frame=curve['peak_frame'],floor_m=curve['floor_max_m'],failed_samples=len(curve['failed_frames'])) for name,curve in [('raw',raw),('previous',a),('minimax',b)]]
    save(output/'summary.json',dict(at=now(),rows=rows,changes=changes,event_preservation=locked,
        current_engine_actor_frames=600,curves_sha256=sha256(output/'curves.json'),
        wrapper_completion_sha256=sha256(folder/'completion.json'),previous_completion_sha256=old['completion_sha256'],
        implementation_sha256=sha256(__file__),quality_approved=False,
        scope='Full integer/half-frame vertex-depth consistency, unchanged raw assets, encoded limits,600 engine actor-frames and recorded decoded event preservation. No continuous, self or triangle collision certificate and no animator approval.'))
    print(rows);print(changes)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder,a.output)
