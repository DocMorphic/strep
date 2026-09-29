"""Reproducible local angular-step comparisons for an audited region release."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler
from inspect_motion import skeleton_metadata


def rate_steps(local_rotations,fps):
    local=np.asarray(local_rotations)
    if local.ndim!=4 or local.shape[-2:]!=(3,3) or len(local)<3 or not np.isfinite(local).all() or not np.isfinite(fps) or fps<=0:
        raise ValueError('Finite rotation track with at least three frames and positive fps required')
    return np.array([(Rotation.from_matrix(local[f]).inv()*Rotation.from_matrix(local[f+1])).as_rotvec()*fps for f in range(len(local)-1)])


def run(audit,output):
    audit,output=Path(audit).resolve(),Path(output).resolve();verification=read(audit/'verification.json')
    if not verification.get('coupled_patch') or not verification.get('release_patch') or 'coupled_input' not in verification['variants']:
        raise ValueError('Audited coupled source and candidate exports required')
    protocol=read(ROOT/verification['study']/'protocol.json');count=protocol['frame_count'];end=protocol['active_interval'][1]
    boundaries=[end-6,end-5,end,end+3,end+4,verification['release_patch']['blend_end']]
    names,parents,_=skeleton_metadata(77);arms=[names.index(s+n) for s in ['Left','Right'] for n in ['Shoulder','Arm','ForeArm','Hand']]
    output.mkdir(parents=True,exist_ok=False);shutil.copyfile(Path(__file__),output/Path(__file__).name);variants={}
    for label in ['coupled_input','candidate']:
        path=audit/(label+'.glb');expected=verification['variants'][label]['glb_sha256']
        if sha256(path)!=expected:raise ValueError('Audited export changed')
        doc,binary=read_glb(path);sampler=AnimationSampler(doc,binary,0);joints=doc['skins'][0]['joints']
        if [doc['nodes'][j]['name'] for j in joints]!=list(names) or abs(sampler.duration-(count-1)/30)>1e-5:raise ValueError('Expected SOMA 30fps export')
        local=[]
        for frame in range(count):
            world=sampler.sample(float(np.float32(frame/30)))[joints,:3,:3];value=world.copy()
            for j,parent in enumerate(parents):
                if parent>=0:value[j]=world[parent].T@world[j]
            local.append(value)
        rates=rate_steps(np.array(local),30);rows=[]
        for frame in boundaries:
            step=np.linalg.norm(rates[frame]-rates[frame-1],axis=1)
            rows.append(dict(frame=frame,maximum_arm_rate_step_rad_s=float(step[arms].max()),worst_joint=names[arms[np.argmax(step[arms])]],
                             joints=[dict(joint=names[j],previous_speed_rad_s=float(np.linalg.norm(rates[frame-1,j])),next_speed_rad_s=float(np.linalg.norm(rates[frame,j])),body_rate_step_difference_rad_s=float(step[j])) for j in arms]))
        variants[label]=dict(glb_sha256=expected,boundaries=rows)
    save(output/'verification.json',dict(at=now(),source_audit=audit.relative_to(ROOT).as_posix(),source_audit_sha256=sha256(audit/'verification.json'),
         implementation_sha256=sha256(output/Path(__file__).name),variants=variants,scope='Decoded local relative-log rate-step diagnostics, including all eight arm joints at window/release boundaries. These differences are not inertial angular acceleration or perceptual approval.',quality_approved=False))
    print({label:[(r['frame'],r['maximum_arm_rate_step_rad_s']) for r in value['boundaries']] for label,value in variants.items()},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('audit',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.audit,args.output)
