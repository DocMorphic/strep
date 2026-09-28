import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import rig_mirror_edit as studio
from strep import save,read,sha256


def test_candidate_drops_stale_success_and_active_scene_targets(monkeypatch,tmp_path):
    inp=tmp_path/'input';inp.mkdir()
    (inp/'character.glb').write_bytes(b'original')
    save(inp/'report.json',dict(frames=3,fps=30,root_node=0,mapping={'Hips':0},source='source.npz',source_sha256='a'*64,
        human_approved=True,engine_import='passed',target_contact_solved=True,roundtrip_max_matrix_error=99))
    save(inp/'contacts.json',dict(mapping={},intervals=[]))
    save(inp/'contact-spec.json',dict(glb_sha256='old',contacts=['old-world-target']))
    save(inp/'timeline.json',dict(period_frames=2))
    save(inp/'events.json',dict(fps=30,events=[dict(name='left_hit',frame=1,requires_review=False)]))
    for name in ('inventory.json','rig-profile.json'):save(inp/name,{})
    recipe=dict(frames=3,label='Test mirror',source_sha256=sha256(inp/'character.glb'));save(tmp_path/'mirror.json',recipe)
    save(tmp_path/'request.json',dict(mirror_sha256=sha256(tmp_path/'mirror.json'),source_job='original',input_variant='transfer',
        input_sidecar_sha256={p.name:sha256(p) for p in inp.iterdir()}))
    def export(source,recipe,out,contacts,events):
        out.mkdir();(out/'character.glb').write_bytes(b'candidate')
        save(out/'contacts.json',dict(mapping={},intervals=[]))
        save(out/'audit.json',dict(scope='test',export=dict(floor_depth_max_m=.01,floor_frames_above_1cm=1,matrix_error=1e-8,skin_error_m=1e-8)))
    monkeypatch.setattr(studio,'write_clip',export)
    report,audit=studio.run(tmp_path)
    assert report['human_approved'] is False and report['engine_import'] is None
    assert 'target_contact_solved' not in report
    assert report['roundtrip_max_matrix_error']==1e-8
    assert report['timeline_edited'] is True
    assert read(tmp_path/'transfer/contacts.json')['origin']=='source_model_predictions'
    assert not (tmp_path/'contact-spec.json').exists()
    assert 'period_frames' not in read(tmp_path/'transfer/timeline.json')
    assert read(inp/'contact-spec.json')['contacts']==['old-world-target']
    assert audit['retained_source_targets']==['contact-spec.json']
    # A changed source annotation must reject before launching the exporter.
    save(inp/'events.json',dict(events=[]))
    with pytest.raises(ValueError,match='snapshot changed'):studio.run(tmp_path)


def test_wrong_source_clock_is_rejected_before_creating_output(monkeypatch,tmp_path):
    import rig_mirror as core
    from types import SimpleNamespace
    source=tmp_path/'clip.glb';source.write_bytes(b'original')
    recipe=dict(schema='strep-rig-mirror-v1',source_sha256=sha256(source),frames=3,fps=30,root_node=0,counterparts={'0':0},plane_normal=[1,0,0],plane_point=[0,0,0],label='Test')
    monkeypatch.setattr(core,'RigAsset',SimpleNamespace(load=lambda _:SimpleNamespace(document={'animations':[{}]},binary=b'')))
    monkeypatch.setattr(core,'AnimationSampler',lambda *_:SimpleNamespace(duration=1.))
    with pytest.raises(ValueError,match='exact recipe duration'):core.write_clip(source,recipe,tmp_path/'out')
    assert not (tmp_path/'out').exists()
    recipe['source_sha256']='b'*64
    with pytest.raises(ValueError,match='bind the selected source'):core.write_clip(source,recipe,tmp_path/'out')
