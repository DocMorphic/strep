"""Bounded, audited continuation across remaining foot-release failures."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import psutil
from strep import ROOT,read,save,sha256,now
from study_repaired_root_release import audited_source


def score(decoded):
    return sum(max(0.,e['candidate_m_s2']-e['limit_m_s2']) for e in decoded['events'])


def run(output,source,audit,blocks=3):
    if output.exists():raise ValueError('Preserve previous sequence')
    if not 1<=blocks<=3:raise ValueError('One to three bounded blocks')
    decoded,_=audited_source(source,audit)
    names=set(read(source/'request.json')['implementation'])|{
        'study_conic_release_sequence.py','study_scheduled_conic_foot.py','conic_buffer_schedule.py',
        'verify_repaired_root_release.py','verify_block_release.py','reconstruct_descent.py',
        'audit_release_normalized.py','verify_guarded_release.py'}
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in sorted(names):shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),source=str(source),audit=str(audit),audit_sha256=sha256(audit),
        source_completion_sha256=sha256(source/'completion.json'),max_blocks=blocks,
        implementation={n:sha256(output/'implementation'/n) for n in sorted(names)},
        method='At most three automatically selected blocks; each has at most12 accepted iterations and nine fixed trust/buffer proposals per iteration. Fresh decoded, normalized and engine audit required after each. Continue only with passing root/foot preservation guards and decreasing sum of original release excesses. Stop at no remaining full-comparison failures, stalled excess, or budget. All trials retained, never quality approval.',quality_approved=False)
    save(output/'request.json',request);request_hash=sha256(output/'request.json')
    save(output/'freeze.json',dict(request_sha256=request_hash))
    owner=psutil.Process();save(output/'runner.json',dict(at=now(),pid=owner.pid,created=owner.create_time()))
    rows=[];state='starting';initial_score=score(decoded)
    def validate():
        if sha256(output/'request.json')!=request_hash:raise ValueError('Sequence request changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Sequence implementation changed: '+name)
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    def command(script,*args):
        validate();subprocess.run([sys.executable,str(ROOT/'scripts'/script),*[str(a) for a in args]],cwd=ROOT,check=True)
    try:
        for index in range(blocks):
            validate()
            if not decoded['failed_full_checks']:state='original_comparisons_passed';break
            previous_score=score(decoded);trial=output/f'block-{index+1:02d}';proof=output/f'audit-{index+1:02d}'
            phase('preparing',block=index+1,source=str(source))
            command('study_scheduled_conic_foot.py','prepare',trial,'--source',source,'--audit',audit)
            phase('fitting',block=index+1)
            command('study_scheduled_conic_foot.py','run',trial)
            phase('auditing',block=index+1)
            command('verify_repaired_root_release.py',trial,proof)
            result=read(proof/'completion.json')
            if not result['all_repaired_root_checks_passed']:raise ValueError('Independent guards failed')
            updated,_=audited_source(trial,proof/'completion.json');new_score=score(updated)
            rows.append(dict(block=index+1,trial=str(trial),audit=str(proof/'completion.json'),
                completion_sha256=sha256(trial/'completion.json'),audit_sha256=sha256(proof/'completion.json'),
                excess_sum_before_m_s2=previous_score,excess_sum_after_m_s2=new_score,
                failed_full_checks=updated['failed_full_checks']))
            save(output/'results.json',dict(rows=rows,quality_approved=False))
            if new_score>=previous_score-1e-8:state='stalled';break
            source,audit,decoded=trial,proof/'completion.json',updated
        else:state='budget_reached' if decoded['failed_full_checks'] else 'original_comparisons_passed'
        validate();save(output/'completion.json',dict(at=now(),request_sha256=request_hash,reason=state,
            rows=rows,selected_source=str(source),selected_audit=str(audit),initial_excess_sum_m_s2=initial_score,
            final_excess_sum_m_s2=score(decoded),failed_full_checks=decoded['failed_full_checks'],quality_approved=False))
        phase('complete',reason=state,blocks=len(rows))
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--source',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    a=p.parse_args();run(a.output.resolve(),a.source.resolve(),a.audit.resolve())
