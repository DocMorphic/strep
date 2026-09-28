"""Actual Godot import checks for every raw breadth clip, in bounded groups."""
import argparse
import gc
import os
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT,read,save,sha256,now
from breadth_study import STUDY,validate_freeze
from run_godot_scene_import import run as engine


def run(output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve existing engine study')
    if read(STUDY/'pipeline.json')['status']!='complete':raise ValueError('Generation is not complete')
    frozen=validate_freeze(STUDY);entries=[]
    for batch in frozen['batches']:
        for trial in read(ROOT/batch['output']/'summary.json')['trials']:
            folder=ROOT/batch['output']/'takes'/trial['id']
            entries.append(dict(id=trial['id'],frames=trial['frames'],motion=str(folder/'motion.npz'),glb=str(folder/'soma.glb'),
                motion_sha256=trial['hashes']['motion.npz'],glb_sha256=trial['hashes']['soma.glb']))
    if len(entries)!=390 or len({r['id'] for r in entries})!=390:raise ValueError('Unexpected source population')
    output.mkdir(parents=True);(output/'implementation').mkdir()
    sources=['study_breadth_native_engine.py','run_godot_scene_import.py','godot_scene_import_audit.gd','scene_constraints.py','inspect_motion.py']
    for name in sources:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    hashes={n:sha256(ROOT/'scripts'/n) for n in sources}
    save(output/'protocol.json',dict(at=now(),source_freeze_sha256=sha256(STUDY/'freeze.json'),entries=entries,group_size=13,implementation=hashes,
        scope='Every raw clip imported alone with identity scene placement, all77 bones and integer 30fps frames. No additional scene contacts, physics, pixel output, root/event playback or semantic approval.'))
    process=psutil.Process();save(output/'runner.json',dict(pid=process.pid,created_at=process.create_time(),status='running'))
    groups=[];save(output/'results.json',dict(groups=groups,planned_clips=len(entries),quality_approved=False))
    for start in range(0,len(entries),13):
        number=start//13+1;folder=output/f'group-{number:02d}';folder.mkdir();manifest=dict(scenes=[],assets={})
        subset=entries[start:start+13]
        for row in subset:
            glb=Path(row['glb']);motion=Path(row['motion'])
            if not glb.is_relative_to(ROOT) or not motion.is_relative_to(ROOT):raise ValueError('Source escapes project')
            relative=os.path.relpath(glb,folder).replace('\\','/')
            scene=dict(id=row['id'],frame_count=row['frames'],actors={'A':dict(motion=motion.relative_to(ROOT).as_posix(),source_sha256=row['motion_sha256'],preview_glb=relative,
                transform=dict(translation_m=[0.,0.,0.],rotation_xyzw=[0.,0.,0.,1.]))})
            save(folder/(row['id']+'.json'),dict(scene=scene));manifest['scenes'].append(dict(id=row['id'],variants={'palm':row['id']+'.json'}))
            manifest['assets'][relative]=dict(sha256=row['glb_sha256'])
        save(folder/'manifest.json',manifest);save(output/'pipeline.json',dict(status='importing',group=number,completed_clips=sum(g.get('clips',0) for g in groups)))
        try:
            if psutil.virtual_memory().available<2*1024**3:raise MemoryError('Available RAM below 2 GiB before group; preserve failure')
            for name,digest in hashes.items():
                if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Frozen engine implementation changed')
            engine(folder,folder/'audit');audit=read(folder/'audit/verification.json')
            checks=audit['checks']
            if len(checks)!=len(subset):raise ValueError('Incomplete group')
            groups.append(dict(group=number,status='complete',clips=len(checks),frames=sum(c['frames'] for c in checks),
                position_error_m=max(c['position_error_m'] for c in checks),rotation_element_error=max(c['rotation_element_error'] for c in checks),
                verification_sha256=sha256(folder/'audit/verification.json')))
        except Exception as error:
            (folder/'failure.txt').write_text(traceback.format_exc(),encoding='utf8')
            groups.append(dict(group=number,status='failed',planned_clips=len(subset),reason=str(error)))
        save(output/'results.json',dict(groups=groups,planned_clips=len(entries),quality_approved=False))
        print('Group',number,groups[-1]['status'],flush=True);gc.collect()
    save(output/'pipeline.json',dict(status='complete' if all(g['status']=='complete' for g in groups) else 'complete_with_failures',finished_at=now(),quality_approved=False))
    save(output/'runner.json',dict(pid=process.pid,created_at=process.create_time(),status='finished'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);run(p.parse_args().output)
