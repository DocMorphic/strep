import sys
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from test_timed_rotation_edit import fixture, model
from gltf_tools import write_glb, read_glb
from strep import read, save, sha256
import verify_scene_pair_angular as replay


def setup(tmp_path, monkeypatch, selected=True):
    prepared = tmp_path/'prepared'; prepared.mkdir(); fit = tmp_path/'fit'; fit.mkdir()
    doc, binary = fixture(); edit = model(doc, binary)
    # Test the replay with an actual GLB; mesh validation belongs to RigAsset's own tests.
    def load(path):
        doc,binary=read_glb(path)
        return SimpleNamespace(document=doc, binary=binary, joints=doc['skins'][0]['joints'])
    monkeypatch.setattr(replay.RigAsset, 'load', load)
    if selected: (fit/'trial-0').mkdir()
    actors = {}; trial_actors = []
    for name in ['A','B']:
        source = prepared/(name+'.glb'); write_glb(source, doc, binary)
        actors[name] = dict(path=source.name, sha256=sha256(source))
        if selected:
            target=fit/'trial-0'/(name+'.glb'); edit.export(np.zeros(edit.size),target)
            trial_actors.append(dict(actor=name,path=target.name,sha256=sha256(target)))
    save(prepared/'request.json', dict(actors=actors,sample_times_seconds=(np.arange(181)/120).tolist(),authored=dict(knots_s=[.1,.4,.7,1.,1.3])))
    save(fit/'request.json', dict(prepared_request=str(prepared/'request.json'),inputs={str(prepared/'request.json'):sha256(prepared/'request.json')}))
    if selected: save(fit/'trials.json',[dict(folder='trial-0',actors=trial_actors)])
    save(fit/'result.json',dict(status='complete',request_sha256=sha256(fit/'request.json'),selected='trial-0' if selected else None,
        trials_sha256=sha256(fit/'trials.json') if selected else None))
    return fit


def test_real_glb_zero_edit_replays_all_joints_with_bound_inputs(tmp_path, monkeypatch):
    fit=setup(tmp_path,monkeypatch); out=tmp_path/'replay'; replay.run(fit,out)
    proof=read(out/'verification.json'); protocol=read(out/'request.json')
    assert proof['passed'] and proof['status']=='complete'
    assert [a['actor'] for a in proof['actors']] == ['A','B']
    assert all(a['rates']['angular_speed_rad_s']['observations']==180*4 for a in proof['actors'])
    for path,digest in protocol['inputs'].items(): assert sha256(path)==digest
    for name,digest in protocol['implementation'].items(): assert sha256(out/'implementation'/name)==digest
    with pytest.raises(ValueError,match='Preserve'): replay.run(fit,out)


def test_no_candidate_never_gets_motion_approval(tmp_path, monkeypatch):
    fit=setup(tmp_path,monkeypatch,selected=False); out=tmp_path/'replay'; replay.run(fit,out)
    proof=read(out/'verification.json')
    assert proof['actors']==[] and proof['selected'] is None and not proof['passed']


@pytest.mark.parametrize('fault',['prepared','trials','candidate'])
def test_changed_input_prevents_completed_replay(tmp_path,monkeypatch,fault):
    fit=setup(tmp_path,monkeypatch); out=tmp_path/'replay'
    path={'prepared':tmp_path/'prepared/request.json','trials':fit/'trials.json','candidate':fit/'trial-0/A.glb'}[fault]
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError): replay.run(fit,out)
    assert not (out/'verification.json').exists()


def test_studio_worker_enables_angular_fit_and_replays_before_publication(tmp_path,monkeypatch):
    # Exercise orchestration without the Windows lock or optional runtime packages.
    monkeypatch.setitem(sys.modules,'action_worker_lock',SimpleNamespace(worker_lock=nullcontext,worker_busy=lambda:False))
    monkeypatch.setitem(sys.modules,'psutil',SimpleNamespace(Process=lambda:SimpleNamespace(create_time=lambda:1.)))
    monkeypatch.setitem(sys.modules,'threadpoolctl',SimpleNamespace(threadpool_limits=lambda **kwargs:nullcontext()))
    monkeypatch.setitem(sys.modules,'study_scene_pair_fit',SimpleNamespace(run=lambda *args,**kwargs:None))
    import scene_pair_job as jobs
    import study_scene_pair_fit, verify_scene_pair_fit, run_godot_rig_import, publish_scene_pair_fit, action_worker_lock
    folder=tmp_path/'job'; folder.mkdir(); save(folder/'request.json',{})
    save(folder/'job.json',dict(prepared_request_sha256=sha256(folder/'request.json'),files={},implementation={}))
    monkeypatch.setattr(jobs,'JOBS',tmp_path); monkeypatch.setattr(action_worker_lock,'worker_lock',nullcontext)
    calls=[]
    def fit(source,target,*,angular):
        assert angular is True; calls.append('fit'); target.mkdir(); save(target/'result.json',dict(selected=None))
    monkeypatch.setattr(study_scene_pair_fit,'run',fit)
    monkeypatch.setattr(verify_scene_pair_fit,'run',lambda *a:calls.append('positional'))
    monkeypatch.setattr(replay,'run',lambda *a:calls.append('angular'))
    monkeypatch.setattr(run_godot_rig_import,'run',lambda *a:calls.append('engine'))
    def publish(*args):calls.append('publish');return 'fixture'
    monkeypatch.setattr(publish_scene_pair_fit,'publish',publish)
    jobs.run(folder)
    assert calls==['fit','positional','angular','engine','publish']
    assert read(folder/'pipeline.json')['status']=='complete'
