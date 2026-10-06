"""Finite native-checked quaternion search on all original joint-rate support.

Continuous controls, original caps and contacts are fixed. The callback must
retain fresh exports and independently decode every actor; returned worlds
and residuals are checked completely. Geometry and quality are separate gates.
"""
import copy
import numpy as np
from sampled_motion_caps import features, measures
from native_rotation_storage_repair import StorageAdjustedEdits
from native_scene_norms import rows
from native_support_feasibility import merit


def apply_choice(corrections, choice):
    """Replace a component's absolute neighbor, or restore its nearest value."""
    identity = tuple(choice[k] for k in ('actor', 'node', 'key_index', 'component'))
    if type(choice['step']) is not int or choice['step'] not in (-1, 0, 1):
        raise ValueError('Absolute negative/nearest/positive storage choice required')
    output = [copy.deepcopy(r) for r in corrections if tuple(r[k] for k in ('actor', 'node', 'key_index', 'component')) != identity]
    if choice['step']:
        output.append(copy.deepcopy(choice))
    return output


def plan(problem, worlds, corrections):
    """Rotation choices on exact original positional/angular rate stencils.

    Positional rates depend on strict ancestors' rotations; a joint's own
    rotation cannot move its origin. Angular rates include the joint itself.
    First derivatives use two samples, second derivatives use three. All
    permitted bracketing keys and all four absolute component choices remain.
    """
    groups, failures = {}, []
    orders = (1, 2, 1, 2)
    for name, actor in problem.scene.actors.items():
        if name not in problem.caps:
            continue
        rate = problem.caps[name]
        for metric, (values, cap) in enumerate(zip(measures(features(worlds[name][problem.rate_ids], actor['rig'].joints), rate.dt), rate.caps)):
            for frame, joint in np.argwhere(values-cap-rate.tolerance > 0):
                node = int(actor['rig'].joints[int(joint)])
                excess = float(values[frame, joint]-cap[frame, joint]-rate.tolerance)
                failures.append(dict(actor=name, metric=metric, frame=int(frame), node=node, excess=excess))
                if name not in problem.edits.actors:
                    continue
                parents = []
                node = node if metric >= 2 else actor['rig'].parents[node]
                while node >= 0:
                    parents.append(node); node = actor['rig'].parents[node]
                for entry in problem.edits.actors[name]['tracks']:
                    if entry['path'] == 'rotation' and entry['node'] in parents:
                        key = name, entry['node'], metric, int(frame)
                        severity = excess/max(float(cap[frame, joint]), .001)
                        groups[key] = max(groups.get(key, -np.inf), severity)
    options, seen = [], set()
    used = {tuple(r[k] for k in ('actor', 'node', 'key_index', 'component')):r['step'] for r in corrections}
    for (name, node, metric, frame), severity in sorted(groups.items(), key=lambda item:(item[1], item[0]), reverse=True):
        entry = next(e for e in problem.edits.actors[name]['tracks'] if e['node'] == node and e['path'] == 'rotation')
        clock, keys = entry['clock'], set();order = orders[metric]
        for time in problem.uniform[frame:frame+order+1]:
            i = int(np.searchsorted(clock, time))
            keys.update([i] if i < len(clock) and clock[i] == time else [max(0, i-1), min(len(clock)-1, i)])
        center = float((problem.uniform[frame]+problem.uniform[frame+order])/2)
        for key in sorted(keys, key=lambda k:(abs(float(clock[k])-center), k)):
            if key not in entry['ids']:
                continue
            for component in (3, 2, 1, 0):
                identity = name, node, key, component
                choices = (0, -used[identity]) if identity in used else (-1, 1)
                for step in choices:
                    if identity+(step,) in seen:
                        continue
                    seen.add(identity+(step,))
                    options.append(dict(actor=name, node=node, key_index=key, component=component, step=step))
    return options, failures


