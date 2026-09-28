"""Preserve the full matched profile/rig denominator in a readable report."""
import argparse
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now


def summarize(study,output):
    study,output=Path(study),Path(output)
    analysis=read(study/'profile-analysis.json');protocol=read(study/'protocol.json')
    if analysis['protocol_sha256']!=sha256(study/'protocol.json') or analysis['results_sha256']!=sha256(study/'results.json'):raise ValueError('Analysis inputs changed')
    if sha256(study/'source-executed-analysis.py')!=protocol['source_executed_analysis_sha256']:raise ValueError('Source metric snapshot changed')
    for name,digest in protocol['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Implementation snapshot changed')
    if analysis['planned']!=108 or len(analysis['rows'])!=108 or len(analysis['engine'])!=36:raise ValueError('Study denominator differs')
    rows=[]
    for action in ['wave','squat','kick']:
        source=analysis['source_response'][action]
        rows.append(dict(action=action,rig='native',response=source))
        for rig in protocol['rigs']:
            response=analysis['target_response'][rig['id']+'/'+action]
            rows.append(dict(action=action,rig=rig['id'],response=response,numerical_screen_changed=response['numerical_direction_screen_pass']!=source['numerical_direction_screen_pass']))
    complete=[r for r in analysis['rows'] if r['status']=='complete']
    transfer_rows=read(study/'results.json')['rows'];ground=[]
    for rig in protocol['rigs']:
        selected=[r for r in transfer_rows if r['rig']==rig['id'] and r['status']=='complete']
        hover=[r.get('predicted_support_foot_region_hover_max_m') for r in selected]
        finite=[v for v in hover if v is not None]
        ground.append(dict(rig=rig['id'],completed=len(selected),floor_over_10mm=sum(r['result']['target_mesh_floor_depth_max_m']>.01 for r in selected),hover_measured=len(finite),hover_missing=len(hover)-len(finite),hover_min_m=min(finite) if finite else None,hover_max_m=max(finite) if finite else None,sole_draft_errors=sorted({r['sole_draft_error'] for r in selected if r.get('sole_draft_error')})))
    summary=dict(at=now(),planned_transfers=108,complete_transfers=len(complete),unscored_transfers=108-len(complete),expected_engine_clips=144,
        verified_engine_actor_frames=sum(r.get('actor_frames',0) for r in analysis['engine']),complete_engine_groups=sum(r['status']=='complete' for r in analysis['engine']),
        target_floor_over_10mm=sum(r['target_mesh_floor_depth_max_m']>.01 for r in complete),rows=rows,
        largest_absolute_excursion_change_degrees=max((abs(r['excursion_change_degrees']) for r in complete),default=None),
        ground_by_rig=ground,profile_analysis_sha256=sha256(study/'profile-analysis.json'),quality_approved=False,style_response_validated=False)
    save(output/'summary.json',summary)
    lines=['# Profile response after character transfer','',f"{len(complete)}/108 transfers complete; {summary['complete_engine_groups']}/36 engine groups complete. All36 original takes remain in the study.",'',
        'Original mobility text already failed the squat and kick direction screens. This study measures transfer of that response; it does not establish semantic style compliance.','',
        '| Action | Rig | Plain | Low | Middle | High | Numerical direction screen |','|---|---|---:|---:|---:|---:|---|']
    for row in rows:
        response=row['response'];m=response.get('medians_degrees');state=response['numerical_direction_screen_pass']
        values=' | '.join(f'{m[k]:.2f}°' for k in ['plain','low','middle','high']) if m else 'missing | missing | missing | missing'
        lines.append(f"| {row['action']} | {row['rig']} | {values} | {('Pass' if state else 'Fail') if state is not None else 'Unscored'} |")
    lines+=['',f"{summary['target_floor_over_10mm']}/{len(complete)} completed targets exceed the proposed10mm floor screen. Maximum absolute source-to-target primary-excursion change: {summary['largest_absolute_excursion_change_degrees']} degrees.",'',
        '| Rig | Floor over10mm | Clips with hover measurement | Per-clip maximum predicted-support hover range |','|---|---:|---:|---:|']
    for g in ground:
        limits=f"{g['hover_min_m']*1000:.2f}-{g['hover_max_m']*1000:.2f} mm" if g['hover_measured'] else 'missing'
        lines.append(f"| {g['rig']} | {g['floor_over_10mm']}/{g['completed']} | {g['hover_measured']}/{g['completed']} | {limits} |")
    lines+=['','Zero floor penetration does not mean the feet are grounded. The hover values use predicted support and a weighted foot envelope, not independent contact annotations. Rig02 also lacks a sufficiently flat automatic sole draft; its envelope diagnostic remains separate from an authored contact patch.','',
        'The same whole-clip p95-p5 semantic-joint descriptors and matched three-seed direction rule were used. These descriptors can reflect wrong actions, side changes or jitter. Target proportions and landmark placement can change measured angles. All per-take differences and failures are retained in the bound profile analysis.','',
        'No new motion was generated or corrected. These are existing development clips and rigs, not held-out release fixtures. Independent action/style ratings and cleanup time remain missing; no animation-quality approval.']
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


def run(study,output):
    study,output=[Path(p).resolve() for p in [study,output]];output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    owner=read(study/'runner.json');proc=psutil.Process();names=['summarize_profile_transfer.py','audit_paired_guides.py','strep.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),study=str(study),owner=dict(pid=owner['pid'],created=owner['created_at']),protocol_sha256=sha256(study/'protocol.json'),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**details));print(status,flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('waiting_for_exact_profile_transfer_owner');await_owner(request['owner'],'pid','created',study,{'complete','complete_with_failures'})
        if sha256(study/'protocol.json')!=request['protocol_sha256']:raise ValueError('Study protocol changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Summary source changed')
        summarize(study,output);save(output/'completion.json',dict(at=now(),summary_sha256=sha256(output/'summary.json'),quality_approved=False));phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
