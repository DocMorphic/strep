"""Wait for an exact fitting process, then audit its retained output once.

Never starts or retries fitting. A missing/failed output remains a failed study.
"""
import argparse
import time
from pathlib import Path
import psutil
from strep import read,save,sha256,now
from audit_scene_region_fit import run as audit_geometry
from audit_scene_joint_rates import run as audit_rates
from run_godot_rig_import import run as audit_engine


def owner_live(pid,creation_time):
    try:
        owner=psutil.Process(pid)
        return owner.is_running() and abs(owner.create_time()-creation_time)<.001
    except psutil.NoSuchProcess:
        return False


def run(study,output,pid,creation_time):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Fresh completion report directory required')
    protocol_hash=sha256(study/'protocol.json')
    output.mkdir(parents=True)
    save(output/'protocol.json',dict(at=now(),study=str(study),study_protocol_sha256=protocol_hash,
                                     owner_pid=pid,owner_creation_time=creation_time,runner_sha256=sha256(__file__)))
    try:
        save(output/'status.json',dict(status='waiting_for_exact_owner',pid=pid,creation_time=creation_time))
        print(dict(status='waiting_for_exact_owner',pid=pid),flush=True)
        while owner_live(pid,creation_time):time.sleep(2)
        if sha256(study/'protocol.json')!=protocol_hash:raise ValueError('Study protocol changed while waiting')
        result=read(study/'result.json')
        if result['status']!='complete':raise ValueError('Fitting did not complete: '+str(result.get('error')))
        save(output/'status.json',dict(status='auditing',at=now()))
        audit_geometry(study,output/'geometry')
        audit_rates(study,output/'joint-rates.json')
        frames=read(study/'authored-scene.json')['frame_count'];cases=[]
        for label in ['source','candidate']:
            path=study/(label+'.glb')
            cases.append(dict(id=label,path=str(path),sha256=sha256(path),frames=frames,fps=30,sample_by_time=True))
        save(output/'manifest.json',dict(cases=cases));audit_engine(output,output/'engine')
        save(output/'status.json',dict(status='complete',at=now(),result_sha256=sha256(study/'result.json'),
             geometry_sha256=sha256(output/'geometry/verification.json'),joint_rates_sha256=sha256(output/'joint-rates.json'),
             engine_sha256=sha256(output/'engine/verification.json'),quality_approved=False))
        print(dict(status='complete',quality_approved=False),flush=True)
    except Exception as exc:
        save(output/'status.json',dict(status='failed',at=now(),error=str(exc),quality_approved=False))
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--pid',type=int,required=True);p.add_argument('--creation-time',type=float,required=True)
    a=p.parse_args();run(a.study,a.output,a.pid,a.creation_time)
