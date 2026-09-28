"""One fixed gesture refit with source root dynamics preserved exactly."""
import argparse
import copy
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from profile_support_surface import load
from sparse_support_surface import SparseSupportReferenceFitter
from fixed_root_support import constant_root_initial,relax_fixed_root
from rig_loop import encode
from verify_breadth_contact import verify
from support_velocity_traces import run as trace
from support_release_metrics import measure
from study_support_release import compare
from run_godot_rig_import import run as engine
from study_whole_support_breadth import check_engine


def prepare(output,case_id='motion-026-rig-01'):
    if output.exists():raise ValueError('Preserve previous study')
    study=ROOT/'reports/whole-support-breadth-v1'
    protocol=read(study/'protocol.json')
    if sha256(study/'protocol.json')!=read(study/'freeze.json')['protocol_sha256']:raise ValueError('Baseline protocol changed')
    if case_id not in {'motion-026-rig-01','motion-026-rig-02','motion-026-rig-03'}:raise ValueError('This development protocol contains only the three declared gesture rigs')
    prior=study/'takes'/case_id
    completed=next(r for r in read(study/'results.json')['rows'] if r['id']==case_id)
    if completed['status']!='complete' or read(prior/'pipeline.json')['status']!='complete':raise ValueError('Prior case is not complete')
    for name,key in [('verification.json','verification_sha256'),('traces.json','traces_sha256')]:
        if sha256(prior/name)!=completed[key]:raise ValueError('Completed baseline evidence changed')
    names=set(protocol['implementation'])|{'study_fixed_root_support.py','fixed_root_support.py',
        'profile_support_surface.py','sparse_support_surface.py','support_release_metrics.py',
        'study_support_release.py','support_release_clip.py','support_release_hold.py'}
    paths=[prior/n for n in ['request.json','spec.json','fit.npz','fit-summary.json','verification.json','traces.json',
        'input/character.glb','input/report.json','candidate/character.glb','candidate/report.json']]
    paths += [study/'protocol.json',study/'freeze.json',ROOT/'reports/sparse-support-surface-proof-v1.json',ROOT/'reports/sparse-support-solver-proof-v1/completion.json']
    with threadpool_limits(limits=1):
        fitter,previous=load(prior,SparseSupportReferenceFitter)
        initial=constant_root_initial(previous,fitter.bounds)
        raw=np.array([fitter.pose(f,np.zeros(len(fitter.bounds)))[0] for f in range(len(previous))])
        placed=np.array([fitter.pose(f,x)[0] for f,x in enumerate(initial)])
        root=fitter.spec['root_node'];delta=placed[:,root,:3,3]-raw[:,root,:3,3]
        acceleration_error=float(np.abs(np.diff(delta,n=2,axis=0)*fitter.spec['fps']**2).max())
        if acceleration_error>1e-9:raise ValueError('Constant offset changed source root acceleration')
        if not all(np.all(np.asarray(g['weights'])==1.) for g in fitter.support_guides.values()):
            raise ValueError('This pilot is declared for whole-clip drafted support only')
        floor=max(max(0.,-float(fitter.rig.vertices(w)[:,1].min())) for w in placed)
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request=dict(at=now(),prior=str(prior),case=case_id,frames=len(previous),sweeps=6,max_nfev=80,
        method='fixed_root_median_leg_refit',root_offset_m=initial[0,:3].tolist(),
        initialization='Retain prior six-sweep leg edits; replace all root edits with their componentwise median. Six additional leg-only sweeps; not an equal-compute ablation.',
        expected_engine_actor_frames=3*len(previous),inputs={str(p):sha256(p) for p in paths},
        resources=protocol['resources'],implementation={n:sha256(output/'implementation'/n) for n in sorted(names)},
        acceptance='Original raw/prior support, hover, floor, root, joint, global and release acceleration screen plus decoded root-acceleration-vector difference <=1e-4m/s2. No quality or semantic approval.',
        quality_approved=False)
    save(output/'request.json',request)
    save(output/'preflight.json',dict(root_offset_m=initial[0,:3].tolist(),root_acceleration_error_m_s2=acceleration_error,
        floor_before_leg_refit_m=floor,quality_approved=False,scope='All150frames with median root and unchanged prior leg edits; not the fitted/exported result.'))
    save(output/'pipeline.json',dict(at=now(),status='prepared',quality_approved=False))
    print(dict(preflight_root_error=acceleration_error,preflight_floor=floor,offset=initial[0,:3].tolist()))


