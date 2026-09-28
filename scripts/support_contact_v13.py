"""V12 contact/clearance formulation with six outer solver stages."""
from support_contact_v12 import CONFIG as BASE_CONFIG
from support_contact_v8 import refine as base_refine
CONFIG={**BASE_CONFIG,'outer_stages':6}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True,physical_finger_parameters=True,release_endpoint_guards=True,object_inequalities=True,outer_stage_count=CONFIG['outer_stages'])
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='V13: unchanged V12 controls and inequalities, six outer stages.'
    return result,recipe
