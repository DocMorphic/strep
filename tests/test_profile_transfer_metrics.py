import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from profile_transfer_study import target_descriptors
from profile_response_study import descriptors

ROLES=['Hips','Neck1','RightArm','RightForeArm','RightLeg','RightShin','RightFoot','LeftLeg','LeftShin','LeftFoot']


def test_semantic_remapping_and_rigid_scale_invariance():
    rng=np.random.default_rng(528);positions=rng.normal(size=(120,len(ROLES),3))
    expected=descriptors(positions,ROLES);order=rng.permutation(len(ROLES));mapping={role:int(np.where(order==i)[0][0]) for i,role in enumerate(ROLES)}
    moved=(positions[:,order]@Rotation.from_rotvec([.3,-.2,.1]).as_matrix().T)*.7+np.array([2.,-5.,7.])
    actual=target_descriptors(moved,mapping)
    for name,value in expected.items():assert abs(actual[name]-value)<1e-10


@pytest.mark.parametrize('fault',['missing','duplicate','negative','outside','boolean','fractional','nonfinite'])
def test_bad_semantic_mapping_or_geometry_rejected(fault):
    rng=np.random.default_rng(631);positions=rng.normal(size=(10,len(ROLES),3));mapping={n:i for i,n in enumerate(ROLES)}
    if fault=='missing':del mapping['Neck1']
    elif fault=='duplicate':mapping['Neck1']=mapping['Hips']
    elif fault=='negative':mapping['Neck1']=-1
    elif fault=='outside':mapping['Neck1']=len(ROLES)
    elif fault=='boolean':mapping['Neck1']=True
    elif fault=='fractional':mapping['Neck1']=1.5
    else:positions[0,0,0]=np.nan
    with pytest.raises(ValueError):target_descriptors(positions,mapping)
