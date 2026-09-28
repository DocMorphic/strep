"""V9 objective and bounds with physical-angle finger parameter scaling."""
from support_contact_v9 import CONFIG as BASE_CONFIG
from support_contact_v8 import refine as base_refine

CONFIG={**BASE_CONFIG,'finger_parameter_units':'physical_radians_before_smooth_bound'}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True,physical_finger_parameters=True)
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='V10: original body coordinates; physical-radian finger controls before the same smooth norm bound. Same objective and reachable edits as V9.'
    return result,recipe
