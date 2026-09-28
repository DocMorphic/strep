"""Fixed, read-only parameter-path diagnostic between two completed attempts.

Every fraction is retained, including failures. No optimization, threshold
tuning, product promotion or engine qualification is performed here.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from profile_support_surface import load
from rig_loop import encode
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_breadth_contact import verify
from support_velocity_traces import run as trace
from support_release_metrics import measure
from study_support_release import compare


def run(output,preserve_peak_joint=False):
    if output.exists():raise ValueError('Preserve earlier diagnostic')
    held=ROOT/'reports/support-release-hold-v1/takes/motion-036-rig-01'
    proposal=ROOT/'reports/support-acceleration-v1/takes/motion-036-rig-01'
    prior=ROOT/'reports/whole-support-breadth-v1/takes/motion-036-rig-01'
    fractions=[0.,1/64,1/32,1/16,1/8,1/4,1/2,1.]
    inputs={str(folder/n):sha256(folder/n) for folder in [held,proposal,prior] for n in
        ['fit.npz','request.json','spec.json','verification.json','traces.json','candidate/character.glb','input/character.glb','input/contacts.json']}
    for folder in [held,proposal]:inputs[str(folder/'release-dynamics.json')]=sha256(folder/'release-dynamics.json')
    protected=None
    if preserve_peak_joint:
        audit_path=ROOT/'reports/support-acceleration-path-audit-v1.json'
        original_done=ROOT/'reports/support-acceleration-path-v1/completion.json'
        audit=read(audit_path)
        if audit['completion_sha256']!=sha256(original_done):raise ValueError('Diagnostic audit binding changed')
        peak=audit['rows'][0]
        protected=dict(node=peak['rotation_peak_node'],name=peak['rotation_peak_name'],observed_step_end=peak['rotation_peak_step_end'],policy='Retain this one joint correction at every frame; all other root/joint parameters follow the same fixed path.')
        inputs[str(audit_path)]=sha256(audit_path);inputs[str(original_done)]=sha256(original_done)
    output.mkdir(parents=True);snap=output/'implementation';snap.mkdir()
    names=set(read(ROOT/'reports/support-acceleration-v1/request.json')['implementation'])|{'probe_support_acceleration_path.py','profile_support_surface.py'}
    for name in names:shutil.copyfile(ROOT/'scripts'/name,snap/name)
    request=dict(at=now(),held=str(held),proposal=str(proposal),prior=str(prior),fractions=fractions,inputs=inputs,
        implementation={n:sha256(snap/n) for n in sorted(names)},method='Linear interpolation of complete root/rotation-vector correction tracks; same fixed fraction at every frame.',
        guards='Decoded hard bounds; floor<=5mm; root acceleration<=max(raw,original prior)+1e-5; local rotation step<=max(raw,held)+1e-4; support max/p95<=max(original prior,held)+1e-6; squared actual-foot acceleration excess strictly below held.',
        scope='Development direction probe. Both endpoints are failed attempts; guarded improvement is not full quality approval. All8 fractions retained; no adaptive fractions or new solver sweeps.',quality_approved=False)
    if protected:request['protected_joint_track']=protected
    save(output/'request.json',request);save(output/'pipeline.json',dict(status='running',at=now(),quality_approved=False))
    fitter,a=load(held);b=np.load(proposal/'fit.npz',allow_pickle=False)['parameters']
    if a.shape!=b.shape:raise ValueError('Parameter shapes differ')
    if protected:
        index=fitter.nodes.index(protected['node']);start=3+3*index
        b=b.copy();b[:,start:start+3]=a[:,start:start+3]
    np.testing.assert_array_equal(np.load(held/'fit.npz')['before'],np.load(proposal/'fit.npz')['before'])
    other=read(proposal/'spec.json')
    for key in ['root_node','edit_joints','limits','patches','frames','fps']:
        if fitter.spec[key]!=other[key]:raise ValueError('Fit parameterization differs')
    spec=fitter.spec;fps=spec['fps'];count=spec['frames'];root=spec['root_node'];fit_request=read(held/'request.json')
    old=read(prior/'verification.json');held_proof=read(held/'verification.json')
    old_trace=read(prior/'traces.json');held_trace=read(held/'traces.json');base_dynamics=read(held/'release-dynamics.json')
    caps=np.asarray(read(proposal/'request.json')['acceleration_caps_m_s2']);rows=[]
    for index,alpha in enumerate(fractions):
        folder=output/f'step-{index:02d}';folder.mkdir();(folder/'input').mkdir();candidate=folder/'candidate';candidate.mkdir()
        for n in ['character.glb','contacts.json','report.json','inventory.json','rig-profile.json']:shutil.copyfile(held/'input'/n,folder/'input'/n)
        save(folder/'spec.json',spec);save(folder/'request.json',fit_request)
        parameters=(1-alpha)*a+alpha*b;world=np.array([fitter.pose(f,x)[0] for f,x in enumerate(parameters)])
        animated={c['target']['node'] for c in fitter.rig.document['animations'][0]['channels']}|set(fitter.nodes)
        times,roundtrip=encode(fitter.rig,world,animated,root,candidate/'character.glb',f'Diagnostic acceleration direction alpha {alpha}')
        shutil.copyfile(folder/'input/contacts.json',candidate/'contacts.json')
        save(candidate/'root-motion.json',dict(times_s=times.tolist(),positions_m=world[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(world[:,root,:3,:3]).as_quat().tolist()))
        np.savez_compressed(folder/'parameters.npz',parameters=parameters)
        proof=verify(folder);traces=trace(folder);dyn=measure(candidate/'character.glb',spec,fit_request['support'])
        points=np.stack([dyn['feet'][s]['centroids_m'] for s in spec['patches']],axis=1)
        excess=np.maximum(np.linalg.norm(np.diff(points,n=2,axis=0)*fps**2,axis=2)-caps,0)
        energy=float(np.sum(excess**2));metric=proof['metrics']['candidate'];flags={}
        flags['floor']=max(metric['floor_depth_max_m'],metric['half_frame_floor_depth_max_m'])<=.005
        flags['root_acceleration']=metric['root_acceleration_max_m_s2']<=max(old['metrics'][v]['root_acceleration_max_m_s2'] for v in ['input','candidate'])+1e-5
        flags['rotation_steps']=metric['local_rotation_step_max_degrees']<=max(old['metrics']['input']['local_rotation_step_max_degrees'],held_proof['metrics']['candidate']['local_rotation_step_max_degrees'])+1e-4
        for side in spec['patches']:
            for label in ['max','p95']:
                key=f'predicted_support_{label}_m_s'
                cap=max(next(v for v in t['variants'] if v['variant']=='candidate')['feet'][side][key] for t in [old_trace,held_trace])
                flags[f'{side}_{label}']=traces['variants'][1]['feet'][side][key]<=cap+1e-6
        flags['acceleration_energy_improves']=bool(index and energy<rows[0]['energy']-1e-9)
        full=compare(old,proof,old_trace,traces,{**base_dynamics,'candidate':dyn})
        endpoint_error=None
        if alpha==0. or (alpha==1. and not protected):
            original=RigAsset.load((held if alpha==0 else proposal)/'candidate/character.glb');sampler=AnimationSampler(original.document,original.binary,0)
            endpoint_error=max(float(np.abs(sampler.sample(float(np.float32(f/fps)))-world[f]).max()) for f in range(count))
            if endpoint_error>2e-6:raise ValueError('Endpoint reconstruction differs')
        row=dict(alpha=alpha,energy=energy,acceleration_excess_max_m_s2=float(excess.max()),guard_checks=flags,
            guarded_improvement=all(flags.values()),full_decision=full,endpoint_reconstruction_max_error=endpoint_error,
            floor_m=max(metric['floor_depth_max_m'],metric['half_frame_floor_depth_max_m']),root_acceleration_m_s2=metric['root_acceleration_max_m_s2'],
            files={str(p.relative_to(folder)):sha256(p) for p in [candidate/'character.glb',folder/'parameters.npz',folder/'verification.json',folder/'traces.json']},quality_approved=False)
        save(folder/'decision.json',row);rows.append(row);save(output/'results.json',dict(rows=rows,quality_approved=False))
        save(output/'pipeline.json',dict(status='running',at=now(),completed_steps=len(rows),quality_approved=False));print({k:v for k,v in row.items() if k in ['alpha','energy','guarded_improvement','floor_m','root_acceleration_m_s2']},flush=True)
    for p,h in inputs.items():
        if sha256(p)!=h:raise ValueError('Endpoint evidence changed')
    save(output/'completion.json',dict(at=now(),request_sha256=sha256(output/'request.json'),results_sha256=sha256(output/'results.json'),steps=len(rows),guarded_improvements=[r['alpha'] for r in rows if r['guarded_improvement']],full_screen_passes=[r['alpha'] for r in rows if r['full_decision']['passes_development_screen']],quality_approved=False))
    save(output/'pipeline.json',dict(status='complete',at=now(),quality_approved=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--preserve-peak-joint',action='store_true');args=p.parse_args()
    with threadpool_limits(limits=1):run(args.output.resolve(),args.preserve_peak_joint)
