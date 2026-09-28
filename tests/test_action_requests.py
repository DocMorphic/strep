import sys
from pathlib import Path
import copy
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from action_requests import validate_batch,timeline,request_digest,conditioning_texts
from action_studio_server import allowed_file
from build_soma_preview import make_preview,ASSET
from gltf_tools import accessor,sample_animation
from strep import ROOT,read


def example():
    return {'schema_version':1,'requests':[{'id':'custom','label':'Unlisted motion',
        'segments':[{'prompt':'Someone mimes winding an enormous clock, then bows.','duration_s':3.2},
                    {'prompt':'They spread their hands and shrug!','duration_s':2}],
        'seeds':[0,4294967295],'scene_requirements':['Clock is imaginary; no prop solver']} ]}


def test_free_text_and_explicit_sequence_not_running_whitelist():
    b=validate_batch(example());schedule=timeline(b['requests'][0]);assert len(conditioning_texts(b))==2
    assert schedule[1]['start_frame']==96 and schedule[1]['blend_frames']==[91,92,93,94,95]
    assert schedule[-1]['end_frame_exclusive']==156
    changed=copy.deepcopy(b);changed['requests'][0]['segments'][1]['prompt']='A completely different motion.'
    assert request_digest(changed)!=request_digest(b)


@pytest.mark.parametrize('duration',[0,10,float('nan'),True,'4'])
def test_invalid_duration_rejected(duration):
    b=example();b['requests'][0]['segments'][0]['duration_s']=duration
    with pytest.raises(ValueError):validate_batch(b)


@pytest.mark.parametrize('change',[{'id':'../escape'},{'seeds':[1,1]},{'seeds':[True]}, {'seeds':[-1]}, {'unknown':'ignored?'}])
def test_unsafe_or_ignored_inputs_rejected(change):
    b=example();b['requests'][0].update(change)
    with pytest.raises(ValueError):validate_batch(b)


@pytest.mark.parametrize('url',['/files/action-coverage-v1/../../models/manifest.json','/assets/../../../../scripts/strep.py','/files/action-jobs/%2e%2e/%2e%2e/models/manifest.json','/files/action-coverage-v1/conditioning/a.safetensors'])
def test_server_does_not_expose_private_or_outside_files(url):
    assert allowed_file(url) is None


def test_finite_export_keeps_every_frame_without_looping():
    source=ROOT/'reports/periodic-controls-v1/takes/arm-10-lean-0-seed-11/motion.npz'
    motion=dict(np.load(source));skin=dict(np.load(ASSET));doc,binary,positions,rotations=make_preview(skin,motion,np.zeros(3),repeat=False)
    times=accessor(doc,binary,doc['animations'][0]['samplers'][0]['input'])
    assert doc['animations'][0]['name']=='action' and len(times)==len(motion['posed_joints'])
    assert times[-1]==pytest.approx((len(times)-1)/30)
    for i in [0,len(times)//2,len(times)-1]:
        world=sample_animation(doc,binary,0,i)[1:78]
        np.testing.assert_allclose(world[:,:3,3],motion['posed_joints'][i],atol=1e-5)


def test_model_worker_lock_prevents_concurrent_jobs_and_releases(tmp_path,monkeypatch):
    import action_worker_lock as locks
    monkeypatch.setattr(locks,'ROOT',tmp_path)
    assert not locks.worker_busy()
    with locks.worker_lock():
        assert locks.worker_busy()
        with pytest.raises(RuntimeError):
            with locks.worker_lock():pass
    assert not locks.worker_busy()
