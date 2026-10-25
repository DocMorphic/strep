import copy
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_self_edit_preflight import analyze
from test_native_surface_locations import fixture


def setup(mixed=False):
    rig,pose,audit=fixture(mixed);rig.parents=[-1,0,0]
    return rig,pose,audit


def test_unused_joint_cannot_repair_crossing_and_all_fixed_vertices_are_listed():
    rig,pose,audit=setup();before=copy.deepcopy(audit)
    r=analyze(rig,pose,audit,[2])
    assert r['cannot_resolve_all_recorded_crossings_with_these_rotations']
    assert r['unaffected_vertex_ids']==list(range(6)) and len(r['unaffected_proper_pairs'])==1
    assert not r['potentially_affected_proper_pairs'] and not r['feasibility_proven']
    assert audit==before


def test_affected_pair_is_unresolved_not_proven_repairable():
    rig,pose,audit=setup(True);r=analyze(rig,pose,audit,[1])
    assert r['unaffected_vertex_ids']==[3,4,5]
    assert len(r['potentially_affected_proper_pairs'])==1 and not r['unaffected_proper_pairs']
    assert not r['feasibility_proven'] and not r['cannot_resolve_all_recorded_crossings_with_these_rotations']


def test_zero_edits_and_descendant_rotation_dependencies():
    rig,pose,audit=setup(True)
    assert analyze(rig,pose,audit,[])['cannot_resolve_all_recorded_crossings_with_these_rotations']
    rig.parents[2]=1
    assert analyze(rig,pose,audit,[1])['unaffected_vertex_ids']==[]


def test_tiny_positive_weight_is_never_silently_discarded():
    rig,pose,audit=setup()
    for p in rig.primitives:
        p['joints']=np.tile([0,1],(3,1));p['weights']=np.tile([1-1e-15,1e-15],(3,1))
    assert analyze(rig,pose,audit,[2])['unaffected_vertex_ids']==[]


@pytest.mark.parametrize('rotations',[[True],[1,1],[-1],[0],(1,)])
def test_invalid_edit_populations_reject(rotations):
    rig,pose,audit=setup()
    with pytest.raises(ValueError):analyze(rig,pose,audit,rotations)
