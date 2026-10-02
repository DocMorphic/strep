"""Bridge checked native previews to the existing support fitter and back."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256


def source(identifier):
    from studio_correction_review import PREVIEWS, NAME, metadata, served_preview
    from inspect_motion import skeleton_metadata
    from rig_asset import RigAsset
    if not isinstance(identifier,str) or not NAME.fullmatch(identifier):
        raise ValueError('Choose a checked native candidate preview')
    relative=PREVIEWS+'/'+identifier+'/candidate.glb';path=served_preview(relative)
    if path is None:raise ValueError('Checked native preview is missing or changed')
    record=read(path.parent/'result.json');selection=record['selection']
    if any(record.get(k) is not False for k in ('quality_approved','training_admitted','release_approved')):
        raise ValueError('Unapproved native preview required')
    data=metadata(selection['draft_id'],selection['draft_sha256'],selection['item_id'],
                  selection['candidate_motion']['path'],selection['candidate_start_frame'])
    if data['recipe']['candidate_motion']!=selection['candidate_motion']:
        raise ValueError('Native preview candidate changed')
    for name,digest in record['methods_sha256'].items():
        if Path(name).name!=name or sha256(path.parent/'methods'/name)!=digest:
            raise ValueError('Native preview method archive changed')
    names,parents,_=skeleton_metadata(77);rig=RigAsset.load(path)
    if (rig.joints!=list(range(1,78)) or [rig.document['nodes'][j].get('name') for j in rig.joints]!=names
            or rig.parents[1]!=-1 or any(rig.parents[j+1]!=p+1 for j,p in enumerate(parents[1:],1))):
        raise ValueError('Checked native skeleton identity required')
    roles={side+part:names.index(side+part)+1 for side in ('Left','Right') for part in ('Leg','Shin','Foot')}
    from pack_native_correction import _motion,selected
    from native_candidate_preview import native_world,source_offsets
    from native_support_clock import NativeSupportSampler
    local,roots=_motion(selection['candidate_motion']['path'],selection['candidate_start_frame'],data['frames'])
    item=selected(Path(data['draft']['path']),selection['item_id'],{})
    with np.load(Path(data['draft']['path']).parent/item['source_motion'],allow_pickle=False) as archive:
        original={k:archive[k][item['source_start_frame']:item['source_end_frame_exclusive']].copy()
                  for k in ('local_rot_mats','root_positions','posed_joints','global_rot_mats')}
    expected=native_world(local.numpy(),roots.numpy(),source_offsets(original,parents),parents)
    reader=NativeSupportSampler(rig.document,rig.binary,0)
    times=np.arange(data['frames'],dtype=np.float32)/30
    if len(rig.document.get('animations',[]))!=1 or len(reader.channels)!=154 or any(c[4]!='LINEAR' or not np.array_equal(c[2],times) for c in reader.channels):
        raise ValueError('Checked native pose tracks and 30 fps clock required')
    if max(float(np.abs(reader.sample(float(t))[1:78]-expected[f]).max()) for f,t in enumerate(times))>1e-5:
        raise ValueError('Native preview differs from its bound motion')
    return None,dict(label=data['prompt'],native_review_selection=selection),None,dict(root_node=1,mapping=roles),path


def method_names():
    return ('native_review_support.py','native_motion_edit.py','native_candidate_preview.py',
            'studio_correction_review.py','pack_native_correction.py','inspect_motion.py','gltf_tools.py',
            'rig_asset.py','rig_clip_import.py','native_support_clock.py',
            'native_support_spec.py','native_support_skin.py','native_contact_diagnostics.py','native_leg_floor.py','contact_rate_path.py',
            'native_engine_clock.py','sampled_motion_caps.py','paired_temporal_neighbor.py',
            'paired_approach_basis.py','absolute_rate_peaks.py','elbow_swivel.py','two_bone_waypoint.py',
            'paired_guarded_temporal.py','native_leg_smoothing.py','native_support_peak_limits.py')


def serialized_screens(source_path, candidate_path, spec):
    """Recheck the converted GLB, not just its pre-conversion fitted neighbor."""
    from rig_asset import RigAsset
    from native_support_clock import NativeSupportSampler
    from native_support_spec import validate
    from native_support_skin import NativeSupportSkin
    from native_leg_floor import foot_region
    from contact_rate_path import ProjectedSkin
    from native_engine_clock import audit_clock
    from sampled_motion_caps import features,measures,SampledMotionCaps
    from paired_temporal_neighbor import rotation_channels
    rig=RigAsset.load(source_path);old=NativeSupportSampler(rig.document,rig.binary,0)
    candidate=RigAsset.load(candidate_path);new=NativeSupportSampler(candidate.document,candidate.binary,0)
    _,rows=validate(spec,rig,old,sha256(source_path))
    uniform=np.arange(int(np.floor(old.duration*120))+1)/120
    declared=uniform.tolist()+[t for row in rows for t in row['stance_s']+row['edit_s']]
    times=audit_clock(old.duration,[c[2] for c in old.channels],declared,rows[0]['stance_s'][0])
    before=np.array([old.sample(float(t)) for t in times]);after=np.array([new.sample(float(t)) for t in times])
    ids=np.searchsorted(times,uniform);caps=SampledMotionCaps(features(before[ids],rig.joints),uniform,np.linspace(0,uniform[-1],5))
    failed=[int(np.count_nonzero(value-cap-caps.tolerance>0)) for value,cap in zip(measures(features(after[ids],rig.joints),caps.dt),caps.caps)]
    skin=NativeSupportSkin(candidate);supports=[]
    a_channels=rotation_channels(rig.document,rig.binary);b_channels=rotation_channels(candidate.document,candidate.binary)
    for row in rows:
        heights=ProjectedSkin(skin,foot_region(skin,rig.parents,row['chain'][-1]),row['up'],row['offset']).evaluate(after).min(axis=1)
        stance=(times>=row['stance_s'][0])&(times<=row['stance_s'][1]);inside=(times>=row['edit_s'][0])&(times<=row['edit_s'][1])
        ankle=np.linalg.norm(after[:,row['chain'][-1],:3,3]-before[:,row['chain'][-1],:3,3],axis=1)
        first,last=row['edit_keys'];angle=max(float(np.rad2deg((Rotation.from_quat(a_channels[n][2][first:last+1]).inv()*Rotation.from_quat(b_channels[n][2][first:last+1])).magnitude()).max()) for n in row['chain'])
        low,high=float(heights[stance].min()),float(heights[stance].max());shift=float(ankle[inside].max())
        supports.append(dict(id=row['id'],minimum_height_m=low,maximum_lowest_height_m=high,maximum_ankle_displacement_m=shift,
            maximum_local_angle_degrees=angle,passed=bool(low>=-1e-8 and high<=row['maximum_height'] and shift<=row['displacement']+1e-7 and angle<=row['angle']+1e-4)))
    return dict(supports=supports,source_rate_failed_rows=failed,source_rates_pass=not any(failed),
                support_samples_pass=all(s['passed'] for s in supports),passed=not any(failed) and all(s['passed'] for s in supports),
                scope='Converted GLB sampled foot-region heights/edit bounds and source-relative 120 Hz motion rates; not a contact or continuous-collision certificate')


def convert(folder,request,output):
    """Only modified rotation channels get reconstructed; all other FP32 tracks copy."""
    from studio_correction_review import metadata, preview_request
    from pack_native_correction import _motion, selected
    from inspect_motion import skeleton_metadata
    from native_candidate_preview import native_world,source_offsets
    from native_motion_edit import _motion as validate_motion, _audit
    from gltf_tools import read_glb
    from native_support_clock import NativeSupportSampler
    folder,output=Path(folder),Path(output)
    selection=request['native_review_selection'];data=metadata(selection['draft_id'],selection['draft_sha256'],selection['item_id'],
                    selection['candidate_motion']['path'],selection['candidate_start_frame'])
    if data['recipe']['candidate_motion']!=selection['candidate_motion']:raise ValueError('Native support source changed')
    names,parents,_=skeleton_metadata(77)
    local,roots=_motion(selection['candidate_motion']['path'],selection['candidate_start_frame'],data['frames'])
    local,roots=local.numpy(),roots.numpy();candidate=local.copy()
    original_document,original_binary=read_glb(folder/'source.glb')
    document,binary=read_glb(output/'candidate.glb')
    if binary[:len(original_binary)]!=original_binary:raise ValueError('Support fit changed native mesh/skin payload')
    for key in ('nodes','meshes','skins','materials','images','textures'):
        if document.get(key)!=original_document.get(key):raise ValueError('Support fit changed native geometry or identities')
    old=NativeSupportSampler(original_document,original_binary,0);new=NativeSupportSampler(document,binary,0)
    if len(old.channels)!=154 or len(new.channels)!=154 or old.duration!=new.duration:
        raise ValueError('Support fit changed native channels or duration')
    expected=np.arange(data['frames'],dtype=np.float32)/30;changed=[]
    spec=read(folder/'draft.json')
    allowed={names.index(row['foot'][:-4]+part)+1 for row in spec['supports'] for part in ('Leg','Shin','Foot')}
    for prior,current in zip(old.channels,new.channels):
        if prior[:2]!=current[:2] or prior[4]!='LINEAR' or current[4]!='LINEAR' or not np.array_equal(prior[2],current[2]) or not np.array_equal(prior[2],expected):
            raise ValueError('Support fit changed the native 30 fps clock')
        node,kind=prior[:2]
        if kind=='translation':
            if not np.array_equal(prior[3],current[3]):raise ValueError('Support fit changed native translations')
        elif kind=='rotation' and not np.array_equal(prior[3],current[3]):
            if node not in allowed:raise ValueError('Support fit changed a joint outside its explicit leg chains')
            altered=np.any(current[3]!=prior[3],axis=1)
            candidate[altered,node-1]=Rotation.from_quat(current[3][altered]).as_matrix();changed.append(names[node-1])
        elif kind!='rotation':raise ValueError('Unknown native pose channel')
    inputs={};item=selected(Path(data['draft']['path']),selection['item_id'],inputs)
    with np.load(Path(data['draft']['path']).parent/item['source_motion'],allow_pickle=False) as archive:
        original={k:archive[k][item['source_start_frame']:item['source_end_frame_exclusive']].copy()
                  for k in ('local_rot_mats','root_positions','posed_joints','global_rot_mats')}
    offsets=source_offsets(original,parents);validate_motion(candidate,roots)
    fit=read(output/'result.json');retained=fit['retained_input'];reason=fit['retention_reason'];error=None
    try:bounds=_audit(original['local_rot_mats'],original['root_positions'],candidate,roots)
    except ValueError as exc:
        error=str(exc);bounds=None;retained=True;reason='native_original_relative_bounds_failed'
    world=native_world(candidate,roots,offsets,parents)
    proposal=folder/'native-proposal.npz'
    np.savez(proposal,local_rot_mats=candidate,root_positions=roots,posed_joints=world[:,:,:3,3].astype(np.float32),global_rot_mats=world[:,:,:3,:3].astype(np.float32))
    # Independently compare native reconstruction with the serialized fitter GLB.
    maximum=0.
    for f,t in enumerate(expected):maximum=max(maximum,float(np.abs(new.sample(float(t))[1:78]-world[f]).max()))
    if maximum>1e-5:raise ValueError('Native support conversion differs from fitted GLB')
    proposal_preview=None;screens=None;proposal_contacts=None
    if not retained:
        proposal_preview=preview_request(dict(selection,candidate_motion=dict(path=str(proposal.resolve()),sha256=sha256(proposal)),candidate_start_frame=0))
        from studio_correction_review import served_preview
        checked=served_preview(proposal_preview['preview_url'].removeprefix('/files/'))
        if checked is None:raise ValueError('Converted proposal preview unavailable')
        screens=serialized_screens(folder/'source.glb',checked,spec)
        from native_contact_diagnostics import measure
        proposal_contacts=measure(folder/'source.glb',checked,spec)
        if not screens['passed']:retained=True;reason='native_serialized_support_screens_failed'
    chosen_local=local if retained else candidate
    chosen_world=native_world(chosen_local,roots,offsets,parents)
    path=folder/'native-candidate.npz'
    np.savez(path,local_rot_mats=chosen_local,root_positions=roots,posed_joints=chosen_world[:,:,:3,3].astype(np.float32),global_rot_mats=chosen_world[:,:,:3,:3].astype(np.float32))
    checked_local,checked_roots=_motion(path,0,data['frames'])
    if not np.array_equal(checked_local.numpy(),chosen_local) or not np.array_equal(checked_roots.numpy(),roots):
        raise ValueError('Native support candidate failed exact serialization')
    ref=dict(path=str(path.resolve()),sha256=sha256(path))
    chosen=dict(selection,candidate_motion=ref,candidate_start_frame=0)
    preview=preview_request(chosen)
    from studio_correction_review import served_preview
    checked=served_preview(preview['preview_url'].removeprefix('/files/'))
    if checked is None:raise ValueError('Converted selected preview unavailable')
    selected_screens=serialized_screens(folder/'source.glb',checked,spec)
    if not retained and not selected_screens['passed']:raise ValueError('Selected native support serialization failed its independent screens')
    from native_contact_diagnostics import measure
    selected_contacts=measure(folder/'source.glb',checked,spec)
    events=folder/'native-support-events.json'
    save(events,dict(source='Explicit authored stance intervals, not measured contact force',
        target_clip_sha256=preview['preview_sha256'],
        constraint_status='satisfied_at_samples' if selected_screens['passed'] else 'unverified_on_retained_input',
        intervals=[dict(id=row['id'],foot=row['foot'],start_s=row['stance_s'][0],end_s=row['stance_s'][1]) for row in spec['supports']],
        quality_approved=False))
    report=dict(schema='strep-native-support-conversion-v1',selection=selection,candidate_motion=ref,
                candidate_start_frame=0,frames=data['frames'],changed_joints=changed,retained_input=retained,
                retention_reason=reason,native_bounds=bounds,native_bound_error=error,
                max_fitted_glb_matrix_error=maximum,preview=preview,
                fitted_support_samples_pass=fit['output_support_samples_pass'],
                proposal_preview=proposal_preview,proposal_serialized_screens=screens,selected_serialized_screens=selected_screens,
                selected_support_samples_pass=selected_screens['support_samples_pass'],
                selected_contact_diagnostics=selected_contacts,proposal_contact_diagnostics=proposal_contacts,
                selected_support_events=dict(path=str(events.resolve()),sha256=sha256(events)),
                proposal=dict(path=str(proposal.resolve()),sha256=sha256(proposal)),
                quality_approved=False,training_admitted=False,release_approved=False,
                scope='Native geometry conversion and inherited sampled support screens; no planted-contact, physics or human approval')
    save(folder/'native-conversion.json',report);return report