def search(problem, value, policy, corrections, decode, *, stages=8, probes_per_stage=32):
    if (type(stages) is not int or not 1 <= stages <= 8
            or type(probes_per_stage) is not int or not 1 <= probes_per_stage <= 64 or not callable(decode)):
        raise ValueError('Explicit finite storage-search budgets and decoded callback required')
    value = problem.edits.controls(value).copy()
    if np.any(value < problem.lower) or np.any(value > problem.upper):
        raise ValueError('Original control boxes remain required')
    StorageAdjustedEdits(problem.edits, policy, corrections)
    original = rows(problem, value); caps, scales = original.caps.copy(), original.scales.copy()
    records, history = [], []
    def observe(candidate, label):
        adjusted = StorageAdjustedEdits(problem.edits, policy, candidate)
        for name in adjusted.actors:
            adjusted.values(name, value)  # Original track/unit/storage envelope before exporting.
        reported, worlds = decode(copy.deepcopy(candidate), label)
        if not isinstance(worlds, dict) or set(worlds) != set(problem.scene.actors):
            raise ValueError('Complete independently decoded actor population required')
        for name, actor in problem.scene.actors.items():
            if np.shape(worlds[name]) != (len(problem.times), len(actor['rig'].parents), 4, 4) or not np.isfinite(worlds[name]).all():
                raise ValueError('Complete finite decoded native worlds required')
        current = problem.constraints(value, worlds)
        if not np.array_equal(reported, current):
            raise ValueError('Reported residual differs from original native conditions')
        system = rows(problem, value, worlds)
        if not np.array_equal(system.caps, caps) or not np.array_equal(system.scales, scales):
            raise ValueError('Original native caps/scales/population changed')
        np.testing.assert_allclose(system.residual(), current, atol=1e-9, rtol=1e-12)
        records.append(dict(label=label, corrections=copy.deepcopy(candidate), merit=list(merit(current)),
            failed_native_rows=int((current > 0).sum()), native_conditions_pass=bool(np.all(current <= 0))))
        return current, worlds
    corrections = copy.deepcopy(corrections)
    current, worlds = observe(corrections, 'start'); label = 'start'; queries = 0
    for stage in range(stages):
        if np.all(current <= 0):
            break
        options, failures = plan(problem, worlds, corrections)
        before = merit(current); item = dict(stage=stage, original_rate_failures=failures,
            planned_options=len(options), maximum_probes=probes_per_stage, probes=[], selected_native_anchor=None)
        history.append(item); improved = None
        for i, choice in enumerate(options[:probes_per_stage]):
            candidate = apply_choice(corrections, choice); candidate_label = f'storage-{stage}-{i}'
            try:
                adjusted = StorageAdjustedEdits(problem.edits, policy, candidate)
                for name in adjusted.actors:
                    adjusted.values(name, value)
            except ValueError as exc:
                item['probes'].append(dict(label=candidate_label, choice=choice, exported=False, rejection=str(exc)))
                continue
            residual, decoded = observe(candidate, candidate_label); queries += 1; score = merit(residual)
            item['probes'].append(dict(label=candidate_label, choice=choice, exported=True, merit=list(score)))
            if np.all(residual <= 0) or score[0] < before[0]-1e-12 or abs(score[0]-before[0]) <= 1e-12 and score[1] < before[1]-1e-15:
                improved = candidate, residual, decoded, candidate_label
                break
        if improved is None:
            break
        corrections, current, worlds, label = improved; item['selected_native_anchor'] = label
    return corrections, dict(schema='strep-native-rate-storage-search-v1', records=records, history=history,
        maximum_stages=stages, maximum_probes_per_stage=probes_per_stage, tested_neighbors=queries,
        final_label=label, native_conditions_pass=bool(np.all(current <= 0)), failed_native_rows=int((current > 0).sum()),
        original_native_caps_scales_unchanged=True, continuous_controls_unchanged=True,
        geometry_assessed=False, quality_approved=False, release_approved=False,
        scope='Finite greedy native-merit search on positional/angular speed and acceleration interpolation support. '
            'Absolute one-neighbor choices may add, restore or replace components without accumulating steps. '
            'All original conditions checked on every complete decoded probe; no exhaustive feasibility or geometry/quality claim.')
