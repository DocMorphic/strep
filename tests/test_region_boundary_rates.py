import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_region_boundary_rates import rate_steps


def test_decoded_rate_step_preserves_rotation_wrap_and_constant_body_rate():
    track=Rotation.from_euler('z',[170,179,188,197],degrees=True).as_matrix()[:,None]
    rates=rate_steps(track,30)
    np.testing.assert_allclose(rates[:,:,2],np.deg2rad(270),atol=1e-12)
    np.testing.assert_allclose(np.diff(rates,axis=0),0,atol=1e-12)
