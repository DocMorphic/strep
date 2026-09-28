import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
from scipy.spatial.transform import Rotation
from study_breadth_partners import placement,point_metrics


def test_placement_preserves_height_and_initial_separation():
    root=np.array([2.,1.03,-3.])
    for actor,z in [('A',-.55),('B',.55)]:
        t=placement(root,actor)
        actual=Rotation.from_quat(t['rotation_xyzw']).apply(root)+t['translation_m']
        np.testing.assert_allclose(actual,[0,1.03,z],atol=1e-12)


def test_no_contact_has_no_timing_success_and_opposing_normals():
    a=np.zeros((6,3));b=a.copy();b[:,0]=.1
    normal=np.tile([0,0,1.],(6,1))
    result=point_metrics(a,b,normal,-normal,2,3)
    assert result['nearest_within_tolerance_timing_error_frames'] is None
    assert result['requested_frames_within_point_tolerance']==0
    assert result['requested_normal_error_max_degrees']==0
    b[5]=0
    result=point_metrics(a,b,normal,normal,2,3)
    assert result['nearest_within_tolerance_timing_error_frames']==2
    assert result['requested_normal_error_max_degrees']==180
