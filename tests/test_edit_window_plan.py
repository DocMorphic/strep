import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from plan_scene_edit_window import plan


def rows():
    return [dict(frame=i/4, minimum_floor_m=.01, object_clearances_m={'box': .01},
                 geometry_passed=True) for i in range(25)]


def test_locked_failure_requires_scope_change_even_if_recorded_pass_is_wrong():
    values = rows()
    values[3]['object_clearances_m']['box'] = -.03
    result = plan(values, [2, 4], 7, .002, .002)
    assert result['locked_geometry_conflict']
    assert result['failure_counts'] == dict(locked_segments=1, boundary_segments=0, edited_window=0)
    assert result['suggested_geometry_envelope'] == [0, 4]
    assert result['requested_window'] == [2, 4]


def test_boundary_failure_can_move_but_suggestion_includes_both_keys():
    values = rows()
    values[7]['minimum_floor_m'] = -.01
    result = plan(values, [2, 4], 7, .002, .002)
    assert not result['locked_geometry_conflict']
    assert result['failure_counts']['boundary_segments'] == 1
    assert result['suggested_geometry_envelope'] == [1, 4]


def test_interior_failure_does_not_request_larger_scope():
    values = rows()
    values[12]['minimum_floor_m'] = -.01
    result = plan(values, [2, 4], 7, .002, .002)
    assert result['sampled_failures'] == 1
    assert not result['changes_requested_scope']
    assert not result['locked_geometry_conflict']


def test_no_observed_failures_is_not_new_quality_approval():
    result = plan(rows(), [2, 4], 7, .002, .002)
    assert result['sampled_failures'] == 0
    assert result['suggested_geometry_envelope'] == [2, 4]
    assert 'does not guarantee' in result['scope']


@pytest.mark.parametrize('failure', ['missing', 'nan', 'threshold'])
def test_invalid_evidence_rejected(failure):
    values = rows()
    if failure == 'missing': values.pop()
    if failure == 'nan': values[0]['minimum_floor_m'] = float('nan')
    with pytest.raises(ValueError):
        plan(values, [2, 4], 7, -.1 if failure == 'threshold' else .002, .002)


def test_held_endpoint_and_adjoining_failure_are_immutable_and_need_extra_margin():
    values=rows()
    values[7]['minimum_floor_m']=-.01  # 1.75: both keys held
    values[8]['minimum_floor_m']=-.01  # 2: selected but held
    values[9]['minimum_floor_m']=-.01  # 2.25: can change via key 3
    result=plan(values,[2,4],7,.002,.002,preserve_boundary_keys=True)
    assert result['immutable_geometry_failures']==2
    assert result['failure_counts']==dict(locked_segments=0,boundary_segments=1,edited_window=2)
    assert result['suggested_geometry_envelope']==[0,4]
    assert result['preserve_boundary_keys']


def test_boundary_envelope_clamps_at_clip_edges_and_keeps_interior_scope():
    values=rows();values[0]['minimum_floor_m']=-.01;values[-1]['minimum_floor_m']=-.01
    result=plan(values,[2,4],7,.002,.002,preserve_boundary_keys=True)
    assert result['suggested_geometry_envelope']==[0,6]
    values=rows();values[12]['minimum_floor_m']=-.01
    result=plan(values,[2,4],7,.002,.002,preserve_boundary_keys=True)
    assert result['suggested_geometry_envelope']==[2,4]
    assert result['immutable_geometry_failures']==0


def test_boundary_policy_is_bound_to_executed_recipe(tmp_path):
    from plan_scene_edit_window import boundary_policy
    from strep import save,sha256
    recipe=tmp_path/'recipe.json'
    for localization,expected in [(None,False),({'outside_keys':2},False),({'locked_boundary_keys':[2,4]},True)]:
        save(recipe,dict(localization=localization))
        save(tmp_path/'result.json',dict(recipe_sha256=sha256(recipe)))
        assert boundary_policy(tmp_path)==expected
    save(recipe,dict(localization=None))
    with pytest.raises(ValueError,match='recipe changed'):boundary_policy(tmp_path)
