"""V11 controls with augmented-Lagrangian sampled object clearance."""
from support_contact_v11 import CONFIG as BASE_CONFIG
from support_contact_v8 import refine as base_refine
CONFIG={**BASE_CONFIG,'object_collision_mode':'per_frame_max_inequality'}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True,physical_finger_parameters=True,release_endpoint_guards=True,object_inequalities=True)
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='V12: V11 controls and release guards with per-object/frame sampled clearance inequalities.'
    return result,recipe
