"""Equal-iteration object-sampling comparison on the unchanged box fixture."""
import argparse
import os
from pathlib import Path
import psutil
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from fit_scene_regions import run as fit
from audit_scene_region_fit import run as audit
from run_godot_rig_import import run as engine


def run(output):
    if output.exists():raise ValueError('Preserve previous comparison')
    scene=ROOT/'reports/region-fit-box-pilot-v1/scene.json'
    output.mkdir(parents=True)
    save(output/'protocol.json',dict(at=now(),scene=str(scene),scene_sha256=sha256(scene),
        implementation_sha256=sha256(__file__),stages=3,iterations=40,seconds_per_method=600,
        scope='Same source, targets, floor sample, budgets and acceptance checks; only object skin coverage changes. Equal iteration caps, not equal runtime. Development fixture.'))
    save(output/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
    rows=[];cases=[]
    with threadpool_limits(limits=1):
        for name,full in [('subset',False),('full',True)]:
            folder=output/name
            save(output/'pipeline.json',dict(status='processing',method=name,at=now()))
            row=dict(method=name,status='processing');rows.append(row);save(output/'results.json',dict(rows=rows))
            try:
                fit(scene,'A',['left-grip','right-grip'],folder,3,40,600,'balanced',full)
                audit(folder,output/(name+'-audit'))
                proof=read(output/(name+'-audit')/'verification.json');recipe=read(folder/'recipe.json');outcome=read(folder/'result.json')
                candidate=proof['variants']['candidate'];source=proof['variants']['source']
                row.update(status='complete',seconds=outcome['seconds'],sampling=recipe['object_sampling'],
                    contact_failures=candidate['contact_failures'],contact_samples=candidate['contact_samples'],
                    geometry_failures=candidate['geometry_failures'],geometry_samples=len(candidate['rows']),
                    minimum_object_clearance_m=min(v for r in candidate['rows'] for v in r['object_clearances_m'].values()),
                    anchor_max_m=max(c['anchor_error_m'] for r in candidate['rows'] for c in r['contacts']),
                    normal_max_degrees=max(c['normal_error_degrees'] for r in candidate['rows'] for c in r['contacts'] if c['normal_error_degrees'] is not None),
                    peak_joint_speed_m_s=candidate['peak_joint_speed_m_s'],peak_joint_acceleration_m_s2=candidate['peak_joint_acceleration_m_s2'],
                    source_speed_m_s=source['peak_joint_speed_m_s'],source_acceleration_m_s2=source['peak_joint_acceleration_m_s2'],
                    edit_bounds_passed=proof['hard_edit_bounds_passed'],result_sha256=sha256(folder/'result.json'),
                    audit_sha256=sha256(output/(name+'-audit')/'verification.json'),quality_approved=False)
                for variant in ['source','candidate']:
                    path=folder/(variant+'.glb')
                    cases.append(dict(id=name+'-'+variant,path=str(path),sha256=sha256(path),frames=5,fps=30,sample_by_time=True))
            except Exception as exc:
                row.update(status='failed',error=str(exc))
            save(output/'results.json',dict(rows=rows,quality_approved=False));print(name,row,flush=True)
    if sha256(scene)!=read(output/'protocol.json')['scene_sha256']:raise ValueError('Authored scene changed')
    if cases:
        save(output/'manifest.json',dict(cases=cases));engine(output,output/'engine')
    save(output/'completion.json',dict(at=now(),protocol_sha256=sha256(output/'protocol.json'),results_sha256=sha256(output/'results.json'),
        failed=sum(r['status']=='failed' for r in rows),engine_sha256=sha256(output/'engine/verification.json') if cases else None,
        engine_actor_frames=sum(c['frames'] for c in cases),quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',at=now()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();run(a.output.resolve())
