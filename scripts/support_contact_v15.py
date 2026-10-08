"""Contact-aware objects with whole-clock quarter-key playback constraints."""
from support_contact_v14 import CONFIG as BASE_CONFIG
from support_contact_v8 import refine as base_refine
CONFIG={**BASE_CONFIG,'object_subframe_divisions':4,'object_sample_margin_m':.00001}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True,physical_finger_parameters=True,
        release_endpoint_guards=True,object_inequalities=True,outer_stage_count=CONFIG['outer_stages'],
        intentional_object_contacts=True,object_subframe_divisions=CONFIG['object_subframe_divisions'],
        object_sample_margin_m=CONFIG['object_sample_margin_m'])
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='V15: V14 controls with all quarter-key local-quaternion object queries and 10 micrometre numerical buffer. Full exported playback still requires independent checks.'
    return result,recipe
