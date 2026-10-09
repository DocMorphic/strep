"""Explicit development CCD comparisons; no motion or release approval."""
import math

PREFIX = 'physics/jolt_physics_3d/'
THRESHOLD = PREFIX + 'simulation/continuous_cd_movement_threshold'
PENETRATION = PREFIX + 'simulation/continuous_cd_max_penetration'
TRACKED_SETTINGS = (THRESHOLD, PENETRATION,
    PREFIX + 'simulation/penetration_slop',
    PREFIX + 'simulation/baumgarte_stabilization_factor',
    PREFIX + 'simulation/position_steps', PREFIX + 'simulation/velocity_steps',
    PREFIX + 'collisions/collision_margin_fraction',
    PREFIX + 'simulation/speculative_contact_distance',
    'physics/common/physics_ticks_per_second', 'physics/3d/default_gravity')
PROFILES = {
    'engine-default': {},
    'ccd-threshold': {THRESHOLD: .05},
    'strict-ccd': {THRESHOLD: .05, PENETRATION: .01},
}


def profile_settings(name):
    if not isinstance(name, str) or name not in PROFILES:
        raise ValueError('Known explicit scene collision profile required')
    return dict(PROFILES[name])


def config_lines(name):
    return ''.join(key.removeprefix('physics/') + '=' + repr(value) + '\n'
                   for key, value in profile_settings(name).items())


def verify_settings(name, echo, rate):
    """Check actual engine values, including unchanged controls, not config text."""
    if not isinstance(echo, dict) or set(echo) != set(TRACKED_SETTINGS):
        raise ValueError('Complete actual engine collision settings required')
    for value in echo.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Finite actual collision setting required')
    expected = {PREFIX + 'simulation/penetration_slop': .001,
                PREFIX + 'collisions/collision_margin_fraction': 0.,
                'physics/common/physics_ticks_per_second': rate,
                'physics/3d/default_gravity': 9.81, **profile_settings(name)}
    if any(abs(echo[key] - value) > 1e-7 for key, value in expected.items()):
        raise ValueError('Actual engine settings differ from collision protocol')
    return dict(echo)


def matched_settings(baseline, candidate, name, rate):
    before=verify_settings('engine-default',baseline,rate)
    after=verify_settings(name,candidate,rate)
    allowed=profile_settings(name)
    if any(after[key]!=value for key,value in before.items() if key not in allowed):
        raise ValueError('Unrelated physics controls changed in comparison')
    return {key:dict(before=before[key],after=after[key]) for key in allowed}
