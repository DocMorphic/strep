"""Influence coverage is not the same as membership in the mapped-joint list."""
from pathlib import Path
import sys
from types import SimpleNamespace
import copy
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from retarget_rig import mapping_skin_coverage


def rig_fixture():
    # Root(0) -> mapped hips(1) -> unmapped helper(2); separate branch(3).
    # Joint slots deliberately differ from node indices; eight influences.
    return SimpleNamespace(joints=[2, 0, 3, 1], parents=[-1, 0, 1, 0],
        document={'nodes': [{'name': n} for n in ('root', 'hips', 'helper', 'branch')]},
        primitives=[dict(node=4, primitive=0, positions=np.zeros((3, 3)),
            joints=np.array([[0,1,2,3,0,1,2,3], [0,1,2,3,0,1,2,3], [0,1,2,3,0,1,2,3]]),
            weights=np.array([[1.,0,0,0,0,0,0,0], [.4,.1,.2,0,0,.1,.2,0], [0,0,0,1,0,0,0,0]]))])


def test_helpers_follow_ancestors_but_positive_parent_and_sibling_weights_are_reported():
    rig=rig_fixture(); before=copy.deepcopy(rig)
    result=mapping_skin_coverage(rig, {'Hips':1})
    assert result['vertices']==3 and result['outside_mapped_hierarchy_vertices']==1
    assert result['maximum_outside_vertex_weight']==pytest.approx(.6)
    assert result['inspection_required']
    assert [(r['joint'],r['affected_vertices'],r['maximum_vertex_weight']) for r in result['outside_influences']]==[(0,1,.2),(3,1,.4)]
    np.testing.assert_array_equal(rig.primitives[0]['weights'],before.primitives[0]['weights'])
    np.testing.assert_array_equal(rig.primitives[0]['joints'],before.primitives[0]['joints'])
    assert rig.document==before.document


def test_mapping_root_covers_all_descendants_without_requiring_every_joint():
    result=mapping_skin_coverage(rig_fixture(), {'Root':0})
    assert result['outside_mapped_hierarchy_vertices']==0
    assert result['outside_influences']==[] and not result['inspection_required']


def test_duplicate_mesh_instances_count_separate_vertices_and_keep_primitive_identity():
    rig=rig_fixture(); second=copy.deepcopy(rig.primitives[0]); second.update(node=5,primitive=1)
    rig.primitives.append(second)
    result=mapping_skin_coverage(rig, {'Hips':1})
    assert result['vertices']==6 and result['outside_mapped_hierarchy_vertices']==2
    assert [(r['mesh_node'],r['primitive']) for r in result['outside_influences']]==[(4,0),(4,0),(5,1),(5,1)]


def test_unskinned_geometry_is_reported_separately_without_dropping_it():
    rig=rig_fixture(); rig.primitives.append(dict(node=5,primitive=0,positions=np.zeros((4,3)),joints=None,weights=None))
    result=mapping_skin_coverage(rig, {'Root':0})
    assert result['vertices']==7 and result['unskinned_vertices']==4
    assert result['outside_mapped_hierarchy_vertices']==0 and result['inspection_required']


def test_zero_weight_outside_joint_slots_do_not_create_a_warning():
    rig=rig_fixture();rig.primitives[0]['weights'][:]=[1,0,0,0,0,0,0,0]
    assert not mapping_skin_coverage(rig, {'Hips':1})['inspection_required']


def test_native_transfer_includes_coverage_without_changing_reference_motion(tmp_path):
    from test_native_rig_transfer import fixture
    from rig_asset import RigAsset
    from strep import read
    from native_rig_transfer import prepare, evaluate_transfer
    path, profile_path = fixture(tmp_path/'rig', 'coverage', helpers=True)
    rig=RigAsset.load(path); profile=read(profile_path)
    sampler,sm,tm,skeleton,offset,scale,diagnostics=prepare(rig,profile,rig,profile,0)
    assert not diagnostics['target_skin_mapping_coverage']['inspection_required']
    times=np.array([0.,sampler.duration/2,sampler.duration])
    world,_,_=evaluate_transfer(rig,rig,sampler,sm,tm,skeleton,offset,profile,times)
    for t,actual in zip(times,world):
        expected=sampler.sample(float(t))
        np.testing.assert_allclose(rig.vertices(actual),rig.vertices(expected),atol=1e-7)
