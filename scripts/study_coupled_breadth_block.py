"""One hardest-relative-conflict pilot before broad coupled correction."""
import argparse
import ast
import os
import shutil
from pathlib import Path
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from profile_support_surface import load
from sparse_support_surface import SparseSupportReferenceFitter
from serialized_pose import SerializedPose
from coupled_breadth_block import CoupledBreadthBlock
from block_release_fit import solve
from check_piecewise_derivative import check_direction
from study_breadth_root_cleanup import active_frames
from verify_authored_root_correction import samples
from audit_coupled_breadth import audit
from audit_authoring_intent import check_files
from rig_loop import encode


def select(diagnosis):
    excluded=[r for r in diagnosis['rows'] if r['excluded_by_vertical_bound']]
    if not excluded:raise ValueError('No demonstrated root-only conflict')
    return max(excluded,key=lambda r:(r['necessary_vertical_bound_max_m_s2']/r['acceptance_peak_m_s2'],r['id']))


def make_problem(folder,request):
    fitter,initial=load(folder/'source',SparseSupportReferenceFitter)
    animated={c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
    evaluator=SerializedPose(fitter.rig,animated,fitter.spec['root_node'],len(initial))
    _,world=samples(folder/'source/candidate/character.glb',len(initial))
    return CoupledBreadthBlock(fitter,initial,evaluator,request['frames'],read(folder/'envelope.json'),request['target'],world)


def prepare(diagnosis_path,output):
    if output.exists():raise ValueError('Preserve earlier attempt')
    diagnosis=read(diagnosis_path);selected=select(diagnosis);case=selected['id']
    source=ROOT/'reports/whole-support-breadth-v1/takes'/case
    if sha256(source/'candidate/character.glb')!=selected['source_sha256']:raise ValueError('Diagnosed source changed')
    output.mkdir(parents=True);dest=output/'source';dest.mkdir()
    names=['fit.npz','request.json','spec.json','verification.json','input/character.glb','input/contacts.json','candidate/character.glb','candidate/contacts.json']
    for name in names:
        target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
    spec=read(dest/'spec.json');rig,world=samples(dest/'candidate/character.glb',spec['frames']);root=spec['root_node']
    points=np.asarray([rig.vertices(w) for w in world[::2]]);patches=spec['patches'];centers=np.array([[p[v['vertices']].mean(0) for v in patches.values()] for p in points])
    active=np.array([active_frames(read(dest/'input/contacts.json'),side,spec['frames']) for side in patches]).T
    root_acc=np.linalg.norm(np.diff(world[::2,root,:3,3],n=2,axis=0)*900,axis=1);center=int(root_acc.argmax()+1)
    frames=list(range(max(2,center-2),min(spec['frames']-2,center+3)))
    targets=sorted({c for f in frames for c in [f-1,f,f+1] if 1<=c<spec['frames']-1})
    envelope=dict(active_frames=active.tolist(),support_steps=(active[1:]&active[:-1]).tolist(),
        hover_caps_m=(np.maximum(0.,[[p[v['vertices'],1].min() for v in patches.values()] for p in points])+1e-6).tolist(),
        safety_caps_m_s2=(np.linalg.norm(np.diff(centers,n=2,axis=0)*900,axis=2)+.0036).tolist(),
        support_speed_caps_m_s=(np.linalg.norm(np.diff(centers[:,:,[0,2]],axis=0)*30,axis=2)+60e-6).tolist(),
        root_safety_caps_m_s2=(root_acc+.0036).tolist(),rotation_cap_radians=float(np.pi))
    save(output/'envelope.json',envelope)
    request=dict(at=now(),case=case,selection='Largest relative necessary vertical bound among all nine excluded cases; one five-frame block at its largest source root peak.',
        diagnosis=str(diagnosis_path),diagnosis_sha256=sha256(diagnosis_path),remaining_cases=[r['id'] for r in diagnosis['rows'] if r['id']!=case],
        frames=frames,target=dict(centers=targets,limit_m_s2=selected['original_peak_m_s2']),maxiter=80,
        source_files={p.relative_to(dest).as_posix():sha256(p) for p in dest.rglob('*') if p.is_file()},quality_approved=False)
    with threadpool_limits(limits=1):
        problem=make_problem(output,request);x=problem.initial[np.ix_(problem.frames,problem.free)].ravel();first=problem.evaluate(x)
        def signature(y):
            v=problem.values(y);ids=[]
            for frame in problem.frames:
                p=problem.fitter.surface_jacobian(int(frame),v[frame])[0]
                ids.extend(int(patch[np.argmin(p[patch,1])]) for patch in problem.patches)
            return ids
        rng=np.random.default_rng(975);directions=[]
        for _ in range(3):
            d=rng.normal(size=len(x));d/=np.linalg.norm(d)
            directions.append(check_direction(lambda z:problem.evaluate(z,False),signature,x,d))
        preflight=dict(objective=first[0],minimum_constraint=float(first[2].min()),geometry=problem.geometric_guard(problem.initial),directions=directions,variables=len(x),constraints=len(first[2]))
    save(output/'preflight.json',preflight)
    # Snapshot the actual dependency closure; old experiments retain their sources.
    impl=output/'implementation';impl.mkdir();pending=[Path(__file__).name];seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name);path=ROOT/'scripts'/name;shutil.copyfile(path,impl/name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules=[node.module] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else []
            for module in modules:
                child=(module or '').split('.')[0]+'.py'
                if (ROOT/'scripts'/child).is_file():pending.append(child)
    request['implementation']={n:sha256(impl/n) for n in sorted(seen)}
    save(output/'request.json',request);save(output/'freeze.json',{n:sha256(output/n) for n in ['request.json','envelope.json','preflight.json']})
    valid=preflight['minimum_constraint']>=-1e-7 and preflight['geometry'] and all(d['passed'] for d in directions)
    save(output/'pipeline.json',dict(status='prepared' if valid else 'preflight_failed',at=now()))
    print(preflight,flush=True)
    if not valid:raise ValueError('Preflight failed; preserve diagnostic evidence')


def run(output):
    from action_worker_lock import worker_lock
    from run_godot_rig_import import run as engine_import
    request=read(output/'request.json')
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Fresh prepared trial required')
    check_files(output,read(output/'freeze.json'));check_files(output/'source',request['source_files']);check_files(ROOT/'scripts',request['implementation']);check_files(output/'implementation',request['implementation'])
    save(output/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
    with worker_lock(),threadpool_limits(limits=1):
        p=make_problem(output,request)
        def progress(row):save(output/'pipeline.json',dict(status='fitting',at=now(),**row));print(row,flush=True)
        save(output/'pipeline.json',dict(status='fitting',at=now()));values,solver=solve(p,request['maxiter'],progress);save(output/'solver.json',solver)
        np.savez_compressed(output/'parameters.npz',parameters=values)
        take=output/'take';take.mkdir();shutil.copytree(output/'source/input',take/'input');(take/'candidate').mkdir()
        for name in ['spec.json','request.json']:shutil.copyfile(output/'source'/name,take/name)
        shutil.copyfile(output/'source/candidate/contacts.json',take/'candidate/contacts.json')
        world=np.array([p.fitter.pose(f,x)[0] for f,x in enumerate(values)]);animated={c['target']['node'] for c in p.fitter.rig.document['animations'][0]['channels']}|set(p.fitter.nodes)
        times,_=encode(p.fitter.rig,world,animated,p.root,take/'candidate/character.glb','Coupled root and leg development candidate')
        save(take/'candidate/root-motion.json',dict(node=p.root,times_s=times.tolist(),positions_m=world[:,p.root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(world[:,p.root,:3,:3]).as_quat().tolist()))
        proof=audit(take,output/'source/candidate/character.glb',request['frames'],request['target']['centers'],request['target']['limit_m_s2']);save(output/'audit.json',proof)
        accepted=solver['accepted_fraction'] is not None and proof['all_guards_passed'] and proof['useful_target_improvement']
        save(output/'manifest.json',dict(cases=[dict(id='source',path=str((output/'source/candidate/character.glb').resolve()),sha256=sha256(output/'source/candidate/character.glb'),frames=len(values),fps=30,sample_by_time=True),
            dict(id='candidate',path=str((take/'candidate/character.glb').resolve()),sha256=sha256(take/'candidate/character.glb'),frames=len(values),fps=30,sample_by_time=True)]))
        engine_import(output,output/'engine');check_files(output/'source',request['source_files']);check_files(ROOT/'scripts',request['implementation'])
        save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),audit_sha256=sha256(output/'audit.json'),engine_sha256=sha256(output/'engine/verification.json'),accepted=accepted,quality_approved=False))
        save(output/'pipeline.json',dict(status='complete',accepted=accepted,at=now(),quality_approved=False));print(proof,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path);p.add_argument('--diagnosis',type=Path);a=p.parse_args()
    if a.command=='prepare':prepare(a.diagnosis.resolve(),a.output.resolve())
    else:
        try:run(a.output.resolve())
        except Exception as exc:save(a.output/'failure.json',dict(at=now(),error=str(exc),quality_approved=False));raise
