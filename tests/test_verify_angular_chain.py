from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_angular_chain as verifier
from strep import save,read,sha256


def fixture(tmp_path,monkeypatch):
    study=tmp_path/'study';source=tmp_path/'source';audit=tmp_path/'source-audit.json'
    (source/'take/candidate').mkdir(parents=True);(source/'take/candidate/character.glb').write_bytes(b'fixture')
    save(audit,{})
    case=dict(id='no-op',source=str(source),audit=str(audit))
    save(study/'protocol.json',dict(cases=[case],max_blocks=2,inputs={},implementation={}))
    save(study/'pipeline.json',dict(status='complete'))
    save(study/'cases/no-op/completion.json',dict(status='already_passed',initial_source=str(source),initial_audit=str(audit),final_source=str(source),final_audit=str(audit),history=[]))
    monkeypatch.setattr(verifier,'measure',lambda *_:(True,0.))
    bind(study);return study


def bind(study):
    case=read(study/'cases/no-op/completion.json')
    rows=[dict(id='no-op',status=case['status'],completion_sha256=sha256(study/'cases/no-op/completion.json'))]
    save(study/'results.json',dict(rows=rows))
    save(study/'completion.json',dict(protocol_sha256=sha256(study/'protocol.json'),results_sha256=sha256(study/'results.json'),rows=rows))


def test_no_op_verifies_without_claiming_quality(tmp_path,monkeypatch):
    study=fixture(tmp_path,monkeypatch);out=tmp_path/'audit';verifier.run(study,out)
    result=read(out/'completion.json')
    assert result['all_chain_checks_passed'] and result['rows'][0]['blocks']==[] and not result['quality_approved']


def test_rehashed_population_omission_is_rejected(tmp_path,monkeypatch):
    study=fixture(tmp_path,monkeypatch);p=read(study/'protocol.json');p['cases'].append(dict(id='omitted',source='other',audit='other'))
    save(study/'protocol.json',p);bind(study)
    with pytest.raises(ValueError,match='population'):verifier.run(study,tmp_path/'audit')


def test_rehashed_final_selection_cannot_point_to_unverified_motion(tmp_path,monkeypatch):
    study=fixture(tmp_path,monkeypatch);p=study/'cases/no-op/completion.json';case=read(p);case['final_source']='unverified';save(p,case);bind(study)
    with pytest.raises(ValueError,match='last verified'):verifier.run(study,tmp_path/'audit')


def test_rehashed_pass_label_cannot_hide_unresolved_peaks(tmp_path,monkeypatch):
    study=fixture(tmp_path,monkeypatch);monkeypatch.setattr(verifier,'measure',lambda *_:(True,1.))
    with pytest.raises(ValueError,match='no-op pass'):verifier.run(study,tmp_path/'audit')
