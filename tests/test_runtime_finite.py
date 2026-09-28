import sys
import shutil
import zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import ROOT,read,save,sha256
from rig_runtime_finite import write
from rig_events import edit


def fixture(folder):
    source=ROOT/'reports/breadth-transfer-v1/takes/motion-036-rig-01'
    for name in ('character.glb','report.json'):shutil.copyfile(source/name,folder/name)
    return read(folder/'report.json')


def test_finite_keeps_terminal_intent_and_excludes_unreviewed_markers(tmp_path):
    report=fixture(tmp_path);last=report['frames']-1
    document=edit(dict(events=[]),[dict(id='last',name='release',frame=last,confirmed=True),dict(id='unknown',name='grasp',frame=1,confirmed=False)],report['glb_sha256'],report['frames'])
    save(tmp_path/'events.json',document)
    result=write(tmp_path)
    assert [(m['event_id'],m['phase_frame']) for m in result['markers']]==[('last',last)]
    assert result['excluded_events'][0]['event']['id']=='unknown'
    assert result['last_sample_time_s']==last/30 and result['duration_s']==report['frames']/30
    assert sha256(tmp_path/'character.glb')==report['glb_sha256']


@pytest.mark.parametrize('fault',['hash','endpoint','frames','fps'])
def test_finite_rejects_inconsistent_metadata_before_writing(tmp_path,fault):
    report=fixture(tmp_path)
    if fault=='hash':report['glb_sha256']='0'*64
    if fault=='endpoint':report['frames']-=1
    if fault=='frames':report['frames']=True
    if fault=='fps':report['fps']=60
    save(tmp_path/'report.json',report)
    with pytest.raises(ValueError):write(tmp_path)
    assert not (tmp_path/'runtime-finite.json').exists()


def test_studio_event_edit_exports_finite_adapter_and_terminal_event(tmp_path,monkeypatch):
    import action_worker_lock
    from rig_event_edit import prepare
    from rig_studio_job import run
    job='20260926-195412-bf0e8a1d';source=ROOT/'reports/rig-jobs'/job/'transfer'
    frames=read(source/'report.json')['frames'];original=sha256(source/'character.glb')
    request=dict(schema='strep-rig-events-v1',job=job,variant='transfer',glb_sha256=original,label='Finite terminal release test',markers=[dict(id='terminal-cue',name='terminal intent',frame=frames-1,confirmed=True)])
    monkeypatch.setattr(action_worker_lock,'ROOT',tmp_path)
    folder=tmp_path/'finite';prepare(request,folder);run(folder)
    result=read(folder/'result.json');metadata=read(folder/'transfer/runtime-finite.json')
    assert result['runtime_finite'].endswith('/transfer/runtime-finite.json')
    assert not (folder/'transfer/runtime-cycle.json').exists()
    assert sha256(folder/'transfer/character.glb')==original
    assert metadata['markers'][0]['phase_frame']==frames-1
    assert metadata['playback']['bindings_automatic'] is False
    with zipfile.ZipFile(folder/'character-animation.zip') as archive:
        assert archive.testzip() is None
        for name in ('godot_finite_adapter.gd','godot_cycle_adapter.gd','godot_event_object_body.gd','runtime-finite.json','GODOT-FINITE.md','GODOT-OBJECT-EVENTS.md'):
            assert archive.read('transfer/'+name)==(folder/'transfer'/name).read_bytes()


@pytest.mark.parametrize('tamper',[False,True])
def test_legacy_corrected_clip_requires_hash_bound_source_timing(tmp_path,tamper):
    source=ROOT/'reports/rig-jobs/20260926-195412-bf0e8a1d'
    for variant,names in [('transfer',('character.glb','report.json')),('corrected',('character.glb','audit.json'))]:
        (tmp_path/variant).mkdir()
        for name in names:shutil.copyfile(source/variant/name,tmp_path/variant/name)
    report=read(tmp_path/'transfer/report.json')
    save(tmp_path/'transfer/events.json',edit(dict(events=[]),[dict(id='intent',name='intent',frame=3,confirmed=True)],report['glb_sha256'],report['frames']))
    if tamper:
        audit=read(tmp_path/'corrected/audit.json');audit['source_glb_sha256']='0'*64;save(tmp_path/'corrected/audit.json',audit)
        with pytest.raises(ValueError,match='provenance'):write(tmp_path/'corrected')
        assert not (tmp_path/'corrected/runtime-finite.json').exists()
    else:
        metadata=write(tmp_path/'corrected')
        assert metadata['glb_sha256']==sha256(tmp_path/'corrected/character.glb')
        assert metadata['correction_source']['source_glb_sha256']==report['glb_sha256']
        assert metadata['markers'][0]['event_id']=='intent'
