from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from package_correction_review import presentation,checked_copy
from strep import sha256


def test_only_successful_correction_gets_corrected_export():
    assert presentation('numerical_pass')[1]
    for status in ['ineligible','failed','budget_exhausted','no_progress','preservation_failed','already_passed','unknown']:
        assert not presentation(status)[1]


def test_stale_source_digest_is_rejected_before_copy(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'original');digest=sha256(source);source.write_bytes(b'changed')
    target=tmp_path/'published'/'clip.glb'
    with pytest.raises(ValueError,match='changed'):checked_copy(source,target,digest)
    assert not target.exists()


def test_copy_keeps_exact_audited_bytes(tmp_path):
    source=tmp_path/'source';source.write_bytes(bytes(range(256)));target=tmp_path/'published'/'clip.glb'
    assert checked_copy(source,target,sha256(source))==sha256(source)==sha256(target)
