import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from restore_grasp_pose import elastic_row_layout,protected_pass,clearance_violation


def test_only_object_rows_get_elastic_metre_scaling():
    labels=['point:LeftHand','normal:grip','floor','object:ball','object:prop']
    order,scale,count=elastic_row_layout(labels)
    np.testing.assert_array_equal(order,[3,4,0,1,2]);np.testing.assert_allclose(scale,[.01,.01,1,1,1]);assert count==2


def test_geometry_slack_cannot_override_failed_protected_contact():
    config=dict(clearance_m=.002,object_clearance_m=.002,point_tolerance_m=.005,normal_tolerance_degrees=10.)
    audit=dict(rotation_norm_bounds_passed=True,minimum_floor_height_m=.002,contacts=[dict(error_m=.006)],normals=[dict(error_degrees=9.)],objects=[dict(minimum_clearance_m=.003)])
    assert clearance_violation(audit,config)==0 and not protected_pass(audit,config)
    audit['contacts'][0]['error_m']=.004;assert protected_pass(audit,config)
    audit['objects'][0]['minimum_clearance_m']=-.02;assert abs(clearance_violation(audit,config)-.022)<1e-12
