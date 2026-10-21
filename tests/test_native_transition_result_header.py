"""Cheap scope rejection never substitutes for full transition verification."""
import copy
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_transition_result_header import validate_header

SCHEMA = 'strep-native-transition-scene-fit-v1'


def valid_header():
    return dict(schema=SCHEMA, status='complete',
        parent_decisions_apply_to_original_only=True,
        native_root_references_consistent=True, root_observations_are_native_only=True,
        original_clip_libraries_retained=True, source_phases_and_boundary_tangents_protected=True,
        original_selected=True, quality_approved=False, training_admitted=False,
        release_approved=False, engine_playback_verified=False)


def test_header_only_does_not_approve_or_mutate_observations():
    result=valid_header();result.update(checks={'geometry':False},controls=['not validated here'])
    before=copy.deepcopy(result)
    assert validate_header(result,SCHEMA) is None
    assert result==before and result['checks']['geometry'] is False


@pytest.mark.parametrize('name',[k for k in valid_header() if k not in ('schema','status')])
@pytest.mark.parametrize('fault',['missing','opposite',None,0,1,'true'])
def test_inconsistent_or_untyped_flags_reject(name,fault):
    result=valid_header()
    if fault=='missing':del result[name]
    elif fault=='opposite':result[name]=not result[name]
    else:result[name]=fault
    with pytest.raises(ValueError,match=name):validate_header(result,SCHEMA)


@pytest.mark.parametrize('name',['schema','status'])
@pytest.mark.parametrize('fault',[None,True,'unexpected'])
def test_wrong_schema_or_incomplete_status_reject(name,fault):
    result=valid_header();result[name]=fault
    with pytest.raises(ValueError,match=name):validate_header(result,SCHEMA)


@pytest.mark.parametrize('value',[None,[],True,0,'complete'])
def test_nonobject_header_rejects(value):
    with pytest.raises(ValueError,match='object required'):validate_header(value,SCHEMA)
