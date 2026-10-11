import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from edit_floor_regions import floor_depths,localize


def test_protected_source_errors_are_separate_from_new_edit_errors():
    result=localize([.02,0,.02,0],[.02,.03,0,0],[0,.5,1,0],[0,.1,.2,.3],limit_m=.005)
    assert result['preexisting_protected_failures']==[0]
    assert result['newly_failed_edited_frames']==[1]
    assert result['recovered_edited_frames']==[2]
    assert result['protected']['frames']==[0,3]
    assert result['edited']['frames']==[1,2]
    assert result['maximum_protected_depth_change_m']==0
    assert not result['floor_screen_pass'] and not result['quality_approved'] and not result['release_approved']


def test_empty_region_and_exact_threshold_do_not_invent_zero_measurements():
    result=localize([.005,.005],[.005,.005],[1,1],[0,1],limit_m=.005)
    assert result['floor_screen_pass'] and result['protected']['count']==0
    assert result['protected']['source_maximum_depth_m'] is None
    assert result['maximum_protected_depth_change_m'] is None


@pytest.mark.parametrize('source,output,weights,times,limit',[
    ([],[],[],[],.005),([0],[0,0],[0],[0],.005),([-.01],[0],[0],[0],.005),
    ([0],[float('nan')],[0],[0],.005),([0],[0],[1.1],[0],.005),
    ([0,0],[0,0],[0,0],[0,0],.005),([0],[0],[0],[-1],.005),
    ([0],[0],[0],[0],True),([0],[0],[0],[0],float('inf'))])
def test_incomplete_or_invalid_measurements_rejected(source,output,weights,times,limit):
    with pytest.raises(ValueError):localize(source,output,weights,times,limit_m=limit)


def test_floor_height_is_explicit_and_complete_vertices_are_used():
    class Rig:
        def vertices(self,world):return np.array([[0,1,0],[0,-.1,0],[0,2,0]])+world[0,:3,3]
    worlds=np.tile(np.eye(4),(2,1,1,1));worlds[1,0,1,3]=.5
    np.testing.assert_allclose(floor_depths(Rig(),worlds,floor_y_m=.2),[.3,0],rtol=0,atol=1e-15)


def test_nonfinite_surface_cannot_be_screened_as_clean():
    class Rig:
        def vertices(self,world):return np.array([[0,float('nan'),0]])
    with pytest.raises(ValueError):floor_depths(Rig(),np.eye(4)[None,None])


def test_legacy_review_does_not_claim_missing_region_measurements():
    from rig_prompt_edit import review_info
    value=review_info(dict(raw_anchor_audit=dict(numerical_screen_passed=False,guides=[dict(maximum={})]),export=dict(floor_failed_frames=2),unchanged_frames=4))
    assert value['preexisting_protected_floor_failures'] is None
    assert value['newly_failed_edited_floor_frames'] is None


def test_review_exposes_separate_source_and_edit_failures():
    from rig_prompt_edit import review_info
    regions=localize([.02,0],[.02,.03],[0,1],[0,.1],limit_m=.005)
    value=review_info(dict(raw_anchor_audit=dict(numerical_screen_passed=False,guides=[dict(maximum={})]),export=dict(floor_failed_frames=2),unchanged_frames=1,floor_regions=regions))
    assert value['preexisting_protected_floor_failures']==1 and value['newly_failed_edited_floor_frames']==1
