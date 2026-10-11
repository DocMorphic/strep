"""Explicit current export limits, distinct from historical correction intent."""
import copy
from native_rotation_speed_policy import limits_for


def requested(draft):return isinstance(draft,dict) and draft.get('schema')=='strep-studio-native-scene-v2'


def policy(draft,digest):
    value=dict(schema='strep-native-rotation-speed-policy-v1',contacts_sha256=digest,
        tracks=copy.deepcopy(draft['rotation_speed_limits']))
    limits_for(value,digest)
    return value


def promote(draft,tracks):
    limits_for(dict(schema='strep-native-rotation-speed-policy-v1',contacts_sha256='draft',tracks=tracks),'draft')
    if requested(draft):policy(draft,'draft')
    result=copy.deepcopy(draft)
    merged={(t['actor'],t['node']):copy.deepcopy(t) for t in result.get('rotation_speed_limits',[])}
    for t in tracks:merged[t['actor'],t['node']]=copy.deepcopy(t)
    result['schema']='strep-studio-native-scene-v2';result['rotation_speed_limits']=list(merged.values())
    policy(result,'draft')
    return result


def methods():
    from native_engine_rotation_speed import METHODS
    return tuple(dict.fromkeys(METHODS+('native_scene_export_speed.py',)))


def replay_export(contacts,policy_path,producer,output):
    from pathlib import Path
    from native_engine_rotation_speed import verify
    from strep import save,sha256
    output=Path(output);result=verify(contacts,policy_path,producer)
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True)
    record=dict(status='complete',source_result_sha256=sha256(Path(producer)/'result.json'),
        recorded_sampled_conditions_pass=result['all_sampled_conditions_pass'],
        all_replayed_observations_exact=True,saved_animation_resources_used=result['saved_animation_resources_used'],
        original_selected=True,quality_approved=False,training_admitted=False,release_approved=False)
    save(output/'result.json',record)
    return record
