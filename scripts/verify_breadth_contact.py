"""Independent decoded checks for full-clip contact-correction experiments."""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from verify_rig_clearance import localize


def verify(folder):
    folder = Path(folder); request = read(folder/'request.json'); spec = read(folder/'spec.json')
    count, fps = spec['frames'], spec['fps']; poses = {}; metrics = {}; rigs = {}
    for version in ('input', 'candidate'):
        rig = RigAsset.load(folder/version/'character.glb'); rigs[version] = rig
        sampler = AnimationSampler(rig.document, rig.binary, 0)
        world = np.array([sampler.sample(float(np.float32(f/fps))) for f in range(count)])
        vertices = np.array([rig.vertices(w) for w in world]); poses[version] = world
        floor = np.maximum(0, -vertices[:,:,1].min(axis=1))
        half = [max(0, -float(rig.vertices(sampler.sample((f+.5)/fps))[:,1].min())) for f in range(count-1)]
        feet = {}
        annotations = read(folder/'input/contacts.json')
        for side, patch in spec['patches'].items():
            points = vertices[:,patch['vertices']]; height = points[:,:,1].min(axis=1)
            centroid = points[:,:,[0,2]].mean(axis=1)
            active = np.zeros(count, bool)
            for interval in annotations['intervals']:
                if interval['joint'] in (side+'Foot', side+'ToeBase'):
                    active[interval['start_frame']:interval['end_frame_exclusive']] = True
            steps = active[:-1]&active[1:]
            speed = np.linalg.norm(np.diff(centroid,axis=0),axis=1)*fps
            guide = request['support']['guides'][side]; used = np.asarray(guide['weights'])>0
            error = np.linalg.norm(centroid-np.asarray(guide['anchors_xz_m']),axis=1)
            feet[side] = dict(surface_height_error_max_m=float(np.abs(height-request['targets_m'][side]).max()),
                predicted_support_steps=int(steps.sum()), predicted_support_speed_p95_m_s=float(np.percentile(speed[steps],95)) if steps.any() else None,
                predicted_support_hover_max_m=float(np.maximum(height[active],0).max()) if active.any() else None,
                drafted_anchor_error_max_m=float(error[used].max()) if used.any() else None,
                drafted_frames=int(used.sum()))
        local = localize(world,rig.parents)
        delta = local[:-1,:,:3,:3].transpose(0,1,3,2)@local[1:,:,:3,:3]
        angles = np.degrees(Rotation.from_matrix(delta.reshape(-1,3,3)).magnitude())
        root = world[:,spec['root_node'],:3,3]
        metrics[version] = dict(floor_depth_max_m=float(floor.max()), half_frame_floor_depth_max_m=max(half),
            floor_failed_frames=np.flatnonzero(floor>spec['screen']['floor_depth_m']).tolist(),
            local_rotation_step_max_degrees=float(angles.max()),
            root_acceleration_max_m_s2=float(np.linalg.norm(np.diff(root,n=2,axis=0),axis=1).max()*fps*fps), feet=feet)
    before, after = poses['input'], poses['candidate']; rig = rigs['input']; root = spec['root_node']
    if sha256(folder/'input/character.glb') != request['input_glb_sha256']:
        raise ValueError('Input clip changed')
    original = localize(before,rig.parents); changed = localize(after,rig.parents)
    shift = after[:,root,:3,3]-before[:,root,:3,3]
    changes = dict(root_horizontal_max_m=float(np.linalg.norm(shift[:,[0,2]],axis=1).max()),
        root_vertical_max_m=float(np.abs(shift[:,1]).max()), root_step_max_m=float(np.linalg.norm(np.diff(shift,axis=0),axis=1).max()))
    for key,limit in [('root_horizontal_max_m','root_horizontal_m'),('root_vertical_max_m','root_vertical_m'),('root_step_max_m','root_step_m')]:
        if changes[key] > spec['limits'][limit]+1e-6:
            raise ValueError('Decoded root edit exceeds '+limit)
    edits = {}; allowed = {root}
    for role, entry in spec['edit_joints'].items():
        n = entry['node']; allowed.add(n)
        delta = original[:,n,:3,:3].transpose(0,2,1)@changed[:,n,:3,:3]
        angles = np.degrees(Rotation.from_matrix(delta).magnitude())
        step = np.degrees(Rotation.from_matrix(delta[:-1].transpose(0,2,1)@delta[1:]).magnitude())
        if angles.max()>entry['limit_degrees']+1e-4 or step.max()>spec['limits']['joint_step_degrees']+1e-4:
            raise ValueError('Decoded joint edit exceeds bounds: '+role)
        edits[role] = dict(max_degrees=float(angles.max()),step_max_degrees=float(step.max()))
    untouched = [n for n in range(len(rig.parents)) if n not in allowed]
    nonroot = [n for n in range(len(rig.parents)) if n!=root]
    preserve = dict(untouched_local_max_error=float(np.abs(original[:,untouched]-changed[:,untouched]).max()),
        root_rotation_max_error=float(np.abs(original[:,root,:3,:3]-changed[:,root,:3,:3]).max()),
        nonroot_translation_max_m=float(np.abs(original[:,nonroot,:3,3]-changed[:,nonroot,:3,3]).max()))
    if max(preserve.values())>1e-5:
        raise ValueError('Unselected transforms changed')
    track = read(folder/'candidate/root-motion.json')
    np.testing.assert_allclose(track['positions_m'],after[:,root,:3,3],atol=1e-5,rtol=0)
    np.testing.assert_allclose(Rotation.from_quat(track['rotations_xyzw']).as_matrix(),after[:,root,:3,:3],atol=1e-5,rtol=0)
    np.testing.assert_allclose(track['times_s'],np.arange(count)/fps,atol=1e-6,rtol=0)
    if (folder/'input/contacts.json').read_bytes() != (folder/'candidate/contacts.json').read_bytes():
        raise ValueError('Original predicted contacts changed')
    report = dict(at=now(), source_sha256=request['input_glb_sha256'],candidate_sha256=sha256(folder/'candidate/character.glb'),
        bounds_and_preservation_passed=True, changes=changes, joints=edits, preservation=preserve, metrics=metrics,
        quality_approved=False, human_review=None,
        scope='Decoded whole and half-frame mesh, predicted foot support proxies, motion derivatives and hard edit limits. Does not establish action correctness, confirmed support, physical balance or realism.')
    save(folder/'verification.json',report)
    return report
