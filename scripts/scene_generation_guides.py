"""Explicit sparse scene guidance; complete contact audits keep their clock.

This plans samples from supplied fitted poses. It does not fit a pose, infer
object/partner awareness, or certify that sparse targets are feasible.
"""
import copy
import json
from pathlib import Path
from generation_constraints import EFFECTORS
from strep import ROOT, read, sha256

MAXIMUM_SPARSE_FRAMES = 19
SCHEMA = 'strep-scene-generation-guide-plan-v1'


def plan_frames(scene, actor, options=None):
    """Keep every interval boundary and effector-set change before spacing.

    Omitting options preserves historical dense guidance. Sparse selection is
    explicit, limited to actual contact frames, and never changes scene intent.
    """
    count = scene.get('frame_count')
    if type(count) is not int or not 3 <= count <= 1800 or actor not in scene['actors']:
        raise ValueError('Declared actor and complete scene clock required')
    contacts = scene.get('contacts')
    if not isinstance(contacts, list) or not 1 <= len(contacts) <= 4096:
        raise ValueError('Complete bounded contact population required')
    calendar = {}; mandatory = set(); intervals = []
    for index, contact in enumerate(contacts):
        joints = []
        if contact['actor'] == actor:
            joints.append(contact['effector'].get('joint'))
        target = contact['target']
        if target.get('space') == 'actor' and target.get('actor') == actor:
            joints.append(target.get('joint'))
        if not joints:
            continue
        if any(j not in EFFECTORS for j in joints):
            raise ValueError('Scene generation guides support hands and feet only')
        start, end = contact['start_frame'], contact['end_frame']
        if type(start) is not int or type(end) is not int or not 0 <= start <= end < count:
            raise ValueError('Contact interval outside scene')
        intervals.append(dict(contact_index=index, contact_id=contact.get('id'),
                              start_frame=start, end_frame=end, joint_names=sorted(set(joints))))
        mandatory.update([start, end])
        for frame in range(start, end + 1):
            calendar.setdefault(frame, set()).update(joints)
    if not calendar:
        raise ValueError('Scene actor needs at least one hand/foot contact pose')
    available = sorted(calendar)
    for previous, current in zip(available, available[1:]):
        if current != previous + 1 or calendar[previous] != calendar[current]:
            mandatory.update([previous, current])
    if options is None:
        selected = available; mode = 'dense'; maximum = None
    else:
        if (not isinstance(options, dict) or options.get('mode') != 'sparse'
                or set(options) - {'mode', 'maximum_frames', 'frame_indices'}):
            raise ValueError('Explicit sparse guide_plan required')
        maximum = options.get('maximum_frames', MAXIMUM_SPARSE_FRAMES)
        if type(maximum) is not int or not 1 <= maximum <= MAXIMUM_SPARSE_FRAMES:
            raise ValueError('Sparse guide budget must be 1–19 frames')
        if len(mandatory) > maximum:
            raise ValueError('Guide budget cannot retain all contact boundaries and effector changes')
        if 'frame_indices' in options:
            selected = options['frame_indices']
            if (not isinstance(selected, list) or not 1 <= len(selected) <= maximum
                    or any(type(f) is not int or f not in calendar for f in selected)
                    or selected != sorted(set(selected)) or not mandatory <= set(selected)):
                raise ValueError('Explicit guide frames must retain every boundary/change inside the contact clock')
            selected = selected.copy()
        else:
            chosen = set(mandatory)
            while len(chosen) < min(maximum, len(available)):
                # Farthest temporal sample, with earliest-frame ties. Values are
                # supplied poses; no interpolation or target inference occurs.
                frame = max((f for f in available if f not in chosen),
                            key=lambda f: (min(abs(f-s) for s in chosen), -f))
                chosen.add(frame)
            selected = sorted(chosen)
        mode = 'sparse'
    return dict(actor=actor, mode=mode, maximum_frames=maximum,
                complete_target_frames=available, selected_frames=selected,
                mandatory_frames=sorted(mandatory), contact_intervals=intervals,
                effectors_by_frame={str(f): sorted(calendar[f]) for f in available},
                within_sparse_recommendation=len(selected) <= MAXIMUM_SPARSE_FRAMES,
                guidance_sampling_only=True, full_scene_contact_intervals_unchanged=True,
                quality_approved=False, release_approved=False)


def guides_from_plan(scene, actor, record):
    """Combine simultaneous effectors into one root-compatible pose guide."""
    entry = scene['actors'][actor]; groups = {}
    for frame in record['selected_frames']:
        joints = tuple(record['effectors_by_frame'][str(frame)])
        groups.setdefault(joints, []).append(frame)
    return [dict(type='end-effector', joint_names=list(joints), motion=entry['motion'],
                 sha256=entry['source_sha256'], source_frames=indices.copy(), frame_indices=indices.copy())
            for joints, indices in groups.items()]


