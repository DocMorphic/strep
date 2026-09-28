"""Profile-based target-rig orientation/hips conversion to native SOMA77 guides."""
import numpy as np
from scipy.spatial.transform import Rotation
from retarget_rig import resolve_profile,calibration,transfer
from inspect_motion import skeleton_metadata,validate_motion


def to_soma(reference,profile,world):
    import torch
    from kimodo.skeleton import SOMASkeleton77
    skeleton=SOMASkeleton77();mapping,offset=resolve_profile(reference,profile)
    corrections,scale,diagnostic=calibration(reference,mapping,skeleton,profile.get('axis_alignment_xyzw'))
    names,parents,feet=skeleton_metadata(77);frames=len(world)
    desired={names.index(role):world[:,node,:3,:3]@np.linalg.inv(corrections[node]) for role,node in mapping.items()}
    local=np.broadcast_to(np.eye(3),(frames,77,3,3)).copy();global_rot=local.copy()
    for node,parent in enumerate(parents):
        parent_rot=np.broadcast_to(np.eye(3),(frames,3,3)) if parent<0 else global_rot[:,parent]
        if node in desired:local[:,node]=Rotation.from_matrix(parent_rot.transpose(0,2,1)@desired[node]).as_matrix()
        global_rot[:,node]=parent_rot@local[:,node]
    root=(world[:,mapping['Hips'],:3,3]-offset)/scale
    rotations,positions,_=skeleton.fk(torch.tensor(local,dtype=torch.float32),torch.tensor(root,dtype=torch.float32))
    motion=dict(local_rot_mats=local.astype(np.float32),root_positions=root.astype(np.float32),global_rot_mats=rotations.numpy(),posed_joints=positions.numpy(),foot_contacts=np.zeros((frames,len(feet)),dtype=np.float32))
    validate_motion(motion,30)
    reconstructed,*_=transfer(reference,motion,skeleton,mapping,offset,profile.get('axis_alignment_xyzw'))
    rotation_error=max(float(np.abs(reconstructed[:,node,:3,:3]-world[:,node,:3,:3]).max()) for node in mapping.values())
    root_error=float(np.linalg.norm(reconstructed[:,mapping['Hips'],:3,3]-world[:,mapping['Hips'],:3,3],axis=1).max())
    if max(rotation_error,root_error)>1e-5:raise ValueError('Rig-to-SOMA mapped orientation/root roundtrip failed')
    mesh_error=max(float(np.linalg.norm(reference.vertices(a)-reference.vertices(b),axis=1).max()) for a,b in zip(world,reconstructed))
    return motion,dict(mapped_rotation_matrix_error=rotation_error,root_error_m=root_error,roundtrip_mesh_error_max_m=mesh_error,leg_scale=scale,calibration=diagnostic,scope='Mapped global orientations and pelvis position inverted through the saved profile. Unmapped SOMA joints use rest local rotations. Bone lengths/helper motion/finger detail can differ; zero contact channels mean no annotations, not confirmed flight.')
