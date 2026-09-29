"""Local right-arm feasibility projection; original reference and audit limits retained."""
import sys,time,os,shutil,copy
from pathlib import Path
import numpy as np
import torch,psutil
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path.cwd()/'scripts'))
from strep import ROOT,read,save,sha256,now
from floor_contact import Surface,reconstruct
from build_soma_preview import ASSET,make_preview
from gltf_tools import write_glb
from inspect_motion import skeleton_metadata
from region_contact_objective import RegionObjective,violations
from scene_constraints import sample_object,pose
from object_geometry import scene_geometry
from audit_scene_region_fit import edit_bounds,native_fk_error,run as audit_geometry
from audit_scene_joint_rates import run as audit_rates
from audit_scene_preserved_support import run as audit_support
from run_godot_rig_import import run as audit_engine
from shared_pose_diagnostic import require_repeated_motion,require_static_scene
from support_contact_v8 import CONFIG,finger_rotation_budgets

def run(parent, root):
    parent,root=Path(parent).resolve(),Path(root).resolve()
    if not root.is_relative_to(ROOT/'reports') or root.exists():raise ValueError('Fresh local report directory required')
    root.mkdir(parents=True)

    source=dict(np.load(parent/'source-motion.npz'));seed=dict(np.load(parent/'motion.npz'));skin=dict(np.load(ASSET))
    scene=read(parent/'authored-scene.json');package=read(parent/'region-constraints.json');oldrecipe=read(parent/'recipe.json')
    assert read(parent/'result.json')['candidate_sha256']==sha256(parent/'motion.npz')
    assert require_repeated_motion(source)==5 and require_repeated_motion(seed)==5;require_static_scene(scene,'A',['left-grip','right-grip'])
    origin,placement=pose(scene['actors']['A']['transform']);assert np.array_equal(origin,np.zeros(3)) and np.array_equal(placement,np.eye(3))
    names,parents,_=skeleton_metadata(77);surface=Surface(skin);torch.set_num_threads(2)
    joint_names=['RightArm','RightForeArm','RightHand','RightHandPinky1','RightHandPinky2','RightHandPinky3','RightHandPinky4']
    joints=[names.index(n) for n in joint_names];dim=len(joints)*3;scale=np.deg2rad(.5)
    fingers=finger_rotation_budgets(names);caps=np.array([fingers.get(j,CONFIG['max_rotation_degrees']) for j in joints])
    records=RegionObjective(package,source,skin,'balanced','penalty','frozen').records
    records=[r for r in records if r['frame']==0]
    for r in records:
     index=next(i for i,x in enumerate(RegionObjective(package,source,skin).records) if x['frame']==0 and x['hand']==r['hand'])
     remap={v:i for i,v in enumerate(r['ids'])};r['triple']=np.array([remap[v] for v in oldrecipe['distributed_regions']['final_witnesses'][index]])
    offsets=np.zeros_like(source['posed_joints'][0],dtype=float)
    for j,p in enumerate(parents):
     if p>=0:offsets[j]=source['global_rot_mats'][0,p].T@(source['posed_joints'][0,j]-source['posed_joints'][0,p])
    def state(x):
     local=seed['local_rot_mats'][0].astype(np.float64,copy=True);local[joints]=local[joints]@Rotation.from_rotvec(x.reshape(-1,3)*scale).as_matrix()
     rotations=np.empty_like(local);positions=np.empty_like(offsets)
     for j,p in enumerate(parents):
      rotations[j]=local[j] if p<0 else rotations[p]@local[j]
      positions[j]=seed['root_positions'][0] if p<0 else positions[p]+rotations[p]@offsets[j]
     return local,rotations,positions
    _,r,p=state(np.zeros(dim));vertices=surface.vertices(r,p)
    assert max(np.abs(r-seed['global_rot_mats'][0]).max(),np.abs(p-seed['posed_joints'][0]).max())<3e-6
    objects=[]
    for name,obj in scene['objects'].items():
     op,orr=sample_object(obj,5);g=scene_geometry(obj);ids=np.flatnonzero(g.distance_gradient(vertices,op[0],orr[0])[0]<.005)
     objects.append((name,g,op[0],orr[0],ids))
    floor_ids=np.flatnonzero(vertices[:,1]<.005)
    selected=np.unique(np.concatenate([r['ids'] for r in records]+[o[4] for o in objects]+[floor_ids]));mapping={v:i for i,v in enumerate(selected)}
    foot_ids=np.unique(np.concatenate([surface.regions['LeftFoot'],surface.regions['RightFoot']]))
    initial_feet=vertices[foot_ids];calls=0;cache=None

    def constraints(x):
     nonlocal calls,cache
     if cache is not None and np.array_equal(x,cache[0]):return cache[1].copy()
     local,r,p=state(x);v=surface.vertices(r,p,selected);out=[]
     # Source-relative rotation balls plus the hard local component trust box.
     angle=np.rad2deg(Rotation.from_matrix(source['local_rot_mats'][0,joints].transpose(0,2,1)@local[joints]).magnitude())
     out.extend((caps-angle)/caps)
     for record in records:
      def t(v):return torch.as_tensor(v,dtype=torch.float64)
      points=v[[mapping[i] for i in record['ids']]]
      residual=violations(t(points),record['faces'],record['triple'],record['anchor'],t(record['target']),t(record['desired_normal']),record['geometry'],t(record['position']),t(record['rotation']),record['limits'],record['anchor_tolerance']).numpy()
      # All authored regional rows, with a tiny solver interior offset only.
      out.extend(-residual-.001)
     for _,g,op,orr,ids in objects:
      if len(ids):out.extend((g.distance_gradient(v[[mapping[i] for i in ids]],op,orr)[0]-.00201)/.001)
     if len(floor_ids):out.extend((v[[mapping[i] for i in floor_ids],1]-.00201)/.001)
     values=np.array(out);assert np.isfinite(values).all();calls+=1;cache=(x.copy(),values.copy());return values

    def jacobian(x):
     h=1e-4;eye=np.eye(dim)*h
     return np.stack([(constraints(x+d)-constraints(x-d))/(2*h) for d in eye],axis=1)

    inputs={str(p):sha256(p) for p in [parent/'source-motion.npz',parent/'motion.npz',parent/'authored-scene.json',parent/'region-constraints.json',parent/'recipe.json',parent/'result.json',ASSET]}
    implementation=['region_contact_objective.py','floor_contact.py','support_contact_v5.py','support_contact_v8.py','contact_spec.py','scene_region_contact.py','scene_constraints.py','object_geometry.py','shared_pose_diagnostic.py','inspect_motion.py','build_soma_preview.py']
    impl={n:sha256(ROOT/'scripts'/n) for n in implementation}
    save(root/'owner.json',dict(pid=os.getpid(),create_time=psutil.Process().create_time(),method_sha256=sha256(__file__)))
    x0=np.zeros(dim);j=jacobian(x0);direction=np.random.default_rng(17).normal(size=dim);direction/=np.linalg.norm(direction)
    h=2e-5;fd=(constraints(x0+h*direction)-constraints(x0-h*direction))/(2*h)
    np.testing.assert_allclose(j@direction,fd,atol=2e-5,rtol=2e-4)
    save(root/'preflight.json',dict(constraints=len(constraints(x0)),coordinates=dim,selected_vertices=len(selected),derivative_max_error=float(abs(j@direction-fd).max()),initial_minimum_constraint=float(constraints(x0).min()),joint_names=joint_names,trust_per_component_degrees=.5,inputs=inputs,implementation=impl))
    print('Preflight',read(root/'preflight.json')['initial_minimum_constraint'],flush=True)
    started=time.monotonic();history=[]
    def callback(x):
     row=dict(iteration=len(history)+1,seconds=time.monotonic()-started,minimum_constraint=float(constraints(x).min()),max_step_degrees=float(abs(x).max()*.5));history.append(row);save(root/'progress.json',dict(status='running',history=history));print(row,flush=True)
     if time.monotonic()-started>240:raise TimeoutError('Projection time budget exceeded')
    fit=minimize(lambda x:float(x@x)/2,x0,jac=lambda x:x,method='SLSQP',bounds=[(-1,1)]*dim,constraints=[dict(type='ineq',fun=constraints,jac=jacobian)],callback=callback,options=dict(maxiter=40,ftol=1e-10))
    local,r,p=state(fit.x);full=surface.vertices(r,p)
    assert np.max(abs(full[foot_ids]-initial_feet))<1e-10
    local_track=np.repeat(local[None],5,axis=0);base={k:v.copy() for k,v in source.items()};base['root_positions']=seed['root_positions'].copy();motion=reconstruct(base,local_track,parents)
    assert edit_bounds(source,motion,names,CONFIG)[0] and native_fk_error(source,motion,parents)<3e-6
    assert require_repeated_motion(motion)==5
    for path,digest in inputs.items():assert sha256(path)==digest
    for name,digest in impl.items():assert sha256(ROOT/'scripts'/name)==digest
    study=root/'projection';study.mkdir();snap=study/'implementation';snap.mkdir()
    for name in implementation:shutil.copyfile(ROOT/'scripts'/name,snap/name)
    shutil.copyfile(__file__,snap/'method.py');impl['method.py']=sha256(__file__)
    shutil.copyfile(parent/'source-motion.npz',study/'source-motion.npz');save(study/'authored-scene.json',scene)
    protocol=dict(at=now(),actor='A',contact_ids=['left-grip','right-grip'],inputs=inputs,implementation=impl,config=CONFIG,preserve_support_regions=['LeftFoot','RightFoot'],method='local constrained right-arm projection',quality_approved=False)
    save(study/'protocol.json',protocol)
    recipe=dict(contact_spec=package['anchor_subproblem'],method='SLSQP',solver_success=bool(fit.success),message=str(fit.message),iterations=int(fit.nit),evaluations=calls,history=history,selected_vertices=selected.tolist(),selected_geometry={o[0]:o[4].tolist() for o in objects},joint_names=joint_names,local_edit_vectors_degrees=(fit.x.reshape(-1,3)*.5).tolist(),root_lift_m=(motion['root_positions'][:,1]-source['root_positions'][:,1]).tolist(),max_rotation_delta_degrees=float(edit_bounds(source,motion,names,CONFIG)[1].max()),minimum_solver_constraint=float(constraints(fit.x).min()),foot_surface_change_m=float(np.max(abs(full[foot_ids]-initial_feet))),quality_approved=False)
    save(study/'recipe.json',recipe);np.savez(study/'motion.npz',**motion)
    for label,clip in [('source',source),('candidate',motion)]:
     doc,binary,_,_=make_preview(skin,clip,np.zeros(3),repeat=False);write_glb(study/(label+'.glb'),doc,binary)
    candidate=copy.deepcopy(scene);candidate['actors']['A']['motion']=(study/'motion.npz').relative_to(ROOT).as_posix();candidate['actors']['A']['source_sha256']=sha256(study/'motion.npz');save(study/'candidate-scene.json',candidate)
    save(study/'result.json',dict(status='complete',seconds=time.monotonic()-started,candidate_sha256=sha256(study/'motion.npz'),candidate_glb_sha256=sha256(study/'candidate.glb'),source_glb_sha256=sha256(study/'source.glb'),recipe_sha256=sha256(study/'recipe.json'),authored_scene_sha256=sha256(study/'authored-scene.json'),protocol_sha256=sha256(study/'protocol.json'),quality_approved=False))
    done=root/'audit';done.mkdir();audit_geometry(study,done/'geometry');audit_rates(study,done/'joint-rates.json');audit_support(study,done/'support.json')
    save(done/'manifest.json',dict(cases=[dict(id=n,path=str(study/(n+'.glb')),sha256=sha256(study/(n+'.glb')),frames=5,fps=30,sample_by_time=True) for n in ['source','candidate']]))
    audit_engine(done,done/'engine')
    save(root/'status.json',dict(status='complete',method_sha256=sha256(__file__),quality_approved=False))
    print('Completed',read(done/'geometry/verification.json')['variants']['candidate']['geometry_failures'],read(done/'geometry/verification.json')['variants']['candidate']['contact_failures'],flush=True)


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("study",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();run(a.study,a.output)
