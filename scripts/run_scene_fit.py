"""Experimental independent actor fits against a frozen authored scene.

Preserves source clips and scene fixtures. Records missed targets/collisions;
never promotes a candidate on the basis of the solver objective alone.
"""
import argparse
import copy
import shutil
import time
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from kimodo.skeleton import SOMASkeleton77
from strep import ROOT,read,save,sha256,now
from action_worker_lock import worker_lock
from build_soma_preview import ASSET
from floor_contact import correct as floor_correct
from body_contact import refine as body_refine
from support_contact_v2 import refine,CONFIG
from compile_scene_contacts import compile_contacts
from scene_constraints import evaluate as scene_evaluate,effector_track
from evaluate_body_contact import evaluate as body_evaluate
from evaluate_contact_spec import evaluate as target_evaluate
from run_body_contact import export_motion


def bundle(scene,motions,assessment):
    native={}
    for c in scene['contacts']:
        def track(name,effector):
            m=motions[name];return effector_track(dict(positions=m['posed_joints'],rotations=m['global_rot_mats']),effector,dict(np.load(ASSET))).tolist()
        item=dict(actual=track(c['actor'],c['effector']))
        if c['target']['space']=='actor':item['target']=track(c['target']['actor'],c['target'])
        native[c['id']]=item
    return dict(scene=scene,evaluation=assessment,native_contact_tracks=native)


def preview_asset(entry,preview_base=None):
    base=Path(preview_base).resolve() if preview_base is not None else ROOT/'reports/scene-preview-v1'
    path=(base/entry['preview_glb']).resolve()
    if preview_base is not None and not path.is_relative_to(base):
        raise ValueError('Actor preview escapes the supplied collection')
    if path.suffix.lower()!='.glb' or not path.is_file():raise ValueError('Actor preview GLB missing')
    return path


