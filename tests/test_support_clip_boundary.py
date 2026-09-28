from pathlib import Path
import json
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_clip_boundary import retain_end_support


def fixture():
    return dict(edge_fade_frames=3,confirmed=False,intervals=[
        dict(side='Left',start_frame=2,end_frame_exclusive=10),
        dict(side='Right',start_frame=1,end_frame_exclusive=7)],guides={
        'Left':dict(weights=[0.,0.,.25,.75,1.,1.,1.,1.,.75,.25],anchors_xz_m=[[0,0]]*10),
        'Right':dict(weights=[0.,.25,.75,1.,1.,.75,.25,0.,0.,0.],anchors_xz_m=[[1,1]]*10)})


def test_retains_clipped_end_without_changing_observed_release_or_source():
    source=fixture();result=retain_end_support(source,10)
    np.testing.assert_allclose(result['guides']['Left']['weights'],[0,0,.25,.75,1,1,1,1,1,1])
    assert result['guides']['Right']==source['guides']['Right']
    assert source==fixture() and result['intervals']==source['intervals']
    assert result['guides']['Left']['anchors_xz_m']==source['guides']['Left']['anchors_xz_m']
    assert len(result['boundary_policy']['changed_weights'])==2
    assert result['boundary_policy']['extrapolated_frames']==0 and not result['confirmed']
    assert json.loads(json.dumps(result,allow_nan=False))==result


def test_short_clipped_interval_retains_real_onset_ramp():
    source=fixture();source['intervals']=[dict(side='Left',start_frame=7,end_frame_exclusive=10)]
    source['guides']['Left']['weights']=[0.]*7+[.25,.75,.25]
    np.testing.assert_allclose(retain_end_support(source,10)['guides']['Left']['weights'][-3:],[.25,.75,1.])


@pytest.mark.parametrize('change', ['nan','negative_fade','invalid_end','unknown_side'])
def test_rejects_malformed_support_data(change):
    source=fixture()
    if change=='nan':source['guides']['Left']['weights'][-1]=float('nan')
    elif change=='negative_fade':source['edge_fade_frames']=-3
    elif change=='invalid_end':source['intervals'][0]['end_frame_exclusive']=11
    else:source['intervals'][0]['side']='Missing'
    with pytest.raises(ValueError):retain_end_support(source,10)
