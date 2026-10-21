"""Reported-time attribution must never turn a mistimed capture into a pass."""
from pathlib import Path
import copy,sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_geometry import closed_fixture
from test_native_scene_engine import mock_actor,serialized
from native_scene_contacts import SceneContacts
from native_import_clock_diagnostic import diagnose
from native_engine_contacts import imported_world
from native_scene_imported_skin import ImportedSceneSkin


def fixture(tmp_path):
    _,_,spec=closed_fixture(tmp_path);scene=SceneContacts(spec,tmp_path);a=scene.actors['A']
    times=[0.,.5,1.,2.];observed=mock_actor(a['rig'],a['sampler'],times)
    return a['rig'],a['sampler'],observed,times


def test_clean_capture_keeps_requested_and_reported_clocks_and_does_not_approve_quality(tmp_path):
    rig,reader,capture,times=fixture(tmp_path);before=copy.deepcopy(capture)
    result=diagnose(rig,reader,capture,times)
    assert result['requested_import_comparison_pass'] and result['bad_clock_indices']==[]
    assert result['maximum_native_shift_from_clock_m']==0
    assert not result['quality_approved'] and not result['release_approved'] and capture==before


def test_actual_time_pose_match_cannot_excuse_clock_failure(tmp_path):
    rig,reader,capture,times=fixture(tmp_path)
    later=mock_actor(rig,reader,[0.,.75,1.,2.])['frames'][1]
    later['requested_time_s']=.5;capture['frames'][1]=later;before=copy.deepcopy(capture)
    result=diagnose(rig,reader,capture,times)
    assert result['bad_clock_indices']==[1] and not result['requested_import_comparison_pass']
    assert result['rows'][1]['reported_time_pose_element_error']<1e-12
    assert result['rows'][1]['native_shift_from_clock_m']>0
    assert capture==before
    with pytest.raises(ValueError,match='clock'):imported_world(capture,times,ImportedSceneSkin(rig,capture).bone_map)


def test_near_endpoint_snap_stays_a_failed_clock(tmp_path):
    rig,reader,capture,times=fixture(tmp_path);times[-2]=2.-3.2e-8
    capture=mock_actor(rig,reader,times);capture['frames'][-2]=copy.deepcopy(capture['frames'][-1])
    capture['frames'][-2]['requested_time_s']=times[-2]
    result=diagnose(rig,reader,capture,times)
    assert result['bad_clock_indices']==[2] and not result['requested_clock_pass']
    assert len(result['rows'])==4 and result['rows'][2]['actual_time_s']==result['rows'][3]['actual_time_s']


def test_spatial_error_stays_visible_even_when_clock_matches(tmp_path):
    rig,reader,capture,times=fixture(tmp_path)
    for bone in capture['frames'][1]['bones']:bone[3][0]+=.01
    result=diagnose(rig,reader,capture,times)
    assert result['requested_clock_pass'] and not result['requested_import_comparison_pass']
    assert result['maximum_requested_skin_error_m']>.009
    assert result['maximum_reported_time_skin_error_m']==result['maximum_requested_skin_error_m']


@pytest.mark.parametrize('fault',['missing-frame','nan-clock','outside-clock','boolean-clock','missing-bone','displaced-mesh','wrong-binding','wrong-echo'])
def test_incomplete_or_corrupt_capture_cannot_approve_import(tmp_path,fault):
    rig,reader,capture,times=fixture(tmp_path);frame=capture['frames'][1]
    if fault=='missing-frame':capture['frames'].pop()
    elif fault=='nan-clock':frame['actual_time_s']=float('nan')
    elif fault=='outside-clock':frame['actual_time_s']=3.
    elif fault=='boolean-clock':frame['actual_time_s']=True
    elif fault=='missing-bone':frame['bones'].pop()
    elif fault=='displaced-mesh':frame['mesh_world'][0]['matrix'][3][0]+=.1
    elif fault=='wrong-binding':capture['bone_names'][0]='another'
    else:
        frame['requested_time_s']+=.001
        result=diagnose(rig,reader,capture,times)
        assert not result['requested_clock_pass'] and result['bad_clock_indices']==[1]
        return
    with pytest.raises(ValueError):diagnose(rig,reader,capture,times)
