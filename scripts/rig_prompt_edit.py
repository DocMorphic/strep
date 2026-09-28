"""Finite target-rig section regeneration with unchanged surrounding poses."""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from rig_contact_authoring import source
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize,compose,blend
from rig_loop import encode


def weights(count,blend_frames):
    t=np.minimum(np.arange(count),np.arange(count)[::-1]);u=np.clip((t-1)/(blend_frames-2),0,1)
    return u*u*(3-2*u)


def review_info(audit):
    guides=audit['raw_anchor_audit']
    return dict(raw_guides_passed=guides['numerical_screen_passed'],raw_anchor_error_m=max(g['maximum'].get('joint_position_error_m',0.) for g in guides['guides']),floor_failed_frames=audit['export']['floor_failed_frames'],preserved_frames=audit['unchanged_frames'],scope='Raw model guides and sampled splice diagnostics; preservation is not semantic or physical approval')


def validate(payload):
    if not isinstance(payload,dict) or set(payload)!={'source_job','variant','edit'}:raise ValueError('Choose source, version and regeneration recipe')
    snapshot=source(payload['source_job'],payload['variant']);report=snapshot[3];glb=snapshot[4];edit=payload['edit']
    if not isinstance(edit,dict) or set(edit)!={'schema','glb_sha256','label','prompt','start_frame','last_frame','blend_frames','seed'} or edit['schema']!='strep-rig-prompt-edit-v1':raise ValueError('Invalid regeneration recipe')
    if edit['glb_sha256']!=sha256(glb):raise ValueError('Regeneration source changed')
    a,b,k=(edit[n] for n in ('start_frame','last_frame','blend_frames'))
    if any(type(v) is not int for v in (a,b,k)) or not 0<=a<b<report['frames'] or not 30<=b-a+1<=270 or not 4<=k or 2*k>=b-a+1:raise ValueError('Choose 30–270 frames and nonoverlapping blends of at least four frames')
    if not isinstance(edit['label'],str) or not 1<=len(edit['label'])<=160:raise ValueError('Name the regenerated clip')
    if not isinstance(edit['prompt'],str) or not 1<=len(edit['prompt'].strip())<=1000 or not any(c.isalnum() for c in edit['prompt']):raise ValueError('Describe the replacement action')
    if type(edit['seed']) is not int or not 0<=edit['seed']<2**32:raise ValueError('Use a nonnegative 32-bit seed')
    timeline=glb.parent/'timeline.json'
    if timeline.exists() and 'period_frames' in read(timeline):raise ValueError('Regenerate a finite source before making a loop; periodic section regeneration is not yet supported')
    return snapshot


def prepare(payload,folder):
    previous,_,original,report,glb=validate(payload);folder=Path(folder);folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source',folder/'source',ignore=shutil.ignore_patterns('implementation'))
    target=folder/'input';target.mkdir();shutil.copyfile(glb,target/'character.glb')
    metadata=glb.parent if (glb.parent/'inventory.json').exists() else previous/'transfer'
    for name in ('inventory.json','rig-profile.json','contacts.json','events.json','timeline.json','contact-review.json'):
        if (metadata/name).exists():shutil.copyfile(metadata/name,target/name)
    shutil.copyfile(glb.parent/'root-motion.json',target/'root-motion.json')
    source_name='character.glb' if report.get('source_kind')=='gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/source_name).resolve()),character=str((folder/'source/character.glb').resolve()))
    if report.get('timeline_edited'):report['contact_annotations_file']=str((target/'contacts.json').resolve())
    save(target/'report.json',report);save(folder/'prompt-edit.json',payload['edit'])
    spec=previous/'input/contact-spec.json' if payload['variant']=='input' else previous/'contact-spec.json'
    if spec.exists():shutil.copyfile(spec,target/'contact-spec.json')
    history=folder/'source/prompt-history'/folder.name;history.mkdir(parents=True);shutil.copytree(target,history/'input');shutil.copyfile(folder/'prompt-edit.json',history/'prompt-edit.json')
    request=dict(kind='prompt_edit',label=payload['edit']['label'],asset_id=original['asset_id'],profile_id=sha256(folder/'source/rig-profile.json'),source_kind=report.get('source_kind','soma_motion'),source_motion_sha256=sha256(folder/'source'/source_name),correct_contacts=False,input_glb_sha256=sha256(glb),recipe_sha256=sha256(folder/'prompt-edit.json'))
    save(folder/'request.json',request);save(folder/'pipeline.json',dict(status='starting'));return request


