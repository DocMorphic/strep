"""Validated user-authored support overrides in metres, Y-up, at source fps.

Intervals include both endpoint frames. An explicit target is a constraint,
not evidence that a generated action achieves it or a measured support force.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from floor_contact import Surface
from support_contact import regions


def validate(spec,frame_count,region_indices):
    if not isinstance(spec,dict) or set(spec)-{'schema_version','fps','frame_count','regions'}:
        raise ValueError('Invalid contact specification fields')
    if type(spec.get('schema_version'))!=int or spec.get('schema_version') not in [1,2] or spec.get('fps')!=30 or spec.get('frame_count')!=frame_count:
        raise ValueError('Contact schema, fps or frame count mismatch')
    overrides=spec.get('regions')
    if not isinstance(overrides,dict) or set(overrides)-set(region_indices):raise ValueError('Unknown support region')
    for name,entry in overrides.items():
        if not isinstance(entry,dict) or set(entry)-{'mode','segments'}:raise ValueError('Invalid region fields')
        mode=entry.get('mode')
        if mode not in ['inferred','disabled','explicit']:raise ValueError('Unknown contact mode')
        segments=entry.get('segments',[])
        if not isinstance(segments,list) or len(segments)>frame_count:raise ValueError('Invalid segment list')
        if mode!='explicit' and segments:raise ValueError('Only explicit mode accepts segments')
        if mode=='explicit' and not segments:raise ValueError('Explicit mode needs a contact interval')
        previous_end=-1
        for segment in segments:
            if not isinstance(segment,dict) or set(segment)-{'start_frame','end_frame','space','position_m','positions_m','vertex_id','tolerance_m'}:raise ValueError('Invalid segment fields')
            if 'tolerance_m' in segment and (type(segment['tolerance_m']) not in [int,float] or not np.isfinite(segment['tolerance_m']) or segment['tolerance_m']<=0):raise ValueError('Contact tolerance must be a positive finite metre distance')
            a,b=segment.get('start_frame'),segment.get('end_frame')
            if type(a)!=int or type(b)!=int or not 0<=a<=b<frame_count or a<=previous_end:raise ValueError('Intervals must be ordered, disjoint and within the clip')
            previous_end=b
            if segment.get('space') not in ['baseline','world','track']:raise ValueError('Target space must be baseline, world or track')
            if 'positions_m' in segment and segment['space']!='track':raise ValueError('Only track targets accept sampled coordinates')
            if segment['space']=='track':
                if spec['schema_version']!=2:raise ValueError('Moving targets require schema version 2')
                points=segment.get('positions_m')
                if not isinstance(points,list) or len(points)!=b-a+1:raise ValueError('Track must have one position per inclusive interval frame')
                if 'position_m' in segment:raise ValueError('Track targets cannot also specify a static position')
                for point in points:
                    if not isinstance(point,list) or len(point)!=3 or any(type(x) not in [int,float] or not np.isfinite(x) or abs(x)>1000 for x in point):raise ValueError('Track positions must be finite XYZ metre coordinates')
                    if point[1]<0:raise ValueError('Contact target cannot be below the ground')
            if segment['space']=='world':
                pos=segment.get('position_m')
                if not isinstance(pos,list) or len(pos)!=3 or any(type(x) not in [int,float] or not np.isfinite(x) or abs(x)>1000 for x in pos):raise ValueError('World position must be three finite coordinates in metres')
                if pos[1]<0:raise ValueError('Floor support target cannot be below the ground')
            elif 'position_m' in segment:raise ValueError('Baseline targets do not accept world coordinates')
            if 'vertex_id' in segment and (type(segment['vertex_id'])!=int or segment['vertex_id'] not in region_indices[name]):raise ValueError('Vertex does not belong to support region')
    return spec


def solver_point_tolerances(contacts,spec,frames,default):
    """Tighten explicit solver keys without relaxing existing solver limits."""
    if type(default) not in [int,float] or not np.isfinite(default) or default<=0:
        raise ValueError('Positive finite default solver tolerance required')
    limits=np.full((frames,len(contacts)),default,dtype=float)
    if spec is not None:
        for column,name in enumerate(contacts):
            entry=spec['regions'].get(name)
            if entry is None or entry['mode']!='explicit':continue
            for segment in entry['segments']:
                if 'tolerance_m' in segment:
                    limits[segment['start_frame']:segment['end_frame']+1,column]=min(default,segment['tolerance_m'])
    return limits



def apply_overrides(contacts,base,skin,spec,fade_frames=2,clearance_m=.002):
    """Return new constraints; do not alter inferred data or source motion."""
    region_indices=regions(skin);validate(spec,len(base['root_positions']),region_indices)
    result={name:{k:v.copy() if isinstance(v,np.ndarray) else list(v) if isinstance(v,list) else v for k,v in c.items()} for name,c in contacts.items()}
    surface=Surface(skin);frames=len(base['root_positions'])
    for name,entry in spec['regions'].items():
        mode=entry['mode'];c=result[name];c['provenance']=mode
        if mode=='inferred':continue
        c['weights']=np.zeros(frames);c['active']=np.zeros(frames,bool);c['spans']=[]
        if mode=='disabled':continue
        # Each interval uses a fixed surface vertex, so a world pin never swaps
        # to a different point simply because the body rotates.
        distances=np.full(frames,np.inf)
        for segment in entry['segments']:
            a,b=segment['start_frame'],segment['end_frame'];vertex=segment.get('vertex_id',int(contacts[name]['vertex_ids'][a]))
            ids=np.array([vertex]);track=np.array([surface.vertices(r,p,ids)[0] for r,p in zip(base['global_rot_mats'],base['posed_joints'])])
            if segment['space']=='world':track[:]=segment['position_m']
            elif segment['space']=='track':
                # Clamp the target outside its interval for the fade weights;
                # do not extrapolate velocity beyond the authored samples.
                track=np.asarray(segment['positions_m'])[np.clip(np.arange(frames)-a,0,b-a)]
            else:track[:,1]=np.maximum(track[:,1],clearance_m)
            distance=np.maximum(a-np.arange(frames),np.maximum(np.arange(frames)-b,0))
            nearest=distance<distances;distances[nearest]=distance[nearest]
            c['targets'][nearest]=track[nearest];c['vertex_ids'][nearest]=vertex
            c['active'][a:b+1]=True;c['spans'].append((a,b))
        c['weights']=gaussian_filter1d(c['active'].astype(float),fade_frames,mode='nearest')
    return result
