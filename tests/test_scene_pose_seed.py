import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_pose_seed import tapered_pose_parameters
from scene_fit_initialization import recover_controls
from support_contact_v5 import correction_basis


def test_pose_seed_remains_recoverable_under_original_spline_and_bounds():
    base=np.repeat(np.eye(3)[None],3,axis=0);guide=base.copy()
    guide[0]=Rotation.from_rotvec([.3,-.1,.05]).as_matrix();guide[1]=Rotation.from_rotvec([.04,.02,0]).as_matrix()
    basis,knots=correction_basis(80,8);limits=np.array([.7,.1]);editable=[0,1]
    rotations,record=tapered_pose_parameters(base,guide,editable,limits,1,basis,knots,24,48,16)
    source=np.repeat(base[None],80,axis=0);seed=source.copy();seed[:,editable]=source[:,editable]@rotations
    _,proof=recover_controls(source,seed,editable,limits,1,True,basis)
    assert proof['maximum_recovered_rotation_vector_error_rad']<1e-12
    vectors=Rotation.from_matrix(rotations.reshape(-1,3,3)).as_rotvec().reshape(80,2,3)
    assert np.all(np.linalg.norm(vectors,axis=-1)<limits)
    np.testing.assert_allclose(seed[32],guide,atol=1e-12)
    np.testing.assert_allclose(seed[:,2],source[:,2],atol=0)
    assert max(np.linalg.norm(vectors[0],axis=-1))<1e-12
    assert record['frame_weights'][32]==pytest.approx(1.)


def test_out_of_budget_pose_and_invalid_interval_rejected():
    reference=np.eye(3)[None];guide=Rotation.from_rotvec([[1.,0,0]]).as_matrix();basis,knots=correction_basis(20,8)
    with pytest.raises(ValueError,match='budgets'):
        tapered_pose_parameters(reference,guide,[0],[.5],1,basis,knots,4,10,4)
    with pytest.raises(ValueError,match='interval'):
        tapered_pose_parameters(reference,reference,[0],[.5],1,basis,knots,4,30,4)
