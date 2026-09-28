"""Complete exports and full-window audits after the exact live study exits.

This never restarts the solver or retries an existing export. Owner loss before
completion is an error; quiet output or observation timeout is not owner loss.
"""
import argparse
import os
from pathlib import Path
import time
import traceback
import psutil
from strep import read,save,sha256,now


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve();recipe=read(study/'request.json')
    if output.exists():raise ValueError('Preserve existing completion attempt')
    output.mkdir();save(output/'runner.json',dict(pid=os.getpid(),created=psutil.Process().create_time(),study=str(study),started_at=now()))
    digest=sha256(study/'request.json');save(output/'request.json',dict(study=str(study),study_request_sha256=digest,implementation_sha256=sha256(__file__)))
    def phase(status):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False));print(status,flush=True)
    try:
        phase('waiting_for_exact_study_owner')
        while True:
            if sha256(study/'request.json')!=digest:raise ValueError('Study request changed')
            try:
                owner=psutil.Process(recipe['pid']);live=owner.create_time()==recipe['process_created'] and owner.is_running()
            except psutil.NoSuchProcess:live=False
            state=read(study/'pipeline.json')['status']
            if not live:
                if state!='complete':raise RuntimeError('Study owner ended before complete evidence')
                break
            time.sleep(5)
        from run_paired_hand_prototype import run as export
        from verify_palm_region import run as event
        from audit_palm_approach import run as window
        from finalize_palm_region import run as finalize
        destination=output/'export';source=Path(recipe['input'])/'input-scene.json'
        phase('export_and_engine');export(destination,study,source)
        phase('independent_event');event(destination,study)
        phase('full_window_half_frames');window(destination,study,output/'window-audit',radius=15,substeps=2)
        phase('final_verification');finalize(destination,study)
        proof=read(destination/'completion-verification.json');audit=read(output/'window-audit/summary.json');samples=read(output/'window-audit/samples.json')['rows']
        if [r['frame'] for r in samples]!=[60+i*.5 for i in range(61)]:raise ValueError('Incomplete declared-window population')
        if audit['samples_sha256']!=sha256(output/'window-audit/samples.json'):raise ValueError('Window samples changed')
        save(output/'completion.json',dict(at=now(),study_request_sha256=digest,export_proof_sha256=sha256(destination/'completion-verification.json'),
            window_summary_sha256=sha256(output/'window-audit/summary.json'),event_screens=proof['event_screens'],
            window_variants=audit['variants'],engine_actor_frames=proof['engine_actor_frames'],sample_count=len(samples),quality_approved=False))
        phase('complete')
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
