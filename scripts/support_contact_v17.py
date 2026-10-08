"""V16 object/contact populations with sparse skin and activation recomputation."""
from support_contact_v16 import CONFIG as BASE_CONFIG
from support_contact_v8 import refine as base_refine
CONFIG={**BASE_CONFIG,'skin_backend':'sparse','object_playback_checkpoint_frames':32}


def refine(*args,**kwargs):
    result,recipe=base_refine(*args,**kwargs,finger_edits=True,physical_finger_parameters=True,
        release_endpoint_guards=True,object_inequalities=True,outer_stage_count=CONFIG['outer_stages'],
        intentional_object_contacts=True,object_subframe_divisions=CONFIG['object_subframe_divisions'],
        object_sample_margin_m=CONFIG['object_sample_margin_m'],point_numerical_margin_m=CONFIG['point_numerical_margin_m'],
        skin_backend=CONFIG['skin_backend'],object_playback_checkpoint_frames=CONFIG['object_playback_checkpoint_frames'])
    recipe['config']=CONFIG.copy()
    recipe['parameterization']='V17: unchanged V16 contact/object limits and complete query populations; exact sparse skin plus recomputed object-query activations in chunks of 32 frames. No reduced clock, mesh population or acceptance.'
    return result,recipe
