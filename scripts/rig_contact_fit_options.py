"""Explicit Studio playback fitting options, separate from the contact draft."""
import copy
from pathlib import Path
from mesh_contact_clock import validate_clock
from strep import read,sha256

def defaults():
    return dict(schema='strep-mesh-playback-fit-v1',contact_clock='authored-keys',spacing_frames=10,
                floor_iterations=30,contact_iterations=60)

def validate(options,glb):
    if not isinstance(options,dict) or set(options)!=set(defaults()) or options['schema']!=defaults()['schema']:
        raise ValueError('Explicit playback fit options required')
    validate_clock(options['contact_clock'])
    for field,maximum in (('spacing_frames',120),('floor_iterations',200),('contact_iterations',200)):
        if type(options[field]) is not int or not 1<=options[field]<=maximum:
            raise ValueError('Invalid playback '+field)
    timeline=Path(glb).parent/'timeline.json'
    if timeline.exists() and 'period_frames' in read(timeline):
        raise ValueError('Playback fitting does not preserve periodic closure; use the cycle contact fit')
    return copy.deepcopy(options)

def methods():
    from rig_mesh_trajectory import METHODS
    return tuple(dict.fromkeys((*METHODS,'rig_contact_fit_options.py','rig_playback_contact_job.py','rig_studio_job.py','rig_contact_authoring.py')))

def bind():
    return {name:sha256(Path(__file__).with_name(name)) for name in methods()}
