"""A declared post-release return with exact protected approach/grasp frames."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from sphere_approach import set_problem_frame


def release_weight(frame, release_frame, blend_end, profile='quintic'):
    if not np.isfinite([frame,release_frame,blend_end]).all() or blend_end<=release_frame:raise ValueError('Finite ordered release interval required')
    t=float(np.clip((frame-release_frame)/(blend_end-release_frame),0.,1.))
    if profile=='quintic':return 1-t**3*(10+t*(-15+6*t))
    # Complement of the Beta(3,8) CDF: monotone, with two flat derivatives
    # at each endpoint; moves the strongest return earlier in the interval.
    if profile=='early-return':return (1-t)**8*(1+8*t+36*t*t)
    raise ValueError('Unknown release profile')


def run(floor_report,output,blend_frames=24,profile='quintic'):
    release_weight(0,0,1,profile)
    floor_report,output=Path(floor_report).resolve(),Path(output).resolve();fp,fr=read(floor_report/'protocol.json'),read(floor_report/'result.json')
    if fr['status']!='complete' or sha256(floor_report/'motion.npz')!=fr['motion_sha256'] or sha256(floor_report/'protocol.json')!=fr['protocol_sha256']:raise ValueError('Completed floor-corrected clip required')
    study=ROOT/fp['base_study'];protocol,result=read(study/'protocol.json'),read(study/'result.json');release=protocol['active_interval'][1];count=protocol['frame_count']
    if type(blend_frames) is not int or blend_frames<2 or release+blend_frames>=count:raise ValueError('Blend must fit after release inside clip')
    end=release+blend_frames;fit=ROOT/protocol['study']/'fit';summary=read(fit/'summary.json');folder=fit/'assets'/summary['trials'][0]['id']/'A'
    inputs=dict(protocol['inputs'])
    for path in [floor_report/'protocol.json',floor_report/'result.json',floor_report/'motion.npz',study/'protocol.json',study/'result.json']:
        inputs[path.relative_to(ROOT).as_posix()]=sha256(path)
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed')
    skin=dict(np.load(ASSET,allow_pickle=False));p=PoseProblem(folder,skin,protocol['active_interval'][0])
    endpoint=np.array(next(r['parameters'] for r in result['rows'] if r['frame']==release));source=dict(np.load(floor_report/'motion.npz',allow_pickle=False));candidate={k:v.copy() for k,v in source.items()}
    output.mkdir(parents=True,exist_ok=False);(output/'implementation').mkdir()
    methods=['region_release_blend.py','grasp_pose_witness.py','sphere_approach.py','floor_contact.py','scene_solver_context.py','object_geometry.py','inspect_motion.py']
    implementation={n:sha256(ROOT/'scripts'/n) for n in methods}
    for n in methods:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
    save(output/'protocol.json',dict(at=now(),floor_report=floor_report.relative_to(ROOT).as_posix(),base_study=study.relative_to(ROOT).as_posix(),release_frame=release,blend_end=end,blend_frames=blend_frames,profile=profile,
         inputs=inputs,implementation=implementation,scope='New post-release return duration. Reuse the original bounded grasp endpoint; use the recorded profile to blend physical edits toward each original V13 frame. Contact events, approach/grasp and clip length unchanged. Norm-ball convexity does not establish collision or dynamics; full exported audit required.',quality_approved=False))
    rows=[]
    for frame in range(release+1,end):
        set_problem_frame(p,frame);relative=p.previous['local_rot_mats'][frame].transpose(0,2,1)@p.candidate['local_rot_mats'][frame]
        baseline=np.r_[Rotation.from_matrix(relative[p.editable]).as_rotvec().ravel(),p.recipe['root_lift_m'][frame]]
        weight=release_weight(frame,release,end,profile);values=(1-weight)*baseline+weight*endpoint;audit,motion=p.independent(values)
        if not audit['rotation_norm_bounds_passed']:raise ValueError('Original edit bounds exceeded')
        for name in candidate:candidate[name][frame]=motion[name][0]
        rows.append(dict(frame=frame,weight=weight,parameters=values.tolist(),geometry=dict(objects=audit['objects'],minimum_floor_height_m=audit['minimum_floor_height_m']),bounds_passed=audit['rotation_norm_bounds_passed']))
    protected=np.r_[np.arange(release+1),np.arange(end,count)]
    for name in source:np.testing.assert_array_equal(source[name][protected],candidate[name][protected])
    np.savez(output/'motion.npz',**candidate)
    for name,digest in inputs.items():
        if sha256(ROOT/name)!=digest:raise ValueError('Input changed')
    for name,digest in implementation.items():
        if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Implementation changed')
    save(output/'result.json',dict(at=now(),status='complete',rows=rows,protected_frames_exact=len(protected),grasp_endpoint_parameters=endpoint.tolist(),
         motion_sha256=sha256(output/'motion.npz'),protocol_sha256=sha256(output/'protocol.json'),quality_approved=False))
    print(dict(release_frame=release,blend_end=end,edited_frames=len(rows),protected_frames_exact=len(protected)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('floor_report',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--blend-frames',type=int,default=24);parser.add_argument('--profile',choices=['quintic','early-return'],default='quintic');args=parser.parse_args();run(args.floor_report,args.output,args.blend_frames,args.profile)
