"""Explicit neutral-mesh height calibration; not a per-clip contact solver."""
import argparse
import copy
from pathlib import Path
import numpy as np
from strep import read,save,sha256


def calibrate(character,profile_path,output):
    import torch
    from kimodo.skeleton import SOMASkeleton77
    from rig_asset import RigAsset
    from retarget_rig import resolve_profile,transfer
    from floor_contact import Surface
    from build_soma_preview import ASSET
    character,profile_path,output=map(Path,(character,profile_path,output))
    if output.exists():raise ValueError('Calibration output already exists')
    profile=read(profile_path)
    if sha256(character)!=profile['character_sha256']:raise ValueError('Character profile mismatch')
    rig=RigAsset.load(character);mapping,authored_offset=resolve_profile(rig,profile);skeleton=SOMASkeleton77()
    local=torch.eye(3).repeat(1,77,1,1);root=torch.zeros((1,3))
    rotations,positions,_=skeleton.fk(local,root)
    motion=dict(root_positions=root.numpy(),global_rot_mats=rotations.numpy())
    matrices,_,_,scale,_=transfer(rig,motion,skeleton,mapping,np.zeros(3),profile.get('axis_alignment_xyzw'))
    source_min_y=float(Surface(dict(np.load(ASSET))).vertices(rotations[0].numpy(),positions[0].numpy())[:,1].min())
    target_min_y=float(rig.vertices(matrices[0])[:,1].min())
    delta=source_min_y*scale-target_min_y
    calibrated=copy.deepcopy(profile);calibrated['world_offset_m']=(authored_offset+[0,delta,0]).tolist()
    calibrated['notes']=('Explicit neutral-mesh height calibration, added to authored placement. '
        'No motion frames used to fit this constant offset; support contacts, floor clearance in other poses and anatomical realism remain unverified.')
    output.parent.mkdir(parents=True,exist_ok=True);save(output,calibrated)
    record=dict(source_profile_sha256=sha256(profile_path),character_sha256=sha256(character),
        source_soma_skin_sha256=sha256(ASSET),source_neutral_min_y_m=source_min_y,target_neutral_min_y_m=target_min_y,
        leg_scale=scale,added_vertical_offset_m=delta,authored_world_offset_m=authored_offset.tolist(),
        calibrated_world_offset_m=calibrated['world_offset_m'],profile_sha256=sha256(output),implementation_sha256=sha256(__file__),
        rule='deltaY = source neutral skin minY * mean leg-length scale - transferred target neutral skin minY, both evaluated with source root zero and no authored offset.',
        limitation='A constant rig calibration only. It can worsen ground poses and cannot solve changing support or object/partner contact.')
    save(output.with_suffix('.calibration.json'),record)
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('character','profile','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();print(calibrate(args.character,args.profile,args.output))
