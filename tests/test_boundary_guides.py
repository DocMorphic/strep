import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT
from study_boundary_guides import guide_variant,diagnostic


@pytest.mark.parametrize('mode',['baseline','smooth','dense','smooth_dense'])
def test_guide_variants_preserve_world_pose_and_canonicalize_smooth_origin(mode):
    original=dict(np.load(ROOT/'reports/rig-jobs/20260926-231829-75e87cd5/source/guide-motion.npz'))
    frozen={k:v.copy() for k,v in original.items()};guide,frames,offset=guide_variant(original,mode)
    for k in ('root_positions','posed_joints'):np.testing.assert_allclose(guide[k]+offset,original[k],atol=1e-7)
    for k in original:assert np.array_equal(original[k],frozen[k])
    assert frames==sorted(set(frames)) and len(frames)==(16 if 'dense' in mode else 4)
    assert set([0,1,49,50])<=set(frames)
    if 'smooth' in mode:
        np.testing.assert_allclose(guide['smooth_root_pos'][0,[0,2]],0,atol=1e-7)
        np.testing.assert_array_equal(guide['smooth_root_pos'][:,1],guide['root_positions'][:,1])
    else:assert np.array_equal(offset,np.zeros(3))


def test_diagnostic_distinguishes_global_shift_from_pose_error():
    expected=np.zeros((4,30,3));found=expected+[.02,.01,0]
    d=diagnostic(found,expected);assert d['max_root_relative_error_m']<1e-12
    found[:,8,2]+=.04
    assert diagnostic(found,expected)['max_root_relative_error_m']==pytest.approx(.04)
