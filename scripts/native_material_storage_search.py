"""Finite material-aware storage correction with complete decoded native gates.

Skin influence ancestry and native interpolation support define proposals.
They do not establish that rounding caused the error or that a fix exists.
The caller must retain every export and provide all additional original gates.
"""
import copy
import numpy as np
from native_material_witness_guides import MaterialWitnessGuides
from native_rotation_storage_repair import StorageAdjustedEdits
from native_scene_norms import rows
from native_rate_storage_search import apply_choice
from native_balanced_rate_storage_search import interleave_options


def excess(gaps, clearances, witnesses, depth_ceiling_m, triangle_ceiling_m):
    """Every frozen material row against the original two global ceilings."""
    gaps, clearances = np.asarray(gaps, float), np.asarray(clearances, float)
    if (gaps.ndim != 1 or not 1 <= len(gaps) <= 4096 or clearances.shape != gaps.shape
            or not np.isfinite(gaps).all() or not np.isfinite(clearances).all()
            or np.any(clearances < 0) or np.any(clearances > .1)
            or not isinstance(witnesses, list) or len(witnesses) != len(gaps)
            or any(type(v) not in (int, float) or not np.isfinite(v) or v < 0
                   for v in (depth_ceiling_m, triangle_ceiling_m))):
        raise ValueError('Complete finite material population and original nonnegative ceilings required')
    result = np.empty(len(gaps))
    for i, witness in enumerate(witnesses):
        if (not isinstance(witness, dict) or type(witness.get('descriptor_index')) is not int
                or witness['descriptor_index'] != i):
            raise ValueError('Complete ordered material witness identities required')
        if witness.get('kind') == 'penetrating-vertex':
            result[i] = -gaps[i]-depth_ceiling_m
        elif witness.get('kind') == 'triangle-separation':
            result[i] = clearances[i]-gaps[i]-triangle_ceiling_m
        else:
            raise ValueError('Explicit containment or triangle witness kind required')
    if not np.isfinite(result).all():
        raise ValueError('Finite complete material excess required')
    return result


