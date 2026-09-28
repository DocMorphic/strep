from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import save,read,sha256
from study_repaired_root_release import audited_source


def source(tmp_path,failures=None):
    trial=tmp_path/'trial';audit=tmp_path/'audit';trial.mkdir();audit.mkdir()
    save(trial/'request.json',dict(case='example'))
    save(trial/'completion.json',dict(request_sha256=sha256(trial/'request.json'),files={}))
    save(trial/'pipeline.json',dict(status='complete'))
    save(audit/'fixed-root-diagnostic.json',dict(completion_sha256=sha256(trial/'completion.json'),failed_full_checks=failures or ['Left_every_release_acceleration_no_worse']))
    save(audit/'completion.json',dict(completion_sha256=sha256(trial/'completion.json'),all_root_aware_checks_passed=True,
        fixed_root_diagnostic_sha256=sha256(audit/'fixed-root-diagnostic.json')))
    return trial,audit/'completion.json'


def test_accepts_bound_root_repair_with_only_remaining_release_failures(tmp_path):
    trial,audit=source(tmp_path);decoded,path=audited_source(trial,audit)
    assert path.name=='fixed-root-diagnostic.json' and len(decoded['failed_full_checks'])==1


def test_rejects_remaining_root_failure(tmp_path):
    trial,audit=source(tmp_path,['root_acceleration_max_m_s2_no_worse'])
    with pytest.raises(ValueError,match='non-release'):audited_source(trial,audit)


def test_rejects_changed_source_or_release_audit(tmp_path):
    trial,audit=source(tmp_path);save(audit.parent/'fixed-root-diagnostic.json',{})
    with pytest.raises(ValueError,match='bound release'):audited_source(trial,audit)
    save(trial/'request.json',dict(case='different'))
    with pytest.raises(ValueError,match='exact completed'):audited_source(trial,audit)