def run(output):
    request=read(output/'request.json');prior=Path(request['prior'])
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Preserve existing run')
    proc=psutil.Process();save(output/'runner.json',dict(pid=proc.pid,created=proc.create_time(),at=now()))
    def validate():
        for path,digest in [*request['inputs'].items(),*request['resources'].items()]:
            if sha256(path)!=digest:raise ValueError('Input changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
    def phase(status,**kw):
        save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    try:
        validate();dest=output/'take';dest.mkdir();shutil.copytree(prior/'input',dest/'input')
        with threadpool_limits(limits=1):
            fitter,previous=load(prior,SparseSupportReferenceFitter);initial=constant_root_initial(previous,fitter.bounds)
            if initial[0,:3].tolist()!=request['root_offset_m']:raise ValueError('Initializer differs')
            spec=copy.deepcopy(fitter.spec);spec['provenance']='Stationary gesture development refit with constant root offset; no extrapolation to locomotion or semantic approval.'
            save(dest/'spec.json',spec)
            fit_request=read(prior/'request.json');fit_request.update(method=request['method'],initialization=request['initialization'],fixed_root_offset_m=request['root_offset_m'])
            save(dest/'request.json',fit_request);phase('fitting')
            parameters,records,convergence=relax_fixed_root(fitter,initial,sweeps=request['sweeps'],
                progress=lambda sweep,change:phase('fitting',sweep=sweep,max_parameter_change=change))
            after=np.array([fitter.pose(f,x)[0] for f,x in enumerate(parameters)])
            raw=np.array([fitter.pose(f,np.zeros(len(fitter.bounds)))[0] for f in range(len(parameters))])
            candidate=dest/'candidate';candidate.mkdir();report=read(dest/'input/report.json');root=report['root_node']
            animated={c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
            times,roundtrip=encode(fitter.rig,after,animated,root,candidate/'character.glb','Experimental constant-root leg refit')
            for name in ['inventory.json','rig-profile.json','contacts.json']:shutil.copyfile(dest/'input'/name,candidate/name)
            save(candidate/'root-motion.json',dict(node=root,times_s=times.tolist(),positions_m=after[:,root,:3,3].tolist(),
                rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist(),space='Corrected pelvis world track; constant world offset, no root extraction'))
            report.update(glb_sha256=sha256(candidate/'character.glb'),human_approved=False,correction_method=request['method'],
                parent_glb_sha256=fit_request['input_glb_sha256'],target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'])
            save(candidate/'report.json',report);np.savez_compressed(dest/'fit.npz',before=raw,after=after,parameters=parameters,initial=initial)
            save(dest/'solver.json',records);save(dest/'fit-summary.json',dict(convergence=convergence,export=roundtrip,quality_approved=False))
            phase('verifying');proof=verify(dest);traces=trace(dest)
            dynamics={v:measure(path,spec,fit_request['support']) for v,path in [('input',dest/'input/character.glb'),('prior',prior/'candidate/character.glb'),('candidate',candidate/'character.glb')]}
            save(dest/'release-dynamics.json',dynamics)
            decision=compare(read(prior/'verification.json'),proof,read(prior/'traces.json'),traces,dynamics)
            from rig_asset import RigAsset
            from rig_clip_import import AnimationSampler
            tracks=[]
            for path in [dest/'input/character.glb',candidate/'character.glb']:
                rig=RigAsset.load(path);sampler=AnimationSampler(rig.document,rig.binary,0)
                tracks.append(np.array([sampler.sample(float(np.float32(f/spec['fps'])))[root,:3,3] for f in range(spec['frames'])]))
            difference=tracks[1]-tracks[0];error=float(np.abs(np.diff(difference,n=2,axis=0)*spec['fps']**2).max())
            decision['checks']['decoded_source_root_acceleration_preserved']=error<=1e-4
            decision['decoded_root_acceleration_vector_error_m_s2']=error
            decision['passes_development_screen']=all(decision['checks'].values());save(dest/'comparison.json',decision)
            group=output/'engine';group.mkdir();checks=[dict(id=request['case']+'-'+v,path=str(path),sha256=sha256(path),frames=request['frames'],fps=spec['fps']) for v,path in [('input',dest/'input/character.glb'),('prior',prior/'candidate/character.glb'),('candidate',candidate/'character.glb')]]
            save(group/'manifest.json',dict(cases=checks));phase('engine');engine(group,group/'audit')
            count=check_engine(read(group/'audit/verification.json'),checks)
            if count!=request['expected_engine_actor_frames']:raise ValueError('Engine population mismatch')
        validate()
        save(output/'completion.json',dict(at=now(),engine_actor_frames=count,request_sha256=sha256(output/'request.json'),
            decision=decision,files={str(p.relative_to(output)):sha256(p) for p in [dest/'comparison.json',dest/'verification.json',dest/'traces.json',dest/'release-dynamics.json',dest/'fit.npz',dest/'candidate/character.glb',group/'audit/verification.json']},quality_approved=False))
        phase('complete')
    except BaseException as exc:phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path)
    p.add_argument('--case',default='motion-026-rig-01',choices=['motion-026-rig-01','motion-026-rig-02','motion-026-rig-03']);a=p.parse_args()
    if a.command=='prepare':prepare(a.output.resolve(),a.case)
    else:run(a.output.resolve())
