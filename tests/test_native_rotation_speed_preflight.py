"""Real scene permissions, frozen keys and pre-fit rejection without export."""
from pathlib import Path
import sys
import copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_fit import prepare
from test_native_scene_boundary_edit import request
from native_scene_edit import SceneEdits
from native_scene_boundary_edit import BoundarySceneEdits
from native_scene_fit import SceneProblem
from native_rotation_speed_preflight import assess_scene, SpeedPreflightSceneProblem, IncompatibleRotationSpeed
from strep import sha256


def edited_root(tmp_path, boundaries=False, protected=()):
    source,_,contacts,p,_,scene,_=prepare(tmp_path,rotation=True)
    p['actors']['A']['tracks'][0]['node']=0
    p['actors']['A']['protected_s']=list(protected)
    edits=BoundarySceneEdits(request(p,'edit','edit'),scene,sha256(contacts)) if boundaries else SceneEdits(p,scene,sha256(contacts))
    return source,scene,edits


def test_unedited_rotation_keeps_zero_budget_and_every_native_neighbor(tmp_path):
    source,_,_,_,_,_,edits=prepare(tmp_path,rotation=True); raw=source.read_bytes()
    bounds,report=assess_scene(edits,{('A',0):20})
    row=report['tracks'][0]
    assert len(bounds['A',0])==10 and row['neighbor_comparisons']==10
    assert row['permitted_edit_caps_degrees']==[0]*11 and report['speed_limits_proven_incompatible']
    np.testing.assert_allclose(bounds['A',0],40,atol=3e-5)
    assert source.read_bytes()==raw and not report['source_changed']


@pytest.mark.parametrize('boundaries',[False,True])
def test_actual_boundary_permissions_change_only_the_allowed_caps(tmp_path,boundaries):
    _,_,edits=edited_root(tmp_path,boundaries)
    bounds,report=assess_scene(edits,{('A',0):0}); caps=report['tracks'][0]['permitted_edit_caps_degrees']
    assert caps[1:-1]==[5.0001]*9 and caps[0]==caps[-1]==(5.0001 if boundaries else 0)
    assert report['speed_limits_proven_incompatible']==(not boundaries)
    # Passing pairwise checks for the boundary-enabled case is not a global
    # constant-trajectory proof: the source travels a full 80 degrees.
    if boundaries: np.testing.assert_array_equal(bounds['A',0],np.zeros(10))


def test_protected_interpolation_keys_have_no_serialization_allowance(tmp_path):
    _,_,edits=edited_root(tmp_path,True,[[.853725,.853725]])
    _,report=assess_scene(edits,{('A',0):0}); row=report['tracks'][0]
    entry=edits.actors['A']['tracks'][0]; frozen=set(range(11))-set(entry['ids'])
    assert frozen and all(row['permitted_edit_caps_degrees'][i]==0 for i in frozen)
    assert report['speed_limits_proven_incompatible'] and row['serialization_allowance_degrees']==.0001


def test_incompatible_limit_stops_before_scene_population_or_any_export(tmp_path,monkeypatch):
    source,scene,edits=edited_root(tmp_path); raw=source.read_bytes()
    def unexpected(*args,**kwargs):raise AssertionError('Expensive scene initialization must not run')
    monkeypatch.setattr(SceneProblem,'__init__',unexpected)
    with pytest.raises(IncompatibleRotationSpeed) as caught:
        SpeedPreflightSceneProblem(scene,edits,rotation_speed_limits={('A',0):0})
    assert caught.value.report['speed_limits_proven_incompatible'] and source.read_bytes()==raw


def test_nonexcluded_limit_initializes_the_existing_scene_problem(tmp_path):
    _,scene,edits=edited_root(tmp_path)
    problem=SpeedPreflightSceneProblem(scene,edits,rotation_speed_limits={('A',0):100})
    assert problem.scene is scene and problem.size==edits.size
    assert not problem.speed_preflight['speed_limits_proven_incompatible']
    assert 'neither enforces' in problem.speed_preflight['scope']


@pytest.mark.parametrize('fault',['empty','actor','bool-node','missing-node','missing-channel','bool-limit','negative-limit','nan-limit','key'])
def test_invalid_limits_reject(tmp_path,fault):
    _,_,_,_,_,_,edits=prepare(tmp_path,rotation=True); limits={('A',0):100}
    if fault=='empty':limits={}
    elif fault=='actor':limits={('B',0):100}
    elif fault=='bool-node':limits={('A',False):100}
    elif fault=='missing-node':limits={('A',999):100}
    elif fault=='missing-channel':
        limits={('A',5):100}
        assert not any(c[:2]==(5,'rotation') for c in edits.scene.actors['A']['sampler'].channels)
    elif fault=='bool-limit':limits={('A',0):True}
    elif fault=='negative-limit':limits={('A',0):-1}
    elif fault=='nan-limit':limits={('A',0):float('nan')}
    else:limits={'A':100}
    with pytest.raises(ValueError):assess_scene(edits,limits)


def test_distinct_scene_instance_rejects_before_fitting(tmp_path):
    _,scene,edits=edited_root(tmp_path)
    with pytest.raises(ValueError):SpeedPreflightSceneProblem(copy.copy(scene),edits,rotation_speed_limits={('A',0):100})
