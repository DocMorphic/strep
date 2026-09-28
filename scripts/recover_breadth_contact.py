"""Resume an authoritatively stopped contact study without replacing evidence."""
import argparse
import os
import shutil
from pathlib import Path
import traceback
import psutil
from strep import ROOT,read,save,sha256,now
from study_breadth_contact import validate


def run(output):
    output=Path(output).resolve();protocol=validate(output);owner=read(output/'runner.json')
    try:
        process=psutil.Process(owner['pid'])
        if abs(process.create_time()-owner['created_at'])<.001:raise ValueError('Original worker is still live')
    except psutil.NoSuchProcess:pass
    # A second recovery must first be inspected independently, not auto-retried.
    incident=output/'interrupted-attempts/recovery-01';incident.mkdir(parents=True,exist_ok=False)
    for name in ('runner.json','pipeline.json','results.json','runner.log'):shutil.copyfile(output/name,incident/name)
    shutil.copyfile(__file__,incident/'recovery-driver.py')
    save(incident/'incident.json',dict(at=now(),original_owner=owner,owner_identity_absent=True,
        cause='Unknown: process identity and original exec handle absent; no exception at end of retained log.',
        protocol_sha256=sha256(output/'protocol.json'),driver_sha256=sha256(__file__),quality_approved=False))
    os.environ.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    import torch
    torch.set_num_threads(1)
    from breadth_contact_fit import run as fit
    from verify_breadth_contact import verify
    from run_godot_rig_import import run as engine
    current=psutil.Process();save(output/'runner.json',dict(pid=current.pid,created_at=current.create_time(),status='running',started_at=now(),recovery='recovery-01'))
    data=read(output/'results.json')
    try:
        for case in protocol['cases']:
            validate(output);checks=[dict(id=case['id']+'-input',path=str(Path(case['source'])/'character.glb'),sha256=case['files']['character.glb'],frames=case['motion']['frames'],fps=30)]
            for method in protocol['methods']:
                row=next(r for r in data['rows'] if r['case']==case['id'] and r['method']==method);dest=output/'takes'/row['id']
                if row['status']=='complete':
                    if read(dest/'verification.json')!=row['verification'] or sha256(dest/'candidate/character.glb')!=row['verification']['candidate_sha256']:raise ValueError('Completed candidate evidence changed')
                elif row['status']=='failed':continue
                else:
                    if dest.exists():
                        archive=(incident/row['id']).resolve();target=dest.resolve()
                        if not target.is_relative_to((output/'takes').resolve()) or not archive.is_relative_to(incident.resolve()) or archive.exists():raise ValueError('Unsafe interrupted-attempt archive path')
                        # Preserve every partial byte before restarting this one
                        # uncheckpointed fit with the original method/budget.
                        hashes={str(p.relative_to(target)):sha256(p) for p in target.rglob('*') if p.is_file()}
                        target.rename(archive)
                        if any(sha256(archive/p)!=h for p,h in hashes.items()):raise ValueError('Archived bytes changed')
                        save(incident/(row['id']+'-files.json'),hashes)
                        row.setdefault('attempts',[]).append(dict(status='interrupted',retained=str(archive),last_stage=read(archive/'pipeline.json'),reason='Verified worker disappearance, not a numerical fit failure'))
                    row.update(status='running',started_at=now());save(output/'results.json',data);save(output/'pipeline.json',dict(status='fitting',id=row['id'],recovery='recovery-01'))
                    try:
                        fit(case['source'],dest,method);proof=verify(dest)
                        row.update(status='complete',finished_at=now(),verification=proof)
                    except Exception as exc:row.update(status='failed',finished_at=now(),error=str(exc),traceback=traceback.format_exc())
                    save(output/'results.json',data);print(row['id']+' '+row['status'],flush=True)
                if row['status']=='complete':checks.append(dict(id=row['id'],path=str(dest/'candidate/character.glb'),sha256=row['verification']['candidate_sha256'],frames=case['motion']['frames'],fps=30))
            group=output/'engine-groups'/case['id'];existing=next((g for g in data['engine_groups'] if g['case']==case['id']),None)
            if existing is not None:
                if existing['status']!='complete':continue
                if read(group/'audit/verification.json')!=existing['proof'] or read(group/'manifest.json')['cases']!=checks:raise ValueError('Completed engine group changed')
                continue
            if group.exists():raise ValueError('Unrecorded engine attempt needs separate inspection')
            group.mkdir(parents=True);save(group/'manifest.json',dict(cases=checks));save(output/'pipeline.json',dict(status='engine',id=case['id'],recovery='recovery-01'))
            try:
                engine(group,group/'audit');data['engine_groups'].append(dict(case=case['id'],status='complete',proof=read(group/'audit/verification.json')))
            except Exception as exc:data['engine_groups'].append(dict(case=case['id'],status='failed',error=str(exc),traceback=traceback.format_exc()))
            save(output/'results.json',data)
        failed=any(r['status']!='complete' for r in data['rows']) or any(g['status']!='complete' for g in data['engine_groups'])
        save(output/'pipeline.json',dict(status='complete_with_failures' if failed else 'complete',finished_at=now(),quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()));raise
    finally:save(output/'runner.json',dict(pid=current.pid,created_at=current.create_time(),status='stopped',finished_at=now(),recovery='recovery-01'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
