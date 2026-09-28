import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from calibrate_rig_height import calibrate


def test_neutral_height_calibration_preserves_authored_offset_and_inputs(tmp_path):
    import torch
    from kimodo.skeleton import SOMASkeleton77
    from rig_asset import RigAsset
    from retarget_rig import transfer,resolve_profile
    character=ROOT/'assets/characters/cesium-man/CesiumMan.glb'
    profile=read(character.parent/'rig-profile-v2.json');profile['world_offset_m']=[.3,.12,-.2]
    original=tmp_path/'original.json';save(original,profile);before=sha256(original)
    output=tmp_path/'calibrated.json';record=calibrate(character,original,output);changed=read(output)
    assert sha256(original)==before
    assert changed['mapping']==profile['mapping'] and changed['axis_alignment_xyzw']==profile['axis_alignment_xyzw']
    assert changed['world_offset_m'][0]==.3 and changed['world_offset_m'][2]==-.2
    assert changed['world_offset_m'][1]==pytest.approx(.12+record['added_vertical_offset_m'])
    # Place source neutral skin on y=0, then apply the calibrated transfer.
    skeleton=SOMASkeleton77();root=torch.tensor([[0.,-record['source_neutral_min_y_m'],0.]])
    rots,_,_=skeleton.fk(torch.eye(3).repeat(1,77,1,1),root)
    rig=RigAsset.load(character);mapping,offset=resolve_profile(rig,changed)
    matrices,*_=transfer(rig,dict(root_positions=root.numpy(),global_rot_mats=rots.numpy()),skeleton,mapping,offset,changed['axis_alignment_xyzw'])
    assert rig.vertices(matrices[0])[:,1].min()==pytest.approx(.12,abs=2e-6)
    assert matrices[0,mapping['Hips'],0,3]==pytest.approx(.3)
    assert matrices[0,mapping['Hips'],2,3]==pytest.approx(-.2)
    with pytest.raises(ValueError,match='already exists'):calibrate(character,original,output)
