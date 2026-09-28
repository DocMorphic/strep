"""Actual simultaneous actor imports with authored world placement in Godot."""
import argparse
import shutil
import subprocess
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from scene_constraints import transform_motion
from inspect_motion import skeleton_metadata


def run(source,output):
    source=Path(source).resolve();output=Path(output).resolve();manifest=read(source/'manifest.json')
    request=dict(scenes=[])
    for item in manifest['scenes']:
        scene=read(source/item['variants']['palm'])['scene'];actors={}
        for name,entry in scene['actors'].items():
            motion=ROOT/entry['motion'];glb=source/entry['preview_glb']
            if sha256(motion)!=entry['source_sha256'] or sha256(glb)!=manifest['assets'][entry['preview_glb']]['sha256']:
                raise ValueError('Scene actor changed before engine import')
            actors[name]=dict(path=str(glb),motion=str(motion),transform=entry['transform'],motion_sha256=sha256(motion),glb_sha256=sha256(glb))
        request['scenes'].append(dict(id=scene['id'],frames=scene['frame_count'],actors=actors))
    output.mkdir(parents=True,exist_ok=False);project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep paired scene import"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
    script=ROOT/'scripts/godot_scene_import_audit.gd';shutil.copyfile(script,project/'audit.gd')
    save(output/'request.json',request);save(output/'pipeline.json',dict(status='processing'))
    executable=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    with (output/'engine.log').open('w',encoding='utf8') as log:
        result=subprocess.run([str(executable),'--headless','--path',str(project),'--script','audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=300)
    if result.returncode:
        save(output/'pipeline.json',dict(status='failed',exit_code=result.returncode));raise RuntimeError('Godot scene import failed; inspect engine.log')
    report=read(output/'engine-output.json');checks=[];names,_,_=skeleton_metadata(77)
    for item,actual in zip(request['scenes'],report['scenes']):
        if item['id']!=actual['id'] or set(item['actors'])!=set(actual['actors']) or len(actual['frames'])!=item['frames']:
            raise ValueError('Engine scene/clock mismatch')
        for name,entry in item['actors'].items():
            motion=dict(np.load(entry['motion'],allow_pickle=False));expected=transform_motion(motion,entry['transform'])
            order=[names.index(n) for n in actual['actors'][name]['bone_names']]
            if len(order)!=77 or len(set(order))!=77:raise ValueError('Imported bone mapping mismatch')
            values=np.array([f[name] for f in actual['frames']]);positions=values[:,:,3];rotations=values[:,:,:3].transpose(0,1,3,2)
            error=float(np.abs(positions-expected['positions'][:,order]).max());rotation_error=float(np.abs(rotations-expected['rotations'][:,order]).max())
            if max(error,rotation_error)>1e-4:raise ValueError('Placed engine pose differs from scene source')
            checks.append(dict(scene_id=item['id'],actor=name,frames=item['frames'],position_error_m=error,rotation_element_error=rotation_error,
                source_sha256=entry['motion_sha256'],glb_sha256=entry['glb_sha256']))
    if len(report['scenes'])!=len(request['scenes']):raise ValueError('Missing engine scenes')
    save(output/'verification.json',dict(created_at=now(),engine=report['engine'],checks=checks,script_sha256=sha256(script),runner_sha256=sha256(__file__),
        scope='Both actors instantiated together; actual Godot GLB import, shared 30fps manual seeking and all77 world bone transforms on every frame. No GPU skin rendering, collision/physics, real-time synchronization, root extraction, marker dispatch or naturalness approval.'))
    save(output/'pipeline.json',dict(status='complete'));print(checks,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('output');args=parser.parse_args();run(args.source,args.output)
