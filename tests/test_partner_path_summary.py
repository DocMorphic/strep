from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from compare_partner_paths import full_curve


def rows():
    return [dict(frame=i*.5,collision=[dict(max_depth_m=.001),dict(max_depth_m=.002)],floor_depth_m=[0.,.003]) for i in range(299)]


def test_half_frame_peak_cannot_be_hidden_by_integer_samples():
    data=rows();data[133]['collision'][1]['max_depth_m']=.022
    result=full_curve(data)
    assert result['max_depth_m']==.022 and result['peak_frame']==66.5
    assert result['failed_frames']==[66.5] and result['floor_max_m']==.003


@pytest.mark.parametrize('fault',['missing','reordered','one_actor','nan','negative'])
def test_incomplete_or_invalid_full_geometry_is_rejected(fault):
    data=rows()
    if fault=='missing':data.pop()
    if fault=='reordered':data.reverse()
    if fault=='one_actor':data[1]['collision'].pop()
    if fault=='nan':data[1]['floor_depth_m'][0]=float('nan')
    if fault=='negative':data[1]['collision'][0]['max_depth_m']=-.001
    with pytest.raises(ValueError):full_curve(data)
