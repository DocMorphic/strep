from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from legacy_angular_source import require_legacy_audit,root_envelope


def test_known_legacy_formats_require_all_guards_and_exact_binding():
    base=dict(study_completion_sha256='c',decoded_audit_sha256='d')
    restore=dict(base,strict_checks={'floor':True},strict_checks_passed=True,original_full_checks_passed=True)
    block=dict(base,envelope_checks={'root':True},failed_full_checks=[],protected_parameters_unchanged=True,accepted_parameter_reconstruction=True,new_release_failures_relative_to_source=[])
    for good in [restore,block]:
        require_legacy_audit(good,'c','d')
        with pytest.raises(ValueError):require_legacy_audit(good,'changed','d')
    for bad in [dict(restore,strict_checks_passed=False),dict(restore,strict_checks={'floor':False}),dict(block,failed_full_checks=['root']),dict(block,accepted_parameter_reconstruction=False),base]:
        with pytest.raises(ValueError):require_legacy_audit(bad,'c','d')


def test_existing_root_envelope_is_not_replaced_and_partial_fields_reject():
    original=dict(root_original_limit_m_s2=1.,root_safety_caps_m_s2=[.5])
    assert root_envelope(None,None,original) is original
    with pytest.raises(ValueError,match='Incomplete'):root_envelope(None,None,dict(root_original_limit_m_s2=1.))
