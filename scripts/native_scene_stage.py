"""Explicit common scene translation, retaining clips and fixed world planes."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts, fields, vector, scalar
from native_scene_geometry import policy_for, evaluate_to_archive as geometry_audit, METHODS as GEOMETRY_METHODS
from strep import ROOT, read, save, sha256, now

METHODS=tuple(dict.fromkeys(GEOMETRY_METHODS+('native_scene_stage.py',)))


def translated(spec, offset):
    """Move actors, props and world targets together; object-local points stay local."""
    offset=np.asarray(offset,float)
    if offset.shape!=(3,) or not np.isfinite(offset).all():raise ValueError('Finite common translation required')
    result=copy.deepcopy(spec)
    for actor in result['actors'].values():
        actor['placement']['translation_m']=(np.asarray(actor['placement']['translation_m'])+offset).tolist()
    for obj in result['objects'].values():
        for key in obj['keyframes']:key['translation_m']=(np.asarray(key['translation_m'])+offset).tolist()
    for contact in result['contacts']:
        if contact['target']['space']=='world':
            contact['target']['points_m']=(np.asarray(contact['target']['points_m'])+offset).tolist()
    return result


def invariant(before, after, before_arrays, after_arrays):
    """Check actual contact clocks/residuals; translation cannot approve a failed contact."""
    maximum=0.
    if len(before['contacts'])!=len(after['contacts']):raise ValueError('Contact population changed')
    for i,(left,right) in enumerate(zip(before['contacts'],after['contacts'])):
        if (left['id']!=right['id'] or left['limits']!=right['limits'] or left['passed']!=right['passed']
                or left['interval_s']!=right['interval_s']):raise ValueError('Stage translation changed contact conditions')
        np.testing.assert_array_equal(before_arrays[f'contact_{i}_times_s'],after_arrays[f'contact_{i}_times_s'])
        errors=[]
        for arrays in (before_arrays,after_arrays):
            errors.append(arrays[f'contact_{i}_effector_world_m']-arrays[f'contact_{i}_target_world_m'])
        difference=float(abs(errors[0]-errors[1]).max());maximum=max(maximum,difference)
        if difference>2e-12:raise ValueError('Translated contact residuals differ')
        if abs(left['maximum_position_error_m']-right['maximum_position_error_m'])>2e-12:
            raise ValueError('Translated contact position metric differs')
        if len(left['relative_speed_populations'])!=len(right['relative_speed_populations']):
            raise ValueError('Contact speed population changed')
        for a,b in zip(left['relative_speed_populations'],right['relative_speed_populations']):
            for key in ('available','passed','rate_hz','phase_offset_frames','times_s'):
                if a[key]!=b[key]:raise ValueError('Contact speed clock/acceptance changed')
            if a['available'] and abs(a['maximum_relative_speed_m_s']-b['maximum_relative_speed_m_s'])>1e-9:
                raise ValueError('Translated contact speed metric differs')
    return maximum


def run(contacts_path, policy_path, control_path, output):
    contacts_path,policy_path,control_path,output=map(lambda p:Path(p).resolve(),(contacts_path,policy_path,control_path,output))
    if output.exists():raise ValueError('Fresh scene translation directory required')
    with worker_lock(),threadpool_limits(limits=1):
        bindings={str(p):sha256(p) for p in (contacts_path,policy_path,control_path)}
        control=read(control_path)
        fields(control,('schema','contacts_sha256','policy_sha256','translation_m','maximum_translation_m'),'scene translation control')
        if (control['schema']!='strep-native-scene-stage-v1' or control['contacts_sha256']!=bindings[str(contacts_path)]
                or control['policy_sha256']!=bindings[str(policy_path)]):raise ValueError('Stage control must bind exact scene and policy')
        offset=vector(control['translation_m'],3,'common stage translation')
        bound=scalar(control['maximum_translation_m'],0,.1,'stage translation bound')
        if np.linalg.norm(offset)>bound:raise ValueError('Translation exceeds explicit scene placement bound')
        spec=read(contacts_path);scene=SceneContacts(spec,contacts_path.parent);bindings.update(scene.inputs)
        policy=read(policy_path);policy_for(policy,scene,bindings[str(contacts_path)])
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True);archive=output/'implementation';archive.mkdir();snapshots={}
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        for i,(path,h) in enumerate(bindings.items()):
            dest=output/'input'/f'{i}{Path(path).suffix}';dest.parent.mkdir(exist_ok=True);shutil.copyfile(path,dest)
            if sha256(dest)!=h:raise ValueError('Scene translation input snapshot differs')
            snapshots[path]=dict(path=dest.relative_to(output).as_posix(),sha256=h)
        save(output/'request.json',dict(at=now(),source_snapshots=snapshots,inputs_sha256=bindings,
            implementation_sha256=methods,translation_m=offset.tolist(),maximum_translation_m=bound,
            clips_edited=False,world_planes_edited=False,quality_approved=False))
        save(output/'pipeline.json',dict(status='processing',source_scene_retained=True,proposal_selected=False))
        try:
            derived=translated(spec,offset)
            for name,entry in derived['actors'].items():
                original=str((contacts_path.parent/spec['actors'][name]['glb']).resolve())
                entry['glb']=str(output/snapshots[original]['path'])
            proposal=output/'proposal';proposal.mkdir();save(proposal/'contacts.json',derived)
            digest=sha256(proposal/'contacts.json');derived_policy=copy.deepcopy(policy);derived_policy['contacts_sha256']=digest
            save(proposal/'policy.json',derived_policy);policy_digest=sha256(proposal/'policy.json')
            after_scene=SceneContacts(derived,proposal)
            before,before_arrays=scene.evaluate();after,after_arrays=after_scene.evaluate()
            difference=invariant(before,after,before_arrays,after_arrays)
            save(output/'source-contacts.json',before);save(output/'proposal-contacts.json',after)
            np.savez_compressed(output/'source-contact-observations.npz',**before_arrays)
            np.savez_compressed(output/'proposal-contact-observations.npz',**after_arrays)
            geometry,transport=geometry_audit(after_scene,derived_policy,digest,output/'geometry-observations.npz')
            geometry.update(**transport);save(output/'geometry.json',geometry)
            scene.check_inputs();after_scene.check_inputs()
            for p,snapshot in snapshots.items():
                if sha256(p)!=snapshot['sha256'] or sha256(output/snapshot['path'])!=snapshot['sha256']:
                    raise ValueError('Scene translation source or snapshot changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):
                raise ValueError('Scene translation implementation changed')
            if sha256(proposal/'contacts.json')!=digest or sha256(proposal/'policy.json')!=policy_digest:
                raise ValueError('Scene translation proposal changed')
            evidence=['source-contacts.json','proposal-contacts.json','source-contact-observations.npz',
                'proposal-contact-observations.npz','geometry.json','geometry-observations.npz','geometry-observations.npz.receipt.json']
            result=dict(status='complete',source_scene_retained=True,proposal_selected=False,
                source_snapshots=snapshots,inputs_sha256=bindings,implementation_sha256=methods,
                translation_m=offset.tolist(),maximum_contact_residual_difference_m=difference,
                clips_edited=False,world_planes_edited=False,contact_samples_pass=after['passed'],
                sampled_geometry_conditions_pass=geometry['sampled_conditions_pass'],
                proposal_contacts_sha256=digest,proposal_policy_sha256=policy_digest,
                evidence_sha256={n:sha256(output/n) for n in evidence},
                engine_playback_verified=False,continuous_collision_certified=False,
                quality_approved=False,training_admitted=False,release_approved=False,
                scope='Explicit common scene placement only. No inferred ground, mesh/animation repair, '
                    'stance fitting, continuous collision or engine/human approval; source scene retained.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',source_scene_retained=True,proposal_selected=False))
            return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),source_scene_retained=True,proposal_selected=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('contacts','policy','control','output'):parser.add_argument(n,type=Path)
    args=parser.parse_args();run(args.contacts,args.policy,args.control,args.output)
