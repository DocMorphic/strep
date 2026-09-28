"""Preserved exploratory two-actor high-five correction and independent audits."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import ROOT,read,save,sha256,now
from build_soma_preview import ASSET
from rig_asset import RigAsset
from target_rig_contact import baseline
from rig_loop import encode
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize
from paired_hand_fit import HandActor,PairFitter
from bounded_partner_surface import penetration


def run(output,refinement=None,source_scene=None):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier prototype')
    actor_class=HandActor
    if refinement is not None and read(Path(refinement)/'request.json').get('actor_kind')=='arm_and_fingers':
        from paired_finger_fit import FingerHandActor
        actor_class=FingerHandActor
    scene_file=Path(source_scene).resolve() if source_scene is not None else ROOT/'reports/breadth-partners-v2/partner_interaction-left-high-five-seed-1301/scene.json'
    parent=scene_file.parent if source_scene is not None else ROOT/'reports/breadth-partners-v2'
    scene=read(scene_file)['scene'];event=scene['contacts'][0]['start_frame'];count=scene['frame_count']
    contact=scene['contacts'][0]
    if set(scene['actors'])!={'A','B'} or len(scene['contacts'])!=1 or contact['actor']!='A' or contact['effector']['joint']!='LeftHand' or contact['target'].get('actor')!='B' or contact['target'].get('joint')!='LeftHand' or contact['effector']['surface_vertex']!=contact['target'].get('surface_vertex'):
        raise ValueError('This prototype supports one A/B left-hand contact using the same native skin vertex')
    if scene['contacts'][0]['end_frame']!=event:raise ValueError('This prototype requires one isolated contact frame')
    output.mkdir(parents=True);(output/'implementation').mkdir()
    implementations=['paired_hand_fit.py','run_paired_hand_prototype.py','rig_asset.py','target_rig_contact.py',
        'rig_clearance_fit.py','rig_loop.py','rig_clip_import.py','verify_rig_clearance.py','bounded_partner_surface.py',
        'run_godot_scene_import.py','godot_scene_import_audit.gd']
    if actor_class is not HandActor:implementations.extend(['paired_finger_fit.py','paired_hand_clearance.py'])
    for name in implementations:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
    save(output/'request.json',dict(at=now(),source_scene=str(scene_file),source_scene_sha256=sha256(scene_file),event_frame=event,fade_frames=15,
        skin_sha256=sha256(ASSET),implementation={n:sha256(ROOT/'scripts'/n) for n in implementations},
        scope='Exploratory first high-five seed, previously inspected development motion. Both actors optimized jointly; no held-out result, collision-aware solve, physics or animator approval.'))
    skin=dict(np.load(ASSET,allow_pickle=False));actors=[];before=[];motions=[]
    for name in ['A','B']:
        entry=scene['actors'][name];source=ROOT/entry['motion'];glb=parent/entry['preview_glb']
        if sha256(source)!=entry['source_sha256']:raise ValueError('Source motion changed')
        folder=output/'input'/name;folder.mkdir(parents=True)
        shutil.copyfile(source,folder/'motion.npz');shutil.copyfile(glb,folder/'character.glb')
        rig=RigAsset.load(glb);world,local=baseline(rig,count);before.append(world);motions.append(dict(np.load(source,allow_pickle=False)))
        actor=actor_class(rig,local,'LeftHand',scene['contacts'][0]['effector']['surface_vertex'],skin['faces'],entry['transform']);actors.append(actor)
        # glTF POSITION is float32; the source bind mesh is float64. Require
        # exact equality to its exported representation, not an arbitrary
        # tolerance that might conceal reordered or modified vertices.
        if len(rig.primitives)!=1 or not np.array_equal(rig.primitives[0]['positions'],skin['bind_vertices'].astype(np.float32)):raise ValueError('Native skin vertex correspondence changed')
    save(output/'pipeline.json',dict(status='joint_fit'))
    fitter=PairFitter(*actors,event=event,fade=15)
    trajectory=None
    if refinement is None:
        with threadpool_limits(limits=1):values,solver=fitter.solve()
    else:
        refinement=Path(refinement).resolve();recipe=read(refinement/'request.json');parameters=read(refinement/'parameters.json')
        if read(refinement/'pipeline.json')['status']!='complete':raise ValueError('Refinement has not finished')
        original=Path(recipe['input'])
        if sha256(original/'input-scene.json')!=recipe['scene_sha256'] or sha256(original/'manifest.json')!=recipe['input_manifest_sha256']:raise ValueError('Refinement source changed')
        original_scene=read(original/'input-scene.json')['scene']
        for name in ['A','B']:
            if original_scene['actors'][name]['source_sha256']!=scene['actors'][name]['source_sha256'] or original_scene['actors'][name]['transform']!=scene['actors'][name]['transform']:raise ValueError('Refinement actor mismatch')
        if not np.array_equal(parameters['envelope'],fitter.envelope) or not np.array_equal(parameters['bounds'],fitter.bounds):raise ValueError('Refinement budget mismatch')
        values=np.array(parameters['values'])
        if values.shape!=fitter.bounds.shape or not np.isfinite(values).all() or np.any(np.abs(values)>fitter.bounds+1e-10):raise ValueError('Invalid refinement parameters')
        if 'trajectory_values' in parameters:
            trajectory=np.asarray(parameters['trajectory_values'],dtype=float)
            if trajectory.shape!=(count,len(values)) or not np.isfinite(trajectory).all():raise ValueError('Invalid trajectory shape')
            if not np.array_equal(trajectory[event],values) or np.any(np.abs(trajectory)>fitter.envelope[:,None]*fitter.bounds+1e-10):raise ValueError('Trajectory exceeds frozen edit envelope')
            if np.any(np.linalg.norm(np.diff(trajectory,axis=0).reshape(count-1,-1,3),axis=2)>np.radians(5)+1e-8):raise ValueError('Trajectory exceeds adjacent edit budget')
        for name,digest in recipe['implementation'].items():
            if sha256(refinement/'implementation'/name)!=digest:raise ValueError('Refinement implementation changed')
        shutil.copytree(refinement,output/'refinement')
        solver=dict(kind='coupled_surface_refinement',request_sha256=sha256(refinement/'request.json'),
            parameters_sha256=sha256(refinement/'parameters.json'),history_sha256=sha256(refinement/'history.json'),quality_approved=False)
    saved_parameters=dict(values=values.tolist(),envelope=fitter.envelope.tolist(),bounds=fitter.bounds.tolist())
    if trajectory is not None:saved_parameters['trajectory_values']=trajectory.tolist()
    save(output/'solver.json',solver);save(output/'parameters.json',saved_parameters)
    audits={};decoded={};manifest=dict(scenes=[],assets={})
    for variant in ['input','candidate']:
        current=copy.deepcopy(scene);current['id']='paired-high-five-'+variant
        for index,name in enumerate(['A','B']):
            actor=actors[index];rig=actor.rig;dest=output/variant/name;dest.mkdir(parents=True,exist_ok=True)
            if variant=='candidate':
                amplitude=values[index*actor.dim:(index+1)*actor.dim]
                world=np.array([actor.pose(f,fitter.envelope[f]*amplitude if trajectory is None else trajectory[f,index*actor.dim:(index+1)*actor.dim]) for f in range(count)])
                animated={c['target']['node'] for c in rig.document['animations'][0]['channels']}|set(actor.nodes)
                root=next(i for i,n in enumerate(rig.document['nodes']) if n.get('name')=='Hips')
                with threadpool_limits(limits=1):times,roundtrip=encode(rig,world,animated,root,dest/'character.glb','Joint paired-hand prototype')
                motion=copy.deepcopy(motions[index]);nodes={n.get('name'):i for i,n in enumerate(rig.document['nodes'])}
                order=[nodes[str(n)] for n in skin['rig_joint_names']]
                ordered=world[:,order]
                motion['posed_joints']=ordered[:,:,:3,3].copy();motion['global_rot_mats']=ordered[:,:,:3,:3].copy()
                for node in actor.nodes:
                    name_in_skin=list(map(str,skin['rig_joint_names'])).index(rig.document['nodes'][node]['name'])
                    parent_node=rig.parents[node]
                    motion['local_rot_mats'][:,name_in_skin]=world[:,parent_node,:3,:3].transpose(0,2,1)@world[:,node,:3,:3]
                if any(motion[k].shape!=motions[index][k].shape for k in motion):raise ValueError('Native array layout changed')
                np.savez_compressed(dest/'motion.npz',**motion)
                save(dest/'root-motion.json',dict(times_s=times.tolist(),positions_m=world[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(world[:,root,:3,:3]).as_quat().tolist(),space='Actor-native pelvis world track; scene placement is separate.'))
                # Only source model support predictions are copied; authored
                # palm intent is in the scene recipe, not promoted to an event.
                save(dest/'metadata.json',dict(quality_approved=False,source_motion_sha256=scene['actors'][name]['source_sha256'],roundtrip=roundtrip))
            mesh=RigAsset.load(dest/'character.glb');sampler=AnimationSampler(mesh.document,mesh.binary,0)
            poses=np.array([sampler.sample(float(np.float32(f/30))) for f in range(count)])
            decoded[(variant,name)]=(mesh,poses)
            entry=current['actors'][name];entry.update(motion=(dest/'motion.npz').relative_to(ROOT).as_posix(),source_sha256=sha256(dest/'motion.npz'),preview_glb=(dest/'character.glb').relative_to(output).as_posix())
            manifest['assets'][entry['preview_glb']]=dict(sha256=sha256(dest/'character.glb'))
            if variant=='candidate':
                source_mesh,original=decoded[('input',name)];old=localize(original,mesh.parents);new=localize(poses,mesh.parents)
                fixed=fitter.envelope==0;untouched=[n for n in range(len(mesh.parents)) if n not in actor.nodes]
                invariant=dict(fixed_world_max_error=float(np.abs(poses[fixed]-original[fixed]).max()),
                    unedited_local_max_error=float(np.abs(old[:,untouched]-new[:,untouched]).max()),
                    all_local_translations_max_error=float(np.abs(old[:,:,:3,3]-new[:,:,:3,3]).max()))
                if max(invariant.values())>1e-5:raise ValueError('Protected pose context changed')
                joint_checks=[]
                for node,limit in zip(actor.nodes,actor.limits):
                    delta=old[:,node,:3,:3].transpose(0,2,1)@new[:,node,:3,:3]
                    angles=Rotation.from_matrix(delta).magnitude();steps=Rotation.from_matrix(delta[:-1].transpose(0,2,1)@delta[1:]).magnitude()
                    if np.any(angles>limit*fitter.envelope+1e-5) or steps.max()>np.radians(5)+1e-5:raise ValueError('Decoded arm edit exceeds limits')
                    joint_checks.append(dict(node=node,max_degrees=float(np.degrees(angles).max()),step_max_degrees=float(np.degrees(steps).max())))
                a=motions[index];b=dict(np.load(dest/'motion.npz',allow_pickle=False))
                for key in ['root_positions','smooth_root_pos','foot_contacts','global_root_heading']:
                    if not np.array_equal(a[key],b[key]):raise ValueError('Protected native track changed: '+key)
                audits[name]=dict(**invariant,fixed_frames=int(fixed.sum()),joint_edits=joint_checks)
        save(output/(variant+'-scene.json'),dict(scene=current));manifest['scenes'].append(dict(id=current['id'],variants={'palm':variant+'-scene.json'}))
    save(output/'manifest.json',manifest);save(output/'preservation.json',audits)
    save(output/'pipeline.json',dict(status='geometry_at_contact'))
    geometry={}
    for variant in ['input','candidate']:
        surfaces={};directions={}
        for index,name in enumerate(['A','B']):
            mesh,poses=decoded[(variant,name)];a=actors[index]
            native=mesh.vertices(poses[event]);surfaces[name]=native@a.rotation.T+a.translation
            adjacent=surfaces[name][a.vertices][a.triangles]
            normal=np.cross(adjacent[:,1]-adjacent[:,0],adjacent[:,2]-adjacent[:,0]).sum(0);normal/=np.linalg.norm(normal)
            knuckles=poses[event,a.knuckles,:3,3].mean(0);wrist=poses[event,a.wrist,:3,3]
            tangent=a.rotation@(knuckles-wrist);tangent-=normal*(normal@tangent);tangent/=np.linalg.norm(tangent)
            directions[name]=(normal,tangent)
        v=scene['contacts'][0]['effector']['surface_vertex'];na,ta=directions['A'];nb,tb=directions['B']
        with threadpool_limits(limits=1):collision=[penetration(surfaces[a],surfaces[b],skin['faces']) for a,b in [('A','B'),('B','A')]]
        geometry[variant]=dict(palm_gap_m=float(np.linalg.norm(surfaces['A'][v]-surfaces['B'][v])),
            opposing_normal_degrees=float(np.degrees(np.arccos(np.clip(-na@nb,-1,1)))),
            tangent_difference_degrees=float(np.degrees(np.arccos(np.clip(ta@tb,-1,1)))),partner_directions=collision)
        save(output/'contact-geometry.json',dict(frame=event,variants=geometry,scope='Independent decoded full skin at contact frame only; not a whole-window collision or realism result.',quality_approved=False))
    save(output/'pipeline.json',dict(status='engine'))
    from run_godot_scene_import import run as engine
    engine(output,output/'engine-audit')
    save(output/'pipeline.json',dict(status='complete',quality_approved=False,finished_at=now()))
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--refinement',type=Path);p.add_argument('--source-scene',type=Path)
    args=p.parse_args();run(args.output,args.refinement,args.source_scene)
