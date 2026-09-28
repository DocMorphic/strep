"""Separate preexisting source edit-limit failures from local-window regressions."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from rig_asset import RigAsset
from rig_transition import localize
from strep import ROOT,now,read,save,sha256


def measure(reference,candidate,parents,spec,weights):
    a=localize(reference,parents);b=localize(candidate,parents)
    shift=candidate[:,spec['root_node'],:3,3]-reference[:,spec['root_node'],:3,3]
    steps=np.linalg.norm(np.diff(shift,axis=0),axis=1)
    touched=(weights[:-1]>0)|(weights[1:]>0)
    roots=[dict(arrival_frame=int(f+1),value_m=float(steps[f]),inside_edit_window=bool(touched[f])) for f in np.flatnonzero(steps>spec['limits']['root_step_m']+1e-6)]
    joints={};pose=[]
    for role,e in spec['edit_joints'].items():
        n=e['node'];delta=a[:,n,:3,:3].transpose(0,2,1)@b[:,n,:3,:3]
        angles=np.degrees(Rotation.from_matrix(delta).magnitude())
        speed=np.degrees(Rotation.from_matrix(delta[:-1].transpose(0,2,1)@delta[1:]).magnitude())
        joints[role]=[dict(arrival_frame=int(f+1),degrees=float(speed[f]),inside_edit_window=bool(touched[f])) for f in np.flatnonzero(speed>spec['limits']['joint_step_degrees']+1e-4)]
        pose.extend(dict(role=role,frame=int(f),degrees=float(angles[f]),inside_edit_window=bool(weights[f]>0)) for f in np.flatnonzero(angles>e['limit_degrees']+1e-4))
    return dict(root_step_violations=roots,joint_step_violations=joints,joint_pose_violations=pose,
        root_step_global_max_m=float(steps.max()),root_step_window_max_m=float(steps[touched].max()),
        root_horizontal_max_m=float(np.linalg.norm(shift[:,[0,2]],axis=1).max()),root_vertical_max_m=float(abs(shift[:,1]).max()))


def run(folder,output):
    if output.exists():raise ValueError('Preserve earlier bounds comparison')
    if read(folder/'pipeline.json')['status']!='complete':raise ValueError('Incomplete window study')
    rows=read(folder/'results.json')['rows'];proof=read(folder/'engine/verification.json')['checks']
    if [(r['id'],r['candidate_sha256']) for r in rows]!=[(r['id'],r['source_sha256']) for r in proof]:raise ValueError('Engine evidence mismatch')
    results=[];inputs={str(folder/n):sha256(folder/n) for n in ['protocol.json','results.json','engine/verification.json']}
    for row in rows:
        for file,digest in row['detail_hashes'].items():
            path=folder/row['id']/file
            if sha256(path)!=digest:raise ValueError('Diagnostic changed')
            inputs[str(path)]=digest
        with np.load(folder/row['id']/'poses.npz',allow_pickle=False) as z:data=dict(z)
        specfile=ROOT/'reports/knee-patch-feasibility-v1'/row['id']/'spec.json';spec=read(specfile)
        body=ROOT/'reports/kneel-body-clearance-v1/takes'/row['id']/'soma.glb'
        if sha256(body)!=row['body_sha256']:raise ValueError('Body input changed')
        rig=RigAsset.load(body);inputs[str(specfile)]=sha256(specfile);inputs[str(body)]=sha256(body)
        before=measure(data['limb'],data['body'],rig.parents,spec,data['weights'])
        after=measure(data['limb'],data['after'],rig.parents,spec,data['weights'])
        result=dict(id=row['id'],before=before,after=after,source_frame=row['source_frame'],
            floor_max_m=row['floor_max_m'],center_contact_passed=row['center_contact_passed'],
            after_order_proxy=row['after_posture']['upright_kneel_upright_proxy_present'],quality_approved=False)
        results.append(result)
    output.mkdir(parents=True);save(output/'comparison.json',dict(at=now(),inputs=inputs,rows=results,quality_approved=False,
        scope='Whole-clip and edited-window limits reported separately. Unedited source failures remain visible and are not attributed to the new blend. No contact-interval or realism approval.'))
    lines=['# Contact-window comparison','','The smooth local edit hits all eight center-frame targets, but every clip reintroduces sampled floor penetration. Preexisting body-clearance edit-limit failures are recorded separately.','',
           '| Case | Floor depth (mm) | Input / candidate root step inside window (mm) | Candidate posture order |','|---|---:|---:|---|']
    for r in results:lines.append(f"| {r['id']} | {r['floor_max_m']*1000:.2f} | {r['before']['root_step_window_max_m']*1000:.2f} / {r['after']['root_step_window_max_m']*1000:.2f} | {r['after_order_proxy']} |")
    lines+=['','All 1,440 candidate Godot actor-frames passed import checks. Geometry was sampled at keys and quarter frames (717 samples per clip). These are failed development corrections, not adopted animations.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(dict(clips=len(results),floor_failed=sum(r['floor_max_m']>.005 for r in results)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.folder.resolve(),a.output.resolve())
