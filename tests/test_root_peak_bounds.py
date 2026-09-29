import sys
from pathlib import Path
import itertools
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from diagnose_root_peak_bounds import vertical_offset_bounds,acceleration_lower_bound


def test_acceleration_interval_encloses_all_box_corners():
    y=np.array([0.,.002,0.,.001,0.]);lo=np.array([-.01,0.,-.004,.001,0.]);hi=lo+.003
    lower,upper,bound=acceleration_lower_bound(y,lo,hi)
    for f in range(3):
        values=[(y[f]+a-2*(y[f+1]+b)+y[f+2]+c)*900 for a,b,c in itertools.product(*zip(lo[f:f+3],hi[f:f+3]))]
        np.testing.assert_allclose([min(values),max(values)],[lower[f],upper[f]],atol=1e-12)
        assert bound[f]<=min(abs(v) for v in values)+1e-12


def test_floor_and_hover_pin_root_even_with_weight_roundoff():
    points=np.zeros((5,2,3));weights=np.array([1-5e-8,1+5e-8]);patches={'Left':{'vertices':[0,1]}}
    lo,hi=vertical_offset_bounds(points,weights,patches,{'Left':np.ones(5,bool)},np.zeros(5),.12,.01,1e-6)
    assert max(abs(lo))<1.000001e-6 and max(abs(hi))<1.000001e-6
    _,_,bound=acceleration_lower_bound(np.array([0.,0.,.01,0.,0.]),lo,hi)
    assert bound.max()>17.99


def test_any_low_vertex_is_allowed_and_inactive_hover_is_not_constrained():
    points=np.zeros((5,2,3));points[:,:,1]=[.001,.0010005]
    # The second vertex becomes the better hover witness because it moves less.
    weights=np.array([1.,.01]);active={'Left':np.array([False,False,True,False,False])}
    lo,hi=vertical_offset_bounds(points,weights,{'Left':{'vertices':[0,1]}},active,np.zeros(5),.12,.01,1e-6)
    assert abs(hi[2]-.00005)<1e-12 and lo[2]<0
    active['Left'][2]=False
    _,unrestricted=vertical_offset_bounds(points,weights,{'Left':{'vertices':[0,1]}},active,np.zeros(5),.12,.01,1e-6)
    assert unrestricted[2]>.01 and unrestricted[0]==1e-6


def test_static_low_vertex_does_not_impose_false_hover_bound():
    points=np.zeros((5,2,3));weights=np.array([0.,1.])
    lo,hi=vertical_offset_bounds(points,weights,{'Left':{'vertices':[0,1]}},{'Left':np.ones(5,bool)},np.zeros(5),.12,.01,1e-6)
    assert hi[2]>.01


@pytest.mark.parametrize('rig_id',['rig-01','rig-02','rig-03'])
def test_actual_export_obeys_affine_skin_assumption(rig_id,tmp_path):
    from strep import ROOT,read
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from authored_root_correction import root_weights,export
    folder=ROOT/'reports/breadth-root-cleanup-v1/takes'/('motion-036-'+rig_id)
    if not folder.exists():pytest.skip('Provisioned target-rig fixtures required')
    spec=read(folder/'contact-spec.json');rig=RigAsset.load(folder/'candidate/character.glb');root=spec['root_node']
    offsets=np.zeros((spec['frames'],3));offsets[20]=[.001,-.002,.003]
    target=tmp_path/'candidate.glb';export(rig,root,offsets,target);other=RigAsset.load(target)
    t=float(np.float32(20/30));before=AnimationSampler(rig.document,rig.binary,0).sample(t);after=AnimationSampler(other.document,other.binary,0).sample(t)
    delta=after[root,:3,3]-before[root,:3,3]
    expected=rig.vertices(before)+root_weights(rig,root)[:,None]*delta
    np.testing.assert_allclose(other.vertices(after),expected,rtol=0,atol=1e-12)
