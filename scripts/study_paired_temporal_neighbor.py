"""Two matched local temporal trials on the first declared high-five pair."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from paired_temporal_neighbor import smooth_export,rotation_channels
from gltf_tools import read_glb,accessor


def preservation(source,candidate,body,record):
    before,binary=read_glb(source);after,payload=read_glb(candidate);bodydoc,bodybin=read_glb(body)
    selected={i for i,n in enumerate(before['nodes']) if n.get('name') in record['selected_joints']}
    locked=np.setdiff1d(np.arange(150),record['frames']);maximum=0.;channels=before['animations'][0]['channels']
    if channels!=after['animations'][0]['channels'] or before['nodes']!=after['nodes'] or before['skins']!=after['skins'] or before['meshes']!=after['meshes']:raise ValueError('Changed rig or channel scope')
    for c in channels:
        a=before['animations'][0]['samplers'][c['sampler']];b=after['animations'][0]['samplers'][c['sampler']]
        np.testing.assert_array_equal(accessor(before,binary,a['input']),accessor(after,payload,b['input']))
        x,y=accessor(before,binary,a['output']),accessor(after,payload,b['output'])
        if c['target']['node'] not in selected or c['target']['path']!='rotation':np.testing.assert_array_equal(x,y)
        else:
            np.testing.assert_array_equal(x[locked],y[locked]);degrees=np.rad2deg((Rotation.from_quat(x).inv()*Rotation.from_quat(y)).magnitude())
            maximum=max(maximum,float(degrees.max()))
    original=rotation_channels(bodydoc,bodybin);changed=rotation_channels(after,payload);finger=[]
    for node,n in enumerate(after['nodes']):
        name=n.get('name','')
        if not name.startswith('LeftHand') or not name[-1:].isdigit():continue
        delta=Rotation.from_quat(original[node][2]).inv()*Rotation.from_quat(changed[node][2]);angle=np.rad2deg(delta.magnitude())
        step=np.rad2deg((delta[:-1].inv()*delta[1:]).magnitude())
        finger.append(dict(joint=name,maximum_edit_degrees=float(angle.max()),maximum_step_degrees=float(step.max()),passed=bool(angle.max()<=60+1e-4 and step.max()<=5+1e-4)))
    if maximum>5+1e-4:raise ValueError('Additional edit budget exceeded')
    return dict(locked_keys_exact=len(locked),unselected_channels_exact=True,translations_exact=True,event_key_exact=True,
                maximum_additional_edit_degrees=maximum,original_finger_limits=finger,original_finger_limits_passed=all(r['passed'] for r in finger))


def run(output):
    output=Path(output).resolve();study=ROOT/'reports/paired-pose-posture-v1';summary_path=ROOT/'reports/paired-pose-posture-summary-v2/summary.json'
    source_request=read(study/'request.json');summary=read(summary_path)
    if source_request['seeds'][0]!=1301:raise ValueError('First declared development seed changed')
    inputs=dict(summary['verified_files']);inputs[str(summary_path)]=sha256(summary_path)
    rates=ROOT/'reports/paired-stage-rates-review-v1/verification.json';inputs[str(rates)]=sha256(rates)
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Development input changed')
    if output.exists():raise ValueError('Preserve earlier trial')
    output.mkdir();snapshot=output/'implementation';snapshot.mkdir()
    methods=['study_paired_temporal_neighbor.py','paired_temporal_neighbor.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','strep.py']
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    source_scene=study/'body_fit_posture-seed-1301.json'
    protocol=dict(at=now(),study=study.relative_to(ROOT).as_posix(),seed=1301,source_scene=source_scene.relative_to(ROOT).as_posix(),
        first=70,event=75,last=80,strength=.25,additional_rotation_limit_degrees=5.,variants=['input','body','body_fingers'],
        inputs=inputs,implementation={n:sha256(snapshot/n) for n in methods},quality_approved=False,
        scope='Matched simultaneous neighbor smoothing on body-only versus body+finger locals. Original frame75, translations, nonselected channels and all outside keys exact. Additional 5-degree local budget and original finger 60-degree/5-degree-step checks. GLB experiments only; no replacement native scene package, collision guarantee, force/anatomical/human or release approval.')
    save(output/'protocol.json',protocol);exports={};cases=[]
    for variant in protocol['variants']:
        folder=output/variant;folder.mkdir();exports[variant]={}
        for actor in ['A','B']:
            source=study/f'seed-1301/{actor}/body_fit_posture/character.glb';body=study/f'seed-1301/{actor}/body_fit/character.glb';target=folder/(actor+'.glb')
            if variant=='input':shutil.copyfile(source,target);record=None;proof=None
            else:
                record=smooth_export(source,target,variant=='body_fingers',70,75,80,.25,5.)
                proof=preservation(source,target,body,record)
            exports[variant][actor]=dict(path=target.relative_to(output).as_posix(),sha256=sha256(target),record=record,preservation=proof)
            cases.append(dict(id=variant+'-'+actor,path=target.relative_to(output).as_posix(),sha256=sha256(target),frames=150,fps=30,sample_by_time=True))
    for file,digest in inputs.items():
        if sha256(file)!=digest:raise ValueError('Input changed during trial')
    for name,digest in protocol['implementation'].items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during trial')
    save(output/'manifest.json',dict(cases=cases,quality_approved=False));save(output/'result.json',dict(at=now(),status='complete',protocol_sha256=sha256(output/'protocol.json'),
        exports=exports,quality_approved=False));print({v:{a:e['preservation'] for a,e in actors.items()} for v,actors in exports.items()},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();run(a.output)
