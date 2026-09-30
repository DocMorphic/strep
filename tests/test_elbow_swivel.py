import sys
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from elbow_swivel import swivel,descendants,segment_distance,capsule_radius,local_transforms
from paired_guarded_temporal import world_from_local


def arm():
    parents=[-1,0,1,2,3,1,0]
    local=np.tile(np.eye(4),(7,1,1));local[1,:3,3]=[.3,.6,0]
    local[2,:3,3]=[.3,.1,0];local[3,:3,3]=[.2,-.1,0]
    local[4,:3,3]=[.1,0,0];local[5,:3,3]=[.1,0,.1];local[6,:3,3]=[-.3,.3,0]
    local[0,:3,:3]=Rotation.from_euler('xyz',[.2,-.4,.3]).as_matrix();local[0,:3,3]=[4,2,1]
    return parents,local,world_from_local(local[None],parents)[0]


@pytest.mark.parametrize('angle',[-.7,0,.4,1.2])
def test_native_local_fk_preserves_hand_subtree_and_bone_lengths(angle):
    parents,local,world=arm();result,edited=swivel(world,parents,1,2,3,angle)
    replay=world_from_local(edited[None],parents)[0]
    np.testing.assert_allclose(replay,result,atol=2e-14,rtol=0)
    np.testing.assert_array_equal(result[descendants(parents,3)],world[descendants(parents,3)])
    np.testing.assert_array_equal(result[[0,6]],world[[0,6]])
    np.testing.assert_allclose(edited[:,:3,3],local[:,:3,3],atol=1e-14,rtol=0)
    if angle:
        assert np.linalg.norm(result[2,:3,3]-world[2,:3,3]) > .01
    else:np.testing.assert_array_equal(result,world)
    # A second inverse swivel reconstructs the entire original pose.
    restored,_=swivel(result,parents,1,2,3,-angle)
    np.testing.assert_allclose(restored,world,atol=2e-14,rtol=0)


@pytest.mark.parametrize('fault',['scale','reflection','nan','cycle','chain','angle','coincident'])
def test_unsupported_inputs_rejected(fault):
    parents,_,world=arm();elbow=2;angle=.2
    if fault=='scale':world[2,:3,0]*=2
    if fault=='reflection':world[2,:3,0]*=-1
    if fault=='nan':world[1,0,3]=np.nan
    if fault=='cycle':parents[0]=4
    if fault=='chain':elbow=5
    if fault=='angle':angle=np.inf
    if fault=='coincident':world[3,:3,3]=world[1,:3,3]
    with pytest.raises(ValueError):swivel(world,parents,1,elbow,3,angle)


@pytest.mark.parametrize('points,expected',[
    ([[0,0,0],[1,0,0],[.5,-1,0],[.5,1,0]],0),
    ([[0,0,0],[1,0,0],[.5,-1,2],[.5,1,2]],2),
    ([[0,0,0],[1,0,0],[0,1,0],[1,1,0]],1),
    ([[0,0,0],[1,0,0],[2,1,0],[3,1,0]],np.sqrt(2)),
    ([[0,0,0],[0,0,0],[1,0,0],[1,0,0]],1),
    ([[0,0,0],[0,0,0],[-1,2,0],[1,2,0]],2)])
def test_segment_distances_include_parallel_degenerate_and_endpoint_cases(points,expected):
    assert segment_distance(*points)==pytest.approx(expected)
    assert segment_distance(*points[2:],*points[:2])==pytest.approx(expected)


def test_capsule_covers_endpoint_caps_as_well_as_cylinder():
    points=np.array([[-.3,0,0],[.5,.2,0],[1.4,0,0]])
    assert capsule_radius(points,[0,0,0],[1,0,0])==pytest.approx(.4)
    with pytest.raises(ValueError):capsule_radius([], [0,0,0],[1,0,0])


def test_proxy_selection_balances_small_edits_and_clearance_without_duplicates():
    from plan_pair_swivel_pose import ranked_candidates
    rows=[dict(id=str(i),angles_degrees=[angle,angle],proxy_clearance_m=gap)
          for i,(angle,gap) in enumerate([(5,.003),(40,.1),(10,.004),(0,-.001),(20,.02)])]
    assert ranked_candidates(rows)==['0','1','2','4']
    assert ranked_candidates(rows,1)==['0']
    assert len(ranked_candidates(rows,9))==5
    for row in rows:row['proxy_clearance_m']*=-1
    assert ranked_candidates(rows,2)[0]=='3'
    with pytest.raises(ValueError):ranked_candidates([rows[0],rows[0]])
    rows[0]['proxy_clearance_m']=np.nan
    with pytest.raises(ValueError):ranked_candidates(rows)


def test_static_pose_export_serializes_locals_and_does_not_modify_source(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import copy
    from plan_pair_swivel_pose import export_pose
    from gltf_tools import read_glb,global_matrices
    from rig_asset import RigAsset
    parents,local,world=arm();expected,edited=swivel(world,parents,1,2,3,.5)
    nodes=[dict(name=str(i),children=[j for j,p in enumerate(parents) if p==i]) for i in range(len(parents))]
    doc=dict(asset=dict(version='2.0'),nodes=nodes,buffers=[dict(byteLength=0)],animations=[dict(name='source')])
    before=copy.deepcopy(doc);rig=SimpleNamespace(document=doc,binary=b'',parents=parents)
    def load(path):
        document,binary=read_glb(path)
        return SimpleNamespace(document=document,reference=global_matrices(document))
    monkeypatch.setattr(RigAsset,'load',staticmethod(load))
    decoded,replayed=export_pose(rig,edited,tmp_path/'pose.glb')
    assert doc==before
    assert decoded.document['animations']==[]
    assert decoded.document['extras']['strep_pose_planning_only'] is True
    np.testing.assert_allclose(replayed,expected,atol=2e-7,rtol=0)
    with pytest.raises(ValueError):export_pose(rig,edited[:-1],tmp_path/'invalid.glb')
