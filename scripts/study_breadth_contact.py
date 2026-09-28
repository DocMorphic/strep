"""Fixed five-seed, two-rig control/candidate contact experiment."""
import argparse
import os
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now

SOURCES=['study_breadth_contact.py','breadth_contact_fit.py','verify_breadth_contact.py',
         'rig_clearance_fit.py','rig_asset.py','rig_contact_authoring.py','rig_contact_tracks.py',
         'target_rig_contact.py','rig_periodic_contact.py','rig_transition.py','rig_loop.py',
         'rig_clip_import.py','gltf_tools.py','build_soma_preview.py','verify_rig_clearance.py',
         'inspect_motion.py','correct_stance.py','run_godot_rig_import.py','godot_import_audit.gd']


def prepare(source,output):
    from breadth_transfer_study import validate
    source,output=Path(source).resolve(),Path(output).resolve()
    spec=validate(source);results=read(source/'results.json')
    motions=[m for m in spec['motions'] if m['case']=='combat-jab-cross-retreat']
    if len(motions)!=5 or len({m['seed'] for m in motions})!=5:
        raise ValueError('Require all five seeds of the fixed combat action')
    if output.exists():raise ValueError('Preserve earlier experiments')
    cases=[]
    for m in motions:
        for rig in ['rig-01','rig-02']:
            identifier=m['id']+'-'+rig
            row=next(r for r in results['rows'] if r['id']==identifier)
            if row['status']!='complete':raise ValueError('Required baseline transfer incomplete')
            cases.append(dict(id=identifier,motion=m,rig=rig,source=str(source/'takes'/identifier),files=row['files']))
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in SOURCES:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    protocol=dict(created_at=now(),source_protocol_sha256=sha256(source/'protocol.json'),cases=cases,
        methods=['clearance','support'],planned_candidates=20,implementation={n:sha256(ROOT/'scripts'/n) for n in SOURCES},
        selection='All five pre-existing seeds of jab-cross-retreat, Cesium and Quaternius female (two rig families). Development correction study, not held-out action evaluation.',
        rules='Same 12cm vertical/4cm horizontal root and existing joint/adjacent-edit bounds; same six-sweep budget. Only support penalty differs. Retain rejected and failed attempts; no per-seed tuning or release approval.',
        support_weight=40.,native_support_height_gate_m=.03,minimum_support_frames=4,edge_fade_frames=3,
        quality_approved=False)
    save(output/'protocol.json',protocol);save(output/'freeze.json',dict(protocol_sha256=sha256(output/'protocol.json')))
    save(output/'results.json',dict(rows=[dict(id=c['id']+'-'+method,case=c['id'],method=method,status='pending') for c in cases for method in protocol['methods']],engine_groups=[],quality_approved=False))
    save(output/'pipeline.json',dict(status='prepared'))
    return protocol


def validate(output):
    p=read(output/'protocol.json')
    if sha256(output/'protocol.json')!=read(output/'freeze.json')['protocol_sha256']:raise ValueError('Protocol changed')
    for name,digest in p['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Frozen implementation changed: '+name)
    for case in p['cases']:
        for name,digest in case['files'].items():
            if sha256(Path(case['source'])/name)!=digest:raise ValueError('Baseline artifact changed')
    return p


def run(output):
    output=Path(output).resolve();p=validate(output)
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Already started; inspect actual process before a new attempt')
    os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1'
    import torch
    torch.set_num_threads(1)
    from breadth_contact_fit import run as fit
    from verify_breadth_contact import verify
    from run_godot_rig_import import run as engine
    process=psutil.Process();save(output/'runner.json',dict(pid=process.pid,created_at=process.create_time(),status='running',started_at=now()))
    data=read(output/'results.json')
    try:
        for case in p['cases']:
            validate(output);checks=[dict(id=case['id']+'-input',path=str(Path(case['source'])/'character.glb'),sha256=case['files']['character.glb'],frames=case['motion']['frames'],fps=30)]
            for method in p['methods']:
                row=next(r for r in data['rows'] if r['case']==case['id'] and r['method']==method)
                dest=output/'takes'/row['id'];row.update(status='running',started_at=now())
                save(output/'results.json',data);save(output/'pipeline.json',dict(status='fitting',id=row['id']))
                try:
                    fit(case['source'],dest,method);proof=verify(dest)
                    row.update(status='complete',finished_at=now(),verification=proof)
                    checks.append(dict(id=row['id'],path=str(dest/'candidate/character.glb'),sha256=proof['candidate_sha256'],frames=case['motion']['frames'],fps=30))
                except Exception as exc:row.update(status='failed',error=str(exc),traceback=traceback.format_exc(),finished_at=now())
                save(output/'results.json',data);print(row['id']+' '+row['status'],flush=True)
            group=output/'engine-groups'/case['id'];group.mkdir(parents=True);save(group/'manifest.json',dict(cases=checks))
            save(output/'pipeline.json',dict(status='engine',id=case['id']))
            try:
                engine(group,group/'audit');data['engine_groups'].append(dict(case=case['id'],status='complete',proof=read(group/'audit/verification.json')))
            except Exception as exc:data['engine_groups'].append(dict(case=case['id'],status='failed',error=str(exc),traceback=traceback.format_exc()))
            save(output/'results.json',data)
        failed=any(r['status']!='complete' for r in data['rows']) or any(g['status']!='complete' for g in data['engine_groups'])
        save(output/'pipeline.json',dict(status='complete_with_failures' if failed else 'complete',finished_at=now(),quality_approved=False))
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()));raise
    finally:save(output/'runner.json',dict(pid=process.pid,created_at=process.create_time(),status='stopped',finished_at=now()))


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('command',choices=['prepare','run']);a.add_argument('--output',type=Path,required=True)
    a.add_argument('--source',type=Path,default=ROOT/'reports/breadth-transfer-v1');args=a.parse_args()
    if args.command=='prepare':print(prepare(args.source,args.output)['planned_candidates'])
    else:run(args.output)
