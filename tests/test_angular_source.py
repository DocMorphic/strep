from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from angular_source import require_angular_preservation


def test_rejects_false_or_missing_added_guard_even_if_root_flag_passes():
    for extra in [{},{'all_preservation_checks_passed':False},{'all_preservation_checks_passed':True,'checks':{'all_angular_safety_caps':False}},
                  {'all_preservation_checks_passed':True,'checks':{'all_angular_safety_caps':True,'original_comparisons_preserved':False}}]:
        with pytest.raises(ValueError):require_angular_preservation(dict(joints=[{}],all_repaired_root_checks_passed=True,**extra))


def test_allows_initial_root_audit_and_guarded_incomplete_target():
    require_angular_preservation({'all_repaired_root_checks_passed':True})
    require_angular_preservation(dict(joints=[{}],target_passed=False,all_joint_peak_comparisons_passed=False,all_preservation_checks_passed=True,checks={'all_angular_safety_caps':True,'original_comparisons_preserved':True}))
