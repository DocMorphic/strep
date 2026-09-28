import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from motion_edit_bounds import check,enforce,EditBoundsError


def budget(angle=30,speed=150):
    return dict(joint_rotation_degrees={'hand':angle},joint_correction_speed_degrees_s={'hand':speed},root_components_m=[.04,.12,.04],root_correction_speed_m_s=.45)


def clip(angles):return Rotation.from_euler('z',angles,degrees=True).as_matrix()[:,None]


def test_wrapped_rotations_and_input_speed_are_not_edit_speed():
    a=clip([179,-179,140]);b=clip([-179,-177,142]);roots=np.zeros((3,3))
    result=enforce(a,b,roots,roots,[0,1/30,2/30],['hand'],budget(angle=3,speed=0))
    assert result['joints'][0]['max_edit_degrees']==pytest.approx(2)


def test_actual_time_and_frozen_joint_budget():
    a=clip([0,0]);b=clip([0,5]);roots=np.zeros((2,3))
    assert check(a,b,roots,roots,[0,1/30],['hand'],budget())['passed']
    with pytest.raises(EditBoundsError) as error:enforce(a,b,roots,roots,[0,1/60],['hand'],budget())
    assert error.value.report['violations'][0]['kind']=='joint_correction_speed'
    assert not check(a,b,roots,roots,[0,1],['hand'],budget(angle=0))['passed']


def test_root_and_motion_integrity_fail_closed():
    a=clip([0,0]);roots=np.zeros((2,3));candidate=roots.copy();candidate[1,0]=.05
    report=check(a,a,roots,candidate,[0,1/30],['hand'],budget())
    assert {v['kind'] for v in report['violations']}=={'root_component','root_correction_speed'}
    with pytest.raises(ValueError,match='proper rotations'):check(a,a*2,roots,roots,[0,1],['hand'],budget())
    with pytest.raises(ValueError,match='timestamps'):check(a,a,roots,roots,[0,0],['hand'],budget())
    incomplete=budget();incomplete['joint_rotation_degrees']={}
    with pytest.raises(ValueError,match='Every joint'):check(a,a,roots,roots,[0,1],['hand'],incomplete)
