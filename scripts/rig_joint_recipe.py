"""Hash-bound sparse world-joint edit recipes for existing Studio rig clips.

Compile against the selected rig, not SOMA joint names or a benchmark action.
This module validates and snapshots inputs; it does not approve motion quality.
"""
import copy
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256
from rig_asset import RigAsset
from rig_contact_authoring import source, empty_spec, metadata
from rig_clearance_fit import foot_regions
from target_rig_contact import baseline


def envelope(frames, first, last):
    if any(type(v) is not int for v in (frames, first, last)) or not 0 <= first < last < frames:
        raise ValueError('Choose a valid source-frame window')
    if not 6 <= last-first <= 120:
        raise ValueError('Joint edit window must span 6–120 frames')
    result = np.zeros(frames)
    distance = np.minimum(np.arange(last-first+1), np.arange(last-first+1)[::-1])
    u = np.clip((distance-1)/(max(distance)-1), 0, 1)
    result[first:last+1] = u*u*(3-2*u)
    return result


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {'source_job', 'variant', 'edit'}:
        raise ValueError('Source clip, version and joint edit recipe required')
    previous, result, original, report, glb = source(payload['source_job'], payload['variant'])
    edit = payload['edit']
    fields = {'schema', 'glb_sha256', 'label', 'start_frame', 'last_frame', 'goals'}
    if not isinstance(edit, dict) or set(edit) != fields or edit['schema'] != 'strep-rig-joint-edit-v1':
        raise ValueError('Invalid joint edit recipe')
    if edit['glb_sha256'] != sha256(glb):
        raise ValueError('Joint targets belong to a different clip version')
    if not isinstance(edit['label'], str) or not 1 <= len(edit['label'].strip()) <= 160:
        raise ValueError('Name the target edit')
    if report['fps'] != 30 or report['frames'] > 900:
        raise ValueError('Joint editing requires a 30fps clip of at most 900 frames')
    timeline = glb.parent/'timeline.json'
    if timeline.exists() and 'period_frames' in read(timeline):
        raise ValueError('Edit a finite source before creating a loop; periodic joint fitting is not supported yet')
    weights = envelope(report['frames'], edit['start_frame'], edit['last_frame'])
    goals = edit['goals']
    if not isinstance(goals, list) or not 1 <= len(goals) <= 8:
        raise ValueError('Author 1–8 sparse joint targets')
    rig = RigAsset.load(glb)
    occupied = set()
    for goal in goals:
        if not isinstance(goal, dict) or set(goal) != {'frame', 'node', 'position_m', 'rotation_xyzw'}:
            raise ValueError('Each goal needs a frame, joint, world position and world orientation')
        frame, node = goal['frame'], goal['node']
        if type(frame) is not int or not 0 <= frame < len(weights) or weights[frame] <= 0:
            raise ValueError('Targets must lie inside the editable window, away from the two fixed edge samples')
        if type(node) is not int or node not in rig.joints or (frame, node) in occupied:
            raise ValueError('Choose a skin joint and avoid duplicate joint/frame targets')
        ancestor = node
        while ancestor >= 0 and ancestor != report['root_node']:
            ancestor = rig.parents[ancestor]
        if ancestor < 0:
            raise ValueError('Target joint must descend from the mapped pelvis')
        occupied.add((frame, node))
        for key, size in [('position_m', 3), ('rotation_xyzw', 4)]:
            value = goal[key]
            if not isinstance(value, list) or len(value) != size or any(type(v) not in (int, float) or not np.isfinite(v) for v in value):
                raise ValueError('Finite world position and quaternion required')
        if abs(np.linalg.norm(goal['rotation_xyzw'])-1) > 1e-5:
            raise ValueError('Target orientation must be a unit XYZW quaternion')
    return previous, original, report, glb, copy.deepcopy(edit)


