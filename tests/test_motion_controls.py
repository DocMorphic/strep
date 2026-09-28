import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT
from correct_stance import load_motion
from motion_controls import edit,edit_diagnostics


@pytest.fixture(scope='module')
def fixture():
    from kimodo.skeleton import SOMASkeleton77
    return load_motion(ROOT/'reports/profile-pilot-v1/stance/neutral/seed-11/corrected.npz'),SOMASkeleton77()


@pytest.mark.parametrize('control,values',[('arm',[20,45,70]),('lean',[0,10,20])])
def test_controls_hit_target_without_changing_root_feet_or_contact(fixture,control,values):
    source,skeleton=fixture;original={k:v.copy() for k,v in source.items()}
    for target in values:
        changed,_=edit(source,skeleton,control,target)
        report=edit_diagnostics(source,changed,skeleton,control,target)
        assert report['target_error_degrees']<.001
        assert report['root_max_change_m']==0 and report['lower_body_max_change_m']<1e-6
        assert report['contacts_unchanged'] and report['unrelated_angle_change_degrees']<.001
        parents=skeleton.joint_parents.numpy()[1:]
        before=np.linalg.norm(source['posed_joints'][:,1:]-source['posed_joints'][:,parents],axis=-1)
        after=np.linalg.norm(changed['posed_joints'][:,1:]-changed['posed_joints'][:,parents],axis=-1)
        np.testing.assert_allclose(after,before,atol=2e-6)
        for key in source:np.testing.assert_array_equal(source[key],original[key])


def test_invalid_control_request_is_rejected(fixture):
    source,skeleton=fixture
    for control,target in [('strength',50),('arm',0),('lean',90),('arm',float('nan'))]:
        with pytest.raises(ValueError):edit(source,skeleton,control,target)
