"""Wait for the exact ten-input study, then publish its full matched comparison."""
import argparse
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now
from audit_paired_guides import await_owner
from compare_support_reference import run as compare


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    names=['finish_support_reference_comparison.py','compare_support_reference.py','summarize_breadth_contact.py','audit_paired_guides.py','strep.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    owner=read(study/'runner.json');proc=psutil.Process()
    request=dict(at=now(),pid=proc.pid,created=proc.create_time(),study=str(study),owner=owner,
                 protocol_sha256=sha256(study/'protocol.json'),implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**details):save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**details));print(status,flush=True)
    try:
        phase('waiting_for_exact_reference_owner');await_owner(owner,'pid','created',study,{'complete'})
        if sha256(study/'protocol.json')!=request['protocol_sha256']:raise ValueError('Study protocol changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Comparison implementation changed')
        rows=read(study/'results.json')['rows']
        if len(rows)!=10 or any(r['status']!='complete' for r in rows):raise ValueError('Require all ten inputs; inspect failed/missing cases')
        phase('comparing');compare(study,output/'comparison')
        result=read(output/'comparison/summary.json')
        if result['completed_pairs']!=10 or result['status']!='complete_population':raise ValueError('Comparison is incomplete')
        save(output/'completion.json',dict(at=now(),summary_sha256=sha256(output/'comparison/summary.json'),quality_approved=False))
        phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
