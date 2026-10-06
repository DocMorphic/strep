"""Guard derivation and diagnostic scope; actual full-pose study is separate."""
import copy
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from native_geometry_source_blockers import scope_for, face_primitive
from native_geometry_failure_profile import editable


@pytest.fixture
def inputs():
    channel=(6,'rotation',np.array([0.,.25,.5,.75,1.]))
    source=SimpleNamespace(actors={'A':{'sampler':SimpleNamespace(channels=[channel])},'B':{'sampler':SimpleNamespace(channels=[channel])}})
    recipe=dict(schema='strep-native-transition-scene-fit-v1',actors={'A':dict(window_s=[0.,1.],protected_s=[[.4,.6]],tracks=[dict(node=6,path='rotation')])})
    return recipe,source,dict(bridge_interval_s=[0.,1.])


def test_selected_channel_tangent_intervals_and_context_remain_protected(inputs):
    recipe,source,sealed=inputs; before=copy.deepcopy(recipe)
    scope=scope_for(recipe,source,sealed,'a'*64)
    assert scope['actors']['A']['protected_s']==[[.4,.6],[0.,.25],[.75,1.]]
    for t in [0.,.125,.25,.4,.5,.6,.75,.875,1.]: assert not editable(scope,'A',t)
    assert editable(scope,'A',.3) and editable(scope,'A',.7)
    assert not editable(scope,'B',.5) and scope['actors']['B'] is None and recipe==before
    assert not scope['object_motion_editable'] and not scope['planes_editable']


@pytest.mark.parametrize('fault',['window','actor','missing-track','duplicate-source-track','missing-boundary','too-few-keys','empty-actors'])
def test_invalid_channel_or_sealed_scope_cannot_explain_a_blocker(inputs,fault):
    recipe,source,sealed=inputs
    if fault=='window':recipe['actors']['A']['window_s']=[.1,.9]
    elif fault=='actor':recipe['actors']['C']=recipe['actors'].pop('A')
    elif fault=='missing-track':recipe['actors']['A']['tracks'][0]['node']=9
    elif fault=='duplicate-source-track':source.actors['A']['sampler'].channels*=2
    elif fault=='missing-boundary':source.actors['A']['sampler'].channels[0]=(6,'rotation',np.array([0.,.2,.4,.6,.8]))
    elif fault=='too-few-keys':source.actors['A']['sampler'].channels[0]=(6,'rotation',np.array([0.,.5,1.]))
    else:recipe['actors']={}
    with pytest.raises(ValueError):scope_for(recipe,source,sealed,'a'*64)


def test_face_identity_uses_complete_generic_primitive_ranges():
    topology=dict(primitives=[dict(node=4,primitive=0,first_face=0,faces=12),dict(node=8,primitive=1,first_face=12,faces=20)])
    assert face_primitive(topology,12)==dict(node=8,primitive=1,face_in_primitive=0)
    assert face_primitive(topology,31)==dict(node=8,primitive=1,face_in_primitive=19)
    with pytest.raises(ValueError):face_primitive(topology,32)
