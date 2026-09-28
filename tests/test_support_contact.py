import sys
from pathlib import Path
import numpy as np
import torch
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_contact import rodrigues, intervals, infer_support
from build_soma_preview import ASSET
from strep import ROOT


def test_rotation_map_matches_scipy_and_has_finite_zero_gradient():
    v=torch.tensor([[0.,0.,0.],[.3,-.2,.4]],dtype=torch.float64,requires_grad=True)
    r=rodrigues(v)
    np.testing.assert_allclose(r.detach().numpy(),Rotation.from_rotvec(v.detach().numpy()).as_matrix(),atol=1e-12)
    r.sum().backward()
    assert torch.isfinite(v.grad).all()


def test_contact_intervals_retain_clip_boundaries_and_one_frame_breaks():
    assert intervals([True,True,False,True,False,True])==[(0,2),(3,4),(5,6)]
    assert intervals([])==[]


def test_geometry_inference_does_not_assign_airborne_supports():
    source=dict(np.load(ROOT/'reports/body-contact-v1/takes/crawl-seed-11/limb/motion.npz'))
    still={k:np.repeat(v[33:34],12,axis=0) for k,v in source.items()}
    skin=dict(np.load(ASSET)); ground=infer_support(still,skin)
    assert any(c['active'].any() for c in ground.values())
    elevated={k:v.copy() for k,v in still.items()}
    elevated['root_positions'][:,1]+=3;elevated['posed_joints'][:,:,1]+=3
    air=infer_support(elevated,skin)
    assert all(not c['active'].any() for c in air.values())
    assert all(not c['weights'].any() for c in air.values())


def test_short_geometric_touches_are_not_sustained_supports():
    source=dict(np.load(ROOT/'reports/body-contact-v1/takes/crawl-seed-11/limb/motion.npz'))
    short={k:np.repeat(v[33:34],3,axis=0) for k,v in source.items()}
    assert all(not c['active'].any() for c in infer_support(short,dict(np.load(ASSET))).values())
