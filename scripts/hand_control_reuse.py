"""Embed verified oriented hand controls into an earlier native-key support."""
from pathlib import Path
import numpy as np
from strep import ROOT,read,sha256
from bound_evidence import bind_inputs


CONTROL_METHODS=['oriented_terminal_hand.py','continuous_waypoint_motion.py','timed_rotation_edit.py',
    'two_bone_waypoint.py','elbow_swivel.py','paired_guarded_temporal.py','gltf_tools.py','rig_asset.py',
    'rig_clip_import.py','paired_temporal_neighbor.py','sampled_motion_caps.py','scalar_angular_replay.py',
    'verify_scene_pair_fit.py','oriented_guide_domain.py']


def embed(controls,source_native,target_native):
    old,new=np.asarray(source_native,float),np.asarray(target_native,float);controls=np.asarray(controls,float)
    for clock in [old,new]:
        if clock.ndim!=1 or len(clock)<3 or not np.isfinite(clock).all() or np.any(np.diff(clock)<=0):
            raise ValueError('Increasing finite native keys required')
    if controls.shape!=(11*(len(old)-2),) or not np.isfinite(controls).all():raise ValueError('Matching finite donor controls required')
    if old[-1]!=new[-1] or new[0]>old[0] or not np.isin(old,new).all():raise ValueError('Target must extend the same native support with the same frozen end')
    result=np.zeros((len(new)-2,11))
    for time,row in zip(old[1:-1],controls.reshape(-1,11)):
        ids=np.flatnonzero(new[1:-1]==time)
        if len(ids)!=1:raise ValueError('Donor editable keys must remain editable')
        result[ids[0]]=row
    return result.ravel()


def load_controls(folder,required,target_native):
    folder=Path(folder).resolve();result=read(folder/'result.json');request=read(folder/'request.json')
    if result['status']!='complete' or not result.get('full_clock_motion_pass') or not request.get('hand_orientation'):
        raise ValueError('Completed motion-valid oriented hand study required')
    files={str(folder/'result.json'):sha256(folder/'result.json')}
    for name in ['request','selected','decoded']:
        path=folder/(name+'.json');digest=result[name+'_sha256']
        if sha256(path)!=digest:raise ValueError('Warm-start artifact changed')
        files[str(path)]=digest
    files.update(bind_inputs(required,request['inputs']))
    for name,digest in request['implementation'].items():
        path=(folder/'implementation'/name).resolve()
        if path.parent!=folder/'implementation' or sha256(path)!=digest:raise ValueError('Warm-start snapshot changed')
        files[str(path)]=digest
    for name in CONTROL_METHODS:
        if request['implementation'].get(name)!=sha256(ROOT/'scripts'/name):raise ValueError('Warm-start control interpretation changed')
    selected=read(folder/'selected.json');decoded=read(folder/'decoded.json')
    if not selected['motion_domain_feasible'] or [r['actor'] for r in decoded]!=['A','B']:
        raise ValueError('Feasible controls and both ordered actors required')
    paths=[]
    for actor in decoded:
        path=(folder/actor['path']).resolve()
        if path.parent!=folder or sha256(path)!=actor['sha256']:raise ValueError('Warm-start GLB changed')
        if actor['positional']['failures'] or any(v['exceeding_observations'] for v in actor['angular'].values()):
            raise ValueError('Warm-start decoded motion failed')
        files[str(path)]=actor['sha256'];paths.append(path)
    return embed(selected['controls'],request['edit_native_times_s'],target_native),paths,files
