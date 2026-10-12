"""Explicit source-bound author limits, separate from anatomical calibration."""
import numpy as np
from native_scene_contacts import fields

METHODS=('native_rotation_speed_policy.py','native_rotation_speed_preflight.py','native_rotation_speed_fit.py','temporal_rotation_bounds.py',
    'native_rotation_storage_repair.py','native_scene_boundary_edit.py')


def limits_for(request,contacts_digest):
    """Parse source-bound author intent without requiring edit permissions."""
    fields(request,('schema','contacts_sha256','tracks'),'rotation speed policy')
    if request['schema']!='strep-native-rotation-speed-policy-v1' or request['contacts_sha256']!=contacts_digest:
        raise ValueError('Rotation speed policy must bind the exact contact request')
    tracks=request['tracks'];limits={}
    if not isinstance(tracks,list) or not 1<=len(tracks)<=64:raise ValueError('Choose 1-64 explicit joint speed limits')
    for track in tracks:
        fields(track,('actor','node','maximum_degrees_per_second'),'rotation speed track')
        name,node,maximum=track['actor'],track['node'],track['maximum_degrees_per_second']
        if not isinstance(name,str) or type(node) is not int or type(maximum) not in (int,float):
            raise ValueError('Explicit actor, integer joint and finite nonnegative authored speed required')
        try:maximum=float(maximum)
        except (ValueError,OverflowError) as error:raise ValueError('Finite representable authored speed required') from error
        if not np.isfinite(maximum) or maximum<0:raise ValueError('Finite nonnegative authored speed required')
        key=name,node
        if key in limits:raise ValueError('Duplicate actor/joint speed limit')
        limits[key]=maximum
    return limits


def policy_for(request,edits,contacts_digest):
    from native_rotation_speed_preflight import assess_scene
    limits=limits_for(request,contacts_digest)
    lower,report=assess_scene(edits,limits)
    return limits,lower,report
