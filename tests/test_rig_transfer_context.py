import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from rig_transition import localize
from retarget_rig import transfer,resolve_profile
from kimodo.skeleton import SOMASkeleton77


def fixture():
    folder=ROOT/'reports/rig-jobs/20260926-231829-75e87cd5'
    reference=RigAsset.load(folder/'source/character.glb');source=RigAsset.load(folder/'input/character.glb')
    profile=read(folder/'source/rig-profile.json');mapping,offset=resolve_profile(reference,profile)
    sample=AnimationSampler(source.document,source.binary,0)
    context=localize(np.array([sample.sample(float(np.float32(f/30))) for f in [5,6,7]]),reference.parents)
    motion={k:v[:3] for k,v in dict(np.load(ROOT/'reports/corrected-rig-transfer-v1/jump-205/aligned-native.npz')).items()}
    return reference,profile,mapping,offset,context,motion


def test_context_retains_animated_translations_and_unmapped_helpers_without_mutating_input():
    rig,profile,mapping,offset,context,motion=fixture()
    helper=next(n for n in range(len(rig.parents)) if n not in mapping.values())
    context[:,helper,:3,:3]=Rotation.from_euler('y',[0,15,30],degrees=True).as_matrix()@context[:,helper,:3,:3]
    frozen=context.copy();oldmotion={k:v.copy() for k,v in motion.items()}
    result,*_=transfer(rig,motion,SOMASkeleton77(),mapping,offset,profile.get('axis_alignment_xyzw'),context_local=context)
    local=localize(result,rig.parents);nonroot=[n for n in range(len(rig.parents)) if n!=mapping['Hips']]
    np.testing.assert_allclose(local[:,nonroot,:3,3],context[:,nonroot,:3,3],atol=1e-8)
    unmapped=[n for n in range(len(rig.parents)) if n not in mapping.values()]
    np.testing.assert_allclose(local[:,unmapped],context[:,unmapped],atol=1e-8)
    np.testing.assert_array_equal(context,frozen)
    for k in motion:np.testing.assert_array_equal(motion[k],oldmotion[k])
    default=transfer(rig,motion,SOMASkeleton77(),mapping,offset,profile.get('axis_alignment_xyzw'))[0]
    np.testing.assert_allclose(result[:,mapping['Hips'],:3,3],default[:,mapping['Hips'],:3,3],atol=1e-7)
    np.testing.assert_allclose(result[:,list(mapping.values()),:3,:3],default[:,list(mapping.values()),:3,:3],atol=1e-6)


@pytest.mark.parametrize('failure',['frames','nodes','nan','affine','scale','reflection'])
def test_invalid_context_rejected(failure):
    rig,profile,mapping,offset,context,motion=fixture()
    if failure=='frames':context=context[:-1]
    elif failure=='nodes':context=context[:,:-1]
    elif failure=='nan':context[0,0,0,3]=np.nan
    elif failure=='affine':context[0,0,3,0]=1
    elif failure=='scale':context[0,0,:3,:3]*=1.1
    elif failure=='reflection':context[0,0,:3,0]*=-1
    with pytest.raises(ValueError):transfer(rig,motion,SOMASkeleton77(),mapping,offset,context_local=context)
