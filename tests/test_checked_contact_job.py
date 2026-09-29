import sys,shutil
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import checked_contact_job as job
from strep import save,sha256


@pytest.fixture
def bound_check(tmp_path,monkeypatch):
    monkeypatch.setattr(job,'ROOT',tmp_path)
    asset=tmp_path/'mesh.npz';asset.write_bytes(b'opaque mesh');monkeypatch.setattr(job,'ASSET',asset)
    check=tmp_path/'reports/contact-jobs/check1';source=tmp_path/'reports/native/take'
    (check/'source').mkdir(parents=True);source.mkdir(parents=True);(tmp_path/'scripts').mkdir()
    inputs={}
    for name in ['motion.npz','soma.glb']:
        (source/name).write_bytes(b'opaque source bytes');shutil.copyfile(source/name,check/'source'/name);inputs[name]=sha256(source/name)
    implementation={}
    for name in job.RATE_METHODS:
        (tmp_path/'scripts'/name).write_text('opaque version');implementation[name]=sha256(tmp_path/'scripts'/name)
    save(check/'edit-request.json',dict(options=dict(edit_window=[2,17])))
    save(check/'contact-spec.json',{});save(check/'bound-contact-spec.json',{})
    save(check/'freeze.json',dict(inputs=inputs,implementation=implementation,mesh_sha256=sha256(asset),
        request_sha256=sha256(check/'edit-request.json'),spec_sha256=sha256(check/'contact-spec.json')))
    save(check/'timing-result.json',dict(status='checked',conflicts=0,source='native/take',requested_window=[2,17],
        files={n:sha256(check/n) for n in ['freeze.json','bound-contact-spec.json']}))
    save(check/'pipeline.json',dict(status='checked'))
    return dict(checked_plan='check1',revision=sha256(check/'timing-result.json')),check,source


def test_exact_checked_identity_and_current_source_required(bound_check):
    payload,check,source=bound_check
    assert job.validate_request(payload)==(check,source)
    (source/'motion.npz').write_bytes(b'changed')
    with pytest.raises(ValueError,match='Current clip differs'):job.validate_request(payload)


def test_window_cannot_change_behind_saved_check(bound_check):
    payload,check,_=bound_check;save(check/'edit-request.json',dict(options=dict(edit_window=[1,18])))
    with pytest.raises(ValueError,match='Checked request changed'):job.validate_request(payload)


def test_altered_bound_points_and_stale_revision_rejected(bound_check):
    payload,check,_=bound_check
    with pytest.raises(ValueError,match='review it again'):job.validate_request(dict(payload,revision='0'*64))
    save(check/'bound-contact-spec.json',dict(changed=True))
    with pytest.raises(ValueError,match='Checked artifact changed'):job.validate_request(payload)


def test_conflicting_check_cannot_start_fit(bound_check):
    payload,check,_=bound_check;save(check/'pipeline.json',dict(status='needs_authoring_change'))
    with pytest.raises(ValueError,match='Resolve timing conflicts'):job.validate_request(payload)


def test_calculation_version_change_requires_new_check(bound_check):
    payload,_,_=bound_check;(job.ROOT/'scripts'/job.RATE_METHODS[0]).write_text('new version')
    with pytest.raises(ValueError,match='Rate calculation changed'):job.validate_request(payload)


def test_mesh_change_requires_new_check(bound_check):
    payload,_,_=bound_check;job.ASSET.write_bytes(b'changed mesh outside pinned point')
    with pytest.raises(ValueError,match='Contact mesh changed'):job.validate_request(payload)


def test_mesh_change_after_job_snapshot_is_rejected(tmp_path,monkeypatch):
    asset=tmp_path/'mesh.npz';asset.write_bytes(b'mesh');monkeypatch.setattr(job,'ASSET',asset)
    save(tmp_path/'checked-freeze.json',dict(implementation={},inputs={},mesh_sha256=sha256(asset)))
    job.verify(tmp_path);asset.write_bytes(b'changed')
    with pytest.raises(ValueError,match='Guarded-job mesh changed'):job.verify(tmp_path)
