"""Require added angular guards when continuing an angular-audited source."""
from strep import read
from study_repaired_root_release import audited_source as root_contact_source
from legacy_angular_source import SCHEMA,validate


def require_angular_preservation(audit):
    if 'joints' in audit:
        checks=audit.get('checks',{})
        if audit.get('all_preservation_checks_passed') is not True or not checks or not all(v is True for v in checks.values()) or checks.get('all_angular_safety_caps') is not True:
            raise ValueError('Previous angular preservation audit must pass before continuation')


def audited_source(source,audit_path):
    audit=read(audit_path)
    if audit.get('schema')==SCHEMA:return validate(source,audit_path)
    require_angular_preservation(audit)
    return root_contact_source(source,audit_path)
