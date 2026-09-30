import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reserve_publication_geometry import checked_summary


def rows():
    source=[dict(sample=i,time_s=i/120,directions=[dict(maximum_depth_m=.02),dict(maximum_depth_m=.01)],floor_depth_m=[.001,.002]) for i in range(3)]
    candidate=[dict(sample=i,time_s=i/120,directions=[dict(max_depth_m=.019),dict(max_depth_m=.009)],floor_depth_m=[.001,.002],
        source_depth_m=.02,candidate_depth_m=.019,cap_excess_m=0.,floor_increase_m=0.) for i in range(3)]
    summary=dict(samples=3,fresh_directional_queries=6,source_peak_m=.02,candidate_peak_m=.019,source_failed_times=3,candidate_failed_times=3,maximum_cap_excess_m=0.,maximum_floor_increase_m=0.)
    return source,candidate,summary


def test_passing_local_step_does_not_imply_clearance():
    source,candidate,summary=rows()
    assert checked_summary(source,candidate,summary)==[]
    assert summary['candidate_failed_times']==3


@pytest.mark.parametrize('fault',['missing_sample','time','direction','depth','floor','nan','summary','count'])
def test_incomplete_or_inconsistent_geometry_cannot_be_reused(fault):
    source,candidate,summary=rows()
    if fault=='missing_sample':candidate.pop()
    if fault=='time':candidate[1]['time_s']+=.0001
    if fault=='direction':candidate[0]['directions'].pop()
    if fault=='depth':candidate[0]['candidate_depth_m']=.018
    if fault=='floor':candidate[0]['floor_depth_m'][0]=.1
    if fault=='nan':candidate[0]['directions'][0]['max_depth_m']=float('nan')
    if fault=='summary':summary['candidate_peak_m']=.018
    if fault=='count':summary['fresh_directional_queries']=3
    with pytest.raises(ValueError):checked_summary(source,candidate,summary)


def test_measured_regression_or_insufficient_improvement_remains_failed():
    source,candidate,summary=rows()
    for row in candidate:
        row['directions'][0]['max_depth_m']=.021;row['candidate_depth_m']=.021;row['cap_excess_m']=.001
        row['floor_depth_m'][0]=.0011;row['floor_increase_m']=.0001
    summary.update(candidate_peak_m=.021,maximum_cap_excess_m=.001,maximum_floor_increase_m=.0001)
    assert checked_summary(source,candidate,summary)==['fresh_surface_caps','floor_regression','no_peak_improvement']
