"""A declared post-release rotation smoothing stage with explicit source replay."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from sphere_approach import set_problem_frame

JOINTS=['Spine1','Spine2','Chest','Neck1','Neck2','Head']


def tapered_weight(frame,first,last,strength):
    if not np.isfinite([frame,first,last,strength]).all() or last<=first or not 0<=strength<=1:raise ValueError('Finite ordered interval and strength in [0,1] required')
    t=float(np.clip((frame-first)/(last-first),0,1))
    return strength*16*t*t*(1-t)*(1-t)


def rotation_neighbor_mean(previous,current,next_,weight):
    if not np.isfinite(weight) or not 0<=weight<=1:raise ValueError('Weight in [0,1] required')
    a,b,c=map(Rotation.from_matrix,[previous,current,next_])
    delta=((b.inv()*a).as_rotvec()+(b.inv()*c).as_rotvec())*.5*weight
    return (b*Rotation.from_rotvec(delta)).as_matrix()


def run(coupled_report,output,strength=.25):
    coupled_report,output=Path(coupled_report).resolve(),Path(output).resolve();cp,cr=read(coupled_report/'protocol.json'),read(coupled_report/'result.json')
    if cr['status']!='complete' or sha256(coupled_report/'protocol.json')!=cr['protocol_sha256'] or sha256(coupled_report/'motion.npz')!=cr['motion_sha256']:raise ValueError('Completed unchanged coupled input required')
    study=ROOT/cp['base_study'];protocol=read(study/'protocol.json');spatial=ROOT/cp['spatial_report'];sp,sr=read(spatial/'protocol.json'),read(spatial/'result.json')
    first=protocol['active_interval'][1]+5;last=first+14;tapered_weight(first,first,last,strength)
    frames=list(range(first+1,last))
    if last>=protocol['frame_count'] or set(frames)&set(cp['frames']):raise ValueError('Post-release window must be separate from coupled grasp edits')
    inputs=dict(cp['inputs'])
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Inherited input changed')
    for folder in [coupled_report,spatial]:
        for name in ['protocol.json','result.json','motion.npz']:inputs[(folder/name).relative_to(ROOT).as_posix()]=sha256(folder/name)
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed')
    fit=ROOT/protocol['study']/'fit';folder=fit/'assets'/read(fit/'summary.json')['trials'][0]['id']/'A';skin=dict(np.load(ASSET,allow_pickle=False));p=PoseProblem(folder,skin,protocol['active_interval'][0])
    joints=[p.names.index(name) for name in JOINTS];columns=np.array([3*p.lookup[j]+axis for j in joints for axis in range(3)])
    parameters={r['frame']:np.array(r['parameters']) for r in sr['rows']}
    source=dict(np.load(coupled_report/'motion.npz',allow_pickle=False));candidate={k:v.copy() for k,v in source.items()}
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    methods=['upper_body_return.py','grasp_pose_witness.py','sphere_approach.py','floor_contact.py','scene_solver_context.py','object_geometry.py','inspect_motion.py'];implementation={n:sha256(ROOT/'scripts'/n) for n in methods}
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'protocol.json',dict(at=now(),coupled_report=coupled_report.relative_to(ROOT).as_posix(),spatial_report=spatial.relative_to(ROOT).as_posix(),base_study=cp['base_study'],inputs=inputs,implementation=implementation,
         joint_names=JOINTS,columns=columns.tolist(),locked_endpoints=[first,last],frames=frames,strength=strength,
         scope='Single simultaneous local rotation-neighbor smoothing pass for six upper-body joints after release. Quartic taper zero at both endpoints. Other physical edits/root and all outside frames unchanged. Source parameter provenance is independently replayed; no geometry/dynamics guarantee without export audit.',quality_approved=False))
    rows=[]
    for frame in frames:
        set_problem_frame(p,frame);base=parameters[frame];_,replay=p.independent(base)
        for name in source:np.testing.assert_array_equal(replay[name][0].astype(source[name].dtype),source[name][frame])
        weight=tapered_weight(frame,first,last,strength)
        desired=rotation_neighbor_mean(source['local_rot_mats'][frame-1,joints],source['local_rot_mats'][frame,joints],source['local_rot_mats'][frame+1,joints],weight)
        values=base.copy();values[columns]=Rotation.from_matrix(p.previous['local_rot_mats'][frame,joints].transpose(0,2,1)@desired).as_rotvec().ravel()
        audit,motion=p.independent(values)
        for name in candidate:candidate[name][frame]=motion[name][0]
        rows.append(dict(frame=frame,weight=weight,parameters=values.tolist(),candidate=audit))
    protected=np.setdiff1d(np.arange(protocol['frame_count']),frames)
    for name in source:np.testing.assert_array_equal(candidate[name][protected],source[name][protected])
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed during smoothing')
    for name,digest in implementation.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed during smoothing')
    np.savez(output/'motion.npz',**candidate)
    save(output/'result.json',dict(at=now(),status='complete',rows=rows,protected_frames_exact=len(protected),motion_sha256=sha256(output/'motion.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    print(dict(edited_frames=frames,protected_frames_exact=len(protected),strength=strength),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('coupled_report',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--strength',type=float,default=.25);args=parser.parse_args();run(args.coupled_report,args.output,args.strength)
