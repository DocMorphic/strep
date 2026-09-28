import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read
from correct_stance import load_motion
from correct_loops import repeat_motion
from combined_controls import combine
from periodic_motion_controls import combine_periodic,cyclic_dynamics
from evaluate_grid import loop_screen


@pytest.mark.parametrize('seed',[11,22,55])
def test_periodic_wide_arms_preserve_targets_and_improve_seam(seed):
    from kimodo.skeleton import SOMASkeleton77
    skel=SOMASkeleton77();source=load_motion(ROOT/f'reports/control-calibration-v1/text/stance/neutral/seed-{seed}/corrected.npz')
    original={k:v.copy() for k,v in source.items()}
    previous,_=combine(source,skel,45,20)
    result,report=combine_periodic(source,skel,45,20)
    assert max(report['target_errors_degrees'].values())<.001
    assert report['root_max_change_m']==0 and report['lower_body_max_change_m']<1e-6
    assert report['contacts_unchanged']
    targets=read(ROOT/'benchmarks/acceptance-v0.json')['targets']
    metric=lambda data:loop_screen(repeat_motion(data,np.zeros(3),3),30,targets)['next_pose_prediction_rms_m']
    assert metric(result)<metric(previous)
    for key,value in cyclic_dynamics(previous).items():assert cyclic_dynamics(result)[key]<=value*1.1
    matrices=result['local_rot_mats']
    np.testing.assert_allclose(np.linalg.det(matrices),1,atol=2e-5)
    for key in source:np.testing.assert_array_equal(source[key],original[key])


def test_existing_compact_styles_are_identical():
    from kimodo.skeleton import SOMASkeleton77
    skel=SOMASkeleton77();source=load_motion(ROOT/'reports/control-calibration-v1/text/stance/neutral/seed-11/corrected.npz')
    for arm in [10,20,30]:
        before,_=combine(source,skel,arm,10);after,report=combine_periodic(source,skel,arm,10)
        assert not report['periodic_filter_applied']
        for key in before:np.testing.assert_array_equal(before[key],after[key])
