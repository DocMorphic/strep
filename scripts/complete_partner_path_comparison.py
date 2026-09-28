"""Run the full path comparison after the exact geometry-audit owner exits."""
import argparse
import os
from pathlib import Path
import traceback
import psutil
from strep import read,save,sha256,now,ROOT
from audit_paired_guides import await_owner
from compare_partner_paths import run as compare


def run(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier waiter')
    output.mkdir(parents=True)
    source=ROOT/'reports/screen-surface-path-completion-v1';owner=read(source/'request.json')
    request=dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),owner=dict(pid=owner['pid'],created=owner['created']),
        source=str(source),source_request_sha256=sha256(source/'request.json'),result=str(ROOT/'reports/partner-path-comparison-v1'),
        implementation={n:sha256(ROOT/'scripts'/n) for n in ['complete_partner_path_comparison.py','compare_partner_paths.py','audit_paired_guides.py']},quality_approved=False)
    save(output/'request.json',request)
    save(output/'pipeline.json',dict(status='waiting_for_exact_geometry_owner',at=now(),quality_approved=False))
    try:
        await_owner(request['owner'],'pid','created',source,{'complete'})
        if sha256(source/'request.json')!=request['source_request_sha256']:raise ValueError('Audit source changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Comparison implementation changed')
        save(output/'pipeline.json',dict(status='comparing',at=now(),quality_approved=False))
        compare(ROOT/'reports/bounded-surface-path-completion-v1',source,Path(request['result']))
        save(output/'completion.json',dict(at=now(),summary_sha256=sha256(Path(request['result'])/'summary.json'),quality_approved=False))
        save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
