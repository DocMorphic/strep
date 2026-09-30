import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from terminal_hand_search import population,candidates,terminal_motion_pass,reject_hand_edge


def test_diagonal_population_preserves_euclidean_rate_and_deduplicates_zero_offsets():
    axes,states=population();ids=candidates(axes,states,.0501,[.8,300,300])
    assert len(axes)==26 and len(states)==150 and len(ids)==3275
    physical=np.array([np.r_[axes[a]*states[s,0],states[s,1:]] for a,s in ids])
    assert len(np.unique(physical,axis=0))==len(ids)
    assert sum(np.all(physical[:,:3]==0,axis=1))==25
    assert np.linalg.norm(physical[:,:3],axis=1).max()/.0501<=.8
    assert np.abs(physical[:,3:]/.0501).max()<=300
    assert len(candidates(axes,states,.025,[.8,300,300]))==711
    with pytest.raises(ValueError):candidates(axes*2,states,.05,[.8,300,300])
    with pytest.raises(ValueError):candidates(axes,states,0,[.8,300,300])
    with pytest.raises(ValueError):candidates(axes,[[.061,0,0]],.05,[.8,300,300])


@pytest.mark.parametrize('reject',[None,'native_pose','edge_motion','frozen_junction_motion'])
def test_frozen_suffix_is_a_required_gate_and_failures_never_reach_geometry(reject):
    seen=[];decoded=(np.array([10,11,12]),[np.zeros((3,4,4)),np.zeros((3,4,4))])
    def check(payload):seen.append('edge');return reject!='edge_motion'
    def join(payload,suffix):seen.append('suffix');return reject!='frozen_junction_motion'
    decoder=SimpleNamespace(decode=lambda *a:None if reject=='native_pose' else decoded,
        combine=lambda *a:{},caps=SimpleNamespace(check=check,join=join),suffix={})
    result,reason=terminal_motion_pass(decoder,4,2,0)
    if reject is None:assert result[0] is decoded[0] and result[1] is decoded[1] and reason=='pass'
    else:assert result is None and reason==reject
    assert seen==([] if reject=='native_pose' else ['edge'] if reject=='edge_motion' else ['edge','suffix'])


def test_between_key_collision_rejects_even_when_endpoint_samples_are_clear():
    # Stored scalar worlds stand in for timestamps; the predicate must inspect
    # every declared time and both directions before it can return a pass.
    ids=np.array([40,41,42]);worlds=[np.arange(3),np.arange(3)];seen=[]
    def query(pair):
        seen.append(int(pair[0]));return [dict(max_depth_m=0.),dict(max_depth_m=.02 if pair[1]==1 else 0.)]
    audit=reject_hand_edge(ids,worlds,query,priority=[1,0,2])
    assert not audit['passed'] and not audit['complete_clock'] and seen==[1]
    assert audit['observed_peak_lower_bound_m']==.02 and audit['rows'][0]['sample']==41
    clear=reject_hand_edge(ids,worlds,lambda pair:[dict(max_depth_m=.005),dict(max_depth_m=0.)],priority=[1,0,2])
    assert clear['passed'] and clear['complete_clock'] and len(clear['rows'])==3
    with pytest.raises(ValueError):reject_hand_edge(ids,worlds,query,priority=[0,2])
    with pytest.raises(ValueError):reject_hand_edge(ids,worlds,lambda _: [dict(max_depth_m=np.nan)]*2)
