import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from support_release_hold import hold_until_release
from support_clip_boundary import retain_end_support
from support_clip_start import retain_start_support


def draft():
    return dict(edge_fade_frames=3,confirmed=False,intervals=[dict(side='Left',start_frame=2,end_frame_exclusive=8),
        dict(side='Right',start_frame=0,end_frame_exclusive=10)],guides={
        'Left':dict(weights=[0,0,.25,.75,1,1,.75,.25,0,0],anchors_xz_m=[[1.,2.]]*10),
        'Right':dict(weights=[.25,.75,1,1,1,1,1,1,.75,.25],anchors_xz_m=[[3.,4.]]*10)})


def test_preserves_onset_anchors_labels_outside_and_input():
    source=draft();original=copy.deepcopy(source);result=hold_until_release(source,10)
    np.testing.assert_allclose(result['guides']['Left']['weights'],[0,0,.25,.75,1,1,1,1,0,0])
    assert source==original and result['guides']['Right']==original['guides']['Right']
    assert result['intervals']==original['intervals'] and result['guides']['Left']['anchors_xz_m']==original['guides']['Left']['anchors_xz_m']
    assert [r['frame'] for r in result['release_hold_policy']['changed_weights']]==[6,7]
    assert not result['confirmed'] and result['release_hold_policy']['extrapolated_frames']==0


def test_respects_existing_clipped_start_and_end_policies():
    s=draft();s['intervals'][0]['start_frame']=0;s['guides']['Left']['weights']=[.25,.75,1,1,1,1,.75,.25,0,0]
    s=retain_start_support(retain_end_support(s,10),10);r=hold_until_release(s,10)
    np.testing.assert_allclose(r['guides']['Left']['weights'],[1]*8+[0,0])
    assert r['guides']['Right']==s['guides']['Right']


def test_short_interval_does_not_remove_onset():
    s=draft();s['intervals']=s['intervals'][:1];s['intervals'][0].update(start_frame=2,end_frame_exclusive=5)
    s['guides']['Left']['weights']=[0,0,.25,.75,.25,0,0,0,0,0]
    np.testing.assert_allclose(hold_until_release(s,10)['guides']['Left']['weights'],[0,0,.25,.75,1,0,0,0,0,0])


@pytest.mark.parametrize('change',['custom','nan','overlap','outside','bad_anchor','zero_fade'])
def test_rejects_custom_or_invalid_guides(change):
    s=draft()
    if change=='custom':s['guides']['Left']['weights'][7]=.4
    elif change=='nan':s['guides']['Left']['weights'][7]=float('nan')
    elif change=='overlap':s['intervals'].append(copy.deepcopy(s['intervals'][0]))
    elif change=='outside':s['intervals'][0]['end_frame_exclusive']=11
    elif change=='bad_anchor':s['guides']['Left']['anchors_xz_m']=[[1,2]]
    else:s['edge_fade_frames']=0
    with pytest.raises(ValueError):hold_until_release(s,10)
