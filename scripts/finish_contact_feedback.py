"""Select feedback exports for Studio while preserving the initial fitted take."""
import copy
from pathlib import Path
import shutil
import numpy as np
from strep import read, save, sha256

EXPORT_FILES = ['motion.npz', 'motion.bvh', 'soma.glb', 'root-motion.json', 'contacts.json']


def finish(source, take, checked_plan, output, config, recipe, evaluation, body, targets, skin):
    from contact_export_repair import run
    from evaluate_contact_spec import evaluate as evaluate_targets
    source, take, output = map(Path, [source, take, output])
    initial = take/'initial-fit'
    initial.mkdir(exist_ok=False)
    for name in EXPORT_FILES+['checked-export-audit.json']:
        shutil.copyfile(take/name, initial/name)
    save(initial/'recipe.json', recipe)
    save(initial/'body-evaluation.json', dict(evaluation=evaluation, body=body))
    save(initial/'explicit-contact-evaluation.json', targets)
    initial_hashes = {p.name: sha256(p) for p in initial.iterdir()}
    report = run(source, initial, checked_plan, output,
                 max_lift=config['max_root_lift_m'], max_degrees=config['max_rotation_degrees'])
    selected = output/'candidate'
    # The adapter's immutable seed path remains initial-fit, never the replaced take.
    for name, digest in initial_hashes.items():
        if sha256(initial/name) != digest:
            raise ValueError('Initial fit changed during export feedback')
    completion = read(output/'completion.json')
    for name in EXPORT_FILES+['checked-export-audit.json', 'body-evaluation.json', 'budgets.json', 'validation.json']:
        if sha256(selected/name) != completion['files']['candidate/'+name]:
            raise ValueError('Selected feedback artifact changed: '+name)
    candidate = dict(np.load(selected/'motion.npz'))
    original = dict(np.load(source/'motion.npz'))
    measured = read(selected/'body-evaluation.json')
    targets = evaluate_targets(original, candidate, skin, read(checked_plan/'bound-contact-spec.json'), .005)
    recipe = copy.deepcopy(recipe)
    recipe['export_feedback'] = dict(report, initial_fit='initial-fit/recipe.json',
        fit_measurements_scope='Optimizer/stage measurements describe the initial fit; final exported measurements are in checked-export-audit.json and feedback-report.json.')
    recipe['root_lift_m'] = (candidate['root_positions'][:, 1].astype(float)-original['root_positions'][:, 1]).tolist()
    recipe['max_rotation_delta_degrees'] = read(selected/'budgets.json')['maximum_rotation_delta_degrees']
    # All selected files and metadata are validated before replacing the take payload.
    for name in EXPORT_FILES+['checked-export-audit.json']:
        shutil.copyfile(selected/name, take/name)
    save(take/'feedback-report.json', report)
    save(take/'feedback-initial-hashes.json', initial_hashes)
    return dict(candidate=candidate, recipe=recipe, evaluation=measured['evaluation'], body=measured['body'],
                targets=targets, export_audit=read(selected/'checked-export-audit.json'),
                validation=read(selected/'validation.json'), feedback=report)


def checked_flags(audit, global_caps, feedback=None):
    """Keep final export failures separate from optimizer convergence diagnostics."""
    flags = []
    if not audit['all_requested_pin_samples_within_5mm']:
        flags.append('exported_checked_pins_missed')
    if audit['floor_nonregression']['maximum_added_depth_m'] > 0:
        flags.append('exported_floor_nonregression_missed')
    if not audit['outside_preservation_passed']:
        flags.append('exported_outside_window_changed')
    if any(max(row['candidate_excess_over_checked']) > 0 for row in audit['phase_rates']):
        flags.append('exported_point_rate_excess')
    peaks = [max(r[k] for r in audit['variants']['candidate']['joints'])
             for k in ['peak_speed_m_s', 'peak_acceleration_m_s2']]
    if any(a > b for a, b in zip(peaks, global_caps, strict=True)):
        flags.append('exported_global_rate_excess')
    if feedback is not None and feedback['serialized_minimum_slack'] < 0:
        flags.append('serialized_contact_constraints_missed')
    return flags
