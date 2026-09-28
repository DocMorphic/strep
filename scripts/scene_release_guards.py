"""Solver-only endpoint guards for continuous contact up to a release event."""
import copy
import numpy as np
from scene_constraints import pose,sample_object,target_track


def compile_release_guards(scene,actor_id,contact_ids):
    frames=scene['frame_count'];origin,rotation=pose(scene['actors'][actor_id]['transform'])
    objects={name:sample_object(obj,frames) for name,obj in scene.get('objects',{}).items()};guards=[]
    for c in scene['contacts']:
        if c['id'] not in contact_ids:continue
        if c['actor']!=actor_id:raise ValueError('Release guard actor mismatch')
        if c['end_frame']==frames-1:continue # Playback and object track both hold their final sample.
        if c['target']['space'] not in ['world','object']:raise ValueError('Release guards require frozen world/object targets')
        frame=c['end_frame']+1
        world=target_track(c['target'],{},objects,frames)
        guards.append(dict(contact_id=c['id'],region=c['effector']['joint'],vertex_id=c['effector']['surface_vertex'],
            start_frame=c['start_frame'],original_end_frame=c['end_frame'],frame=frame,position_m=((world[frame]-origin)@rotation).tolist()))
    return guards


def extend_solver_spec(spec,guards):
    result=copy.deepcopy(spec)
    for guard in guards:
        region=result['regions'].get(guard['region'])
        if region is None or region['mode']!='explicit':raise ValueError('Release guard requires explicit contact')
        segments=region['segments']
        matches=[s for s in segments if s['start_frame']==guard['start_frame'] and s['end_frame']==guard['original_end_frame'] and s.get('vertex_id')==guard['vertex_id']]
        if len(matches)!=1:raise ValueError('Release guard does not match its original contact segment')
        segment=matches[0];frame=guard['frame']
        if frame!=segment['end_frame']+1 or frame>=spec['frame_count']:raise ValueError('Release guard must follow the last contact key')
        if any(s is not segment and s['start_frame']<=frame<=s['end_frame'] for s in segments):raise ValueError('Release guard overlaps an adjacent contact; explicit handoff handling is required')
        position=np.asarray(guard['position_m'],dtype=float)
        if position.shape!=(3,) or not np.isfinite(position).all():raise ValueError('Invalid release guard position')
        if segment['space']!='track':raise ValueError('Release guards require compiled scene tracks')
        segment['end_frame']=frame;segment['positions_m'].append(position.tolist())
    return result
