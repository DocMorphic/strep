import copy
from pathlib import Path
import sys
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from strep import read, save, sha256
from finish_contact_feedback import finish, checked_flags, EXPORT_FILES
import contact_export_repair
import evaluate_contact_spec


def audit():
    return dict(all_requested_pin_samples_within_5mm=True,
                floor_nonregression=dict(maximum_added_depth_m=0, samples_over_1um_numerical_budget=0),
                outside_preservation_passed=True, phase_rates=[dict(candidate_excess_over_checked=[0, 0])],
                variants=dict(candidate=dict(joints=[dict(peak_speed_m_s=1, peak_acceleration_m_s2=2)])))


def test_raw_floor_and_global_rate_failures_cannot_be_hidden():
    a = audit();a['floor_nonregression']['maximum_added_depth_m'] = 1e-12
    assert checked_flags(a, [1, 2]) == ['exported_floor_nonregression_missed']
    a = audit();a['variants']['candidate']['joints'][0]['peak_acceleration_m_s2'] += 1e-12
    assert checked_flags(a, [1, 2]) == ['exported_global_rate_excess']
    assert checked_flags(audit(), [1, 2], dict(serialized_minimum_slack=-1e-12)) == ['serialized_contact_constraints_missed']


def test_all_final_export_failure_categories_retained():
    a = audit();a['all_requested_pin_samples_within_5mm'] = False
    a['outside_preservation_passed'] = False;a['phase_rates'][0]['candidate_excess_over_checked'] = [.1, 0]
    assert checked_flags(a, [1, 2]) == ['exported_checked_pins_missed', 'exported_outside_window_changed', 'exported_point_rate_excess']


@pytest.mark.parametrize('corrupt', [False, True])
def test_selected_motion_metadata_and_initial_provenance(tmp_path, monkeypatch, corrupt):
    source, take, plan, output = [tmp_path/n for n in ['source', 'take', 'check', 'feedback']]
    for p in [source, take, plan]:p.mkdir()
    np.savez(source/'motion.npz', root_positions=np.zeros((2, 3)))
    np.savez(take/'motion.npz', root_positions=np.ones((2, 3))*.1)
    for n in EXPORT_FILES[1:]: (take/n).write_bytes(b'initial')
    save(take/'checked-export-audit.json', audit());save(plan/'bound-contact-spec.json', dict(marker='exact-plan'))
    recipe = dict(root_lift_m=[.1, .1], max_rotation_delta_degrees=30, support={'initial': True})
    original_recipe = copy.deepcopy(recipe)
    initial_hash = sha256(take/'motion.npz')

    def adapter(src, seed, check, dest, *, max_lift, max_degrees):
        assert (src, seed, check, dest) == (source, take/'initial-fit', plan, output)
        assert (max_lift, max_degrees) == (.22, 40)
        assert sha256(seed/'motion.npz') == initial_hash
        selected = dest/'candidate';selected.mkdir(parents=True)
        motion = np.zeros((2, 3));motion[:, 1] = .05
        np.savez(selected/'motion.npz', root_positions=motion)
        for n in EXPORT_FILES[1:]: (selected/n).write_bytes(b'selected')
        save(selected/'checked-export-audit.json', audit())
        save(selected/'body-evaluation.json', dict(evaluation=dict(flags=['selected-body']), body=dict(selected=True)))
        save(selected/'validation.json', dict(selected_validation=True))
        save(selected/'budgets.json', dict(maximum_rotation_delta_degrees=20))
        save(dest/'completion.json', dict(files={'candidate/'+p.name: sha256(p) for p in selected.iterdir()}))
        if corrupt:(selected/'soma.glb').write_bytes(b'changed after completion')
        return dict(selected_export='trial-2-0', serialized_minimum_slack=0, export_and_native_screen=True)

    def targets(src, candidate, skin, spec, tolerance):
        assert spec == dict(marker='exact-plan') and tolerance == .005
        assert not src['root_positions'].any()
        assert (candidate['root_positions'][:, 1] == .05).all()
        return dict(intervals=[dict(frames_outside_tolerance=0)])

    monkeypatch.setattr(contact_export_repair, 'run', adapter)
    monkeypatch.setattr(evaluate_contact_spec, 'evaluate', targets)
    args = (source, take, plan, output, dict(max_root_lift_m=.22, max_rotation_degrees=40), recipe,
            dict(flags=['initial-body']), dict(initial=True), dict(intervals=[]), {})
    if corrupt:
        with pytest.raises(ValueError, match='Selected feedback artifact changed'):finish(*args)
        assert sha256(take/'motion.npz') == initial_hash
        return
    result = finish(*args)
    assert recipe == original_recipe
    assert result['recipe']['root_lift_m'] == [.05, .05]
    assert result['recipe']['max_rotation_delta_degrees'] == 20
    assert result['evaluation']['flags'] == ['selected-body'] and result['body'] == dict(selected=True)
    assert read(take/'initial-fit/recipe.json') == original_recipe
    assert sha256(take/'initial-fit/motion.npz') == initial_hash
    assert sha256(take/'motion.npz') == sha256(output/'candidate/motion.npz')
    assert (take/'root-motion.json').read_bytes() == b'selected'
    assert read(take/'feedback-report.json')['selected_export'] == 'trial-2-0'
