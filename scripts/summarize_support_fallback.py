"""Verify a completed fallback trial and summarize direct exported-asset evidence."""
import argparse
from pathlib import Path
from strep import read,save,sha256,now
from audit_authoring_intent import check_files
from compare_midpoint_support import verified
from study_whole_support_breadth import check_engine


def bound_pair(pair_path,case,before_hash,after_hash,kind):
    pair=read(pair_path)
    if pair['case']!=case or pair['comparison_kind']!=kind or pair['before_sha256']!=before_hash or pair['after_sha256']!=after_hash:
        raise ValueError('Pair belongs to another comparison')
    for name,digest in pair['inputs'].items():
        # Code may evolve after completion; the recorded data inputs may not.
        if Path(name).suffix not in ('.py','.gd') and sha256(name)!=digest:
            raise ValueError('Measured input changed: '+name)
    if sha256(pair_path.parent/'timeline.json')!=pair['timeline_sha256']:
        raise ValueError('Measured timeline changed')
    return pair


def run(study,pairs,output,input_pairs=None):
    if output.exists():raise ValueError('Preserve earlier summaries')
    protocol=read(study/'protocol.json');complete=read(study/'completion.json')
    if complete['protocol_sha256']!=sha256(study/'protocol.json'):
        raise ValueError('Trial protocol changed')
    check_files(study,complete['files']);check_files(study/'implementation',protocol['implementation'])
    source=Path(protocol['source']);bp,bc=verified(source)
    if protocol['source_completion_sha256']!=sha256(source/'completion.json') or protocol['population']!=bp['cases']:
        raise ValueError('Reference population changed')
    if [r['id'] for r in complete['rows']]!=[c['id'] for c in bp['cases']]:
        raise ValueError('Trial omitted or reordered reference rows')
    proof=study/'engine/verification.json'
    if sha256(proof)!=complete['engine_verification_sha256']:raise ValueError('Engine proof changed')
    frames=check_engine(read(proof),read(study/'manifest.json')['cases'])
    if frames!=complete['engine_actor_frames']:raise ValueError('Engine frame count differs')
    rows=[];measured=0;times=0;input_measured=0
    for row in complete['rows']:
        item=dict(row);pair_path=pairs/row['id']/'completion.json'
        item['pair_audit']='not_probed' if row['status']=='not_probed' else 'pending'
        if row['status']=='evaluated' and pair_path.exists():
            old=next(r for r in bc['rows'] if r['id']==row['id'])
            pair=bound_pair(pair_path,row['id'],old['selected_sha256'],row['candidate_sha256'],'fallback_pilot')
            item.update(pair_audit='complete',pair_completion_sha256=sha256(pair_path),
                samples=pair['samples'],floor=pair['floor'],
                root_peak_change_m_s2=pair['root_acceleration']['peak_change'],
                root_max_local_increase_m_s2=pair['root_acceleration']['maximum_pointwise_increase'],
                decoded_foot_peak_changes={k:v.get('peak_change') for k,v in pair['feet'].items()})
            measured+=1;times+=pair['samples']
        item['common_input_pair_audit']='not_probed' if row['status']=='not_probed' else 'pending'
        input_path=input_pairs/row['id']/'completion.json' if input_pairs else None
        if row['status']=='evaluated' and input_path and input_path.exists():
            base=study/row['id']/'base/selected/character.glb'
            pair=bound_pair(input_path,row['id'],sha256(base),row['candidate_sha256'],'fallback_common_input')
            item.update(common_input_pair_audit='complete',common_input_pair_completion_sha256=sha256(input_path),
                common_input_samples=pair['samples'],common_input_floor=pair['floor'],
                sampled_common_input_floor_preserved=pair['floor']['worsened_samples']==0)
            input_measured+=1
        rows.append(item)
    output.mkdir(parents=True)
    summary=dict(at=now(),study=str(study),completion_sha256=sha256(study/'completion.json'),
        reference_population=len(rows),planned=len(protocol['pilot_cases']),evaluated=sum(r['status']=='evaluated' for r in rows),
        failed=sum(r['status']=='failed' for r in rows),audited=measured,comparison_times=times,
        engine_actor_frames=frames,common_input_audited=input_measured,
        common_input_floor_regressions=sum(r.get('sampled_common_input_floor_preserved') is False for r in rows),
        rows=rows,quality_approved=False,
        scope='Development evidence only. Sampled geometry and import agreement do not prove continuous-time safety, naturalness, semantics or human approval.')
    save(output/'summary.json',summary)
    lines=['# Original-priority fallback trial','',f'{summary["evaluated"]}/{summary["planned"]} planned cases evaluated; {measured} direct pair audits; {frames} engine actor-frames.','',
           '| Case | Outcome | Excess-energy change | Right foot peak change (m/s) | Pair audit | Input floor preserved |','|---|---|---:|---:|---|---|']
    for r in rows:
        lines.append(f'| {r["id"]} | {r["status"]} | {r.get("energy_delta", "—")} | {r.get("foot_peak_changes",{}).get("Right","—")} | {r["pair_audit"]} | {r.get("sampled_common_input_floor_preserved","pending" if r["status"]!="not_probed" else "—")} |')
    lines+=['',summary['scope']]
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print({k:summary[k] for k in ['reference_population','planned','evaluated','failed','audited','comparison_times','engine_actor_frames']})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('study','pairs','output'):p.add_argument(arg,type=Path)
    p.add_argument('--input-pairs',type=Path)
    a=p.parse_args();run(a.study.resolve(),a.pairs.resolve(),a.output.resolve(),a.input_pairs.resolve() if a.input_pairs else None)
