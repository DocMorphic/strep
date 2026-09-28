"""Studio adapter for immutable, mapped-hand posture edits."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read,save,sha256,now
from rig_asset import RigAsset
from rig_contact_authoring import source
from hand_posture import validate as validate_posture,run as author


def hands(rig,mapping):
    result=[]
    for role in ('LeftHand','RightHand'):
        root=mapping.get(role)
        if root not in rig.joints:continue
        fingers=[]
        for n in rig.joints:
            p=rig.parents[n]
            while p>=0 and p!=root:p=rig.parents[p]
            if p==root:
                from gltf_tools import local_matrix
                q=Rotation.from_matrix(local_matrix(rig.document['nodes'][n])[:3,:3]).as_quat()
                fingers.append(dict(node=n,label=rig.document['nodes'][n].get('name',f'Bone {n}'),reference_xyzw=q.tolist()))
        if fingers:result.append(dict(role=role,node=root,joints=fingers))
    return result


def metadata(job_id,variant):
    folder,result,request,report,glb=source(job_id,variant)
    profile=read(folder/'source/rig-profile.json')
    if sha256(folder/'source/rig-profile.json')!=request['profile_id']:raise ValueError('Saved mapping changed')
    return dict(job_id=job_id,variant=variant,glb_sha256=sha256(glb),frames=report['frames'],fps=report['fps'],
        hands=hands(RigAsset.load(glb),profile['mapping']))


def validate(payload):
    if not isinstance(payload,dict) or set(payload)!={'source_job','variant','label','posture'}:raise ValueError('Choose a source clip, version, name and posture')
    if not isinstance(payload['label'],str) or not 1<=len(payload['label'].strip())<=160:raise ValueError('Name the hand posture edit')
    previous,result,request,report,glb=source(payload['source_job'],payload['variant'])
    meta=metadata(payload['source_job'],payload['variant']);recipe=payload['posture']
    validate_posture(recipe,RigAsset.load(glb),meta['glb_sha256'])
    if recipe['frames']!=meta['frames'] or recipe['fps']!=meta['fps']:raise ValueError('Posture clock differs from selected clip')
    if not set(recipe['hand_roots'])<=set(h['node'] for h in meta['hands']):raise ValueError('Hand roots must match the saved character mapping')
    return previous,request,report,glb,copy.deepcopy(recipe)


def prepare(payload,folder):
    previous,original,report,glb,recipe=validate(payload);folder=Path(folder);folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source',folder/'source',ignore=shutil.ignore_patterns('implementation'))
    dest=folder/'input';dest.mkdir();shutil.copyfile(glb,dest/'character.glb')
    fallback=previous/'transfer'
    for name in ('inventory.json','rig-profile.json','contacts.json','root-motion.json','events.json','timeline.json','contact-review.json'):
        path=glb.parent/name
        if not path.exists():path=fallback/name
        if path.exists():shutil.copyfile(path,dest/name)
    prior_spec=previous/'input/contact-spec.json' if payload['variant']=='input' else previous/'contact-spec.json'
    if prior_spec.exists():shutil.copyfile(prior_spec,dest/'contact-spec.json')
    source_name='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/source_name).resolve()),character=str((folder/'source/character.glb').resolve()))
    if report.get('timeline_edited'):report['contact_annotations_file']=str((dest/'contacts.json').resolve())
    save(dest/'report.json',report);save(folder/'hand-posture.json',recipe)
    request=dict(kind='posture_edit',label=payload['label'].strip(),asset_id=original['asset_id'],profile_id=sha256(folder/'source/rig-profile.json'),
        source_kind=report.get('source_kind','soma_motion'),source_motion_sha256=sha256(folder/'source'/source_name),correct_contacts=False,
        source_job=previous.name,input_variant=payload['variant'],input_glb_sha256=sha256(glb),posture_sha256=sha256(folder/'hand-posture.json'))
    save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'));return request


def run(folder):
    folder=Path(folder);request=read(folder/'request.json');recipe=read(folder/'hand-posture.json');input=folder/'input';out=folder/'transfer'
    if sha256(input/'character.glb')!=request['input_glb_sha256'] or sha256(folder/'hand-posture.json')!=request['posture_sha256']:raise ValueError('Posture snapshot changed')
    report=read(input/'report.json');rig=RigAsset.load(input/'character.glb')
    mapping=read(folder/'source/rig-profile.json')['mapping']
    if not set(recipe['hand_roots'])<=set(h['node'] for h in hands(rig,mapping)):raise ValueError('Posture mapping changed')
    world=author(input/'character.glb',recipe,out)
    from rig_clip_import import AnimationSampler
    times=np.arange(recipe['frames'],dtype=np.float32)/30
    original=AnimationSampler(rig.document,rig.binary,0)
    before=np.array([original.sample(float(t)) for t in times])
    # Independent body/root preservation before retaining the original root sidecar.
    selected=set(t['node'] for p in recipe['poses'] for t in p['targets'])
    affected=set(selected)
    for n in range(len(rig.parents)):
        p=rig.parents[n]
        while p>=0:
            if p in selected:affected.add(n);break
            p=rig.parents[p]
    body=[n for n in range(len(rig.parents)) if n not in affected]
    body_error=float(np.abs(world[:,body]-before[:,body]).max())
    if report['root_node'] in affected or body_error>1e-5:raise ValueError('Posture changed protected body/root motion')
    sidecars={}
    for name in ('inventory.json','rig-profile.json','root-motion.json','contacts.json','events.json','timeline.json','contact-review.json'):
        if (input/name).exists():
            shutil.copyfile(input/name,out/name);sidecars[name]=sha256(out/name)
    minimum_y=[float(rig.vertices(frame)[:,1].min()) for frame in world]
    floor=[max(0.,-v) for v in minimum_y]
    np.savez_compressed(out/'target-transforms.npz',global_matrices=world,times_s=times)
    # Source reports may carry old solver success/roundtrip/contact metrics. Keep
    # that history under input/, never relabel it as this candidate's evidence.
    retained=('character','character_sha256','source','source_sha256','source_kind','profile_sha256',
        'frames','fps','last_key_time_s','sample_coverage_s','root_node','mapping','timeline_edited')
    report={k:report[k] for k in retained if k in report}
    audit=read(out/'verification.json')
    report.update(created_at=now(),implementation_sha256=sha256(__file__),posture_implementation_sha256=sha256(Path(__file__).with_name('hand_posture.py')),
        input_report_sha256=sha256(input/'report.json'),animation_name='Authored hand posture',
        roundtrip_max_matrix_error=audit['roundtrip']['matrix_error'],roundtrip_max_vertex_error_m=audit['roundtrip']['skin_error_m'],
        target_mesh_min_y_m=min(minimum_y),limitations=['Authored local finger rotations; no anatomical or contact validity established.',
        'Source diagnostics remain in input/report.json. Ground inspection is recomputed for this candidate.',
        'Input root and annotation timing retained. Gameplay timing confirmation does not verify contact.'])
    report.update(glb_sha256=sha256(out/'character.glb'),edit_parent_glb_sha256=sha256(input/'character.glb'),
        target_mesh_floor_depth_max_m=max(floor),target_mesh_floor_frames_above_1cm=sum(v>.01 for v in floor),
        hand_posture_authored=True,human_approved=False,engine_import=None,
        posture_contact_status='Unverified: prior annotations and event timing retained as provenance; finger/object contact must be reviewed.')
    if report.get('timeline_edited'):report.update(contact_annotations_file=str((out/'contacts.json').resolve()),contact_annotations_sha256=sha256(out/'contacts.json'))
    if (input/'contact-spec.json').exists():
        spec=read(input/'contact-spec.json');spec['glb_sha256']=report['glb_sha256']
        spec['provenance']=spec.get('provenance','')+' Targets retained after a hand posture edit; fitting and physical contact require renewed review.'
        save(folder/'contact-spec.json',spec)
    save(out/'report.json',report)
    audit.update(protected_body_world_max_error=body_error,preserved_sidecar_sha256=sidecars,
        source_job=request['source_job'],recipe_sha256=request['posture_sha256'],
        sidecar_scope='Unchanged timeline/root/annotation bytes. Existing timing confirmation is retained; no contact, loop-runtime or anatomical approval is conferred.')
    if (folder/'contact-spec.json').exists():audit['retained_contact_targets']=dict(input_sha256=sha256(input/'contact-spec.json'),output_sha256=sha256(folder/'contact-spec.json'),requires_refit_and_review=True)
    save(out/'verification.json',audit);return report,audit
