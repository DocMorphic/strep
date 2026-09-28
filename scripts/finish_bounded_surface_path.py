"""Export and independently audit a completed wider-window arm path.

Wait for exact owners; do not rerun fitting. Both original and final clips are
retained, including failed candidates. No sampled screen is human approval.
"""
import argparse
import copy
import os
from pathlib import Path
import shutil
import traceback
import psutil
from strep import ROOT, read, save, sha256, now


def compose_path(local, parents, nodes, values):
    import numpy as np
    from scipy.spatial.transform import Rotation
    from bounded_pose_ik import hierarchy_order, world_matrices
    local=np.asarray(local,dtype=float);values=np.asarray(values,dtype=float)
    if values.shape!=(len(local),3*len(nodes)) or not np.isfinite(values).all() or len(set(nodes))!=len(nodes):
        raise ValueError('Finite per-frame vectors for distinct edited nodes required')
    candidate=local.copy()
    for j,node in enumerate(nodes):
        candidate[:,node,:3,:3]=local[:,node,:3,:3]@Rotation.from_rotvec(values[:,3*j:3*j+3]).as_matrix()
    order=hierarchy_order(parents)
    return candidate,np.asarray([world_matrices(frame,parents,order) for frame in candidate])


def validate_control_protocol(recipe,parameters,initial):
    import numpy as np
    from paired_hand_fit import envelope
    from paired_hand_trajectory import basis as make_basis
    controls=np.asarray(parameters['controls']);basis=np.asarray(parameters['basis']);trajectory=np.asarray(parameters['trajectory_values'])
    knots=recipe['knots'];count=len(knots)
    if not 2<=count<=40 or basis.shape!=(150,count) or controls.shape!=(24*count,) or trajectory.shape!=(150,24):raise ValueError('Unexpected path dimensions')
    if parameters['basis']!=initial['basis'] or parameters['control_radii']!=initial['control_radii'] or parameters['control_bounds']!=initial['control_bounds']:
        raise ValueError('Control clock or budgets changed')
    expected=make_basis(envelope(150,75,30),knots)
    if not np.array_equal(basis,expected):raise ValueError('Basis differs from declared knots and envelope')
    if not np.isfinite(controls).all() or np.any(basis<0) or np.any(basis.sum(axis=1)>1+1e-12):raise ValueError('Invalid path basis')
    radii=np.asarray(parameters['control_radii']);expected_radii=np.tile(np.radians(recipe['joint_edit_degrees']),2*count)
    if not np.array_equal(radii,expected_radii) or not np.array_equal(np.asarray(parameters['control_bounds']),np.repeat(radii,3)):
        raise ValueError('Control budgets differ from declared joint limits')
    if radii.shape!=(8*count,) or np.any(radii<=0) or np.any(np.linalg.norm(controls.reshape(-1,3),axis=1)>radii+1e-8):raise ValueError('Control norm budget exceeded')
    calculated=np.concatenate([basis@part.reshape(count,12) for part in np.split(controls,2)],axis=1)
    if not np.allclose(calculated,trajectory,rtol=0,atol=1e-12):raise ValueError('Recorded trajectory differs from controls')
    if not np.array_equal(trajectory[:46],np.zeros_like(trajectory[:46])) or not np.array_equal(trajectory[105:],np.zeros_like(trajectory[105:])):
        raise ValueError('Correction outside declared path window')
    return controls,basis,trajectory


