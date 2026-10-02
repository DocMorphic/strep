"""Supervised offline Studio alignment/transfer job with optional bounded cleanup."""
import argparse
import os
import shutil
import zipfile
from pathlib import Path
from strep import ROOT, read, save, sha256, now


def neutral(path):
    import numpy as np
    import torch
    from kimodo.skeleton import SOMASkeleton77
    skeleton=SOMASkeleton77()
    local=torch.eye(3).repeat(2,77,1,1)
    root=torch.tensor([[0.,-float(skeleton.neutral_joints[:,1].min()),0.]]).repeat(2,1)
    rotations,positions,_=skeleton.fk(local,root)
    np.savez(path,local_rot_mats=local.numpy(),global_rot_mats=rotations.numpy(),root_positions=root.numpy(),
             posed_joints=positions.numpy(),foot_contacts=np.zeros((2,len(skeleton.foot_joint_names)),dtype=bool))


def run(folder):
    folder=Path(folder).resolve()
    try:
        import psutil
        save(folder/'worker.json',dict(pid=os.getpid(),created_at=psutil.Process().create_time()))
        request=read(folder/'request.json')
        from action_worker_lock import worker_lock
        with worker_lock():
            save(folder/'pipeline.json',dict(status='processing',stage='Validating character and mapping',started_at=now()))
            character=folder/'source/character.glb';profile=folder/'source/rig-profile.json';motion=folder/'source/motion.npz'
            imported=request.get('source_kind')=='gltf_animation'
            if imported:motion=character
            motion_origin = None
            if request.get('motion_origin') is not None or (folder/'source/motion-origin').exists():
                from motion_origin import verify
                motion_origin = verify(motion, folder/'source/motion-origin', request.get('motion_origin'))
            if sha256(character)!=request['asset_id'] or sha256(profile)!=request['profile_id']:
                raise ValueError('Character/profile snapshot changed')
            snapshot=folder/'source/implementation';snapshot.mkdir(exist_ok=False)
            for name in ['rig_studio_job.py','retarget_rig.py','rig_asset.py','gltf_tools.py','target_rig_contact.py','audit_rig_ground.py','rig_contact_authoring.py','rig_clip_import.py','inspect_rig_contacts.py','rig_clip_edit.py','rig_contact_tracks.py','rig_transition.py','rig_loop.py','rig_runtime_cycle.py','godot_cycle_adapter.gd','godot_cycle_blend.gd']:
                shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            for name in ('rig_events.py','rig_event_retime.py','rig_event_edit.py','rig_periodic_contact.py'):shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            for name in ('rig_runtime_finite.py','godot_finite_adapter.gd','godot_event_object_body.gd'):shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            if request.get('contact_fit') is not None:
                from rig_contact_fit_options import methods
                for name in methods():shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            shutil.copyfile(ROOT/'scripts/motion_origin.py',snapshot/'motion_origin.py')
            shutil.copyfile(ROOT/'scripts/motion_origin_inventory.py',snapshot/'motion_origin_inventory.py')
            for name in ('rig_prompt_edit.py','rig_motion_bridge.py','reuse_action_conditioning.py','action_requests.py','generation_constraints.py','generate_actions.py','action_encoder.py','run_actions.py','export_actions.py'):shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            if request['kind']=='posture_edit':
                for name in ('hand_posture.py','rig_posture_edit.py','verify_rig_clearance.py'):shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            if request['kind']=='mirror_edit':
                for name in ('rig_mirror.py','rig_mirror_edit.py'):shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            if request['kind']=='joint_edit':
                for name in ('rig_joint_recipe.py','rig_joint_edit.py','rig_pose_trajectory.py','rig_pose_tolerances.py','rig_target_refinement.py','rig_coupled_pose.py','temporal_basis.py','rig_trajectory_fit.py','rig_clearance_fit.py','support_contact_v5.py'):
                    shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
            if not imported:shutil.copyfile(ROOT/'vendor/kimodo/LICENSE',folder/'source/SOMA-code-LICENSE.txt')
            if request['kind']=='neutral':neutral(motion)
            elif sha256(motion)!=request['source_motion_sha256']:raise ValueError('Motion snapshot changed')
            from retarget_rig import export
            save(folder/'pipeline.json',dict(status='processing',stage='Transferring and verifying every frame'))
            clip_edit_audit=None
            if request['kind']=='mirror_edit':
                from rig_mirror_edit import run as mirror_clip
                report,mirror_audit=mirror_clip(folder)
            elif request['kind']=='posture_edit':
                from rig_posture_edit import run as edit_posture
                report,posture_audit=edit_posture(folder)
            elif request['kind']=='joint_edit':
                from rig_joint_edit import run as edit_joints
                report,joint_edit_audit=edit_joints(folder)
            elif request['kind']=='prompt_edit':
                from rig_prompt_edit import run as regenerate
                report,prompt_edit_audit=regenerate(folder)
            elif request['kind']=='event_edit':
                from rig_event_edit import run as edit_events
                report=edit_events(folder)
            elif request['kind']=='loop':
                from rig_loop import run as make_loop
                report,loop_audit=make_loop(folder)
            elif request['kind']=='transition':
                from rig_transition import run as join_clips
                report,transition_audit=join_clips(folder)
            elif request['kind']=='clip_edit':
                from rig_clip_edit import run as edit_clip
                report,clip_edit_audit=edit_clip(folder)
            elif request['kind']=='contact_edit':
                report=read(folder/'transfer/report.json')
                if sha256(folder/'transfer/character.glb')!=request['input_glb_sha256'] or sha256(folder/'contact-spec.json')!=request['authored_spec_sha256']:
                    raise ValueError('Authored contact input snapshot changed')
            elif request['kind']=='rough_import':
                from rig_clip_import import export as import_clip
                report=import_clip(character,profile,request['animation_index'],folder/'transfer')
            else:report=export(character,profile,motion,folder/'transfer')
            from audit_rig_ground import audit as inspect_ground
            ground=inspect_ground(folder/'transfer')
            if request['kind'] in ('clip_edit','prompt_edit','joint_edit','posture_edit','mirror_edit'):inspect_ground(folder/'input')
            if request['kind']=='loop':inspect_ground(folder/'repeated')
            if request['kind'] in ('contact_edit','event_edit'):
                report['target_mesh_floor_depth_max_m']=ground['worst_floor']['depth_m']
                save(folder/'transfer/report.json',report)
            base='/files/rig-jobs/'+folder.name+'/'
            result=dict(kind=request['kind'],label=request['label'],frames=report['frames'],fps=report['fps'],root_node=report['root_node'],
                variants=dict(transfer=dict(label='Input clip' if request['kind']=='contact_edit' else 'Imported clip' if imported else 'Rig transfer',glb=base+'transfer/character.glb',sha256=report['glb_sha256'],root_track=base+'transfer/root-motion.json')),
                report=base+'transfer/report.json',root_track=base+'transfer/root-motion.json',contacts=base+'transfer/contacts.json',
                profile=base+'source/rig-profile.json',source_motion_sha256=sha256(motion),source_character_sha256=request['asset_id'],
                floor_depth_m=report['target_mesh_floor_depth_max_m'],source_kind=report.get('source_kind','soma_motion'),human_approved=False,engine_import=None)
            if request['kind']=='neutral':
                result['note']='Synthetic SOMA neutral pose for mapping/axis review; not generated motion or a ground-contact test.'
            elif request['kind']=='contact_edit':
                result['note']='Authored mesh contacts fitted to a preserved input clip. Review support placement, action and naturalness; engine validation is not part of this job.'
                if request.get('contact_fit') is not None:result['contact_fit_options']=base+'contact-fit.json'
            elif request['kind']=='mirror_edit':
                result['variants']['transfer']['label']='Mirrored clip'
                result['variants']['input']=dict(label='Original clip',glb=base+'input/character.glb',sha256=request['input_glb_sha256'],root_track=base+'input/root-motion.json',report=base+'input/report.json',contacts=base+'input/contacts.json')
                if (folder/'input/contact-spec.json').exists():result['variants']['input']['contact_spec']=base+'input/contact-spec.json'
                result.update(mirror_recipe=base+'mirror.json',mirror_audit=base+'transfer/audit.json',timeline=base+'transfer/timeline.json')
                result['note']='Whole-clip side swap on this rig, with reflected root motion and unchanged timing. Original proportions retained. Contact predictions swap sides; events need review. Source mesh targets stay under input for re-authoring. Review action, floor clearance and naturalness. Finite export; previous loop contract is not retained.'
            elif request['kind']=='posture_edit':
                result['variants']['transfer']['label']='Hand posture candidate'
                result['variants']['input']=dict(label='Input clip',glb=base+'input/character.glb',sha256=request['input_glb_sha256'],root_track=base+'input/root-motion.json',report=base+'input/report.json',contacts=base+'input/contacts.json')
                result.update(posture_recipe=base+'hand-posture.json',posture_audit=base+'transfer/verification.json',posture_intents=base+'transfer/posture-events.json')
                if (folder/'contact-spec.json').exists():result['contact_spec']=base+'contact-spec.json'
                if (folder/'input/contact-spec.json').exists():result['variants']['input']['contact_spec']=base+'input/contact-spec.json'
                result['note']='Timed local finger rotations authored on mapped hands. Body/root motion and original annotation timing retained. Posture intents are not verified contacts or gameplay events. Anatomy, interaction and naturalness need review.'
            elif request['kind']=='joint_edit':
                result['variants']['transfer']['label']='Joint target candidate'
                result['variants']['input']=dict(label='Input clip',glb=base+'input/character.glb',sha256=request['input_glb_sha256'],root_track=base+'input/root-motion.json',report=base+'input/report.json',contacts=base+'input/contacts.json')
                result.update(joint_edit_recipe=base+'joint-edit.json',joint_edit_audit=base+'transfer/joint-edit-audit.json',
                    joint_edit_status='numerical_screens_met' if joint_edit_audit['numerical_screen_passed'] else 'rejected',
                    joint_targets_reached=joint_edit_audit['targets_reached'])
                if (folder/'contact-spec.json').exists():result['contact_spec']=base+'contact-spec.json'
                result['note']=('Sparse world-joint edit: '+('targets met' if joint_edit_audit['targets_reached'] else 'targets missed')+'. '+
                    ('Numerical screens met.' if joint_edit_audit['numerical_screen_passed'] else 'Failed checks: '+', '.join(joint_edit_audit['flags'])+'.')+
                    ' Input, target-fitting stage and candidate retained. Outside-window context and hard motion limits checked. Timing retained; contact, action and naturalness require review. No animator or engine approval.')
            elif request['kind']=='prompt_edit':
                from rig_prompt_edit import review_info
                result['prompt_edit_info']=review_info(prompt_edit_audit)
                result['variants']['transfer']['label']='Regenerated section'
                result['variants']['input']=dict(label='Input clip',glb=base+'input/character.glb',sha256=request['input_glb_sha256'],root_track=base+'input/root-motion.json',report=base+'input/report.json',contacts=base+'input/contacts.json')
                result.update(prompt_edit_recipe=base+'prompt-edit.json',prompt_edit_audit=base+'transfer/prompt-edit-audit.json',source_timeline=base+'transfer/timeline.json',raw_generation=base+'generation/summary.json')
                result['note']='Selected section regenerated from its replacement description and converted boundary poses. Surrounding frames and two samples at each edge are preserved. Raw generation, guide errors and the spliced result remain separate. Contacts, markers and action correctness need review.'
            elif request['kind']=='clip_edit':
                input_report=read(folder/'input/report.json')
                result['variants']['transfer']['label']='Edited clip'
                result['variants']['input']=dict(label='Input clip',glb=base+'input/character.glb',sha256=request['input_glb_sha256'],root_track=base+'input/root-motion.json',frames=input_report['frames'],fps=input_report['fps'],root_node=input_report['root_node'])
                result['variants']['input'].update(contacts=base+'input/contacts.json',report=base+'input/report.json')
                if (folder/'input/contact-spec.json').exists():result['variants']['input']['contact_spec']=base+'input/contact-spec.json'
                result.update(edit_timeline=clip_edit_audit['timeline'],edit_recipe=base+'clip-edit.json',edit_audit=base+'transfer/clip-edit-audit.json',timeline=base+'transfer/timeline.json')
                if (folder/'contact-spec.json').exists():result['contact_spec']=base+'contact-spec.json'
                result['note']='Trim, speed and smooth local pose edits applied. Input comparison follows the source-frame mapping. World placement is retained; contact intervals are retimed and need review. Dynamics and realism are not validated.'
            elif request['kind']=='transition':
                result['variants']['transfer']['label']='Joined clip'
                result.update(transition_recipe=base+'transition.json',transition_audit=base+'transfer/transition-audit.json',timeline=base+'transfer/timeline.json',contact_review=base+'transfer/contact-review.json',events=base+'transfer/events.json')
                recipe=read(folder/'transition.json')
                result['transition_info']=dict(start=transition_audit['blend_start_frame'],last=transition_audit['blend_last_frame'],first_frames=[c['first_frame'] for c in recipe['clips']],pose_disagreement_degrees=transition_audit['source_pose_disagreement_max_degrees'],ambiguous_support_count=transition_audit['ambiguous_support_count'])
                result['note']='Two source clips joined with an explicit overlap and heading adjustment. Source targets are retained in Contact review; they have not been fitted. Inspect support, floor clearance, action and dynamics before use.'
            elif request['kind']=='loop':
                repeated=read(folder/'repeated/report.json')
                result['variants']['transfer']['label']='One cycle'
                result['variants']['repeated']=dict(label='Three cycles · review',glb=base+'repeated/character.glb',sha256=repeated['glb_sha256'],root_track=base+'repeated/root-motion.json',report=base+'repeated/report.json',contacts=base+'repeated/contacts.json',frames=repeated['frames'],fps=30,root_node=report['root_node'])
                result['variants']['repeated'].update(events=base+'repeated/events.json',contact_review=base+'repeated/contact-review.json',timeline=base+'repeated/timeline.json')
                result.update(loop_recipe=base+'loop.json',loop_audit=base+'transfer/loop-audit.json',timeline=base+'transfer/timeline.json',loop_period_frames=loop_audit['period_frames'])
                if (folder/'transfer/runtime-cycle.json').exists():
                    result.update(runtime_cycle=base+'transfer/runtime-cycle.json',runtime_adapter=base+'transfer/godot_cycle_adapter.gd',runtime_readme=base+'transfer/GODOT-CYCLES.md')
                elif (folder/'transfer/runtime-unavailable.json').exists():result['runtime_unavailable']=read(folder/'transfer/runtime-unavailable.json')['reason']
                result['note']='Cycle extracted with a blended return and accumulated root placement. One cycle includes a terminal phase-zero sample. Three-cycle review exposes repeated seams; edit the one-cycle version. Source events stay in the package for periodic review. Contacts and realism remain unconfirmed.'
            elif imported:
                result['note']='Existing animation sampled at 30fps for editing. Original timing and source file are preserved; between-frame motion is approximated. No contacts were inferred. Mapping offsets and reference-axis corrections were not applied.'
            else:
                result['note']='Finite transfer verified against target joints and skin. Review action, reference axes and contact; engine validation is not part of this job.'
            if (folder/'transfer/events.json').exists():result['events']=base+'transfer/events.json'
            if request['kind']=='event_edit':
                result['variants']['transfer']['label']='Authored markers'
                result['event_recipe']=base+'event-edit.json'
                result['note']='Authored event timing changed; selected GLB bytes are unchanged. Timing confirmation does not establish physical contact or action correctness.'
                if request.get('inherited_joint_edit'):
                    inherited=request['inherited_joint_edit'];result['inherited_joint_edit']=inherited
                    result['joint_edit_status']=inherited['status'];result['joint_targets_reached']=inherited['targets_reached']
                    result['joint_edit_audit']=base+'transfer/joint-edit-audit.json'
                    result['note']+=' Joint-edit quality status is inherited unchanged: '+inherited['status']+'.'
                if request.get('inherited_correction'):
                    inherited=request['inherited_correction'];result['inherited_correction']=inherited
                    result['correction_status']=inherited['status'];result['correction_audit']=inherited['audit']
                    result['note']+=' Motion-quality status is inherited unchanged: '+inherited['status']+'.'
                    if (folder/'transfer/audit.json').exists():result['audit']=base+'transfer/audit.json'
                if (folder/'transfer/timeline.json').exists():
                    timeline=read(folder/'transfer/timeline.json')
                    if 'period_frames' in timeline:result['loop_period_frames']=timeline['period_frames']
                if (folder/'repeated').exists():
                    repeated=read(folder/'repeated/report.json')
                    result['variants']['repeated']=dict(label='Three cycles · review',glb=base+'repeated/character.glb',sha256=repeated['glb_sha256'],root_track=base+'repeated/root-motion.json',frames=repeated['frames'],fps=30,root_node=report['root_node'],events=base+'repeated/events.json',report=base+'repeated/report.json',contacts=base+'repeated/contacts.json',timeline=base+'repeated/timeline.json',contact_review=base+'repeated/contact-review.json')
                if (folder/'transfer/runtime-cycle.json').exists():result.update(runtime_cycle=base+'transfer/runtime-cycle.json',runtime_adapter=base+'transfer/godot_cycle_adapter.gd',runtime_readme=base+'transfer/GODOT-CYCLES.md')
            if (folder/'transfer/contact-review.json').exists():result['contact_review']=base+'transfer/contact-review.json'
            if request['kind']=='contact_edit' and (folder/'transfer/timeline.json').exists():result['source_timeline']=base+'transfer/timeline.json'
            if request.get('correct_contacts'):
                save(folder/'pipeline.json',dict(status='processing',stage='Checking target-contact feasibility'))
                from target_rig_contact import draft,RigAsset,baseline,floor_lower_bound,run as correct,SoleDraftUnsupported
                try:
                    if request['kind']=='contact_edit':
                        from target_rig_contact import validate
                        spec=read(folder/'contact-spec.json');validate(spec,RigAsset.load(folder/'transfer/character.glb'))
                    else:spec=draft(folder/'transfer',folder/'contact-spec.json')
                except SoleDraftUnsupported as exc:
                    spec=None
                    result['correction_status']='unsupported'
                    result['note']='Transfer retained. Automatic foot correction is unavailable: '+str(exc)
                    save(folder/'correction-unavailable.json',dict(status='unsupported',reason=str(exc)))
                if spec is not None:
                    if request['kind']!='contact_edit':spec['objective']['rotation_prior_m_per_radian']=.15
                    save(folder/'contact-spec.json',spec)
                    rig=RigAsset.load(folder/'transfer/character.glb');before,_=baseline(rig,spec['frames'])
                    feasibility=floor_lower_bound(rig,spec,before);save(folder/'feasibility.json',feasibility)
                    result['feasibility']=feasibility;result['contact_spec']=base+'contact-spec.json'
                    if feasibility['floor_infeasible_under_declared_edits']:
                        result['correction_status']='infeasible';result['note']='Input retained. Current editable joints and root budget cannot clear this mesh; revise the contact targets or editable joints before fitting.'
                    else:
                        save(folder/'pipeline.json',dict(status='processing',stage='Fitting target mesh contacts; raw transfer retained'))
                        if request.get('contact_fit') is not None:
                            from rig_playback_contact_job import run as fit_playback
                            save(folder/'pipeline.json',dict(status='processing',stage='Fitting contacts across playback; input retained'))
                            evidence,playback_review=fit_playback(folder)
                            result['playback_contact_fit']=dict(**playback_review,options=base+'contact-fit.json',review=base+'contact-fit-review.json',
                                request=base+'mesh-fit/request.json',audit=base+'mesh-fit/result.json',
                                contacts=base+'mesh-fit/playback-contact-inspection.json',floor=base+'mesh-fit/subframe-floor-inspection.json')
                            result['note']='Playback contact candidate '+('passes the sampled numerical screens.' if playback_review['numerical_screen_passed'] else 'fails the sampled numerical screens; input retained.')+' Fixed world targets, motion bounds, authored-key or full-frame contact timing and decoded floor are checked. Anatomy, action and naturalness remain unreviewed.'
                        else:evidence=correct(folder/'transfer',folder/'contact-spec.json',folder/'corrected')
                        inspect_ground(folder/'corrected',{**report,'glb_sha256':evidence['glb_sha256']})
                        result['variants']['corrected']=dict(label='Contact candidate',glb=base+'corrected/character.glb',sha256=evidence['glb_sha256'],root_track=base+'corrected/root-motion.json')
                        result['correction_status']='provisional_pass' if evidence['numerical_screen_passed'] else 'rejected'
                        result['correction_audit']=evidence;result['audit']=base+'corrected/audit.json'
                        result['root_track']=base+'corrected/root-motion.json'
                        if 'period_frames' in evidence:
                            p=evidence['period_frames'];repeated=read(folder/'corrected/repeated/report.json')
                            inspect_ground(folder/'corrected/repeated')
                            result['loop_period_frames']=p
                            result['variants']['corrected'].update(report=base+'corrected/report.json',contacts=base+'corrected/contacts.json',events=base+'corrected/events.json',contact_review=base+'corrected/contact-review.json',timeline=base+'corrected/timeline.json',runtime_cycle=base+'corrected/runtime-cycle.json',runtime_adapter=base+'corrected/godot_cycle_adapter.gd',runtime_readme=base+'corrected/GODOT-CYCLES.md')
                            result['variants']['repeated']=dict(label='Corrected three cycles · review',source_variant='corrected',glb=base+'corrected/repeated/character.glb',sha256=repeated['glb_sha256'],root_track=base+'corrected/repeated/root-motion.json',report=base+'corrected/repeated/report.json',contacts=base+'corrected/repeated/contacts.json',events=base+'corrected/repeated/events.json',contact_review=base+'corrected/repeated/contact-review.json',timeline=base+'corrected/repeated/timeline.json',frames=repeated['frames'],fps=30,root_node=report['root_node'])
                            result['note']='Periodic contact candidate retains cycle placement and exact terminal closure. Correction-step bounds also apply across the seam. Explicit targets may be infeasible; inspect the audit and repeated preview. Motion quality remains unapproved.'
            for runtime_variant in ['transfer','corrected']:
                variant_folder=folder/runtime_variant
                if (variant_folder/'character.glb').exists() and not (variant_folder/'runtime-cycle.json').exists():
                    from rig_runtime_finite import write as write_finite
                    target_result=result if runtime_variant=='transfer' else result['variants'][runtime_variant]
                    try:
                        write_finite(variant_folder)
                    except ValueError as error:
                        save(variant_folder/'runtime-finite-unavailable.json',dict(reason=str(error),animation_preserved=True))
                        target_result['runtime_finite_unavailable']=base+runtime_variant+'/runtime-finite-unavailable.json'
                    else:
                        target_result.update(runtime_finite=base+runtime_variant+'/runtime-finite.json',runtime_finite_adapter=base+runtime_variant+'/godot_finite_adapter.gd',runtime_finite_readme=base+runtime_variant+'/GODOT-FINITE.md')
                if (folder/runtime_variant/'godot_cycle_blend.gd').exists():
                    target_result=result if runtime_variant=='transfer' else result['variants'][runtime_variant]
                    target_result.update(runtime_blend_adapter=base+runtime_variant+'/godot_cycle_blend.gd',runtime_blend_readme=base+runtime_variant+'/GODOT-BLENDS.md')
            if motion_origin is not None:
                result['source_generation_origin'] = dict(manifest=base+'source/motion-origin/manifest.json',
                    manifest_sha256=sha256(folder/'source/motion-origin/manifest.json'),status=motion_origin['status'],
                    scope=motion_origin['scope'],applies_to='original_source_motion',quality_approved=False)
                for name in motion_origin['files']:
                    result['source_generation_origin'][name.removesuffix('.json').replace('-','_')] = base+'source/motion-origin/'+name
            from motion_origin_inventory import write as write_generation_sources
            generation_sources=write_generation_sources(folder)
            result['generation_sources']=dict(manifest=base+'generation-sources.json',manifest_sha256=sha256(folder/'generation-sources.json'),
                distinct_source_records=generation_sources['distinct_source_records'],retained_locations=generation_sources['retained_locations'],
                recorded_sources=generation_sources['recorded_sources'],unavailable_sources=generation_sources['unavailable_sources'],
                applies_to=generation_sources['applies_to'],scope=generation_sources['scope'],quality_approved=False)
            package=folder/'character-animation.zip'
            # Only local project snapshots and outputs; original input asset remains unchanged.
            paths=[p for directory in ['source','input','following','transfer','repeated','corrected','generation','target-fit','quality-fit','mesh-fit'] if (folder/directory).exists()
                   for p in (folder/directory).rglob('*') if p.is_file()]
            paths += [folder/name for name in ['request.json','contact-spec.json','contact-fit.json','contact-fit-review.json','clip-edit.json','mirror.json','transition.json','loop.json','event-edit.json','prompt-edit.json','joint-edit.json','joint-spec.json','joint-targets.json','joint-input.npz','hand-posture.json','feasibility.json','correction-unavailable.json'] if (folder/name).is_file()]
            paths.append(folder/'generation-sources.json')
            note=('Local Strep character animation. No independent animator or engine approval. '
                  'Source character, saved rig profile and '+('original embedded animations' if imported else 'SOMA motion')+' are retained under source/. '
                  'Root tracks describe the mapped pelvis in world metres; engine root extraction is not applied. '
                  'Predicted contact intervals are not confirmed gameplay events. '
                  'Check transfer/report.json and any corrected/audit.json; rejected candidates remain included. '
                  'When present, source/motion-origin/ retains hash-bound original generation intent, not a quality rating or a claim about later edits. '
                  'generation-sources.json indexes verified bundled generation records, including donor and regeneration history; it does not assign their profiles to the edited result. '
                  'The source asset retains its own licensing. This package does not include model weights or the original inference environment.\n')
            with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as archive:
                for path in paths:archive.write(path,path.relative_to(folder).as_posix())
                archive.writestr('README.txt',note)
            with zipfile.ZipFile(package) as archive:
                if archive.testzip() is not None:raise ValueError('Package CRC check failed')
                for path in paths:
                    import hashlib
                    if hashlib.sha256(archive.read(path.relative_to(folder).as_posix())).hexdigest()!=sha256(path):raise ValueError('Package bytes changed')
            result['package']=base+'character-animation.zip';result['package_sha256']=sha256(package)
            save(folder/'result.json',result)
            save(folder/'pipeline.json',dict(status='complete',finished_at=now(),stage='Ready for review'))
    except Exception as exc:
        save(folder/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    run(parser.parse_args().folder)
