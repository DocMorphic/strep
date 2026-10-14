"""Explicit original-bound Godot skin-weight export selection and receipts."""
import copy
MODE='godot-u16-original-fidelity-v1'


def selection(value):
    if 'skin_weight_export' not in value:return None
    if type(value['skin_weight_export']) is not str or value['skin_weight_export']!=MODE:
        raise ValueError('Explicit supported skin weight export mode required')
    return MODE


def methods():
    from native_skin_export import METHODS
    from verify_native_scene_engine import VERIFIER_METHODS
    return tuple(dict.fromkeys(METHODS+VERIFIER_METHODS+('audit_conditioned_skin_fidelity.py',
        'native_scene_weight_export.py','action_worker_lock.py')))


def portable_receipt(proof, original_sha256, derivative_sha256, scene_sha256):
    if set(proof['actors'])!=set(original_sha256) or set(original_sha256)!=set(derivative_sha256):
        raise ValueError('Complete actor weight export correspondence required')
    return dict(schema='strep-native-scene-weight-export-v1',mode=MODE,portable_scene_sha256=scene_sha256,
        original_actor_sha256=copy.deepcopy(original_sha256),derivative_actor_sha256=copy.deepcopy(derivative_sha256),
        actors=copy.deepcopy(proof['actors']),original_reference_fidelity_pass=proof['all_original_reference_fidelity_pass'],
        mesh_weights_changed=True,animation_changed=False,original_selected=True,
        quality_approved=False,training_admitted=False,release_approved=False)