def run(study,output,wait_audit=None):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier completion attempt')
    recipe=read(study/'request.json');output.mkdir();(output/'implementation').mkdir()
    names=['finish_bounded_surface_path.py','audit_paired_guides.py','bounded_pose_ik.py','motion_edit_bounds.py',
           'rig_asset.py','rig_clip_import.py','rig_loop.py','verify_rig_clearance.py','inspect_motion.py',
           'run_godot_scene_import.py','godot_scene_import_audit.gd','convex_partner_surface.py','verify_palm_region.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    wait_audit=Path(wait_audit).resolve() if wait_audit else None
    audit_record=read(wait_audit/'request.json') if wait_audit else None
    request=dict(at=now(),pid=os.getpid(),created=psutil.Process().create_time(),study=str(study),study_request_sha256=sha256(study/'request.json'),
        frames=[i*.5 for i in range(299)],variants=['raw','candidate'],wait_audit=str(wait_audit) if wait_audit else None,
        wait_audit_request_sha256=sha256(wait_audit/'request.json') if wait_audit else None,
        implementation={n:sha256(output/'implementation'/n) for n in names},quality_approved=False)
    save(output/'request.json',request)
    def phase(status,**kwargs):
        save(output/'pipeline.json',dict(status=status,at=now(),quality_approved=False,**kwargs));print(status,kwargs,flush=True)
    try:
        from audit_paired_guides import await_owner
        phase('waiting_for_exact_path_owner')
        await_owner(recipe,'pid','created',study,{'complete_pending_export_and_full_geometry'})
        if wait_audit:
            phase('waiting_for_prior_geometry_owner')
            await_owner(audit_record,'pid','created',wait_audit,{'complete'})
            if sha256(wait_audit/'request.json')!=request['wait_audit_request_sha256']:raise ValueError('Prior audit request changed')
        if sha256(study/'request.json')!=request['study_request_sha256']:raise ValueError('Path request changed')
        for folder,implementation in [(study,recipe['implementation']),(output,request['implementation'])]:
            for name,digest in implementation.items():
                if sha256(folder/'implementation'/name)!=digest or sha256(ROOT/'scripts'/name)!=digest:
                    raise ValueError('Frozen implementation changed: '+name)
        from threadpoolctl import threadpool_limits
        with threadpool_limits(limits=1):
            complete(study,output,recipe,request,phase)
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc(),quality_approved=False));raise


