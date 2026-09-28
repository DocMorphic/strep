"""Summarize the complete paired generation population without quality promotion."""
import argparse
from pathlib import Path
from strep import read,save,sha256,now


def run(audit,output):
    audit,output=Path(audit).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier summary')
    if read(audit/'pipeline.json')['status']!='complete':raise ValueError('Require complete scene audit')
    completion=read(audit/'completion.json');manifest=read(audit/'manifest.json');results=read(audit/'results.json')['rows']
    if sha256(audit/'results.json')!=completion['results_sha256'] or sha256(audit/'manifest.json')!=completion['manifest_sha256']:raise ValueError('Changed audit population')
    expected={(m,s) for m in ['baseline','hand','body'] for s in [1301,2089,3253,4099,5101]}
    if len(results)!=15 or {(r['method'],r['seed']) for r in results}!=expected:raise ValueError('Incomplete method/seed population')
    files={}
    for relative,entry in manifest['assets'].items():
        if sha256(audit/relative)!=entry['sha256']:raise ValueError('Changed audit asset: '+relative)
        files[relative]=entry['sha256']
    frames=sorted(set(range(150))|{60+i*.5 for i in range(61)});rows=[];total=0
    for result in results:
        folder=audit/result['id'];samplefile=folder/'samples.json';enginefile=folder/'engine-audit/verification.json'
        if result['status']!='complete' or sha256(samplefile)!=result['samples_sha256'] or sha256(enginefile)!=result['engine_sha256']:raise ValueError('Incomplete/changed scene evidence')
        samples=read(samplefile)['rows'];engine=read(enginefile)['checks']
        if [s['frame'] for s in samples]!=frames or len(engine)!=2 or {c['actor'] for c in engine}!={'A','B'} or any(c['frames']!=150 for c in engine):raise ValueError('Incomplete sample/engine population')
        total+=sum(c['frames'] for c in engine)
        event=next(s for s in samples if s['frame']==75)
        if event!=result['event']:raise ValueError('Event summary mismatch')
        maximum=max(c['max_depth_m'] for s in samples for c in s['collision']);floor=max(max(s['floor_depth_m']) for s in samples)
        if maximum!=result['max_depth_m'] or floor!=result['floor_max_depth_m']:raise ValueError('Extrema mismatch')
        region=all(d['within_tolerance_count']>=3 and min(d['source_area_witness']['area_m2'],d['target_area_witness']['area_m2'])>=2.5e-5 for d in event['region']['directions'])
        rows.append(dict(id=result['id'],method=result['method'],seed=result['seed'],event_gap_m=event['gap_m'],point_pass=event['gap_m']<=.03,
            event_region_pass=region,whole_clip_max_depth_m=maximum,whole_clip_floor_depth_m=floor,collision_pass=maximum<=.005,floor_pass=floor<=.005))
        files[samplefile.relative_to(audit).as_posix()]=sha256(samplefile);files[enginefile.relative_to(audit).as_posix()]=sha256(enginefile)
    if total!=4500 or total!=completion['engine_actor_frames']:raise ValueError('Incomplete engine frames')
    comparisons=[]
    for seed in [1301,2089,3253,4099,5101]:
        group={r['method']:r for r in rows if r['seed']==seed}
        for method in ['hand','body']:
            base,current=group['baseline'],group[method]
            comparisons.append(dict(seed=seed,method=method,point_improvement_m=base['event_gap_m']-current['event_gap_m'],
                depth_increase_m=current['whole_clip_max_depth_m']-base['whole_clip_max_depth_m'],floor_increase_m=current['whole_clip_floor_depth_m']-base['whole_clip_floor_depth_m']))
    output.mkdir();save(output/'summary.json',dict(at=now(),audit=str(audit),completion_sha256=sha256(audit/'completion.json'),verifier_sha256=sha256(__file__),
        verified_files=files,rows=rows,comparisons=comparisons,engine_actor_frames=total,quality_approved=False,
        scope='Complete development population. Raw baseline uses its saved baseline placement; guided actors use the declared common guide placement. Source target itself fails point/region/floor checks. No isolated model-error attribution, continuous collision, action correctness or animator approval.'))
    lines=['# Complete shared-guide comparison','',f'15 pairs, 180 decoded samples per pair, {total:,} actual engine actor-frames. All recorded source assets and sample/engine proof hashes checked.','',
        '| Method | Seed | Event palm gap (mm) | Worst body penetration (mm) | Worst floor penetration (mm) | Event region |',
        '|---|---:|---:|---:|---:|---|']
    for row in rows:lines.append(f"| {row['method']} | {row['seed']} | {row['event_gap_m']*1000:.2f} | {row['whole_clip_max_depth_m']*1000:.2f} | {row['whole_clip_floor_depth_m']*1000:.2f} | {'pass' if row['event_region_pass'] else 'fail'} |")
    lines.extend(['','The original authored target itself fails point, region and floor screens. Guided-vs-baseline outcomes combine target placement and generation effects; they do not isolate model error. A completed engine import or an individual geometric screen is not animation approval. No independent human ratings or cleanup-time evidence are included.'])
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print({'pairs':len(rows),'engine_actor_frames':total,'quality_approved':False},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('audit',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.audit,a.output)
