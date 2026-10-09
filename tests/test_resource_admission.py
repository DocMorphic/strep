import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from resource_admission import ResourcePolicy,Admission,MIN_AVAILABLE,MAX_TREE_RSS


def test_low_sample_revokes_readiness_and_requires_a_new_stable_interval():
    p=ResourcePolicy(2*1024**3,stable_seconds=10,admission_seconds=30)
    a=Admission(p,100);need=p.required_available_bytes
    assert a.observe(100,need)=='waiting_resources'
    assert a.observe(109,need)=='waiting_resources'
    assert a.observe(110,need-1)=='waiting_resources' and a.ready_since is None
    assert a.observe(115,need)=='waiting_resources'
    assert a.observe(124,need)=='waiting_resources'
    assert a.observe(125,need)=='ready'


def test_deadline_never_starts_a_worker_even_if_last_sample_is_high():
    p=ResourcePolicy(1024,stable_seconds=10,admission_seconds=20)
    a=Admission(p,0)
    assert a.observe(0,0)=='waiting_resources'
    assert a.observe(19,p.required_available_bytes)=='waiting_resources'
    assert a.observe(20,p.required_available_bytes)=='deferred'


@pytest.mark.parametrize('options',[
    dict(expected_rss_bytes=True),dict(expected_rss_bytes=0),dict(expected_rss_bytes=MAX_TREE_RSS+1),
    dict(min_available_bytes=MIN_AVAILABLE-1),dict(max_tree_rss_bytes=MAX_TREE_RSS+1),
    dict(max_tree_rss_bytes=512),dict(max_seconds=3601),dict(max_seconds=float('nan')),
    dict(stable_seconds=0),dict(admission_seconds=601),dict(admission_seconds=5),
    dict(poll_seconds=11),dict(poll_seconds=True),dict(poll_seconds=float('inf'))])
def test_invalid_or_weakened_guards_rejected(options):
    defaults=dict(expected_rss_bytes=1024);defaults.update(options)
    with pytest.raises(ValueError):ResourcePolicy(**defaults)


@pytest.mark.parametrize('clock,available',[(99,1024),(float('nan'),1024),(True,1024),(100,True),(100,-1)])
def test_invalid_samples_cannot_admit(clock,available):
    with pytest.raises(ValueError):Admission(ResourcePolicy(1024),100).observe(clock,available)


def test_invalid_start_clock_rejected():
    with pytest.raises(ValueError):Admission(ResourcePolicy(1024),float('nan'))
