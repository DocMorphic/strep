import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_support_block_coverage import classify


def test_both_edge_endpoints_determine_coverage_without_hiding_untouched_peaks():
    rows=classify([.2,.3,.4,.5,.6],np.ones(6,bool),.1,[1,2])
    assert [r['coverage'] for r in rows]==['boundary','inside','boundary','untouched','untouched']
    assert [r['step_end_frame'] for r in rows]==[1,2,3,4,5]


def test_only_bilateral_support_edges_above_original_reporting_bin_are_included():
    rows=classify([.4,.101,.1005,.3,.5],[False,True,True,True,True,False],.1,[2,3])
    assert [r['step_end_frame'] for r in rows]==[4]
    assert rows[0]['coverage']=='boundary'


@pytest.mark.parametrize('edited',[[6],[-1],[1.5]])
def test_unknown_edit_frames_rejected(edited):
    with pytest.raises(ValueError):classify([.2]*5,[True]*6,.1,edited)
