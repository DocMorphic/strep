import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_primitive_grasp_fit import contact_mask


def test_dense_contact_interval_includes_fractional_release_boundary():
    frames=np.array([59.75,60,60.25,119.75,120,120.25,120.75,121,121.25])
    np.testing.assert_array_equal(contact_mask(frames,dict(start_frame=60,end_frame=120)),[False,True,True,True,True,True,True,False,False])
