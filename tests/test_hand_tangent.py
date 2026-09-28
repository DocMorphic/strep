import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from build_soma_preview import ASSET
from scene_solver_context import compile_context
from palm_contacts import hand_tangent_track,surface_normal_track
from scene_constraints import transform_motion


def test_projected_tangent_orthogonal_and_rigid_transform_equivariant():
    scene=read(ROOT/'reports/scene-fit-fixtures-v3/high-five.json');skin=dict(np.load(ASSET));a=scene['actors']['A'];motion=dict(np.load(ROOT/a['motion']))
    actor=transform_motion(motion,a['transform']);t=hand_tangent_track(actor,skin,16974,'RightHand');n=surface_normal_track(actor,skin,16974)
    np.testing.assert_allclose(np.sum(t*n,axis=1),0,atol=1e-12);np.testing.assert_allclose(np.linalg.norm(t,axis=1),1,atol=1e-12)
    rotated=transform_motion(motion,scene['actors']['B']['transform']);other=hand_tangent_track(rotated,skin,16974,'RightHand')
    np.testing.assert_allclose(other,t*[-1,1,-1],atol=1e-12)


def test_tangent_context_rejects_conflicting_hand_frame():
    scene=read(ROOT/'reports/scene-fit-fixtures-v3/high-five.json');skin=dict(np.load(ASSET));c=scene['contacts'][0]
    c['tangent_target']=dict(space='world',direction=[0,1,0]);context=compile_context(scene,'A',[c['id']],skin)
    assert len(context['normals'][0]['knuckle_joints'])==4
    c['tangent_target']['direction']=[0,0,1]
    with pytest.raises(ValueError,match='orthogonal'):compile_context(scene,'A',[c['id']],skin)
