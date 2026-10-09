"""Transport explicit recorded Jolt settings without changing legacy requests."""
from scene_collision_profile import PREFIX,THRESHOLD,PENETRATION,profile_settings
import math


def profile_document(name,rate):
    overrides=profile_settings(name)
    if type(rate) is not int or rate not in (60,120,240):
        raise ValueError('Explicit supported physics rate required')
    settings={THRESHOLD:.75,PENETRATION:.25,
        PREFIX+'simulation/penetration_slop':.001,
        PREFIX+'simulation/baumgarte_stabilization_factor':.2,
        PREFIX+'simulation/position_steps':2,PREFIX+'simulation/velocity_steps':10,
        PREFIX+'collisions/collision_margin_fraction':0.,
        PREFIX+'simulation/speculative_contact_distance':.02,
        'physics/common/physics_ticks_per_second':rate,'physics/3d/default_gravity':9.81}
    settings.update(overrides)
    return dict(name=name,backend='Jolt Physics',settings=settings)


def project_lines(document,rate):
    if document is None:return ''
    if not isinstance(document,dict) or document!=profile_document(document.get('name'),rate):
        raise ValueError('Exact declared runtime collision profile required')
    if any(type(value) not in (int,float) for value in document['settings'].values()):
        raise ValueError('Numeric runtime collision settings required')
    return ''.join(key.removeprefix('physics/')+'='+repr(value)+'\n'
        for key,value in document['settings'].items() if key!='physics/common/physics_ticks_per_second')


def verify_actual(document,echo,rate):
    project_lines(document,rate)
    if document is None or not isinstance(echo,dict) or set(echo)!=set(document['settings']):
        raise ValueError('Complete recorded actual collision settings required')
    for key,value in echo.items():
        if type(value) not in (int,float) or not math.isfinite(value) or abs(value-document['settings'][key])>1e-7:
            raise ValueError('Recorded collision setting differs from declared profile')
    return dict(echo)
