"""Certify restricted finger-only clearance obstructions at a frozen body pose."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem,BODY
from skin_edit_displacement_bound import skin_displacement_bound


def run(study,seed_report,output):
    study=Path(study).resolve();seed_report=Path(seed_report).resolve();output=Path(output).resolve();fit=study/'fit';summary=read(fit/'summary.json');record=read(seed_report/'result.json');protocol=read(seed_report/'protocol.json');frame=protocol['frame']
    if protocol['fit_summary_sha256']!=sha256(fit/'summary.json') or sha256(seed_report/'pose.npz')!=record['pose_sha256']:raise ValueError('Seed binding mismatch')
    for name,digest in protocol['inputs'].items():
        if sha256(ROOT/name)!=digest:raise ValueError('Seed inputs changed')
    skin=dict(np.load(ASSET,allow_pickle=False));folder=fit/'assets'/summary['trials'][0]['id']/'A';p=PoseProblem(folder,skin,frame);seed=np.array(record['parameters']);audit,motion=p.independent(seed)
    if not audit['rotation_norm_bounds_passed']:raise ValueError('Seed violates budgets')
    vertices=p.surface.vertices(motion['global_rot_mats'][0],motion['posed_joints'][0]);angles=np.linalg.norm(seed[:-1].reshape(-1,3),axis=1);radii=np.zeros(77)
    for i in range(len(BODY),len(p.editable)):radii[p.editable[i]]=min(np.pi,p.limits[i]+angles[i])
    local=np.einsum('vwij,vj->vwi',p.surface.inverse[skin['lbs_indices']],p.surface.points)[:,:,:3]
    displacement=skin_displacement_bound(skin['lbs_indices'],skin['lbs_weights'],local,p.parents,np.linalg.norm(p.offsets.numpy(),axis=1),radii)
    rows=[];allowance=2e-6
    for geometry,name,position,rotation in p.objects:
        if geometry.shape!='sphere':raise ValueError('This certificate currently covers exact sphere radial clearance only')
        distance=geometry.distance_gradient(vertices,position.numpy()[0],rotation.numpy()[0])[0]
        upper=distance+displacement+allowance;vertex=int(upper.argmin());required=p.config['object_clearance_m']
        rows.append(dict(object=name,vertex=vertex,current_signed_distance_m=float(distance[vertex]),maximum_finger_displacement_m=float(displacement[vertex]),best_possible_signed_distance_upper_bound_m=float(upper[vertex]),required_clearance_m=required,obstruction=bool(upper[vertex]<required),unavoidable_penetration_lower_bound_m=float(max(0,-upper[vertex])),positive_skin_weights=[dict(joint=p.names[j],weight=float(w)) for j,w in zip(skin['lbs_indices'][vertex],skin['lbs_weights'][vertex]) if w>0]))
    output.mkdir(parents=True,exist_ok=False);snap=output/'implementation';snap.mkdir()
    methods=['certify_finger_pose_clearance.py','skin_edit_displacement_bound.py','grasp_pose_witness.py','floor_contact.py','object_geometry.py','support_contact_v8.py']
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,snap/n)
    save(output/'certificate.json',dict(at=now(),frame=frame,study=study.relative_to(ROOT).as_posix(),seed_result_sha256=sha256(seed_report/'result.json'),seed_pose_sha256=sha256(seed_report/'pose.npz'),seed_protocol_sha256=sha256(seed_report/'protocol.json'),mesh_sha256=sha256(ASSET),inputs=protocol['inputs'],implementation={n:sha256(ROOT/'scripts'/n) for n in methods},finger_local_rotation_distance_bounds_radians={p.names[j]:float(radii[j]) for j in np.flatnonzero(radii)},numeric_allowance_m=allowance,objects=rows,restricted_clearance_obstruction=any(r['obstruction'] for r in rows),scope='Conditional certificate only: body/root frozen at this seed, 38 finger norm budgets relative to original preprocessing, rigid bone lengths and fixed eight-weight LBS. Does NOT prove infeasibility when body poses, targets or budgets change; no whole-clip or anatomical claim.',quality_approved=False))
    print(rows,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('seed_report',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.study,args.seed_report,args.output)
