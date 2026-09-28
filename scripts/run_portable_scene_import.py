"""Import an extracted scene ZIP, actors and objects together on one clock."""
import argparse
import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from scene_constraints import transform_motion
from inspect_motion import skeleton_metadata
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def run(source,output):
    source=Path(source).resolve();output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False);package=output/'extracted';package.mkdir()
    with zipfile.ZipFile(source/'scene-animation.zip') as archive:
        if archive.testzip() is not None:raise ValueError('Damaged package')
        for name in archive.namelist():
            target=(package/name).resolve()
            if not target.is_relative_to(package.resolve()):raise ValueError('Package path escapes extraction')
            if name!='README.txt' and hashlib.sha256(archive.read(name)).hexdigest()!=sha256(source/name):raise ValueError('Package differs from saved output')
        archive.extractall(package)
    scene=read(package/'portable-scene.json');actors={}
    for name,entry in scene['actors'].items():
        motion=(package/entry['motion']).resolve();glb=(package/entry['preview_glb']).resolve()
        if not motion.is_relative_to(package) or not glb.is_relative_to(package):raise ValueError('Nonportable actor')
        if sha256(motion)!=entry['source_sha256']:raise ValueError('Actor source mismatch')
        actors[name]=dict(path=str(glb),motion=str(motion),transform=entry['transform'],motion_sha256=sha256(motion),glb_sha256=sha256(glb))
    object_glb=(package/scene['objects_glb']).resolve()
    if not object_glb.is_relative_to(package):raise ValueError('Nonportable objects')
    request=dict(scenes=[dict(id=scene['id'],frames=scene['frame_count'],actors=actors,objects_glb=str(object_glb),object_names=list(scene['objects']))])
    save(output/'request.json',request);save(output/'pipeline.json',dict(status='processing'))
    project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep portable scene import"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
    script=ROOT/'scripts/godot_scene_import_audit.gd';shutil.copyfile(script,project/'audit.gd')
    executable=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    with (output/'engine.log').open('w',encoding='utf8') as log:
        result=subprocess.run([str(executable),'--headless','--path',str(project),'--script','audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=300)
    if result.returncode:
        save(output/'pipeline.json',dict(status='failed',exit_code=result.returncode));raise RuntimeError('Engine failed; inspect engine.log')
    report=read(output/'engine-output.json');assert len(report['scenes'])==1
    actual=report['scenes'][0];assert actual['id']==scene['id'] and set(actual['actors'])==set(actors)
    assert len(actual['frames'])==len(actual['object_frames'])==scene['frame_count']
    checks=[];names,_,_=skeleton_metadata(77)
    for name,entry in actors.items():
        expected=transform_motion(dict(np.load(entry['motion'],allow_pickle=False)),entry['transform'])
        order=[names.index(n) for n in actual['actors'][name]['bone_names']];assert len(order)==len(set(order))==77
        values=np.asarray([f[name] for f in actual['frames']]);positions=values[:,:,3];rotations=values[:,:,:3].transpose(0,1,3,2)
        pe=float(np.abs(positions-expected['positions'][:,order]).max());re=float(np.abs(rotations-expected['rotations'][:,order]).max())
        checks.append(dict(actor=name,frames=scene['frame_count'],max_position_error_m=pe,max_rotation_element_error=re,precision_screen=1e-4,passed=max(pe,re)<=1e-4))
    doc,binary=read_glb(object_glb);sampler=AnimationSampler(doc,binary,0);object_checks=[]
    for name in scene['objects']:
        node=next(i for i,n in enumerate(doc['nodes']) if n.get('extras',{}).get('strep_object_id')==name)
        pe=0.;re=0.;worst=None
        for frame in range(scene['frame_count']):
            assert set(actual['object_frames'][frame])==set(scene['objects'])
            observed=np.asarray(actual['object_frames'][frame][name]);expected=sampler.sample(float(np.float32(frame/30)))[node]
            pe=max(pe,float(np.abs(observed[3]-expected[:3,3]).max()))
            error=float(np.abs(observed[:3].T-expected[:3,:3]).max())
            if error>re:re=error;worst=frame
        object_checks.append(dict(object=name,frames=scene['frame_count'],max_position_error_m=pe,max_rotation_element_error=re,worst_rotation_frame=worst,precision_screen=1e-5,passed=max(pe,re)<=1e-5))
    verification=dict(at=now(),engine=report['engine'],actors=checks,objects=object_checks,all_precision_screens_passed=all(c['passed'] for c in checks+object_checks),package_sha256=sha256(source/'scene-animation.zip'),
        script_sha256=sha256(script),runner_sha256=sha256(__file__),scope='Relocated ZIP, separate actor and object GLBs instantiated together, authored placements and shared 30fps manual seeking. All actor bones and object transforms checked at every frame. No runtime physics, GPU rendering, event dispatch or human approval.')
    save(output/'verification.json',verification);save(output/'pipeline.json',dict(status='complete',quality_approved=False));print(verification,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('output');args=parser.parse_args();run(args.source,args.output)
