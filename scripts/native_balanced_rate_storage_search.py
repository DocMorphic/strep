"""Finite best-improvement search with interleaved original rate options.

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


from native_rate_storage_search import plan as original_plan, apply_choice


def interleave_options(options):
    """Round-robin actor/joint groups in original first-encounter order.

    Preserve every absolute choice and each group's internal order. Exhausted
    groups drop out. This only allocates a finite prefix across joint groups;
    it does not enlarge the option family or prove that a candidate will pass.
    """
    groups = {}
    for option in options:
        groups.setdefault((option['actor'], option['node']), []).append(option)
    return [group[i] for i in range(max(map(len, groups.values()), default=0))
            for group in groups.values() if i < len(group)]


def plan(problem, worlds, corrections):
    options, failures = original_plan(problem, worlds, corrections)
    return interleave_options(options), failures


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
        history.append(item); improved = None; best_score = None
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
                if improved is None or score < best_score:
                    improved = candidate, residual, decoded, candidate_label; best_score = score
                if np.all(residual <= 0):
                    break  # Zero positive merit is already optimal within this gate.
        if improved is None:
            break
        corrections, current, worlds, label = improved; item['selected_native_anchor'] = label
    return corrections, dict(schema='strep-native-balanced-rate-storage-search-v1', records=records, history=history,
        maximum_stages=stages, maximum_probes_per_stage=probes_per_stage, tested_neighbors=queries,
        final_label=label, native_conditions_pass=bool(np.all(current <= 0)), failed_native_rows=int((current > 0).sum()),
        original_native_caps_scales_unchanged=True, continuous_controls_unchanged=True,
        geometry_assessed=False, quality_approved=False, release_approved=False,
        scope='Finite best-improvement native-merit search among eligible probed positional/angular rate neighbors, interleaved by actor/joint while preserving every option and within-group order, with first stable tie and early exit only on native pass. '
            'Absolute one-neighbor choices may add, restore or replace components without accumulating steps. '
            'All original conditions checked on every complete decoded probe; no exhaustive feasibility or geometry/quality claim.')
