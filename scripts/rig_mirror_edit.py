"""Studio adapter: preserve source, mirror a finite clip, invalidate scene intent."""
import copy
import shutil
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now
from rig_contact_authoring import source
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_mirror import draft_correspondence,validate_recipe,write_clip,annotations,correspondence


def metadata(job_id,variant):
    folder,result,request,report,glb=source(job_id,variant)
    rig=RigAsset.load(glb);mapping=report['mapping'];root=report['root_node']
    if root!=mapping['Hips']:raise ValueError('Mapped pelvis and source root disagree')
    pairs=draft_correspondence(rig,mapping)
    normal=rig.reference[mapping['LeftLeg'],:3,3]-rig.reference[mapping['RightLeg'],:3,3];normal[1]=0
    if np.linalg.norm(normal)<1e-6:raise ValueError('Reference thighs do not define a lateral plane')
    normal/=np.linalg.norm(normal)
    point=AnimationSampler(rig.document,rig.binary,0).sample(0)[root,:3,3]
    recipe=dict(schema='strep-rig-mirror-v1',source_sha256=sha256(glb),frames=report['frames'],fps=report['fps'],root_node=root,
        counterparts=pairs,plane_normal=normal.tolist(),plane_point=point.tolist(),label=('Mirror · '+result['label'])[:160])
    validate_recipe(glb,recipe)
    names={str(n):rig.document['nodes'][n].get('name','Bone '+str(n)) for n in map(int,pairs)}
    return dict(job_id=job_id,variant=variant,recipe=recipe,names=names,
        scope='Whole clip, unchanged timing. Default plane passes through the starting pelvis and follows the reference thighs. Verify bone pairs and plane before applying. Scene targets need re-authoring; events need review. Loop runtime is not carried forward.')


def sidecar(folder,glb,name):
    path=glb.parent/name
    return path if path.exists() else folder/'transfer'/name


def validate(payload):
    if not isinstance(payload,dict) or set(payload)!={'source_job','variant','recipe'}:raise ValueError('Choose source, version and mirror recipe')
    previous,result,request,report,glb=source(payload['source_job'],payload['variant']);recipe=payload['recipe']
    rig,_=validate_recipe(glb,recipe)
    if (recipe['frames'],recipe['fps'],recipe['root_node'])!=(report['frames'],report['fps'],report['root_node']):raise ValueError('Mirror clock or root differs from selected clip')
    contacts=read(sidecar(previous,glb,'contacts.json'));event_path=sidecar(previous,glb,'events.json')
    events=read(event_path) if event_path.exists() else dict(fps=30,events=[])
    annotations(contacts,events,recipe['frames'],correspondence(rig,recipe['root_node'],recipe['counterparts']),recipe['source_sha256'])
    return previous,request,report,glb,copy.deepcopy(recipe)


def prepare(payload,folder):
    previous,original,report,glb,recipe=validate(payload);folder=Path(folder);folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source',folder/'source',ignore=shutil.ignore_patterns('implementation'))
    dest=folder/'input';dest.mkdir();shutil.copyfile(glb,dest/'character.glb')
    for name in ('inventory.json','rig-profile.json','contacts.json','root-motion.json','events.json','timeline.json','contact-review.json'):
        path=sidecar(previous,glb,name)
        if path.exists():shutil.copyfile(path,dest/name)
    spec=previous/'input/contact-spec.json' if payload['variant']=='input' else previous/'contact-spec.json'
    if spec.exists():shutil.copyfile(spec,dest/'contact-spec.json')
    source_name='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/source_name).resolve()),character=str((folder/'source/character.glb').resolve()))
    if report.get('timeline_edited'):report['contact_annotations_file']=str((dest/'contacts.json').resolve())
    save(dest/'report.json',report);save(folder/'mirror.json',recipe)
    request=dict(kind='mirror_edit',label=recipe['label'],asset_id=original['asset_id'],profile_id=sha256(folder/'source/rig-profile.json'),
        source_kind=report.get('source_kind','soma_motion'),source_motion_sha256=sha256(folder/'source'/source_name),correct_contacts=False,
        source_job=previous.name,input_variant=payload['variant'],input_glb_sha256=sha256(glb),mirror_sha256=sha256(folder/'mirror.json'),
        input_sidecar_sha256={p.name:sha256(p) for p in dest.iterdir() if p.is_file()})
    save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'));return request


def run(folder):
    folder=Path(folder);request=read(folder/'request.json');recipe=read(folder/'mirror.json');input=folder/'input';out=folder/'transfer'
    if sha256(folder/'mirror.json')!=request['mirror_sha256']:raise ValueError('Mirror recipe changed')
    for name,digest in request['input_sidecar_sha256'].items():
        if sha256(input/name)!=digest:raise ValueError('Mirror input snapshot changed: '+name)
    report=read(input/'report.json')
    write_clip(input/'character.glb',recipe,out,input/'contacts.json',input/'events.json' if (input/'events.json').exists() else None)
    for name in ('inventory.json','rig-profile.json'):shutil.copyfile(input/name,out/name)
    contact=read(out/'contacts.json');contact.setdefault('origin','none_supplied' if report.get('source_kind')=='gltf_animation' else 'source_model_predictions');save(out/'contacts.json',contact)
    audit=read(out/'audit.json');check=audit['export']
    retained=('character','character_sha256','source','source_sha256','source_kind','profile_sha256','frames','fps','last_key_time_s','sample_coverage_s','root_node','mapping')
    report={k:report[k] for k in retained if k in report}
    report.update(created_at=now(),implementation_sha256=sha256(__file__),mirror_implementation_sha256=sha256(Path(__file__).with_name('rig_mirror.py')),
        input_report_sha256=sha256(input/'report.json'),animation_name=recipe['label'],human_approved=False,engine_import=None,
        glb_sha256=sha256(out/'character.glb'),edit_parent_glb_sha256=sha256(input/'character.glb'),
        target_mesh_floor_depth_max_m=check['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=check['floor_frames_above_1cm'],
        roundtrip_max_matrix_error=check['matrix_error'],roundtrip_max_vertex_error_m=check['skin_error_m'],
        timeline_edited=True,contact_annotations_file=str((out/'contacts.json').resolve()),contact_annotations_sha256=sha256(out/'contacts.json'),
        mirror_scope=audit['scope'],scene_targets_status='Source targets retained under input only. Re-author for mirrored action.',loop_status='Finite clip. Previous periodic runtime contract not transferred.')
    save(out/'report.json',report)
    save(out/'timeline.json',dict(frames=recipe['frames'],fps=30,source_frames=list(range(recipe['frames'])),input_sha256=recipe['source_sha256'],operation='mirror_motion',timing_changed=False,source_timeline_retained=(input/'timeline.json').exists()))
    audit.update(source_job=request['source_job'],input_variant=request['input_variant'],recipe_sha256=request['mirror_sha256'],
        retained_source_targets=[name for name in ('contact-spec.json','contact-review.json') if (input/name).exists()])
    save(out/'audit.json',audit);return report,audit
