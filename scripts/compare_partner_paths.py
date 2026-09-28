"""Compare completed strict/screen-preserving paths on their full decoded clocks."""
import argparse
from pathlib import Path
import math
from strep import read,save,sha256,now


def full_curve(rows):
    clock=[i*.5 for i in range(299)]
    if [r['frame'] for r in rows]!=clock:raise ValueError('Require every whole/half frame in the full 150-frame clip')
    depth=[];floor=[]
    for row in rows:
        if len(row['collision'])!=2 or len(row['floor_depth_m'])!=2:raise ValueError('Both actors required')
        values=[c['max_depth_m'] for c in row['collision']]+row['floor_depth_m']
        if any(not math.isfinite(v) or v<0 for v in values):raise ValueError('Finite nonnegative geometry required')
        depth.append(max(c['max_depth_m'] for c in row['collision']));floor.append(max(row['floor_depth_m']))
    return dict(frames=clock,body_depth_m=depth,floor_depth_m=floor,max_depth_m=max(depth),floor_max_m=max(floor),
        peak_frame=clock[depth.index(max(depth))],failed_frames=[f for f,d in zip(clock,depth) if d>.005])


def load(folder):
    folder=Path(folder).resolve()
    if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Full completion audit is not terminal/complete')
    done=read(folder/'completion.json');request=read(folder/'request.json');study=Path(request['study'])
    if sha256(study/'request.json')!=request['study_request_sha256']:raise ValueError('Study request changed')
    for file,key in [('manifest.json','manifest_sha256'),('source-evidence.json','source_evidence_sha256'),('engine-audit/verification.json','engine_sha256'),('geometry-summary.json','geometry_summary_sha256')]:
        if sha256(folder/file)!=done[key]:raise ValueError('Completion evidence changed: '+file)
    for name,digest in request['implementation'].items():
        if sha256(folder/'implementation'/name)!=digest:raise ValueError('Completion implementation snapshot changed')
    for name,digest in read(study/'request.json')['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Study implementation snapshot changed')
    evidence=read(folder/'source-evidence.json')
    for name,key in [('parameters.json','parameters_sha256'),('initial-parameters.json','initial_parameters_sha256'),('history.json','history_sha256')]:
        if sha256(study/name)!=evidence[key]:raise ValueError('Study output changed')
    manifest=read(folder/'manifest.json')
    for name,item in manifest['assets'].items():
        path=(folder/name).resolve()
        if not path.is_relative_to(folder) or sha256(path)!=item['sha256']:raise ValueError('Scene asset changed/escaped')
    engine=read(folder/'engine-audit/verification.json')['checks']
    if len(engine)!=4 or {(c['scene_id'],c['actor']) for c in engine}!={(v+'-seed-1301',a) for v in ['raw','candidate'] for a in ['A','B']}:
        raise ValueError('Engine actor/scene population differs')
    for c in engine:
        variant='raw' if c['scene_id'].startswith('raw') else 'candidate';prefix='assets/'+c['actor']+'/'+variant+'/'
        if c['frames']!=150 or c['glb_sha256']!=manifest['assets'][prefix+'character.glb']['sha256'] or c['source_sha256']!=manifest['assets'][prefix+'motion.npz']['sha256']:
            raise ValueError('Engine clock/source mismatch')
    if done['engine_actor_frames']!=600 or done['samples_per_scene']!=299 or done['scenes']!=2:raise ValueError('Incomplete completion population')
    for actor in ['A','B']:
        bounds=read(folder/(actor+'-decoded-bounds.json'))
        if not bounds['bounds']['passed'] or bounds['bounds']['samples']!=299:raise ValueError('Decoded bounds failed')
    result={}
    for row in read(folder/'geometry-summary.json')['rows']:
        path=folder/'geometry'/row['variant']/'samples.json'
        if sha256(path)!=row['samples_sha256']:raise ValueError('Geometry samples changed')
        curve=full_curve(read(path)['rows'])
        if curve['max_depth_m']!=row['max_depth_m'] or curve['floor_max_m']!=row['floor_max_depth_m'] or curve['failed_frames']!=row['collision_failed_frames']:
            raise ValueError('Published geometry extrema disagree with full samples')
        result[row['variant']]=dict(curve=curve,event=row['event'],samples_sha256=row['samples_sha256'])
    if set(result)!={'raw','candidate'}:raise ValueError('Missing geometry variant')
    return dict(folder=str(folder),completion_sha256=sha256(folder/'completion.json'),request=read(study/'request.json'),
        initial=read(study/'initial-parameters.json'),history=read(study/'history.json')['iterations'],manifest=manifest,variants=result)


def run(strict,screen,output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier comparisons')
    a,b=load(strict),load(screen)
    fixed=['seed','source_scene_sha256','sources','source_summary_sha256','pose_results_sha256','palm_region_sha256','frames','knots','envelope_frames','joint_edit_degrees','adjacent_rotation_vector_edit_degrees','iterations','inner_max_iterations','component_trust_degrees','safeguard_trials']
    if any(a['request'][k]!=b['request'][k] for k in fixed) or a['initial']!=b['initial']:raise ValueError('Matched initialization/protocol differs')
    if a['variants']['raw']['curve']!=b['variants']['raw']['curve']:raise ValueError('Decoded raw baselines differ')
    for actor in ['A','B']:
        for name in ['character.glb','motion.npz']:
            key='assets/'+actor+'/raw/'+name
            if a['manifest']['assets'][key]!=b['manifest']['assets'][key]:raise ValueError('Raw source assets differ')
    old=a['variants']['candidate']['curve'];new=b['variants']['candidate']['curve']
    changes=dict(newly_failing_frames=[f for f,x,y in zip(old['frames'],old['body_depth_m'],new['body_depth_m']) if x<=.005<y],
        worsened_frames=[f for f,x,y in zip(old['frames'],old['body_depth_m'],new['body_depth_m']) if y>x+1e-8],
        maximum_increase_m=max(y-x for x,y in zip(old['body_depth_m'],new['body_depth_m'])),
        peak_change_m=new['max_depth_m']-old['max_depth_m'])
    rows=[]
    for name,item in [('raw',a['variants']['raw']),('strict',a['variants']['candidate']),('screen',b['variants']['candidate'])]:
        event=item['event'];curve=item['curve']
        rows.append(dict(method=name,max_body_depth_m=curve['max_depth_m'],peak_frame=curve['peak_frame'],failed_samples=len(curve['failed_frames']),floor_max_m=curve['floor_max_m'],event_gap_m=event['gap_m'],opposing_normal_degrees=event['region']['opposing_normal_degrees']))
    output.mkdir(parents=True)
    save(output/'curves.json',dict(raw=a['variants']['raw']['curve'],strict=old,screen=new))
    save(output/'summary.json',dict(at=now(),rows=rows,full_clock_changes=changes,strict_completion_sha256=a['completion_sha256'],screen_completion_sha256=b['completion_sha256'],
        accepted_steps={n:sum(t['accepted'] for i in x['history'] for t in i.get('step_trials',[])) for n,x in [('strict',a),('screen',b)]},
        curves_sha256=sha256(output/'curves.json'),verifier_sha256=sha256(__file__),quality_approved=False,
        scope='Same development seed, initialization and fixed protocol. Both decoded full clocks/exports/engine inputs verified. Sparse guard improvements are checked for off-sample regressions; no continuous collision, anatomy, realism or held-out approval.'))
    print(rows);print(changes)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('strict',type=Path);p.add_argument('screen',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.strict,a.screen,a.output)
