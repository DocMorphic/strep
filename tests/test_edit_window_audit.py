import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_scene_edit_window import summarize


def rows():
    return [dict(frame=i/4, joint_position_error_m=0., basis_error=0., skin_position_error_m=0.)
            for i in range(17)]


def test_boundary_changes_are_not_hidden_by_locked_segment_success():
    values = rows(); values[3]['skin_position_error_m'] = .01
    report = summarize(values, [1, 3], 5)
    assert report['locked_segments']['samples'] == 2
    assert report['boundary_segments']['samples'] == 6
    assert report['edited_window']['samples'] == 9
    assert report['locked_segments']['within_numerical_tolerance']
    assert not report['all_outside_times']['within_numerical_tolerance']


def test_no_locked_coverage_is_not_a_preservation_pass():
    report = summarize(rows(), [0, 4], 5)
    assert report['locked_segments']['samples'] == 0
    assert report['locked_segments']['within_numerical_tolerance'] is None


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'negative', 'nan', 'bool'])
def test_incomplete_clock_or_invalid_error_rejected(change):
    values = rows()
    if change == 'missing': values.pop()
    elif change == 'duplicate': values[1]['frame'] = 0.
    else: values[0]['skin_position_error_m'] = {'negative': -1., 'nan': float('nan'), 'bool': True}[change]
    with pytest.raises(ValueError): summarize(values, [1, 3], 5)


def test_publisher_recomputes_window_evidence_and_rejects_missing_or_stale_data():
    import copy
    from package_scene_fit_review import window_assessment
    from audit_scene_edit_window import POSITION_TOLERANCE_M,BASIS_TOLERANCE
    values=rows()
    report=dict(result_sha256='result',window=[1,3],frames=5,position_tolerance_m=POSITION_TOLERANCE_M,basis_tolerance=BASIS_TOLERANCE,rows=values,groups=summarize(values,[1,3],5))
    assert window_assessment(report,[1,3],5,'result')['locked_segments']['within_numerical_tolerance']
    for key,value in [('result_sha256','old'),('window',[0,4]),('frames',6),('position_tolerance_m',.1),('groups',{})]:
        changed=copy.deepcopy(report);changed[key]=value
        with pytest.raises(ValueError):window_assessment(changed,[1,3],5,'result')
    with pytest.raises(ValueError):window_assessment(None,[1,3],5,'result')
    changed=copy.deepcopy(report);changed['rows'][0]['skin_position_error_m']=.1
    with pytest.raises(ValueError):window_assessment(changed,[1,3],5,'result')
