import sys,itertools
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from motion_lattice import bounded_path
from sampled_motion_caps import SampledMotionCaps,features
from scipy.spatial.transform import Rotation


def test_second_order_search_matches_exhaustive_including_frozen_boundaries():
    times=np.arange(5.);states=np.array([[0.],[1.],[2.]])
    costs=np.array([[0,9,9],[9,1,0],[9,0,1],[9,1,0],[0,9,9.]])
    edge=lambda i,a,b: (i,a,b)
    def join(a,b):
        return abs((a[2]-a[1])-(b[2]-b[1]))<=1
    prefix=(-1,0,0);suffix=(4,0,0);options=[]
    for middle in itertools.product(range(3),repeat=3):
        ids=[0,*middle,0];edges=[prefix]+[(i,a,b) for i,(a,b) in enumerate(zip(ids[:-1],ids[1:]))]+[suffix]
        if all(join(a,b) for a,b in zip(edges[:-1],edges[1:])):
            value=sum(costs[i,s] for i,s in enumerate(ids))+.1*np.sum((np.diff(states[ids],axis=0)/2)**2)
            options.append((value,ids))
    path,result=bounded_path(times,states,costs,[2],edge,join,prefix,suffix)
    assert result['total_cost']==pytest.approx(min(options)[0]);assert result['state_indices']==min(options)[1]


def test_rejected_edges_and_terminal_join_cannot_be_bypassed():
    path,result=bounded_path([0,1,2],[[0],[1]],[[0,0],[np.inf,0],[0,0]],[1],
        lambda i,a,b:None,lambda a,b:True,None,None)
    assert path is None and result['edges_rejected']==1
    path,result=bounded_path([0,1,2],[[0],[1]],[[0,0],[np.inf,0],[0,0]],[1],
        lambda i,a,b:(a,b),lambda a,b:b!='suffix','prefix','suffix')
    assert path is None and result['junctions_rejected']>0


def payload(values,angles=None,start=0):
    p=np.asarray(values,float)[:,None,None]*np.array([[[1.,0,0]]])
    r=np.tile(np.eye(3),(len(p),1,1,1)) if angles is None else Rotation.from_euler('z',angles).as_matrix()[:,None]
    return dict(indices=np.arange(start,start+len(p)),positions=p,rotations=r)


def test_caps_detect_speed_acceleration_and_angular_boundary_failures():
    source=payload(np.arange(8.));caps=SampledMotionCaps(source,np.arange(8.),[0,4,7])
    assert caps.check(source)
    assert not caps.check(payload(np.arange(8.)*1.01))
    assert not caps.join(payload([0,1,2]),payload([3,3.9,4.8],start=3))
    assert not caps.check(payload(np.arange(8.),np.arange(8.)*.001))
    with pytest.raises(ValueError):caps.join(payload([0,1]),payload([3,4],start=3))


def test_angular_direction_reversal_fails_acceleration_without_exceeding_speed():
    source=payload(np.arange(8.),np.arange(8.)*.1)
    caps=SampledMotionCaps(source,np.arange(8.),[0,4,7])
    before=payload([0,1,2],[0,.1,.2]);after=payload([3,4,5],[.1,0,-.1],start=3)
    assert caps.check(before) and caps.check(after)
    assert not caps.join(before,after)


@pytest.mark.parametrize('fault',['clock','bins','negative_tolerance','nan_pose','rotation','indices','population'])
def test_motion_limits_reject_malformed_inputs(fault):
    source=payload(np.arange(8.));times=np.arange(8.);knots=[0,4,7];tolerance=1e-5
    if fault=='clock':times[2]=times[1]
    if fault=='bins':knots=[0,4,4]
    if fault=='negative_tolerance':tolerance=-1
    if fault=='nan_pose':source['positions'][0,0,0]=np.nan
    if fault=='rotation':source['rotations'][0,0,0,0]=2
    with pytest.raises(ValueError):
        caps=SampledMotionCaps(source,times,knots,tolerance)
        if fault=='indices':source['indices'][2]=source['indices'][1]
        if fault=='population':source['positions']=np.tile(source['positions'],(1,2,1))
        caps.check(source)


def test_partition_and_whole_track_agree_with_existing_independent_rate_replay():
    from verify_scene_pair_fit import rate_check
    from scalar_angular_replay import angular_replay
    times=np.arange(24)/120;knots=[0,.08,.14,.2]
    source=payload(np.sin(times),times**2);candidate=payload(np.sin(times)+.002*np.sin(80*times),times**2+.003*np.cos(40*times))
    caps=SampledMotionCaps(source,times,knots)
    pos=rate_check(source['positions'],candidate['positions'],times,knots)
    angular=angular_replay(source['rotations'],candidate['rotations'],times,knots)
    assert caps.check(candidate)==(pos['failures']==0 and all(r['exceeding_observations']==0 for r in angular.values()))
    for track in [source,candidate]:
        parts=[{k:v[a:b] for k,v in track.items()} for a,b in [(0,6),(6,12),(12,18),(18,24)]]
        result=all(caps.check(p) for p in parts) and all(caps.join(a,b) for a,b in zip(parts[:-1],parts[1:]))
        assert result==caps.check(track)
