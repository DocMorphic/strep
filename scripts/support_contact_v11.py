"""V10 contact fitting with an explicit target at the release event boundary."""
from support_contact_v10 import CONFIG as BASE_CONFIG
from support_contact_v8 import refine as base_refine

CONFIG={**BASE_CONFIG,'release_endpoint_guards':True}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True,physical_finger_parameters=True,release_endpoint_guards=True)
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='V11: V10 bounded controls with solver-only release-boundary targets and surface frames. Authored contact end events are preserved.'
    return result,recipe