def compile_recipe(rig, report, edit, authored_spec=None):
    """Build geometry and bounds without inventing confirmed contact labels."""
    before, local = baseline(rig, report['frames'])
    weights = envelope(report['frames'], edit['start_frame'], edit['last_frame'])
    spec = empty_spec(report)
    spec['provenance'] = ('Sparse authored world-joint targets. Weighted foot regions preserve height; '
                          'they are not contact annotations. Any inherited patch supports retain their original provenance.')
    # Weighted foot geometry supplies height preservation, never support inference.
    regions = foot_regions(rig, report['mapping'])
    spec['patches'] = {side: dict(vertices=ids.tolist()) for side, ids in regions.items()}
    # Include the actual target ancestry; imported bones need not use SOMA names.
    nodes = {entry['node']: entry for entry in spec['edit_joints'].values()}
    for goal in edit['goals']:
        node = goal['node']
        while node != report['root_node'] and node >= 0:
            if node in rig.joints and node not in nodes:
                nodes[node] = dict(node=node, limit_degrees=25)
            node = rig.parents[node]
    if not 1 <= len(nodes) <= 20:
        raise ValueError('This window needs more than 20 editable joints; split the target edit')
    spec['edit_joints'] = {str(node): entry for node, entry in nodes.items()}
    supports = []
    if authored_spec is not None:
        from target_rig_contact import validate as validate_contacts
        if authored_spec.get('glb_sha256') != edit['glb_sha256'] or authored_spec.get('frames') != report['frames']:
            raise ValueError('Saved contact targets do not match the selected input')
        validate_contacts(authored_spec, rig)
        for name, patch in authored_spec['patches'].items():
            spec['patches']['contact:'+name] = dict(vertices=patch['vertices'])
        for contact in authored_spec['contacts']:
            if set(contact) != {'patch', 'start_frame', 'end_frame_exclusive', 'target_position_m'}:
                raise ValueError('Moving or oriented contact targets require a scene edit; they cannot be silently discarded')
            side = 'contact:'+contact['patch']
            supports.append(dict(side=side, vertices=spec['patches'][side]['vertices'],
                start_frame=contact['start_frame'], end_frame_exclusive=contact['end_frame_exclusive'],
                target_position_m=contact['target_position_m'], provenance=authored_spec['provenance']))
    points = np.array([rig.vertices(w) for w in before])
    heights = {side: np.maximum(0, points[:, patch['vertices'], 1].min(axis=1)) for side, patch in spec['patches'].items()}
    goals = [dict(frame=g['frame'], node=g['node'], position_m=g['position_m'],
                  rotation_matrix=Rotation.from_quat(g['rotation_xyzw']).as_matrix().tolist(),
                  position_weight=60., rotation_weight=.5,
                  provenance='Authored world-space target on input SHA256 '+edit['glb_sha256']) for g in edit['goals']]
    return dict(before=before, local=local, spec=spec, envelope=weights, targets=heights, supports=supports, goals=goals)


def prepare(payload, folder):
    previous, original, report, glb, edit = validate(payload)
    prior_spec = previous/'input/contact-spec.json' if payload['variant'] == 'input' else previous/'contact-spec.json'
    # Rebind the same authored patches/world targets using the existing Studio
    # metadata path, which already handles corrected versus input clip versions.
    authored = metadata(payload['source_job'], payload['variant'])['spec'] if prior_spec.exists() else None
    # Resolve rig/contact compatibility before creating an output job.
    compiled = compile_recipe(RigAsset.load(glb), report, edit, authored)
    folder = Path(folder); folder.mkdir(exist_ok=False)
    shutil.copytree(previous/'source', folder/'source', ignore=shutil.ignore_patterns('implementation'))
    dest = folder/'input'; dest.mkdir()
    shutil.copyfile(glb, dest/'character.glb')
    metadata_folder = glb.parent if (glb.parent/'inventory.json').exists() else previous/'transfer'
    for name in ('inventory.json', 'rig-profile.json', 'contacts.json'):
        shutil.copyfile(metadata_folder/name, dest/name)
    for name in ('events.json', 'timeline.json', 'contact-review.json'):
        if (metadata_folder/name).exists():shutil.copyfile(metadata_folder/name, dest/name)
    shutil.copyfile(glb.parent/'root-motion.json', dest/'root-motion.json')
    if authored is not None:
        save(dest/'contact-spec.json', authored)
        shutil.copyfile(prior_spec, dest/'parent-contact-spec.json')
    source_name = 'character.glb' if report.get('source_kind') == 'gltf_animation' else 'motion.npz'
    report.update(source=str((folder/'source'/source_name).resolve()), character=str((folder/'source/character.glb').resolve()))
    if report.get('timeline_edited'):report['contact_annotations_file'] = str((dest/'contacts.json').resolve())
    save(dest/'report.json', report); save(folder/'joint-edit.json', edit)
    save(folder/'joint-spec.json', compiled['spec'])
    save(folder/'joint-targets.json', dict(envelope=compiled['envelope'].tolist(),
        targets_m={k:v.tolist() for k,v in compiled['targets'].items()}, supports=compiled['supports'], goals=compiled['goals']))
    np.savez_compressed(folder/'joint-input.npz', before=compiled['before'], local=compiled['local'])
    request = dict(kind='joint_edit', label=edit['label'], asset_id=original['asset_id'],
        profile_id=sha256(folder/'source/rig-profile.json'), source_kind=report.get('source_kind', 'soma_motion'),
        source_motion_sha256=sha256(folder/'source'/source_name), correct_contacts=False,
        source_job=previous.name, input_variant=payload['variant'], input_glb_sha256=sha256(glb),
        input_files={name:sha256(folder/name) for name in ['joint-edit.json', 'joint-spec.json', 'joint-targets.json', 'joint-input.npz']})
    request['input_files'].update({p.relative_to(folder).as_posix():sha256(p) for p in dest.iterdir() if p.is_file()})
    save(folder/'request.json', request); save(folder/'pipeline.json', dict(status='starting',stage='Joint-target input snapshot prepared'))
    return request
