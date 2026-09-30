import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from refined_reserve_inputs import completed, install_refined_models, load_refined_audit
from strep import save, sha256


def actor_fixture():
    from test_timed_rotation_edit import fixture
    from timed_rotation_edit import TimedRotationEdit
    from scene_pair_problem import MotionRows
    from diagnose_scene_pair_refinement import refine_knots
    doc, binary = fixture()
    old = TimedRotationEdit(doc, binary, ['Arm', 'Twin'], np.arange(181)/120, [.1, 1.3], [[.713, .713]])
    knots, _ = refine_knots(old.knots, 2)
    actor = dict(name='A', model=old, rates=MotionRows(old, doc['skins'][0]['joints'], np.eye(3), np.zeros(3)),
        rig=SimpleNamespace(joints=doc['skins'][0]['joints']))
    description = dict(actor='A', original_knots_s=old.knots.tolist(), refined_knots_s=knots.tolist(),
        original_controls=old.size, refined_controls=2*(len(knots)-2)*3)
    return actor, description


def test_reconstructed_curve_retains_original_positional_and_angular_policy():
    from angular_motion_rows import AngularMotionRows
    actor, description = actor_fixture(); old = actor['model']; rates = actor['rates']
    angular = AngularMotionRows(old, actor['rig'].joints)
    before = rates.values(old.source_world)[0].copy(); angular_before = angular.values(old.source_world)[0].copy()
    install_refined_models([actor], [description])
    assert actor['rates'] is rates and actor['model'].size > old.size
    np.testing.assert_array_equal(actor['original_knots'], old.knots)
    np.testing.assert_array_equal(angular.knots, old.knots)
    np.testing.assert_array_equal(rates.values(actor['model'].source_world)[0], before)
    np.testing.assert_array_equal(angular.values(actor['model'].source_world)[0], angular_before)


@pytest.mark.parametrize('field,value', [('actor','B'), ('original_controls',999), ('refined_controls',999),
    ('original_knots_s',[0, .5, 1]), ('refined_knots_s',[0, .25, .5, .75, 1])])
def test_changed_actor_or_control_layout_rejected(field, value):
    actor, description = actor_fixture(); description[field] = value
    with pytest.raises((ValueError, AssertionError)): install_refined_models([actor], [description])


def test_completed_evidence_rejects_changed_or_incomplete_inputs(tmp_path):
    source = tmp_path/'source'; source.write_text('original')
    save(tmp_path/'request.json', dict(inputs={str(source):sha256(source)}, implementation={}))
    save(tmp_path/'trials.json', [])
    result = dict(status='complete', request_sha256=sha256(tmp_path/'request.json'), trials_sha256=sha256(tmp_path/'trials.json'))
    save(tmp_path/'result.json', result)
    _, files = completed(tmp_path, ['request.json', 'trials.json'])
    assert str(source) in files
    source.write_text('changed')
    with pytest.raises(ValueError, match='Declared evidence changed'): completed(tmp_path, ['request.json', 'trials.json'])
    result['status'] = 'running'; save(tmp_path/'result.json', result)
    with pytest.raises(ValueError, match='Completed'): completed(tmp_path, ['request.json', 'trials.json'])


@pytest.mark.parametrize('change', ['caps', 'kinds', 'scaling', 'study'])
def test_refined_inputs_reject_policy_and_objective_changes(tmp_path, monkeypatch, change):
    import refined_reserve_inputs as module
    study = tmp_path/'study'; refinement = tmp_path/'refinement'; refinement.mkdir()
    linear = {key:np.ones((2,3) if key in ['surface_vectors','vectors'] else 2) for key in ['surface_vectors','gaps','depth_caps','vectors','radii']}
    linear['kinds'] = np.array(['speed','angular_speed'])
    changed = {k:v.copy() for k,v in linear.items()}
    if change == 'caps': changed['radii'][0] += .01
    if change == 'kinds': changed['kinds'][0] = 'edit'
    np.savez(refinement/'linearization.npz', **changed)
    parent = dict(study=str(study if change != 'study' else tmp_path/'other'), inputs={},
        solver_scaling=dict(scale=.025, regularizer=.00002 if change != 'scaling' else .00003))
    monkeypatch.setattr(module, 'completed', lambda path,names: (parent if Path(path)==refinement else dict(angular_motion=True, refinement=str(refinement), inputs={}), {}))
    with pytest.raises((ValueError, AssertionError)): load_refined_audit(tmp_path/'audit', study, linear, {})