def run(folder):
    import torch
    from kimodo.skeleton import SOMASkeleton77
    from kimodo.constraints import compute_heading_angle
    from rig_motion_bridge import to_soma
    from retarget_rig import transfer,resolve_profile
    from inspect_motion import validate_motion
    from rig_contact_tracks import signals,ROLES
    from rig_events import load as load_events
    folder=Path(folder);request=read(folder/'request.json');edit=read(folder/'prompt-edit.json');report=read(folder/'input/report.json')
    if sha256(folder/'input/character.glb')!=request['input_glb_sha256'] or sha256(folder/'prompt-edit.json')!=request['recipe_sha256']:raise ValueError('Regeneration snapshot changed')
    rig=RigAsset.load(folder/'input/character.glb');reference=RigAsset.load(folder/'source/character.glb');profile=read(folder/'source/rig-profile.json');sampler=AnimationSampler(rig.document,rig.binary,0)
    before=np.array([sampler.sample(float(np.float32(f/30))) for f in range(report['frames'])]);a,b,k=(edit[n] for n in ('start_frame','last_frame','blend_frames'));n=b-a+1
    bridge,bridge_audit=to_soma(reference,profile,before[a:b+1]);origin=bridge['root_positions'][0].copy();origin[1]=0
    for key in ('root_positions','posed_joints'):bridge[key]=bridge[key]-origin
    guide_path=folder/'source/guide-motion.npz';np.savez_compressed(guide_path,**bridge);save(folder/'source/guide-audit.json',bridge_audit)
    skeleton=SOMASkeleton77();heading=float(compute_heading_angle(torch.from_numpy(bridge['posed_joints'][:1]),skeleton)[0])
    anchors=[0,1,n-2,n-1]
    generation=folder/'generation';generation.mkdir()
    batch=dict(schema_version=1,requests=[dict(id='replacement',label=edit['label'][:120],segments=[dict(prompt=edit['prompt'],duration_s=n/30)],seeds=[edit['seed']],first_heading_angle=heading,generation_constraints=[dict(type='fullbody',motion=guide_path.relative_to(ROOT).as_posix(),sha256=sha256(guide_path),source_frames=anchors,frame_indices=anchors)])])
    save(generation/'request.json',batch)
    from reuse_action_conditioning import reuse
    reused=reuse(batch,generation/'conditioning')
    save(folder/'pipeline.json',dict(status='processing',stage='Regenerating selected section with boundary pose guides',conditioning_reused=reused))
    from run_actions import run as generate
    generate(generation/'request.json',generation)
    raw=generation/'takes'/f'replacement-seed-{edit["seed"]}'/'motion.npz';generated=dict(np.load(raw,allow_pickle=False))
    for key in ('root_positions','posed_joints','smooth_root_pos'):
        if key in generated:generated[key]=generated[key]+origin
    validate_motion(generated,30);np.savez_compressed(generation/'aligned-generated.npz',**generated)
    history=folder/'source/prompt-history'/folder.name
    shutil.copytree(generation,history/'generation');shutil.copyfile(guide_path,history/'guide-motion.npz');shutil.copyfile(folder/'source/guide-audit.json',history/'guide-audit.json')
    mapping,offset=resolve_profile(reference,profile)
    replacement,_,_,_,transfer_diagnostic=transfer(reference,generated,skeleton,mapping,offset,profile.get('axis_alignment_xyzw'),context_local=localize(before[a:b+1],rig.parents))
    w=weights(n,k);local=localize(before,rig.parents);local[a:b+1]=blend(local[a:b+1],localize(replacement,rig.parents),w);after=compose(local,rig.parents)
    out=folder/'transfer';out.mkdir();animated={c[0] for c in sampler.channels}|set(mapping.values())
    times,roundtrip=encode(rig,after,animated,report['root_node'],out/'character.glb',edit['label'])
    full_weights=np.zeros(len(before));full_weights[a:b+1]=w;changed=full_weights>0
    root=report['root_node'];save(out/'root-motion.json',dict(node=root,space='Selected target pelvis world transform; unchanged outside the edit envelope',times_s=times.tolist(),positions_m=after[:,root,:3,3].tolist(),rotations_xyzw=Rotation.from_matrix(after[:,root,:3,:3]).as_quat().tolist()))
    original,origin_kind=signals(report);_,_,labels=validate_motion(generated,30);intervals=[];ambiguous=[]
    for role in ROLES:
        prediction=generated['foot_contacts'][:,labels.index(role)]>=.5 if role in labels else np.zeros(n,bool)
        active=original[role].copy()
        for i in range(n):
            f=a+i
            if w[i]==1:active[f]=prediction[i]
            elif w[i]>0:
                if bool(active[f])!=bool(prediction[i]):ambiguous.append(dict(frame=f,joint=role))
                active[f]=bool(active[f] and prediction[i])
        edges=np.diff(np.r_[False,active,False].astype(int))
        intervals.extend(dict(joint=role,start_frame=int(x),end_frame_exclusive=int(y),start_seconds=x/30,end_seconds_exclusive=y/30) for x,y in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)))
    save(out/'contacts.json',dict(origin='regenerated_source_predictions',source_origins=[origin_kind,'source_model_predictions'],intervals=intervals,ambiguous_support_frames=ambiguous,scope='Original predictions outside the edit, generated predictions in its full-weight interior, conservative intersection during blends. Unknown source support remains unknown; no physical contact approval.'))
    events=load_events(folder/'input')
    for e in events['events']:
        if changed[e['frame']]:e.update(requires_review=True,regeneration_review='Pose changed at the marked frame; semantic intent must be reviewed')
    save(out/'events.json',events)
    clock=[[dict(source=0,frame=f,weight=float(1-full_weights[f]))]+([dict(source=1,frame=f-a,weight=float(full_weights[f]))] if changed[f] else []) for f in range(len(before))]
    save(out/'timeline.json',dict(fps=30,frames=len(before),contributors=clock,source_glb_sha256=request['input_glb_sha256'],generated_motion_sha256=sha256(raw),regeneration=dict(start_frame=a,last_frame=b,blend_frames=k,weights=w.tolist()),scope='Fixed source clock. Raw model result retained separately; source endpoint neighborhoods restored explicitly.'))
    if (folder/'input/contact-review.json').exists():
        review=read(folder/'input/contact-review.json');review.update(requires_review=True,regenerated_frames=np.flatnonzero(changed).tolist());save(out/'contact-review.json',review)
    for name in ('inventory.json','rig-profile.json'):shutil.copyfile(folder/'input'/name,out/name)
    report.update(glb_sha256=sha256(out/'character.glb'),timeline_edited=True,contact_annotations_file=str((out/'contacts.json').resolve()),contact_annotations_sha256=sha256(out/'contacts.json'),target_mesh_floor_depth_max_m=roundtrip['floor_depth_max_m'],target_mesh_floor_frames_above_1cm=roundtrip['floor_frames_above_1cm'])
    save(out/'report.json',report)
    if (folder/'input/contact-spec.json').exists():shutil.copyfile(folder/'input/contact-spec.json',folder/'contact-spec.json')
    audit=dict(created_at=now(),bridge=bridge_audit,origin_offset_m=origin.tolist(),first_heading_angle=heading,range=[a,b],blend_frames=k,unchanged_frames=int((~changed).sum()),surrounding_matrix_error=float(np.abs(after[~changed]-before[~changed]).max()),raw_anchor_audit=read(raw.parent/'constraint-audit.json'),export=roundtrip,raw_motion_sha256=sha256(raw),human_approved=False,scope='Prompt-conditioned replacement plus explicit geodesic splice, not a trained source-text editor or semantic/physical approval. Outside-envelope poses and two samples at each boundary retained. Source anatomy conversion is approximate.')
    audit['transfer_context']=transfer_diagnostic
    save(out/'prompt-edit-audit.json',audit);return report,audit
