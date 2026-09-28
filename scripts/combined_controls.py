"""Compose explicit controls in a fixed order; measure both final targets."""
import numpy as np
from motion_controls import edit, edit_diagnostics, KEYS


def combine(source, skeleton, arm, lean):
    # Lean changes the arm's world orientation. Solve the arm range last.
    leaned, lean_parameters = edit(source, skeleton, 'lean', lean)
    result, arm_parameters = edit(leaned, skeleton, 'arm', arm)
    report = edit_diagnostics(source, result, skeleton, 'arm', arm)
    report['target_errors_degrees'] = {
        'arm': abs(report['after'][KEYS['arm']] - arm),
        'lean': abs(report['after'][KEYS['lean']] - lean),
    }
    report['parameters'] = {'order': ['lean', 'arm'], 'lean': lean_parameters, 'arm': arm_parameters}
    assert all(np.isfinite(v).all() for v in result.values())
    return result, report


def screen(report, loop_flags, baseline_accepted, rules):
    flags = list(loop_flags)
    if not baseline_accepted: flags.append('neutral_baseline_quality')
    for key, error in report['target_errors_degrees'].items():
        if error > rules['target_error_degrees'][key]: flags.append(key + '_target')
    if max(report['root_max_change_m'], report['lower_body_max_change_m']) > rules['root_and_lower_body_tolerance_m']:
        flags.append('lower_body_changed')
    if not report['contacts_unchanged']: flags.append('contacts_changed')
    if report['max_local_edit_degrees'] > rules['maximum_local_edit_degrees']:
        flags.append('edit_budget')
    return sorted(set(flags))