def validate_actor_plan(scene, plan):
    """Validate arbitrary prompt schedules without importing a model runtime."""
    from action_requests import validate_request
    if (not isinstance(plan, dict) or set(plan) != set(scene['actors'])
            or any(not isinstance(entry, dict) for entry in plan.values())):
        raise ValueError('Guide plan must cover every scene actor')
    for entry in plan.values():
        if not {'segments','seeds'} <= set(entry) or set(entry)-{'segments','seeds','guide_plan'}:
            raise ValueError('Actor plan requires segments, seeds and optional guide_plan')
        validate_request(dict(id='scene-guide-plan',label='Scene guide plan',
                              segments=entry['segments'],seeds=entry['seeds']))
        if sum(round(segment['duration_s']*30) for segment in entry['segments']) != scene['frame_count']:
            raise ValueError('Prompt schedule must match the complete scene clock')
    if any('guide_plan' in entry and not isinstance(entry['guide_plan'], dict) for entry in plan.values()):
        raise ValueError('An explicitly supplied guide_plan must select sparse guidance')


def audit_plan(scene, plan):
    validate_actor_plan(scene, plan)
    return dict(schema=SCHEMA, frame_count=scene['frame_count'],
                actor_order=list(plan), actors={name: plan_frames(scene, name, entry.get('guide_plan'))
                                              for name, entry in plan.items()},
                full_scene_evaluation_unchanged=True, sparse_guides_do_not_guarantee_contacts=True,
                quality_approved=False, release_approved=False)


def validate_prepared_guidance(folder, freeze, batch):
    """Before inference/export, bind the plan and exact request populations.

    Legacy batches have no new guide-plan artifact. A newly prepared batch
    cannot discard the binding and masquerade as a legacy batch.
    """
    folder = Path(folder); artifact = folder/'generation-guide-plan.json'
    snapshot = folder/'source-snapshot/scene_generation_guides.py'
    expected = freeze.get('generation_guide_plan_sha256')
    if expected is None:
        if artifact.exists() or snapshot.exists():
            raise ValueError('Generation guide-plan binding was dropped')
        return None
    if not artifact.is_file() or not snapshot.is_file():
        raise ValueError('Missing generation guide-plan artifact or planner snapshot')
    if sha256(artifact) != expected:
        raise ValueError('Changed generation guide plan')
    scene, plan = read(folder/'authored-scene.json'), read(folder/'actor-plan.json')
    if sha256(folder/'authored-scene.json') != freeze['scene_sha256'] or sha256(folder/'actor-plan.json') != freeze['plan_sha256']:
        raise ValueError('Changed scene or actor plan')
    if (sha256(snapshot) != freeze.get('guide_planner_sha256')
            or sha256(ROOT/'scripts/scene_generation_guides.py') != freeze['guide_planner_sha256']):
        raise ValueError('Changed generation guide planner')
    result = read(artifact)
    if result != audit_plan(scene, plan) or freeze['actor_order'] != list(plan):
        raise ValueError('Rebound generation guide-plan population or decision')
    if not isinstance(batch, dict) or not isinstance(batch.get('requests'), list):
        raise ValueError('Complete generation request required')
    requests = {r['id']: r for r in batch['requests']}
    ids = {f'actor-{i}-{mode}' for i in range(len(plan)) for mode in ['baseline', 'guided']}
    if len(requests) != len(batch['requests']) or set(requests) != ids:
        raise ValueError('Generation actor/request population changed')
    for i, (name, entry) in enumerate(plan.items()):
        for mode in ['baseline', 'guided']:
            request = requests[f'actor-{i}-{mode}']
            if request['segments'] != entry['segments'] or request['seeds'] != entry['seeds']:
                raise ValueError('Generation prompt schedule or seeds changed')
            expected_guides = guides_from_plan(scene, name, result['actors'][name]) if mode == 'guided' else []
            if request.get('generation_constraints', []) != expected_guides:
                raise ValueError('Generation guide frames or effectors changed')
    return copy.deepcopy(result)


def preview(scene_path, plan_path, output):
    """Preview temporal planning without loading poses, weights or 3D assets."""
    output=Path(output)
    if output.exists():
        raise ValueError('Preserve the previous guide preview; select a new output')
    methods=Path(__file__).resolve().parent
    bindings={str(Path(p).resolve()):sha256(p) for p in
              [scene_path,plan_path,Path(__file__),methods/'action_requests.py',methods/'generation_constraints.py',methods/'strep.py']}
    source=read(scene_path);scene=source.get('scene',source);plan=read(plan_path)
    result=dict(schema='strep-scene-generation-guide-preview-v1',plan=audit_plan(scene,plan),
                inputs_sha256=bindings,source_pose_geometry_checked=False,
                generated_motion_checked=False,quality_approved=False,release_approved=False)
    if any(sha256(p)!=h for p,h in bindings.items()):
        raise ValueError('Guide preview inputs changed during planning')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False);stream.write('\n')
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene',type=Path);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();preview(args.scene,args.plan,args.output)
