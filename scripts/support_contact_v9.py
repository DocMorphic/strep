"""Experimental v8 objective with bounded native finger articulation enabled."""
from support_contact_v8 import CONFIG as BASE_CONFIG,refine as base_refine

CONFIG={**BASE_CONFIG,'finger_edits':True,'finger_base_thumb_degrees':8.,'finger_base_other_degrees':5.,'finger_distal_degrees':12.}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True)
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='Cubic body and finger edit controls; v9 experimental. Finger bounds are edit budgets, not anatomical joint limits.'
    return result,recipe
