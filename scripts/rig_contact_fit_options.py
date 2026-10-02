"""Explicit Studio playback fitting options, separate from the contact draft."""
import copy
from pathlib import Path
from mesh_contact_clock import validate_clock,validate_overrides
from strep import read,sha256

def defaults():
    return dict(schema='strep-mesh-playback-fit-v1',contact_clock='authored-keys',spacing_frames=10,
                floor_iterations=30,contact_iterations=60)

def validate_shape(options,spec=None):
    if not isinstance(options,dict) or set(options)-{'contact_clock_overrides'}!=set(defaults()) or options['schema']!=defaults()['schema']:
        raise ValueError('Explicit playback fit options required')
    validate_clock(options['contact_clock'])
    if 'contact_clock_overrides' in options:
        if spec is None:raise ValueError('Contact draft required to bind interval timing choices')
        if options['contact_clock_overrides'] is None:raise ValueError('Contact clock overrides must be an explicit map')
        validate_overrides(options['contact_clock_overrides'],len(spec['contacts']))
    for field,maximum in (('spacing_frames',120),('floor_iterations',200),('contact_iterations',200)):
        if type(options[field]) is not int or not 1<=options[field]<=maximum:
            raise ValueError('Invalid playback '+field)
    return copy.deepcopy(options)


def validate(options,glb,spec=None):
    result=validate_shape(options,spec)
    timeline=Path(glb).parent/'timeline.json'
    if timeline.exists() and 'period_frames' in read(timeline):
        raise ValueError('Playback fitting does not preserve periodic closure; use the cycle contact fit')
    return result

def methods():
    from rig_mesh_trajectory import METHODS
    return tuple(dict.fromkeys((*METHODS,'rig_contact_fit_options.py','rig_contact_timing.py','rig_playback_contact_job.py','rig_studio_job.py','rig_contact_authoring.py')))

def bind():
    return {name:sha256(Path(__file__).with_name(name)) for name in methods()}
