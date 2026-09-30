import copy
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from scene_pair_relinearization import angular_at, refreshed_problem, retain_original_surfaces
from scene_pair_problem import ScenePairProblem
from angular_motion_rows import AngularMotionRows
from test_scene_pair_problem import actors, samples


def test_nonzero_angular_linearization_keeps_source_caps_and_uses_current_pose():
    pair = actors(); problem = ScenePairProblem(pair, samples(pair))
    policies = [AngularMotionRows(a['model'], a['rig'].joints) for a in pair]
    controls = np.random.default_rng(45).normal(size=problem.size)*.015
    base = problem.linearize(controls)
    result, proofs = angular_at(pair, policies, base, controls)
    values = []; zero_values = []
    for actor, policy, part in zip(pair, policies, problem.split(controls)):
        values.append(policy.values(actor['model'].world(part))[0])
        zero_values.append(policy.values(actor['model'].source_world)[0])
    start = len(base['radii'])
    np.testing.assert_array_equal(result['vectors'][start:], np.concatenate(values))
    np.testing.assert_array_equal(result['radii'][start:], np.concatenate([p.radii for p in policies]))
    assert np.max(np.abs(np.concatenate(values)-np.concatenate(zero_values))) > .01
    delta = np.random.default_rng(49).normal(size=problem.size)*1e-7
    actual = np.concatenate([p.values(a['model'].world(c))[0] for a,p,c in zip(pair,policies,problem.split(controls+delta))])
    np.testing.assert_allclose(actual, result['vectors'][start:]+np.einsum('nid,d->ni',result['jacobians'][start:],delta), atol=1e-5, rtol=0)
    assert all(max(p['directional_errors'].values()) < 1e-5 for p in proofs)


def test_refresh_changes_witnesses_but_never_rebases_source_depth_caps():
    pair = actors(); old = samples(pair); changed = copy.deepcopy(old)
    for row in changed:
        for direction in row['directions']:
            direction['maximum_depth_m'] = .2
            direction['records'][0]['normal'] = [0., 1., 0.]
            direction['records'][0]['barycentric'] = [.5, .4, .1]
    original, current = refreshed_problem(pair, old, changed)
    for group in current.groups:
        np.testing.assert_array_equal(group['caps'], .02)
        np.testing.assert_array_equal(group['normals'][:,1], 1)
    controls = np.ones(original.size)*.003
    before, after = original.linearize(controls), current.linearize(controls)
    joined = retain_original_surfaces(after, before)
    for key in ['gaps','gap_jacobian','depth_caps','surface_vectors','surface_jacobians']:
        np.testing.assert_array_equal(joined[key][len(after[key]):], before[key])
    assert not np.array_equal(before['gaps'], after['gaps'])
    assert old[0]['directions'][0]['records'][0]['normal'] == [1.,0.,0.]


@pytest.mark.parametrize('fault',['shape','nan','policy'])
def test_nonzero_angular_rejects_invalid_control_or_policy_population(fault):
    pair = actors(); problem = ScenePairProblem(pair, samples(pair)); controls = np.zeros(problem.size)
    policies = [AngularMotionRows(a['model'],a['rig'].joints) for a in pair]
    if fault=='shape': controls=controls[:,None]
    if fault=='nan': controls[0]=np.nan
    if fault=='policy': policies=policies[:1]
    with pytest.raises(ValueError): angular_at(pair,policies,{},controls)


@pytest.mark.parametrize('fault',[None,'changed','rejected','duplicate','shape','nan'])
def test_continuation_starts_from_one_bound_accepted_trial(tmp_path,fault):
    from study_scene_pair_relinearization import selected_controls
    from strep import save,sha256
    row=dict(folder='candidate',accepted_local_step=True,reasons=[],controls=[.1,.2,.3])
    if fault=='rejected': row['reasons']=['exported_motion']
    if fault=='shape': row['controls']=[[.1,.2,.3]]
    if fault=='nan': row['controls']=['nan',0.,0.]
    save(tmp_path/'trials.json',[row,row] if fault=='duplicate' else [row])
    result=dict(selected='candidate',trials_sha256=sha256(tmp_path/'trials.json'))
    if fault=='changed': save(tmp_path/'trials.json',[])
    if fault is None: np.testing.assert_array_equal(selected_controls(tmp_path,result),row['controls'])
    else:
        with pytest.raises(ValueError): selected_controls(tmp_path,result)
