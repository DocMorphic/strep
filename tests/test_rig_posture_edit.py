import copy
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import rig_posture_edit as studio
from test_hand_posture import fixture


def bound(monkeypatch):
    rig,_,recipe=fixture()
    meta=dict(glb_sha256='a'*64,frames=61,fps=30,hands=[dict(node=1)])
    monkeypatch.setattr(studio,'source',lambda *_:(Path('source'),{}, {},dict(frames=61),Path('clip.glb')))
    monkeypatch.setattr(studio,'metadata',lambda *_:copy.deepcopy(meta))
    monkeypatch.setattr(studio,'RigAsset',SimpleNamespace(load=lambda _:rig))
    return dict(source_job='job',variant='transfer',label='Test',posture=recipe)


def test_saved_mapping_cannot_be_replaced_with_body_root(monkeypatch):
    p=bound(monkeypatch);studio.validate(p)
    p['posture']['hand_roots']=[0];p['posture']['poses'][0]['hand_root']=0
    # This passes the generic descendant test, but is not the saved hand mapping.
    with pytest.raises(ValueError,match='saved character mapping'):studio.validate(p)


def test_stale_clip_or_clock_rejected(monkeypatch):
    p=bound(monkeypatch);p['posture']['source_glb_sha256']='b'*64
    with pytest.raises(ValueError,match='changed'):studio.validate(p)
    p=bound(monkeypatch);p['posture']['frames']=62
    with pytest.raises(ValueError,match='clock differs'):studio.validate(p)
    p=bound(monkeypatch);p['label']=' '
    with pytest.raises(ValueError,match='Name'):studio.validate(p)


def test_hand_inventory_excludes_hand_root_and_other_body_nodes():
    rig=SimpleNamespace(parents=[-1,0,1,0],joints=[0,1,2,3],document={'nodes':[{'name':str(i)} for i in range(4)]})
    result=studio.hands(rig,{'LeftHand':1,'RightHand':3})
    assert len(result)==1 and result[0]['node']==1
    assert result[0]['joints']==[dict(node=2,label='2',reference_xyzw=[0.,0.,0.,1.])]


def test_adapter_preserves_annotations_and_separates_old_quality_claims(monkeypatch,tmp_path):
    import numpy as np
    from strep import save,read,sha256
    import rig_clip_import
    inp=tmp_path/'input';inp.mkdir();src=tmp_path/'source';src.mkdir()
    (inp/'character.glb').write_bytes(b'source');save(src/'rig-profile.json',dict(mapping={'LeftHand':1}))
    recipe=dict(frames=3,hand_roots=[1],poses=[dict(targets=[dict(node=2)])])
    save(tmp_path/'hand-posture.json',recipe)
    save(tmp_path/'request.json',dict(input_glb_sha256=sha256(inp/'character.glb'),posture_sha256=sha256(tmp_path/'hand-posture.json'),source_job='parent'))
    save(inp/'report.json',dict(frames=3,fps=30,root_node=0,mapping={'LeftHand':1},timeline_edited=True,
        source='old-source',source_sha256='a'*64,roundtrip_max_matrix_error=99,predicted_contact_foot_speed={'stale':True},human_approved=True))
    for name,data in [('root-motion.json',{'node':0}),('contacts.json',{'intervals':[]}),('events.json',{'events':[{'frame':1,'requires_review':False}]}),('timeline.json',{'period_frames':2}),('contact-review.json',{'authored_targets':[]}),('contact-spec.json',{'glb_sha256':'old','contacts':[{'authored':True}],'provenance':'Original targets.'})]:save(inp/name,data)
    world=np.tile(np.eye(4),(3,4,1,1))
    rig=SimpleNamespace(parents=[-1,0,1,0],joints=[0,1,2,3],document={'nodes':[{} for _ in range(4)]},binary=b'',vertices=lambda frame:frame[:,:3,3])
    monkeypatch.setattr(studio,'RigAsset',SimpleNamespace(load=lambda _:rig))
    monkeypatch.setattr(rig_clip_import,'AnimationSampler',lambda *_:SimpleNamespace(sample=lambda _:world[0]))
    def authored(source,recipe,out):
        out.mkdir();(out/'character.glb').write_bytes(b'candidate')
        save(out/'verification.json',dict(roundtrip=dict(matrix_error=1e-8,skin_error_m=2e-8)))
        return world
    monkeypatch.setattr(studio,'author',authored)
    report,audit=studio.run(tmp_path);out=tmp_path/'transfer'
    assert report['human_approved'] is False and report['roundtrip_max_matrix_error']==1e-8
    assert 'predicted_contact_foot_speed' not in report
    for name in ('root-motion.json','contacts.json','events.json','timeline.json','contact-review.json'):assert (out/name).read_bytes()==(inp/name).read_bytes()
    assert report['contact_annotations_file']==str((out/'contacts.json').resolve())
    targets=read(tmp_path/'contact-spec.json');assert targets['glb_sha256']==sha256(out/'character.glb')
    assert targets['contacts']==[{'authored':True}]
    assert audit['retained_contact_targets']['requires_refit_and_review'] is True
