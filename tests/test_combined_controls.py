import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT, read
from correct_stance import load_motion
from combined_controls import combine, screen


@pytest.mark.parametrize('seed',[11,22,55])
def test_combination_preserves_both_targets_and_lower_body(seed):
    from kimodo.skeleton import SOMASkeleton77
    source=load_motion(ROOT/f'reports/control-calibration-v1/text/stance/neutral/seed-{seed}/corrected.npz')
    original={k:v.copy() for k,v in source.items()};skeleton=SOMASkeleton77()
    for arm,lean in [(10,20),(20,10),(30,0),(45,20)]:
        changed,report=combine(source,skeleton,arm,lean)
        assert max(report['target_errors_degrees'].values())<.001
        assert report['root_max_change_m']==0 and report['lower_body_max_change_m']<1e-6
        assert report['contacts_unchanged']
        parents=skeleton.joint_parents.numpy()[1:]
        before=np.linalg.norm(source['posed_joints'][:,1:]-source['posed_joints'][:,parents],axis=-1)
        after=np.linalg.norm(changed['posed_joints'][:,1:]-changed['posed_joints'][:,parents],axis=-1)
        np.testing.assert_allclose(before,after,atol=2e-6)
    for key in source:np.testing.assert_array_equal(source[key],original[key])


def test_failed_baseline_or_seam_cannot_pass_combination_screen():
    rules=read(ROOT/'benchmarks/combined-controls-v1.json')
    report={'target_errors_degrees':{'arm':0,'lean':0},'root_max_change_m':0,
        'lower_body_max_change_m':0,'contacts_unchanged':True,'max_local_edit_degrees':0}
    assert screen(report,[],True,rules)==[]
    assert 'neutral_baseline_quality' in screen(report,[],False,rules)
    assert 'pose_seam' in screen(report,['pose_seam'],True,rules)
