"""Explain saved sampled geometry failures under explicit actor edit windows.

This reads diagnostics; it does not recompute collision or grant approval.
An editable failure is not a feasibility claim. Frozen failures require changed
source/scene intent or a broader explicit edit epoch, not relaxed acceptance.
"""
import argparse
from collections import Counter
import math
import re
from pathlib import Path

from native_scene_contacts import fields
from strep import read, save, sha256

SCHEMA = 'strep-native-geometry-failure-profile-v1'
SCOPE_SCHEMA = 'strep-native-geometry-edit-scope-v1'


def require(value, message):
    if not value: raise ValueError(message)


def number(value):
    require(type(value) in (int, float) and math.isfinite(value), 'Finite numeric geometry value required')
    return float(value)


def boolean(value):
    require(type(value) is bool, 'Typed geometry decisions required')
    return value


def editable(scope, actor, time):
    entry = scope['actors'][actor]
    if entry is None: return False
    start, end = entry['window_s']
    return start < time < end and not any(a <= time <= b for a, b in entry['protected_s'])


def summarize(report, scope, geometry_sha256):
    require(isinstance(geometry_sha256, str) and re.fullmatch(r'[a-f0-9]{64}', geometry_sha256), 'Exact geometry SHA256 required')
    fields(scope, ('schema', 'geometry_sha256', 'actors', 'object_motion_editable', 'planes_editable'), 'geometry edit scope')
    require(scope['schema'] == SCOPE_SCHEMA and scope['geometry_sha256'] == geometry_sha256
            and scope['object_motion_editable'] is False and scope['planes_editable'] is False,
            'Exact report binding and fixed object/plane intent required')
    require(report['schema'] == 'strep-native-scene-geometry-result-v1' and report['status'] == 'complete',
            'Completed saved geometry diagnostics required')
    times = report['times_s']; samples = report['samples']
    require(isinstance(times, list) and len(times) >= 2 and len(times) == len(samples)
            and number(times[0]) == 0 and all(number(a) < number(b) for a, b in zip(times, times[1:])),
            'Complete sorted unique geometry sample population required')
    actors = set(report['topology'])
    require(isinstance(scope['actors'], dict) and set(scope['actors']) == actors and actors,
            'Complete explicit actor edit scope required')
    for entry in scope['actors'].values():
        if entry is None: continue
        fields(entry, ('window_s', 'protected_s'), 'actor edit window')
        require(isinstance(entry['protected_s'], list), 'Explicit protected ranges required')
        ranges = [entry['window_s']] + entry['protected_s']
        require(all(isinstance(r, list) and len(r) == 2
                and 0 <= number(r[0]) < number(r[1]) <= times[-1] for r in ranges), 'Valid complete edit/protection intervals required')
    limit = number(report['limits']['penetration_m'])
    require(limit >= 0, 'Nonnegative original penetration limit required')
    totals, reasons, crossings = Counter(), Counter(), Counter()
    failures = []; peaks = {}; failed_samples = 0
    for index, (time, sample) in enumerate(zip(times, samples)):
        require(number(sample['time_s']) == time and set(sample['degenerate_faces']) == actors,
                'Geometry sample alignment or actor population changed')
        all_conditions = []
        for group in ('actor_objects', 'actor_pairs', 'world_planes'):
            for condition in sample[group]:
                passed = boolean(condition['passed']); totals[group + '_samples'] += 1
                participants = condition['actors'] if group == 'actor_pairs' else [condition['actor']]
                require(participants and len(set(participants)) == len(participants) and set(participants) <= actors,
                        'Existing distinct geometry participants required')
                why = []
                if group == 'actor_pairs':
                    kinds = Counter(r['kind'] for r in condition['surface']['records'])
                    require(not set(kinds) - {'proper_crossing', 'boundary_or_near_contact', 'coplanar_or_near_parallel_overlap', 'degenerate'},
                            'Known surface diagnostic kinds required')
                    crossings.update(kinds)
                    if kinds['proper_crossing']: why.append('transverse-surface-crossings')
                    if kinds['boundary_or_near_contact']: why.append('unresolved-boundary-or-near-contact')
                    if kinds['coplanar_or_near_parallel_overlap']: why.append('unresolved-coplanar-or-near-parallel')
                    if kinds['degenerate']: why.append('degenerate-surface')
                    for depth in condition['vertex_containment']:
                        if not boolean(depth['available']): why.append('vertex-containment-unavailable'); continue
                        value = number(depth['max_depth_m'])
                        key = depth['source'] + '->' + depth['target']
                        if value > peaks.get(key, {'depth_m': -1})['depth_m']:
                            peaks[key] = dict(depth_m=value, time_s=time, vertex=depth['deepest_vertex'])
                        if value > limit: why.append('vertex-depth-exceeds-limit')
                elif group == 'actor_objects':
                    if number(condition['maximum_depth_lower_m']) > limit: why.append('object-depth-lower-exceeds-limit')
                    elif number(condition['maximum_depth_upper_m']) > limit: why.append('object-depth-bracket-exceeds-limit')
                    if condition['containment']['status'] != 'outside': why.append('object-containment-' + condition['containment']['status'])
                elif number(condition['maximum_depth_m']) > limit: why.append('plane-depth-exceeds-limit')
                all_conditions.append(passed)
                if not passed:
                    totals[group + '_failed'] += 1
                    why = sorted(set(why or ['unresolved-or-degenerate-condition']))
                    frozen = all(not editable(scope, a, time) for a in participants)
                    totals['immutable_failed_conditions' if frozen else 'potentially_editable_failed_conditions'] += 1
                    reasons.update(why)
                    failures.append(dict(sample_index=index, time_s=time, group=group, actors=participants,
                                         immutable_under_declared_windows=frozen, reasons=why))
        available = boolean(sample['conditions_available'])
        require(available == bool(all_conditions), 'Declared geometry condition population changed')
        expected = bool(available and all(all_conditions) and not any(sample['degenerate_faces'].values()))
        require(boolean(sample['passed']) == expected, 'Saved geometry sample decision inconsistent')
        if not expected: failed_samples += 1
    require(boolean(report['sampled_conditions_pass']) == (failed_samples == 0), 'Whole-report geometry decision inconsistent')
    return dict(schema=SCHEMA, geometry_sha256=geometry_sha256, samples=len(samples), failed_samples=failed_samples,
                original_penetration_limit_m=limit, counts=dict(totals), reason_counts=dict(reasons),
                surface_record_counts=dict(crossings), vertex_depth_peaks=peaks, failures=failures,
                source_window_blockers_present=bool(totals['immutable_failed_conditions']),
                original_geometry_decision=report['sampled_conditions_pass'], original_acceptance_unchanged=True,
                input_collision_audit_recomputed=False, editable_failures_proven_feasible=False,
                quality_approved=False, release_approved=False,
                scope='Complete saved diagnostic population classified under explicit actor windows/protected spans and fixed objects/planes. '
                      'No anatomy inference, collision recomputation, source-pose equality proof, continuous-time or quality approval. '
                      'Immutable failures cannot be corrected by changing only declared editable actor samples.')


def run(geometry, scope, output):
    geometry, scope, output = [Path(p).resolve() for p in (geometry, scope, output)]
    require(not output.exists(), 'Fresh geometry profile output required')
    bindings = {str(p): sha256(p) for p in (geometry, scope)}
    result = summarize(read(geometry), read(scope), bindings[str(geometry)])
    require(all(sha256(p) == h for p, h in bindings.items()), 'Geometry profile inputs changed')
    result['inputs_sha256'] = bindings
    result['implementation_sha256'] = sha256(Path(__file__))
    save(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('geometry', type=Path); parser.add_argument('scope', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); print(run(args.geometry, args.scope, args.output))
