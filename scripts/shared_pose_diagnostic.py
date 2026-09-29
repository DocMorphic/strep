"""Validation and one-control basis for an explicitly frozen pose diagnostic.

This is not a temporal motion model or a contact feasibility certificate.
"""
import numpy as np


def require_repeated_motion(motion, frames=None):
    count = len(motion['root_positions'])
    if count < 3 or (frames is not None and count != frames):
        raise ValueError('Shared pose requires at least three matching repeated frames')
    for key in ['root_positions', 'local_rot_mats', 'global_rot_mats', 'posed_joints']:
        value = np.asarray(motion[key])
        if len(value) != count or not np.isfinite(value).all() or not np.array_equal(value, np.repeat(value[:1], count, axis=0)):
            raise ValueError('Shared pose requires exactly repeated motion: ' + key)
    return count


def shared_basis(frames):
    if type(frames) is not int or frames < 3:
        raise ValueError('Shared pose requires at least three frames')
    return np.ones((frames, 1)), np.array([0], dtype=int)


def require_static_scene(scene, actor, contact_ids):
    from scene_constraints import sample_object
    if set(scene['actors']) != {actor} or scene.get('partner_cut_file'):
        raise ValueError('Shared pose diagnostic requires one actor and no partner cuts')
    for obj in scene.get('objects', {}).values():
        for values in sample_object(obj, scene['frame_count']):
            if not np.allclose(values, values[:1], atol=1e-12, rtol=0):
                raise ValueError('Shared pose diagnostic requires frozen objects')
    contacts = [c for c in scene['contacts'] if c['id'] in contact_ids]
    if len(contacts) != len(set(contact_ids)):
        raise ValueError('Shared pose contacts must exist')
    for contact in contacts:
        if contact['actor'] != actor or contact['start_frame'] != 0 or contact['end_frame'] != scene['frame_count'] - 1:
            raise ValueError('Shared pose contacts must cover the complete frozen window')
        if contact['target']['space'] not in ['world', 'object']:
            raise ValueError('Shared pose requires world or frozen-object targets')
