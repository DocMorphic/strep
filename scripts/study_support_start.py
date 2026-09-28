"""Matched clipped-start repair after the declared moderate temporal correction."""
import argparse
import copy
import os
from pathlib import Path
import shutil
import traceback
import numpy as np
import psutil
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now


def run(source,output):
    completed_temporal=Path(source).resolve();source=completed_temporal/'curvature_10';output=Path(output).resolve()
    if read(completed_temporal/'pipeline.json')['status']!='complete':raise ValueError('Temporal initializer is incomplete')
    temporal_proof=read(completed_temporal/'completion.json')
    for name,key in [('results.json','results_sha256'),('traces.json','traces_sha256'),('engine/audit/verification.json','engine_sha256')]:
        if sha256(completed_temporal/name)!=temporal_proof[key]:raise ValueError('Temporal completion evidence changed')
    if output.exists():raise ValueError('Preserve earlier experiment')
    proof=read(source/'verification.json');request=read(source/'request.json');spec=read(source/'spec.json')
    if read(source/'pipeline.json')['status']!='complete' or not proof['bounds_and_preservation_passed']:
        raise ValueError('Requires a complete bounded comparison candidate')
    if sha256(source/'candidate/character.glb')!=proof['candidate_sha256'] or sha256(source/'input/character.glb')!=proof['source_sha256']:
        raise ValueError('Changed verified clip')
    parent=completed_temporal;protocol=read(parent/'request.json')
    temporal_row=next(r for r in read(parent/'results.json')['rows'] if r['variant']=='curvature_10')
    if temporal_row['verification']!=proof:raise ValueError('Temporal initializer proof changed')
    for name,digest in protocol['implementation'].items():
        if sha256(parent/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:
            raise ValueError('Source study implementation changed: '+name)
    output.mkdir();(output/'implementation').mkdir()
    names=sorted(set(protocol['implementation'])|{'study_support_start.py','support_clip_start.py','relax_support_start.py'})
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    first,last=0,11
    variants=['same_start_weights','retain_start_support']
    sources={name:sha256(source/name) for name in ['request.json','spec.json','fit.npz','verification.json','input/character.glb','candidate/character.glb','input/contacts.json']}
    save(output/'request.json',dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),source=str(source),
        source_hashes=sources,completed_temporal=str(completed_temporal),temporal_completion_sha256=sha256(completed_temporal/'completion.json'),
        variants=variants,first_editable_frame=first,last_editable_frame=last,
        sweeps=6,max_nfev=spec['max_nfev'],implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False,
        scope='Targeted first-seed comparison on both rigs after endpoint repair and weight10 interior temporal correction. Weight10 is the lower tested nonzero development setting, not a held-out optimality claim. Both methods start from the same saved initializer and receive six identical reversed-clock sweeps over frames0-11. Only the generated clipped-start ramp differs; custom weights and observed internal transitions are preserved. No source-frame extrapolation, contact confirmation, generalization or quality approval.'))
    def phase(status,**kwargs):
        save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**kwargs));print(status,kwargs,flush=True)
    try:
        from rig_asset import RigAsset
        from target_rig_contact import baseline
        from support_reference_fit import SupportReferenceFitter
        from relax_support_start import relax
        from support_clip_start import retain_start_support
        from rig_loop import encode
        from verify_breadth_contact import verify
        from run_godot_rig_import import run as engine
        from rig_clip_import import AnimationSampler
        rig=RigAsset.load(source/'input/character.glb');before,local=baseline(rig,spec['frames'])
        archive=np.load(source/'fit.npz',allow_pickle=False);initial=archive['parameters']
        np.testing.assert_allclose(before,archive['before'],atol=1e-9,rtol=0)
        surfaces=np.asarray([rig.vertices(w) for w in before]);rows=[]
        with threadpool_limits(limits=1):
            for variant in variants:
                folder=output/variant;folder.mkdir();shutil.copytree(source/'input',folder/'input')
                recipe=copy.deepcopy(request)
                recipe.pop('root_curvature_weight',None)
                if variant=='retain_start_support':recipe['support']=retain_start_support(recipe['support'],spec['frames'])
                recipe.update(method=variant,parent_correction_sha256=proof['candidate_sha256'],first_editable_frame=first,last_editable_frame=last,initializer_root_curvature_weight=10.,max_sweeps=6)
                save(folder/'request.json',recipe);save(folder/'spec.json',spec)
                fitter=SupportReferenceFitter(rig,spec,local,recipe['targets_m'],np.ones(len(before)),surfaces,
                    guides=recipe['support']['guides'],support_weight=recipe['support_weight'])
                reconstructed=np.asarray([fitter.pose(f,x)[0] for f,x in enumerate(initial)])
                np.testing.assert_allclose(reconstructed,archive['after'],atol=1e-9,rtol=0)
                phase('fitting',variant=variant)
                values,solver,convergence=relax(fitter,initial,last=last,sweeps=6,
                    progress=lambda sweep,change:phase('fitting',variant=variant,sweep=sweep,max_parameter_change=change))
                after=np.asarray([fitter.pose(f,x)[0] for f,x in enumerate(values)])
                dest=folder/'candidate';dest.mkdir()
                animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(fitter.nodes)
                times,roundtrip=encode(rig,after,animated,spec['root_node'],dest/'character.glb',variant)
                for name in ['inventory.json','rig-profile.json','contacts.json']:shutil.copyfile(source/'input'/name,dest/name)
                root=spec['root_node'];save(dest/'root-motion.json',dict(node=root,times_s=times.tolist(),
                    positions_m=after[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist()))
                report=read(source/'candidate/report.json');report.update(glb_sha256=sha256(dest/'character.glb'),human_approved=False,
                    correction_method=variant,parent_glb_sha256=proof['candidate_sha256'],
                    target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'])
                save(dest/'report.json',report);np.savez_compressed(folder/'fit.npz',before=before,after=after,parameters=values)
                save(folder/'solver.json',solver);save(folder/'fit-summary.json',dict(convergence=convergence,export=roundtrip,quality_approved=False))
                verification=verify(folder)
                save(folder/'pipeline.json',dict(status='complete',quality_approved=False))
                decoded=RigAsset.load(dest/'character.glb');sampler=AnimationSampler(decoded.document,decoded.binary,0)
                parent_rig=RigAsset.load(source/'candidate/character.glb');parent_sampler=AnimationSampler(parent_rig.document,parent_rig.binary,0)
                prefix_error=max(float(np.abs(sampler.sample(float(np.float32(f/30)))-parent_sampler.sample(float(np.float32(f/30)))).max()) for f in list(range(first))+list(range(last+1,spec['frames'])))
                if prefix_error>1e-5:raise ValueError('Decoded motion outside the window changed')
                rows.append(dict(variant=variant,verification=verification,decoded_outside_window_max_error=prefix_error,convergence=convergence))
                save(output/'results.json',dict(rows=rows,quality_approved=False))
            paths=[('raw',source/'input/character.glb'),('parent_correction',source/'candidate/character.glb')]+[(v,output/v/'candidate/character.glb') for v in variants]
            phase('engine');group=output/'engine';group.mkdir()
            save(group/'manifest.json',dict(cases=[dict(id=name,path=str(path),sha256=sha256(path),frames=spec['frames'],fps=30) for name,path in paths]))
            engine(group,group/'audit')
            checks=read(group/'audit/verification.json')['checks']
            if len(checks)!=4 or any(c['frames']!=spec['frames'] for c in checks):raise ValueError('Incomplete engine evidence')
            traces=[];annotations=read(source/'input/contacts.json')
            for name,path in paths:
                clip=RigAsset.load(path);sampler=AnimationSampler(clip.document,clip.binary,0);tracks={side:[] for side in spec['patches']};root_positions=[]
                for f in range(spec['frames']):
                    world=sampler.sample(float(np.float32(f/30)));vertices=clip.vertices(world)
                    root_positions.append(world[spec['root_node'],:3,3])
                    for side,patch in spec['patches'].items():tracks[side].append(vertices[patch['vertices']][:,[0,2]].mean(0))
                feet={}
                for side,points in tracks.items():
                    active=np.zeros(spec['frames'],bool)
                    for c in annotations['intervals']:
                        if c['joint'] in [side+'Foot',side+'ToeBase']:active[c['start_frame']:c['end_frame_exclusive']]=True
                    speed=np.linalg.norm(np.diff(points,axis=0),axis=1)*30;steps=active[:-1]&active[1:]
                    feet[side]=dict(speed_m_s=speed.tolist(),predicted_support_steps=steps.tolist(),
                        support_max_m_s=float(speed[steps].max()) if steps.any() else None,
                        support_p95_m_s=float(np.percentile(speed[steps],95)) if steps.any() else None,last_step_m_s=float(speed[-1]))
                acceleration=np.diff(root_positions,n=2,axis=0)*900
                traces.append(dict(variant=name,source_sha256=sha256(path),feet=feet,
                    root_positions_m=np.asarray(root_positions).tolist(),root_acceleration_xyz_m_s2=acceleration.tolist(),
                    root_acceleration_magnitude_m_s2=np.linalg.norm(acceleration,axis=1).tolist()))
            save(output/'traces.json',dict(variants=traces,quality_approved=False))
            save(output/'completion.json',dict(at=now(),results_sha256=sha256(output/'results.json'),traces_sha256=sha256(output/'traces.json'),
                engine_sha256=sha256(group/'audit/verification.json'),engine_actor_frames=sum(c['frames'] for c in checks),quality_approved=False))
            phase('complete')
    except BaseException as exc:
        phase('failed',error=str(exc),traceback=traceback.format_exc());raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.source,a.output)