def run(scene_paths,output,solver_version=2,preview_base=None,*,preserve_body=False):
    from scene_fit_body_policy import validate_mode
    validate_mode(solver_version,preserve_body)
    global refine,CONFIG
    if solver_version in [3,4,5,6,7,8,9,10,11,12,13,14,15,16,17]:
        import importlib
        solver=importlib.import_module('support_contact_v'+str(solver_version));refine,CONFIG=solver.refine,solver.CONFIG
    out=Path(output).resolve();out.mkdir(parents=True,exist_ok=False);save(out/'pipeline.json',dict(status='processing'))
    sources=['run_scene_fit.py','compile_scene_contacts.py','contact_spec.py','scene_constraints.py','object_geometry.py','palm_contacts.py','support_contact_v2.py',
        'support_contact_v3.py','support_contact_v4.py','support_contact_v5.py','support_contact_v6.py','support_contact_v7.py','support_contact_v8.py','support_contact_v9.py','support_contact_v10.py','support_contact_v11.py','support_contact_v12.py','support_contact_v13.py','support_contact_v14.py','support_contact_v15.py','support_contact_v16.py','support_contact_v17.py','linear_skin_operator.py','object_playback_checkpoint.py','point_numerical_headroom.py','object_subframe_constraints.py','intentional_object_clearance.py','scene_release_guards.py','scene_solver_context.py','partner_surface_cuts.py','audit_scene_orientation.py','support_contact.py','floor_contact.py','body_contact.py','evaluate_contact_spec.py','evaluate_body_contact.py','evaluate_floor_contact.py','run_body_contact.py']
    sources.append('scene_fit_body_policy.py')
    if preserve_body:sources.extend(['native_body_objective.py','skin_point_reach_bound.py'])
    snapshot=out/'source-snapshot';snapshot.mkdir()
    for name in sources:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    skin=dict(np.load(ASSET));skeleton=SOMASkeleton77();summary=dict(created_at=now(),solver_version=solver_version,config=CONFIG,trials=[],
        implementation={name:sha256(snapshot/name) for name in sources},mesh_sha256=sha256(ASSET),
        scope=('In-sample deterministic point and surface-frame fitting with sampled primitive clearance; optional frozen partner cuts in v8.' if solver_version>=6 else 'In-sample deterministic point fitting; no orientation solve.')+' Not model training or scene-aware inference. All candidates unreviewed; no physical attachment, joint partner solve or dynamic simulation.')
    if preserve_body:
        from scene_fit_body_policy import description
        summary['body_preservation']=description()
    manifest=dict(created_at=now(),scenes=[],assets={},scope=summary['scope'])
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',out/'SOMA-preview-LICENSE.txt')
    try:
        with worker_lock():
            for scene_path in scene_paths:
                source_scene=read(scene_path);scene=copy.deepcopy(source_scene.get('scene',source_scene));scene_id=scene['id']
                if solver_version<8:
                    from object_geometry import scene_geometry
                    if any(scene_geometry(obj).shape!='box' for obj in scene.get('objects',{}).values()):
                        raise ValueError('Non-box scene contact fitting requires solver version 8 or newer')
                if solver_version<8 and (scene.get('partner_cut_file') or any(c.get('tangent_target') for c in scene['contacts'])):
                    raise ValueError('Hand tangents and partner cuts require solver version 8 or newer')
                if any(t['id']==scene_id for t in summary['trials']):raise ValueError('Duplicate scene id')
                folder=out/scene_id;save(folder/'authored-scene.json',scene)
                if preserve_body:
                    from scene_fit_body_policy import reach_report
                    incompatible=False
                    for name,entry in scene['actors'].items():
                        ids=[c['id'] for c in scene['contacts'] if c['actor']==name and c['target']['space']!='actor']
                        spec,compilation=compile_contacts(scene,name,ids,skin)
                        raw=dict(np.load(ROOT/entry['motion'],allow_pickle=False))
                        path=out/'assets'/scene_id/name
                        save(path/'contact-spec.json',spec);save(path/'compilation.json',compilation)
                        reach=reach_report(raw,skin,spec);save(path/'body-reach-preflight.json',dict(**reach,
                            source_sha256=sha256(ROOT/entry['motion']),skin_sha256=sha256(ASSET),
                            contact_spec_sha256=sha256(path/'contact-spec.json')))
                        incompatible |= reach['status']=='provably_incompatible_native_keys'
                    if incompatible:
                        raise ValueError('Requested native contacts conflict with the 22 cm body budget; see body-reach-preflight.json')
                before=scene_evaluate(scene,skin);save(folder/'before.json',before)
                original=copy.deepcopy(scene);raw_motions={};motions={};records={}
                for name,entry in scene['actors'].items():
                    # Partner surface targets remain diagnostics. Shared world
                    # targets drive each actor independently, avoiding chasing.
                    ids=[c['id'] for c in scene['contacts'] if c['actor']==name and c['target']['space']!='actor']
                    spec,compilation=compile_contacts(original,name,ids,skin)
                    source=ROOT/entry['motion'];digest=sha256(source);raw=dict(np.load(source));raw_motions[name]=raw
                    path=out/'assets'/scene_id/name;path.mkdir(parents=True)
                    shutil.copyfile(source,path/'raw-motion.npz');save(path/'contact-spec.json',spec);save(path/'compilation.json',compilation)
                    raw_glb=preview_asset(entry,preview_base);shutil.copyfile(raw_glb,path/'raw.glb')
                    original['actors'][name].update(preview_glb=(path/'raw.glb').relative_to(out).as_posix())
                    start=time.perf_counter();base,limb_recipe=floor_correct(raw,skin);previous,body_recipe=body_refine(base,skin)
                    context_args={}
                    if solver_version>=6:
                        from scene_solver_context import compile_context
                        context_args['scene_context']=compile_context(original,name,ids,skin,release_endpoint_guards=solver_version>=11,intentional_object_contacts=solver_version>=14);save(path/'scene-context.json',context_args['scene_context'])
                    if preserve_body:
                        from scene_fit_body_policy import arguments
                        context_args.update(arguments(raw,base,previous))
                    candidate,recipe=refine(base,previous,skin,lambda r:print(scene_id,name,r['evaluations'],round(r['loss'],5),flush=True),raw,spec,**context_args)
                    evaluation,body=body_evaluate(raw,base,candidate,skin,recipe);targets=target_evaluate(base,candidate,skin,spec)
                    lift=candidate['root_positions'][:,1]-base['root_positions'][:,1]
                    assert lift.min()>=-2e-7 and lift.max()<=CONFIG['max_root_lift_m']+2e-7
                    relative=previous['local_rot_mats'].transpose(0,1,3,2)@candidate['local_rot_mats']
                    angle=np.rad2deg(np.linalg.norm(Rotation.from_matrix(relative.reshape(-1,3,3)).as_rotvec(),axis=1)).max()
                    assert angle<=CONFIG['max_rotation_degrees']+1e-4
                    validation=export_motion(path,candidate,skin,skeleton,evaluation['after']['per_frame_max_depth_m'])
                    np.savez(path/'limb-motion.npz',**base);np.savez(path/'previous-motion.npz',**previous)
                    save(path/'recipe.json',dict(limb=limb_recipe,body=body_recipe,contact=recipe))
                    flags=list(evaluation['flags'])
                    if not targets['all_explicit_targets_within_tolerance']:flags.append('authored_contact_target_missed')
                    record=dict(source_sha256=digest,seconds=time.perf_counter()-start,flags=flags,target_evaluation=targets,
                        body_evaluation=body,floor_evaluation=evaluation,export_validation=validation,
                        measured_rotation_delta_degrees=float(angle),root_lift_min_m=float(lift.min()),root_lift_max_m=float(lift.max()),
                        human_approved=False,engine_import=None)
                    save(path/'evaluation.json',record);records[name]=record;motions[name]=candidate
                    entry.update(motion=(path/'motion.npz').relative_to(ROOT).as_posix(),preview_glb=(path/'soma.glb').relative_to(out).as_posix(),source_sha256=sha256(path/'motion.npz'))
                    assert sha256(source)==digest
                    for file in [path/'soma.glb',path/'raw.glb']:manifest['assets'][file.relative_to(out).as_posix()]=dict(sha256=sha256(file))
                after=scene_evaluate(scene,skin);save(folder/'after.json',after)
                missed=[c['id'] for c in after['contacts'] if not c['all_requested_frames_within_tolerance']]
                collisions=[c for c in after['object_collisions'] if c['max_skin_vertex_depth_m']>.01]
                missed_normals=[]
                save(folder/'requested-events.json',dict(fps=30,contacts=scene['contacts'],provenance='Requested times and points, not validated gameplay events. See independent after.json measurements.'))
                for version,spec,motion,evaluation in [('source',original,raw_motions,before),('candidate',scene,motions,after)]:
                    spec=copy.deepcopy(spec);spec['id']=scene_id+'-'+version
                    spec['review_note']=('Unchanged motion; authored scene trajectory.' if version=='source' else 'Experimental deterministic contact fit; unreviewed. Targets and collisions measured separately.')+(' Surface-frame and sampled primitive-clearance terms enabled.' if version=='candidate' and solver_version>=6 else ' No palm orientation solve.')+(' Frozen partner clearance cuts applied; independent geometry recheck required.' if version=='candidate' and scene.get('partner_cut_file') else ' No partner clearance solve.')+' No physical attachment or joint partner dynamics.'
                    packaged=bundle(spec,motion,evaluation)
                    if solver_version>=6:
                        from audit_scene_orientation import audit
                        oriented=audit(spec,skin);packaged['orientation']=oriented
                        save(folder/(version+'-orientation-audit.json'),oriented)
                        if version=='candidate':
                            save(folder/'orientation-audit.json',oriented)
                            missed_normals=[c['id'] for c in oriented['contacts'] if c['frames_over_tolerance'] or c.get('tangent_frames_over_tolerance',0)]
                    save(folder/(version+'.json'),packaged)
                    manifest['scenes'].append(dict(id=spec['id'],label=spec['id'].replace('-',' '),variants=dict(palm=scene_id+'/'+version+'.json')))
                summary['trials'].append(dict(id=scene_id,scene_source_sha256=sha256(scene_path),actors=records,missed_scene_contacts=missed,
                    objects_over_1cm=collisions,missed_scene_normals=missed_normals,status='flagged' if missed or missed_normals or collisions or any(r['flags'] for r in records.values()) else 'within_provisional_numerical_screen',human_approved=False))
                save(out/'summary.json',summary);save(out/'manifest.json',manifest)
                print('SCENE',scene_id,'missed',missed,'object collision count',len(collisions),flush=True)
        save(out/'pipeline.json',dict(status='complete'));save(out/'summary.json',dict(**summary,finished_at=now()))
    except Exception as e:save(out/'pipeline.json',dict(status='failed',error=str(e)));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('scenes',nargs='+',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--solver-version',type=int,choices=[2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17],default=2)
    parser.add_argument('--preview-base',type=Path,help='Explicit saved collection root for relative actor GLBs')
    parser.add_argument('--preserve-body',action='store_true',help='Experimental V17 body inequalities against raw/limb/previous references; no feasibility guarantee')
    args=parser.parse_args();run(args.scenes,args.output,args.solver_version,args.preview_base,preserve_body=args.preserve_body)
