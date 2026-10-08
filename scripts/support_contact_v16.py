"""V15 playback guards with numerical headroom for explicit contact points."""
from support_contact_v15 import CONFIG as BASE_CONFIG
from support_contact_v8 import refine as base_refine
CONFIG={**BASE_CONFIG,'point_numerical_margin_m':.00001}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True,physical_finger_parameters=True,
        release_endpoint_guards=True,object_inequalities=True,outer_stage_count=CONFIG['outer_stages'],
        intentional_object_contacts=True,object_subframe_divisions=CONFIG['object_subframe_divisions'],
        object_sample_margin_m=CONFIG['object_sample_margin_m'],point_numerical_margin_m=CONFIG['point_numerical_margin_m'])
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='V16: V15 controls and playback queries, reserving up to 10 micrometres (at most 1%) of active explicit point limits. Authored specs and independent acceptance are unchanged.'
    return result,recipe
