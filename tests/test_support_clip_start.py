import copy
import json
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_clip_start import retain_start_support


def fixture():
    return dict(edge_fade_frames=3,confirmed=False,intervals=[dict(side='Left',start_frame=0,end_frame_exclusive=6),
        dict(side='Right',start_frame=2,end_frame_exclusive=10)],guides={
        'Left':dict(weights=[.25,.75,1.,1.,.75,.25,0,0,0,0]),
        'Right':dict(weights=[0,0,.25,.75,1,1,1,1,1,1])})


def test_start_ramp_removed_but_real_release_onset_and_source_preserved():
    source=fixture();result=retain_start_support(source,10)
    np.testing.assert_allclose(result['guides']['Left']['weights'],[1,1,1,1,.75,.25,0,0,0,0])
    assert result['guides']['Right']==source['guides']['Right'] and source==fixture()
    assert result['intervals']==source['intervals'] and not result['confirmed']
    assert json.loads(json.dumps(result,allow_nan=False))==result


def test_both_clipped_edges_keep_the_already_repaired_ending():
    source=fixture();source['intervals']=[dict(side='Left',start_frame=0,end_frame_exclusive=10)]
    source['guides']['Left']['weights']=[.25,.75]+[1.]*8
    np.testing.assert_allclose(retain_start_support(source,10)['guides']['Left']['weights'],np.ones(10))


def test_short_interval_keeps_overlapping_observed_release():
    source=fixture();source['intervals']=[dict(side='Left',start_frame=0,end_frame_exclusive=4)]
    source['guides']['Left']['weights']=[.25,.75,.75,.25]+[0.]*6
    np.testing.assert_allclose(retain_start_support(source,10)['guides']['Left']['weights'],[1,1,.75,.25]+[0.]*6)


@pytest.mark.parametrize('change',['nan','negative_fade','invalid_end','unknown_side','custom_weight'])
def test_invalid_inputs_rejected(change):
    source=fixture()
    if change=='nan':source['guides']['Left']['weights'][0]=float('nan')
    elif change=='negative_fade':source['edge_fade_frames']=-3
    elif change=='invalid_end':source['intervals'][0]['end_frame_exclusive']=11
    elif change=='custom_weight':source['guides']['Left']['weights'][0]=.1
    else:source['intervals'][0]['side']='Missing'
    with pytest.raises(ValueError):retain_start_support(source,10)
