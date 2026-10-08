"""V13 controls with explicit hand/foot contact buffers for named objects."""
from support_contact_v13 import CONFIG as BASE_CONFIG
from support_contact_v8 import refine as base_refine
CONFIG={**BASE_CONFIG,'intentional_object_clearance':'hand_foot_region_contact_keys'}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True,physical_finger_parameters=True,
        release_endpoint_guards=True,object_inequalities=True,outer_stage_count=CONFIG['outer_stages'],
        intentional_object_contacts=True)
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='V14: V13 controls with zero extra buffer for the complete declared hand/foot region against its intended object on solver contact keys; physical penetration remains constrained.'
    return result,recipe
