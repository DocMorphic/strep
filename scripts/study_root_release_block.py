"""Frozen root-aware follow-up for held clips rejected by the fixed-root protocol."""
import argparse
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
from serialized_pose import SerializedPose
from root_release_block import RootBlockProblem
from block_release_fit import solve
from study_guarded_release import support_frames,caps_from_baselines
from release_trial_selection import peak_joint
from check_piecewise_derivative import check_direction
from rig_transition import localize
from finalize_release_trial import finalize


def problem_for(request,envelope):
    held=Path(request['held']);fitter,initial=load(held,SparseSupportReferenceFitter)
    if request.get('source_trial'):initial=np.load(Path(request['source_trial'])/'take/parameters.npz',allow_pickle=False)['parameters']
    animated={c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
    oracle=SerializedPose(fitter.rig,animated,fitter.spec['root_node'],len(initial))
    free=[i for i in range(initial.shape[1]) if i not in envelope['protected_columns']]
    return RootBlockProblem(fitter,initial,oracle,request['frames'],free,envelope,request['root_target'])


def prepare(output,case,source=None):
    if output.exists():raise ValueError('Preserve prior study')
    held=ROOT/'reports/support-release-hold-v1/takes'/case;prior=ROOT/'reports/whole-support-breadth-v1/takes'/case
    eligibility=ROOT/'reports/release-method-eligibility-v1.json';entry=next(r for r in read(eligibility)['rows'] if r['case']==case)
    for path,digest in entry['inputs'].items():
        if sha256(ROOT/path)!=digest:raise ValueError('Eligibility source changed')
    if entry['prerequisites']['unchanged_root_already_passes']:raise ValueError('This protocol targets the recorded root-failure population')
    fitter,initial=load(held,SparseSupportReferenceFitter);spec=fitter.spec
    if spec['fps']!=30:raise ValueError('Current export supports30fps')
    input_paths=[eligibility,ROOT/'reports/held-root-acceleration-attribution-v1.json']
    input_paths.extend(folder/name for folder in [held,prior] for name in ['fit.npz','request.json','spec.json','candidate/character.glb','verification.json','traces.json'])
    input_paths.extend(held/name for name in ['input/character.glb','input/contacts.json','input/report.json','release-dynamics.json','comparison.json'])
    if source:
        source=source.resolve();original=read(source/'request.json');done=read(source/'completion.json')
        if original['case']!=case or read(source/'pipeline.json')['status']!='complete':raise ValueError('Completed same-case source required')
        for name,digest in done['files'].items():
            if sha256(source/name)!=digest:raise ValueError('Completed source changed')
        initial=np.load(source/'take/parameters.npz',allow_pickle=False)['parameters']
        input_paths.extend(source/name for name in ['request.json','completion.json','envelope.json','take/parameters.npz','take/candidate/character.glb'])
    animated={c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
    oracle=SerializedPose(fitter.rig,animated,spec['root_node'],len(initial))
    world=np.array([oracle.pose(fitter.pose(f,x)[0]) for f,x in enumerate(initial)])
    surfaces=np.array([fitter.rig.vertices(w) for w in world]);patches=[p['vertices'] for p in spec['patches'].values()]
    centers=np.array([[surface[ids].mean(axis=0) for ids in patches] for surface in surfaces])
    active=support_frames(held,spec);root_norm=np.linalg.norm(np.diff(world[:,spec['root_node'],:3,3],n=2,axis=0)*spec['fps']**2,axis=1)
    attribution=next(r for r in read(input_paths[1])['rows'] if r['case']==case);root_limit=attribution['original_global_limit_m_s2']
    if source:
        envelope=read(source/'envelope.json');selection=original['joint_selection']
    else:
        selection=peak_joint(localize(world,fitter.rig.parents),fitter.nodes);protected=[]
        for node in selection['protected_nodes']:
            start=3+3*fitter.nodes.index(node);protected.extend(range(start,start+3))
        caps=np.maximum(caps_from_baselines(held,spec),np.linalg.norm(np.diff(centers,n=2,axis=0)*spec['fps']**2,axis=2))
        dynamics=read(held/'release-dynamics.json');releases=[]
        for index,side in enumerate(spec['patches']):
            global_cap=max(dynamics[v]['feet'][side]['global_acceleration_max_m_s2'] for v in ['input','prior'])+1e-5
            # Global comparison already passes on these held cases.
            caps[:,index]=np.minimum(caps[:,index],global_cap)
            tracks=[dynamics[v]['feet'][side]['releases'] for v in ['input','prior','candidate']]
            if len({len(t) for t in tracks})!=1:raise ValueError('Release population differs')
            for raw,previous,current in zip(*tracks):
                if len({r['release_frame'] for r in [raw,previous,current]})!=1:raise ValueError('Release clocks differ')
                limit=max(raw['acceleration_max_m_s2'],previous['acceleration_max_m_s2'])+1e-5
                protection=max(limit,current['acceleration_max_m_s2']);indices=np.asarray(current['acceleration_frames'])-1
                caps[indices,index]=np.minimum(caps[indices,index],protection)
                releases.append(dict(side=side,release_frame=current['release_frame'],original_limit_m_s2=limit,frozen_protection_m_s2=protection))
        local=localize(world,fitter.rig.parents);delta=local[:-1,:,:3,:3].transpose(0,1,3,2)@local[1:,:,:3,:3]
        envelope=dict(safety_caps_m_s2=caps.tolist(),support_speed_caps_m_s=np.linalg.norm(np.diff(centers[:,:,[0,2]],axis=0)*spec['fps'],axis=2).tolist(),
            support_steps=(active[:-1]&active[1:]).tolist(),active_frames=active.tolist(),
            hover_caps_m=np.maximum(.01,[[s[ids,1].min() for ids in patches] for s in surfaces]).tolist(),
            protected_columns=protected,rotation_cap_radians=float(Rotation.from_matrix(delta.reshape(-1,3,3)).magnitude().max()),
            root_safety_caps_m_s2=np.maximum(root_limit,root_norm).tolist(),root_original_limit_m_s2=root_limit,release_protection=releases)
    bad=np.flatnonzero(root_norm>root_limit)
    if not len(bad):raise ValueError('No remaining root failure; do not rerun optimization')
    center=int(bad[np.argmax(root_norm[bad])]+1);frames=list(range(max(0,center-2),min(len(initial),center+3)))
    names=set(read(ROOT/'reports/block-release-dance-v3/request.json')['implementation'])|{'root_release_block.py','study_root_release_block.py','finalize_release_trial.py'}
    request=dict(at=now(),case=case,held=str(held),prior=str(prior),source_trial=str(source) if source else None,
        frames=frames,root_target=dict(centers=[center],limit_m_s2=root_limit),protected_nodes=selection['protected_nodes'],joint_selection=selection,
        remaining_root_failure_centers=(bad+1).tolist(),maxiter=80,inputs={str(p):sha256(p) for p in input_paths},
        method='Largest current root acceleration excess, five-frame block, root and unprotected leg variables. One80iteration SLSQP proposal and8fixed safeguard fractions. Actual serialized values with smooth proposal derivatives. Original absolute/adjacent/floor/hover/rotation/foot limits and no-new-release protection; fixed root acceleration envelope=max(original comparison cap, initial held magnitude) per center. No cap ratchet.',
        acceptance='Original full development comparison retained. Root preservation is intentionally replaced by frozen all-center root acceleration envelopes and original edit bounds; other guard thresholds unchanged. Original root limit remains the objective. Human/held-out approval absent.',quality_approved=False)
    output.mkdir(parents=True);(output/'implementation').mkdir()
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    request['implementation']={name:sha256(output/'implementation'/name) for name in sorted(names)}
    save(output/'request.json',request);save(output/'envelope.json',envelope)
    with threadpool_limits(limits=1):
        problem=problem_for(request,envelope);x=problem.initial[np.ix_(problem.frames,problem.free)].ravel();rows=[];rng=np.random.default_rng(924)
        def signature(y):
            values=problem.values(y);chosen=[]
            for f in problem.frames:
                pos=problem.fitter.surface_jacobian(int(f),values[f])[0]
                chosen.extend(int(ids[np.argmin(pos[ids,1])]) for side,ids in enumerate(problem.patches) if active[f,side])
            return chosen
        for _ in range(3):
            d=rng.normal(size=len(x));d/=np.linalg.norm(d);rows.append(check_direction(lambda y:problem.evaluate(y,False),signature,x,d))
        first=problem.evaluate(x);geometry=problem.geometric_guard(problem.initial)
        valid=all(r['passed'] for r in rows) and first[2].min()>=-1e-7 and geometry and np.all(np.abs(initial)<=fitter.bounds+1e-8)
    proof=dict(at=now(),rows=rows,passed=bool(valid),initial_objective=first[0],minimum_constraint=float(first[2].min()),geometry=geometry,
        variables=len(x),constraints=len(first[2]),quality_approved=False)
    save(output/'derivative-proof.json',proof)
    if not valid:
        save(output/'pipeline.json',dict(at=now(),status='preparation_failed',quality_approved=False));raise ValueError('Root block preflight failed; evidence retained')
    save(output/'freeze.json',{name:sha256(output/name) for name in ['request.json','envelope.json','derivative-proof.json']})
    save(output/'pipeline.json',dict(at=now(),status='prepared',quality_approved=False));print(proof)


def run(output):
    request=read(output/'request.json');freeze=read(output/'freeze.json')
    if read(output/'pipeline.json')['status']!='prepared':raise ValueError('Preserve previous run')
    process=psutil.Process();save(output/'runner.json',dict(at=now(),pid=process.pid,created=process.create_time()))
    def phase(status,**kw):save(output/'pipeline.json',dict(at=now(),status=status,quality_approved=False,**kw));print(status,kw,flush=True)
    def validate():
        for name,digest in freeze.items():
            if sha256(output/name)!=digest:raise ValueError('Protocol changed')
        for path,digest in request['inputs'].items():
            if sha256(path)!=digest:raise ValueError('Input changed')
        for name,digest in request['implementation'].items():
            if sha256(ROOT/'scripts'/name)!=digest or sha256(output/'implementation'/name)!=digest:raise ValueError('Implementation changed')
    try:
        validate();envelope=read(output/'envelope.json')
        with threadpool_limits(limits=1):
            problem=problem_for(request,envelope);phase('fitting');values,solver=solve(problem,request['maxiter'],lambda item:phase('fitting',**item))
            phase('verifying_and_engine');result=finalize(output,request,problem.fitter,problem.initial,values,envelope,solver)
        validate();save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),**result,quality_approved=False));phase('complete',passed_development_screen=result['passed_development_screen'])
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('output',type=Path);p.add_argument('--case');p.add_argument('--source',type=Path);a=p.parse_args()
    if a.command=='prepare':
        if not a.case:p.error('--case required for preparation')
        prepare(a.output.resolve(),a.case,a.source)
    else:run(a.output.resolve())