def plan(observer, material_excess, corrections, *, maximum_options=65536):
    """All positive-weight skin ancestors on both ends of each failed row.

    Include the influenced node itself; rotating a skin point differs from
    rotating a joint origin. Include only target corners with nonzero authored
    barycentric weight. Retain both interpolation brackets, all editable
    ancestors, all four quaternion components and both absolute alternatives.
    An oversized option family is rejected whole, never silently truncated.
    """
    if (not isinstance(observer, MaterialWitnessGuides)
            or type(maximum_options) is not int or not 1 <= maximum_options <= 65536):
        raise ValueError('Validated complete material observer and bounded option population required')
    values = np.asarray(material_excess, float)
    if values.shape != (len(observer.prepared),) or not np.isfinite(values).all():
        raise ValueError('Complete finite material excess population required')
    if not isinstance(corrections, list) or len(corrections) > 64:
        raise ValueError('Complete bounded absolute correction list required')
    used = {}
    for row in corrections:
        if (not isinstance(row, dict) or set(row) != {'actor', 'node', 'key_index', 'component', 'step'}
                or type(row['actor']) is not str or row['actor'] not in observer.problem.edits.actors
                or any(type(row[k]) is not int for k in ('node', 'key_index', 'component', 'step'))
                or not 0 <= row['component'] < 4 or row['step'] not in (-1, 1)):
            raise ValueError('Distinct permitted absolute one-neighbor choices required')
        identity = tuple(row[k] for k in ('actor', 'node', 'key_index', 'component'))
        tracks = [e for e in observer.problem.edits.actors[row['actor']]['tracks']
                  if e['node'] == row['node'] and e['path'] == 'rotation']
        if identity in used or len(tracks) != 1 or row['key_index'] not in tracks[0]['ids']:
            raise ValueError('Distinct permitted absolute one-neighbor choices required')
        used[identity] = row['step']
    failures, options, seen = [], [], set()
    for index in sorted(np.flatnonzero(values > 0).tolist(), key=lambda i:(-values[i], i)):
        a, vertex, b, ids, bary, frame, _, _, _ = observer.prepared[index]
        time = float(observer.problem.times[frame]); support = {}
        for name, vertices in ((a, [vertex]), (b, ids[bary > 0].tolist())):
            actor = observer.problem.scene.actors[name]; skin = actor['skin']
            nodes, weights, parents = np.asarray(skin.nodes), np.asarray(skin.weights), np.asarray(actor['rig'].parents)
            if (nodes.ndim != 2 or weights.shape != nodes.shape or not np.issubdtype(nodes.dtype, np.integer)
                    or parents.ndim != 1 or not np.issubdtype(parents.dtype, np.integer)
                    or nodes.min() < 0 or nodes.max() >= len(parents)
                    or not np.isfinite(weights).all() or np.any(weights < 0)
                    or np.any(weights.sum(axis=1) <= 0)):
                raise ValueError('Complete source skin influence population required')
            ancestors = set()
            for source in vertices:
                for node in nodes[source][weights[source] > 0]:
                    visited = set(); node = int(node)
                    while node >= 0:
                        if node >= len(parents) or node in visited or parents[node] < -1:
                            raise ValueError('Acyclic valid source ancestry required')
                        visited.add(node); ancestors.add(node); node = int(parents[node])
            support[name] = dict(vertex_ids=vertices, influencing_ancestors=sorted(ancestors))
            if name not in observer.problem.edits.actors:
                continue
            for entry in observer.problem.edits.actors[name]['tracks']:
                if entry['path'] != 'rotation' or entry['node'] not in ancestors:
                    continue
                clock = np.asarray(entry['clock'], float)
                if (clock.ndim != 1 or not len(clock) or not np.isfinite(clock).all()
                        or np.any(np.diff(clock) <= 0)):
                    raise ValueError('Complete strictly increasing native key clock required')
                insertion = int(np.searchsorted(clock, time))
                brackets = ([insertion] if insertion < len(clock) and clock[insertion] == time
                            else [max(0, insertion-1), min(len(clock)-1, insertion)])
                for key in sorted(set(brackets), key=lambda k:(abs(float(clock[k])-time), k)):
                    if key not in entry['ids']:
                        continue
                    for component in (3, 2, 1, 0):
                        identity = name, entry['node'], key, component
                        for step in ((0, -used[identity]) if identity in used else (-1, 1)):
                            if identity+(step,) in seen:
                                continue
                            if len(options) >= maximum_options:
                                raise ValueError('Complete material option population exceeds its budget; no subset')
                            seen.add(identity+(step,))
                            options.append(dict(actor=name, node=entry['node'], key_index=key, component=component, step=step))
        failures.append(dict(row=index, excess_m=float(values[index]), time_s=time, support=support))
    return interleave_options(options), failures


