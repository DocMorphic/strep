import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from build_soma_preview import ASSET
from scene_solver_context import compile_context,box_signed_distance
from support_contact_v6 import torch_box_depth


def test_box_penalty_matches_geometry_and_has_outward_gradient():
    rotation=Rotation.from_euler('y',31,degrees=True).as_matrix();origin=np.array([2.,1.,-3.]);size=np.array([.4,.8,1.])
    local=np.array([[.1,0,0],[.3,0,0],[0,.39,0]]);world=local@rotation.T+origin
    points=torch.tensor(world[None],requires_grad=True,dtype=torch.float64)
    depths=torch_box_depth(points,torch.tensor(origin[None]),torch.tensor(rotation[None]),torch.tensor(size))
    np.testing.assert_allclose(depths.detach()[0],np.maximum(0,-box_signed_distance(world,origin,rotation,size)),atol=1e-12)
    depths.square().sum().backward();local_gradient=points.grad.numpy()[0]@rotation
    assert local_gradient[0,0]<0 # descent pushes the point toward +X / outside
    np.testing.assert_allclose(local_gradient[1],0,atol=1e-12)
    assert torch.isfinite(points.grad).all()


def test_oriented_box_context_uses_actor_native_normal_and_geometry():
    scene=read(ROOT/'reports/scene-fit-fixtures-v2/box-seed-11.json');skin=dict(np.load(ASSET))
    rotation=Rotation.from_euler('y',90,degrees=True)
    scene['actors']['A']['transform']=dict(translation_m=[2,0,-1],rotation_xyzw=rotation.as_quat().tolist())
    context=compile_context(scene,'A',['left-grip','right-grip'],skin)
    np.testing.assert_allclose(context['normals'][0]['directions'][60],[0,0,-1],atol=1e-12)
    np.testing.assert_allclose(rotation.apply(context['boxes'][0]['positions_m'][60])+[2,0,-1],[0,.2,.55],atol=1e-12)
    assert len(context['normals'])==2


def test_explicit_high_five_normal_has_correct_local_direction():
    scene=read(ROOT/'reports/scene-fit-fixtures-v1/high-five.json');skin=dict(np.load(ASSET))
    c=scene['contacts'][1];c['normal_target']=dict(space='world',direction=[0,0,-1])
    context=compile_context(scene,'B',['B-meeting'],skin)
    np.testing.assert_allclose(context['normals'][0]['directions'][60],[0,0,1],atol=1e-12)
    c['normal_target']['direction']=[0,0,-2]
    with pytest.raises(ValueError):compile_context(scene,'B',['B-meeting'],skin)
