"""Reconstruct chain lineage and freshly audit every completed correction export."""
import argparse
import contextlib
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now,ROOT
from angular_source import audited_source
from verify_angular_release import angles
from verify_projected_angular import run as verify_block


def measure(source,audit):
    done=read(source/'completion.json')
    if done['request_sha256']!=sha256(source/'request.json'):raise ValueError('Request changed')
    for name,digest in done['files'].items():
        if sha256(source/name)!=digest:raise ValueError('Completed file changed')
    decoded,_=audited_source(source,audit)
    if decoded['failed_full_checks']:return False,None
    request=read(source/'request.json');spec=read(source/'take/spec.json');nodes=[v['node'] for v in spec['edit_joints'].values()]
    paths=[source/'take/input/character.glb',Path(request['prior'])/'candidate/character.glb',source/'take/candidate/character.glb']
    values=[angles(p,nodes,spec['frames'],spec['fps']) for p in paths]
    cap=np.maximum(values[0].max(axis=0),values[1].max(axis=0))+np.radians(1e-5)
    excess=np.maximum(values[2]-cap[None],0)
    if not np.isfinite(excess).all():raise ValueError('Nonfinite angular measurement')
    return True,float(np.sum(np.degrees(excess)**2))


def run(study,output):
    if output.exists():raise ValueError('Preserve earlier chain audit')
    protocol=read(study/'protocol.json');done=read(study/'completion.json');result=read(study/'results.json')
    if read(study/'pipeline.json')['status']!='complete' or done['protocol_sha256']!=sha256(study/'protocol.json') or done['results_sha256']!=sha256(study/'results.json'):
        raise ValueError('Incomplete or stale chain')
    if done['rows']!=result['rows'] or [r['id'] for r in result['rows']]!=[c['id'] for c in protocol['cases']]:raise ValueError('Declared case population differs')
    for path,digest in protocol['inputs'].items():
        if sha256(path)!=digest:raise ValueError('Frozen input changed')
    for name,digest in protocol['implementation'].items():
        if sha256(study/'implementation'/name)!=digest:raise ValueError('Frozen implementation changed')
    output.mkdir(parents=True);rows=[]
    for case,stored in zip(protocol['cases'],result['rows']):
        case_path=study/'cases'/case['id'];case_done=read(case_path/'completion.json');source=Path(case['source']);audit=Path(case['audit'])
        if sha256(case_path/'completion.json')!=stored['completion_sha256'] or case_done['status']!=stored['status']:raise ValueError('Case result changed')
        if case_done['initial_source']!=str(source) or case_done['initial_audit']!=str(audit):raise ValueError('Initial source changed')
        history=case_done['history']
        if len(history)>protocol['max_blocks']:raise ValueError('Correction budget exceeded')
        eligible,score=measure(source,audit);initial_eligible=eligible;initial_score=score;blocks=[]
        for index,entry in enumerate(history,1):
            if not eligible or score==0:raise ValueError('Unnecessary or ineligible correction launched')
            trial=case_path/f'block-{index:02d}';old_audit=case_path/f'audit-{index:02d}/completion.json'
            if entry['index']!=index or entry['source']!=str(source) or entry['source_audit']!=str(audit) or entry['trial']!=str(trial) or entry['audit']!=str(old_audit):raise ValueError('Incorrect chain lineage')
            if entry['status']=='failed':
                if index!=len(history) or case_done['status']!='failed' or not case_done.get('error'):raise ValueError('Unbound terminal failure')
                blocks.append(dict(index=index,status='failed_unapproved'));break
            request=read(trial/'request.json')
            if request['source']!=str(source) or request['independent_source_audit']!=str(audit):raise ValueError('Trial uses a different source')
            if entry['after'].get('eligible') and (entry['after']['completion_sha256']!=sha256(trial/'completion.json') or entry['after']['audit_sha256']!=sha256(old_audit)):raise ValueError('Trial assessment binding differs')
            fresh=output/case['id']/f'block-{index:02d}'
            fresh.parent.mkdir(parents=True,exist_ok=True)
            with (fresh.parent/(fresh.name+'.log')).open('w',encoding='utf8') as log,contextlib.redirect_stdout(log):verify_block(trial,fresh)
            check=read(fresh/'completion.json');next_eligible,next_score=measure(trial,fresh/'completion.json')
            passed=check['all_preservation_checks_passed'] and check['projection_reconstructed'] and next_eligible
            blocks.append(dict(index=index,audit=str(fresh/'completion.json'),audit_sha256=sha256(fresh/'completion.json'),preservation_passed=passed,remaining_score=next_score))
            if entry['status']=='verified':
                if not passed or (next_score!=0 and score-next_score<=1e-10):raise ValueError('Unverified or nonimproving candidate promoted')
                source=trial;audit=old_audit;score=next_score;eligible=next_eligible
            elif entry['status']=='no_progress':
                if not passed or next_score==0 or score-next_score>1e-10 or case_done['status']!='no_progress' or index!=len(history):raise ValueError('No-progress verdict differs')
            elif entry['status']=='rejected':
                if passed or case_done['status']!='preservation_failed' or index!=len(history):raise ValueError('Rejection verdict differs')
            else:raise ValueError('Unknown trial status')
        status=case_done['status']
        if status=='ineligible' and (initial_eligible or history):raise ValueError('Invalid ineligibility')
        if status=='already_passed' and (not initial_eligible or initial_score!=0 or history):raise ValueError('Invalid no-op pass')
        if status=='numerical_pass' and (not history or not eligible or score!=0 or history[-1]['status']!='verified'):raise ValueError('Incomplete result marked passing')
        if status=='budget_exhausted' and (len(history)!=protocol['max_blocks'] or score==0 or history[-1]['status']!='verified'):raise ValueError('Invalid budget result')
        if status in {'no_progress','preservation_failed'} and not history:raise ValueError('Missing terminal trial')
        if status=='failed' and not case_done.get('error'):raise ValueError('Missing failure evidence')
        if status not in {'ineligible','already_passed','numerical_pass','budget_exhausted','no_progress','preservation_failed','failed'}:raise ValueError('Unknown result')
        if case_done['final_source']!=str(source) or case_done['final_audit']!=str(audit):raise ValueError('Final selection is not last verified source')
        row=dict(id=case['id'],status=status,case_completion_sha256=stored['completion_sha256'],blocks=blocks,final_source=str(source),candidate_sha256=sha256(source/'take/candidate/character.glb'),final_excess_score=score,quality_approved=False)
        rows.append(row);print(case['id'],status,len(blocks),flush=True)
    save(output/'completion.json',dict(at=now(),chain_completion_sha256=sha256(study/'completion.json'),implementation_sha256=sha256(__file__),rows=rows,all_chain_checks_passed=True,quality_approved=False,
        scope='Full declared case population and chain provenance; fresh independent block audits and decoded rotation scores. Failed/ineligible cases remain unapproved. Repeated development inputs are not held-out evidence or human ratings.'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('study',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.study.resolve(),args.output.resolve())