def search(problem, value, policy, corrections, observer, witnesses,
           depth_ceiling_m, triangle_ceiling_m, decode, check_extra, *, stages=4, probes_per_stage=64):
    """Native/extra-gated best material improvement among a declared finite prefix.

    All native conditions must pass at the starting export. Every probe checks
    complete native norms, caps/scales, material rows and caller-supplied gates.
    Failed probes remain recorded; only a passing native/extra probe with strict
    lexicographic material improvement can become the next search state.
    """
    if (type(stages) is not int or not 1 <= stages <= 8 or type(probes_per_stage) is not int
            or not 1 <= probes_per_stage <= 64 or not callable(decode) or not callable(check_extra)
            or not isinstance(observer, MaterialWitnessGuides) or observer.problem is not problem):
        raise ValueError('Explicit finite budgets, original observer and complete decoded gate callbacks required')
    value = problem.edits.controls(value).copy()
    if np.any(value < problem.lower) or np.any(value > problem.upper):
        raise ValueError('Original cumulative control boxes remain required')
    witnesses = copy.deepcopy(witnesses)
    excess(np.zeros(len(observer.prepared)), observer.clearances, witnesses, depth_ceiling_m, triangle_ceiling_m)
    StorageAdjustedEdits(problem.edits, policy, corrections)
    baseline = rows(problem, value); caps, scales = baseline.caps.copy(), baseline.scales.copy()
    records, history = [], []
    def observe(candidate, label):
        adjusted = StorageAdjustedEdits(problem.edits, policy, candidate)
        for name in adjusted.actors:
            adjusted.values(name, value)
        reported, worlds = decode(copy.deepcopy(candidate), label)
        if not isinstance(worlds, dict) or set(worlds) != set(problem.scene.actors):
            raise ValueError('Complete independently decoded actor population required')
        for name, actor in problem.scene.actors.items():
            if (np.shape(worlds[name]) != (len(problem.times), len(actor['rig'].parents), 4, 4)
                    or not np.isfinite(worlds[name]).all()):
                raise ValueError('Complete finite decoded native worlds required')
        scalar = problem.constraints(value, worlds); native = rows(problem, value, worlds)
        if not np.array_equal(reported, scalar) or not np.isfinite(scalar).all():
            raise ValueError('Complete original scalar native residual required')
        if not np.array_equal(native.caps, caps) or not np.array_equal(native.scales, scales):
            raise ValueError('Original native caps/scales/population changed')
        np.testing.assert_allclose(native.residual(), scalar, atol=1e-9, rtol=1e-12)
        _, gaps = observer.observe(worlds)
        material = excess(gaps, observer.clearances, witnesses, depth_ceiling_m, triangle_ceiling_m)
        positive = np.maximum(material, 0); score = (float(positive.max()), float(np.linalg.norm(positive)))
        extra = check_extra(value.copy(), worlds, label)
        if type(extra) is not bool:
            raise ValueError('Explicit boolean complete additional gate result required')
        native_pass = bool(np.all(scalar <= 0) and np.all(native.residual() <= 0))
        record = dict(label=label, corrections=copy.deepcopy(candidate), material_merit_m=list(score),
                      failed_material_rows=int((material > 0).sum()), native_conditions_pass=native_pass,
                      complete_extra_gates_pass=extra, eligible_search_state=native_pass and extra)
        records.append(record)
        return material, score, record
    corrections = copy.deepcopy(corrections)
    material, score, initial = observe(corrections, 'start'); label = 'start'; queries = 0
    if not initial['eligible_search_state']:
        raise ValueError('Starting actual export must pass all original native and additional gates')
    for stage in range(stages):
        if np.all(material <= 0):
            break
        options, failures = plan(observer, material, corrections)
        item = dict(stage=stage, complete_options=options, material_failures=failures,
                    maximum_probes=probes_per_stage, probes=[], selected_label=None)
        history.append(item); best = None; best_score = score
        for i, choice in enumerate(options[:probes_per_stage]):
            candidate = apply_choice(corrections, choice); candidate_label = f'material-storage-{stage}-{i}'
            try:
                adjusted = StorageAdjustedEdits(problem.edits, policy, candidate)
                for name in adjusted.actors:
                    adjusted.values(name, value)
            except ValueError as error:
                item['probes'].append(dict(label=candidate_label, choice=choice, exported=False, rejection=str(error)))
                continue
            values, candidate_score, record = observe(candidate, candidate_label); queries += 1
            item['probes'].append(dict(label=candidate_label, choice=choice, exported=True))
            if record['eligible_search_state'] and candidate_score < best_score:
                best = candidate, values, candidate_label; best_score = candidate_score
                if candidate_score == (0., 0.):
                    break
        if best is None:
            break
        corrections, material, label = best; score = best_score; item['selected_label'] = label
    return corrections, dict(schema='strep-native-material-storage-search-v1', records=records, history=history,
        maximum_stages=stages, maximum_probes_per_stage=probes_per_stage, tested_neighbors=queries,
        final_label=label, material_conditions_pass=bool(np.all(material <= 0)), continuous_controls_unchanged=True,
        original_native_caps_scales_unchanged=True, geometry_assessed=False, quality_approved=False, release_approved=False,
        scope='Complete material-aware option family and explicit finite tested prefixes; native and caller gates hard. '
              'Absolute single-neighbor components with stable best lexicographic material improvement. '
              'No exhaustive feasibility, pure-rounding attribution, fresh derivative, collision or release approval.')