def complete(study,output,recipe,request,phase):
    import numpy as np
    from scipy.spatial.transform import Rotation
    from rig_asset import RigAsset, array
    from rig_clip_import import AnimationSampler
    from verify_rig_clearance import localize
    from rig_loop import encode
    from inspect_motion import skeleton_metadata
    from motion_edit_bounds import check
    from convex_partner_surface import penetration
    from verify_palm_region import measure
    from run_godot_scene_import import run as engine
    source_scene=Path(recipe['source_scene'])
    if sha256(source_scene)!=recipe['source_scene_sha256']:raise ValueError('Source scene changed')
    scene=read(source_scene)['scene'];parameters=read(study/'parameters.json');initial=read(study/'initial-parameters.json')
    controls,basis,trajectory=validate_control_protocol(recipe,parameters,initial)
    evidence=dict(parameters_sha256=sha256(study/'parameters.json'),initial_parameters_sha256=sha256(study/'initial-parameters.json'),history_sha256=sha256(study/'history.json'))
    save(output/'source-evidence.json',evidence)
    patch_path=study/'palm-region.json'
    if sha256(patch_path)!=recipe['palm_region_sha256']:raise ValueError('Contact patches changed')
    patches=read(patch_path);save(output/'palm-region.json',patches)
    names,_,_=skeleton_metadata(77);manifest=dict(scenes=[],assets={})
    scenes={mode:copy.deepcopy(scene) for mode in ['raw','candidate']}
    for mode,s in scenes.items():s['id']=mode+'-seed-'+str(recipe['seed'])
    times=np.arange(150,dtype=np.float32)/30;sample_times=np.asarray(request['frames'])/30
    bounds_rows=[]
    phase('exporting')
    for index,label in enumerate(['A','B']):
        source=recipe['sources'][label];glb=Path(source['raw_glb']);local_path=study/f'{label}-source-local.npz'
        for path,digest in [(glb,source['raw_glb_sha256']),(Path(source['posture_glb']),source['posture_glb_sha256']),
                            (Path(source['event_pose']),source['event_pose_sha256']),(local_path,source['local_npz_sha256'])]:
            if sha256(path)!=digest:raise ValueError('Changed source: '+str(path))
        motion=ROOT/scene['actors'][label]['motion']
        if sha256(motion)!=scene['actors'][label]['source_sha256']:raise ValueError('Changed original motion')
        rig=RigAsset.load(glb);sampler=AnimationSampler(rig.document,rig.binary,0)
        raw_world=np.asarray([sampler.sample(float(t)) for t in times]);raw_local=localize(raw_world,rig.parents)
        stored=dict(np.load(local_path,allow_pickle=False));authored=stored['authored_finger_local']
        if not np.array_equal(raw_local,stored['raw_local']):raise ValueError('Stored original differs from source decoding')
        labels=[str(n.get('name') or f'node-{i}') for i,n in enumerate(rig.document['nodes'])];nodes={n:i for i,n in enumerate(labels)}
        arm_roles=['LeftShoulder','LeftArm','LeftForeArm','LeftHand'];arm=[nodes[n] for n in arm_roles]
        fingers=[i for i,n in enumerate(labels) if n.startswith('LeftHand') and n[-1:].isdigit()]
        if fingers!=source['finger_nodes']:raise ValueError('Finger mapping changed')
        other=[i for i in range(len(labels)) if i not in fingers]
        if not np.array_equal(authored[:,other],raw_local[:,other]) or not np.array_equal(authored[:,:,:3,3],raw_local[:,:,:3,3]):
            raise ValueError('Authored source changes more than fingers')
        local,world=compose_path(authored,rig.parents,arm,trajectory[:,12*index:12*(index+1)])
        hips=nodes['Hips'];limits=dict(joint_rotation_degrees={n:0. for n in labels},joint_correction_speed_degrees_s={n:150. for n in labels},
            root_components_m=[0.,0.,0.],root_correction_speed_m_s=0.)
        for role,value in zip(arm_roles,recipe['joint_edit_degrees']):limits['joint_rotation_degrees'][role]=value
        for i in fingers:limits['joint_rotation_degrees'][labels[i]]=60.
        integer=check(raw_local[:,:,:3,:3],local[:,:,:3,:3],raw_world[:,hips,:3,3],world[:,hips,:3,3],times,labels,limits)
        save(output/f'{label}-integer-bounds.json',integer)
        if not integer['passed']:raise ValueError('Integer correction bounds failed; report retained')
        raw_folder=output/'assets'/label/'raw';raw_folder.mkdir(parents=True)
        shutil.copyfile(glb,raw_folder/'character.glb');shutil.copyfile(motion,raw_folder/'motion.npz')
        dest=output/'assets'/label/'candidate';dest.mkdir()
        animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(arm+fingers)
        _,roundtrip=encode(rig,world,animated,rig.skin.get('skeleton',rig.joints[0]),dest/'character.glb','Bounded surface path')
        data=dict(np.load(motion,allow_pickle=False));ordered=np.take(world,[nodes[n] for n in names],axis=1)
        data['local_rot_mats']=np.take(local,[nodes[n] for n in names],axis=1)[:,:,:3,:3].copy()
        data['global_rot_mats']=ordered[:,:,:3,:3].copy();data['posed_joints']=ordered[:,:,:3,3].copy()
        np.savez_compressed(dest/'motion.npz',**data)
        decoded=RigAsset.load(dest/'character.glb');candidate_sampler=AnimationSampler(decoded.document,decoded.binary,0)
        old=np.asarray([sampler.sample(float(np.float32(t))) for t in sample_times])
        new=np.asarray([candidate_sampler.sample(float(np.float32(t))) for t in sample_times])
        old_local,new_local=localize(old,rig.parents),localize(new,rig.parents)
        half=check(old_local[:,:,:3,:3],new_local[:,:,:3,:3],old[:,hips,:3,3],new[:,hips,:3,3],sample_times,labels,limits)
        untouched=[i for i in range(len(labels)) if i not in arm+fingers]
        preserve=dict(protected_local_max_error=float(np.abs(old_local[:,untouched]-new_local[:,untouched]).max()),
            local_translation_max_m=float(np.abs(old_local[:,:,:3,3]-new_local[:,:,:3,3]).max()))
        outside=(np.array(request['frames'])<=45)|(np.array(request['frames'])>=105)
        preserve['outside_window_max_error']=float(np.abs(old[outside]-new[outside]).max())
        save(output/f'{label}-decoded-bounds.json',dict(bounds=half,preservation=preserve,roundtrip=roundtrip))
        if not half['passed'] or max(preserve.values())>1e-5:raise ValueError('Decoded bounds or preservation failed; candidate retained')
        bounds_rows.append(dict(actor=label,integer_samples=150,decoded_samples=len(sample_times),passed=True))
        for mode in scenes:
            folder=output/'assets'/label/mode;relative=(folder/'character.glb').relative_to(output).as_posix()
            scenes[mode]['actors'][label].update(preview_glb=relative,motion=(folder/'motion.npz').relative_to(ROOT).as_posix(),source_sha256=sha256(folder/'motion.npz'))
            for path in [folder/'character.glb',folder/'motion.npz']:
                manifest['assets'][path.relative_to(output).as_posix()]=dict(sha256=sha256(path))
    for mode,s in scenes.items():
        relative=mode+'.json';save(output/relative,dict(scene=s));manifest['scenes'].append(dict(id=s['id'],variants={'palm':relative}))
        manifest['assets'][relative]=dict(sha256=sha256(output/relative))
    save(output/'manifest.json',manifest);save(output/'bounds-summary.json',dict(rows=bounds_rows,quality_approved=False))
    phase('engine_import');engine(output,output/'engine-audit')
    checks=read(output/'engine-audit/verification.json')['checks']
    if len(checks)!=4 or {(c['scene_id'],c['actor']) for c in checks}!={(s['id'],a) for s in scenes.values() for a in ['A','B']} or any(c['frames']!=150 for c in checks):
        raise ValueError('Incomplete engine population')
    rows=[]
    for mode,s in scenes.items():
        actors=[];folder=output/'geometry'/mode;folder.mkdir(parents=True);samples=[]
        for label in ['A','B']:
            entry=s['actors'][label];rig=RigAsset.load(output/entry['preview_glb'])
            actors.append((rig,AnimationSampler(rig.document,rig.binary,0),Rotation.from_quat(entry['transform']['rotation_xyzw']).as_matrix(),np.asarray(entry['transform']['translation_m'])))
        primitive=actors[0][0].document['meshes'][0]['primitives'][0]
        faces=array(actors[0][0].document,actors[0][0].binary,primitive['indices']).reshape(-1,3)
        vertex=s['contacts'][0]['effector']['surface_vertex']
        for frame in [75]+[f for f in request['frames'] if f!=75]:
            points=[rig.vertices(sampler.sample(float(np.float32(frame/30))))@r.T+t for rig,sampler,r,t in actors]
            collisions=[penetration(points[a],points[b],faces) for a,b in [(0,1),(1,0)]]
            row=dict(frame=frame,gap_m=float(np.linalg.norm(points[0][vertex]-points[1][vertex])),floor_depth_m=[max(0.,-float(p[:,1].min())) for p in points],collision=collisions)
            if frame==75:row['region']=measure(points,[patches['A'],patches['B']],faces,.003)
            samples.append(row);samples.sort(key=lambda r:r['frame']);save(folder/'samples.json',dict(rows=samples,quality_approved=False))
            save(output/'pipeline.json',dict(status='geometry',variant=mode,completed_samples=len(samples),total_samples=len(request['frames']),quality_approved=False))
        if [r['frame'] for r in samples]!=request['frames']:raise ValueError('Incomplete geometry clock')
        event=next(r for r in samples if r['frame']==75)
        rows.append(dict(variant=mode,samples_sha256=sha256(folder/'samples.json'),event=event,
            max_depth_m=max(c['max_depth_m'] for r in samples for c in r['collision']),floor_max_depth_m=max(max(r['floor_depth_m']) for r in samples),
            collision_failed_frames=[r['frame'] for r in samples if max(c['max_depth_m'] for c in r['collision'])>.005]))
        save(output/'geometry-summary.json',dict(rows=rows,quality_approved=False))
    for relative,entry in manifest['assets'].items():
        if sha256(output/relative)!=entry['sha256']:raise ValueError('Export asset changed during audit')
    save(output/'completion.json',dict(at=now(),engine_actor_frames=600,samples_per_scene=299,scenes=2,
        manifest_sha256=sha256(output/'manifest.json'),source_evidence_sha256=sha256(output/'source-evidence.json'),
        engine_sha256=sha256(output/'engine-audit/verification.json'),geometry_summary_sha256=sha256(output/'geometry-summary.json'),
        quality_approved=False,scope='Original and final development pair, all integer and half-frame skin samples and actual engine bone transforms. No continuous/self-collision, anatomy, action correctness or independent human approval.'))
    phase('complete')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);p.add_argument('--wait-audit',type=Path)
    a=p.parse_args();run(a.study,a.output,a.wait_audit)
