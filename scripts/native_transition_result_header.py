"""Reject impossible transition-result claims before numerical replay.

Passing this check is not verification. The caller must still reproduce all
source bindings, observations, artifact populations and decisions.
"""


def validate_header(value, schema):
    if type(value) is not dict:
        raise ValueError('Invalid native transition result header: object required')
    for name, expected in (('schema', schema), ('status', 'complete')):
        if type(value.get(name)) is not str or value[name] != expected:
            raise ValueError('Invalid native transition result header: ' + name)
    flags = {
        'parent_decisions_apply_to_original_only': True,
        'native_root_references_consistent': True,
        'root_observations_are_native_only': True,
        'original_clip_libraries_retained': True,
        'source_phases_and_boundary_tangents_protected': True,
        'original_selected': True,
        'quality_approved': False,
        'training_admitted': False,
        'release_approved': False,
        'engine_playback_verified': False,
    }
    for name, expected in flags.items():
        if value.get(name) is not expected:
            raise ValueError('Invalid native transition result header: ' + name)
