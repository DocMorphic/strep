"""Reduce complete saved breadth metadata; never run poses or approve motion."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

MAX_BYTES = 16 * 1024**2
MAX_CASES = 1024
MAX_ROWS = 32768
SCREENS = {
    'mesh_floor': ('mesh_floor_depth_m', 'mesh_floor_screen'),
    'joint_floor': ('joint_floor_depth_m', 'joint_floor_screen'),
    'predicted_support_speed': ('predicted_foot_speed_p95_m_s', 'predicted_foot_speed_screen'),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def label(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 256


def reduce(protocol, coverage, execution):
    """Every case/actor/seed remains present, including N/A and missing exports."""
    require(all(isinstance(v, dict) for v in (protocol, coverage, execution)), 'Explicit saved JSON objects required')
    require(protocol.get('schema') == 1 and type(protocol['schema']) is int, 'Saved breadth protocol schema required')
    require(isinstance(protocol.get('screens'), dict), 'Explicit saved diagnostic threshold object required')
    cases = protocol.get('cases')
    require(isinstance(cases, list) and 1 <= len(cases) <= MAX_CASES, 'Complete bounded case population required')
    require(type(protocol.get('expected_cases')) is int and protocol['expected_cases'] == len(cases), 'Declared case count differs')
    require(coverage.get('quality_approved') is False, 'Raw metadata cannot grant quality approval')
    thresholds = {
        'mesh_floor': execution.get('surface_threshold_m'),
        'joint_floor': protocol['screens'].get('joint_floor_depth_m'),
        'predicted_support_speed': protocol['screens'].get('predicted_foot_speed_p95_m_s'),
    }
    require(all(number(v) and v > 0 for v in thresholds.values()), 'Explicit unchanged diagnostic thresholds required')
    expected, lookup = {}, {}
    for case in cases:
        require(isinstance(case, dict), 'Explicit protocol case object required')
        require(label(case.get('id')) and label(case.get('family')) and case['id'] not in lookup, 'Unique explicit cases and families required')
        require(label(case.get('context')) and label(case.get('scene_validation')), 'Explicit source context and validation state required')
        require(type(case.get('flat_floor_screen_applicable')) is bool, 'Explicit floor applicability required')
        require(not case['flat_floor_screen_applicable'] or case['context'] == 'floor', 'Floor diagnostic requires declared floor context')
        actors, seeds = case.get('actors'), case.get('seeds')
        require(isinstance(actors, list) and actors and all(isinstance(a, dict) and label(a.get('id')) for a in actors), 'Complete explicit actor population required')
        require(len({a['id'] for a in actors}) == len(actors), 'Duplicate actors in protocol')
        require(isinstance(seeds, list) and seeds and all(type(s) is int and 0 <= s < 2**63 for s in seeds)
                and len(set(seeds)) == len(seeds), 'Distinct explicit seeds required')
        lookup[case['id']] = case
        for actor in actors:
            for seed in seeds:
                expected[case['id'], actor['id'], seed] = case
                require(len(expected) <= MAX_ROWS, 'Complete population exceeds row budget; no subset returned')
    require(type(protocol.get('expected_actor_clips')) is int and protocol['expected_actor_clips'] == len(expected), 'Declared complete actor/seed count differs')
    require(type(coverage.get('planned_cases')) is int and type(coverage.get('planned_actor_clips')) is int
            and coverage['planned_cases'] == len(cases) and coverage['planned_actor_clips'] == len(expected), 'Coverage denominator differs')
    rows = coverage.get('rows')
    require(isinstance(rows, list) and len(rows) == len(expected), 'Every expected saved row required')
    keyed = {}
    for row in rows:
        require(isinstance(row, dict) and label(row.get('case')) and label(row.get('actor')) and type(row.get('seed')) is int,
                'Explicit saved case/actor/seed identity required')
        require({'semantic_rating', *(key for pair in SCREENS.values() for key in pair)} <= row.keys(),
                'Explicit saved diagnostic fields required, including null values')
        key = row['case'], row['actor'], row['seed']
        require(key in expected and key not in keyed, 'Unknown or duplicate saved population row')
        case = expected[key]
        for field in ('family', 'context', 'flat_floor_screen_applicable', 'scene_validation'):
            require(row.get(field) == case[field] and type(row.get(field)) is type(case[field]), 'Saved context or family differs: '+field)
        require(type(row.get('exported')) is bool, 'Explicit export availability required')
        require(row.get('quality_approved') is False and row.get('independent_human_review') is False
                and row.get('semantic_rating') is None, 'Unreviewed diagnostic rows required; human evidence needs its own importer')
        for name, (metric, flag) in SCREENS.items():
            value, passed = row.get(metric), row.get(flag)
            require(value is None or number(value), 'Finite nonnegative saved metric required: '+metric)
            if not case['flat_floor_screen_applicable']:
                require(passed is None, 'Inapplicable scene-dependent screen must remain N/A')
            else:
                require(passed is None if value is None else type(passed) is bool and passed == (value <= thresholds[name]),
                        'Saved metric/screen disagreement: '+name)
        keyed[key] = row
    require(set(keyed) == set(expected), 'Missing saved population identity')
    require(type(coverage.get('exported')) is int and coverage['exported'] == sum(r['exported'] for r in rows), 'Export availability total differs')

    def group(records):
        value = dict(actor_clips=len(records), exported=sum(r['exported'] for r in records),
                     missing_exports=sum(not r['exported'] for r in records),
                     floor_applicable=sum(r['flat_floor_screen_applicable'] for r in records),
                     context_validation_not_established=sum(not r['flat_floor_screen_applicable'] for r in records),
                     semantic_reviews_verified=0, supported_actions_established=0, screens={})
        for name, (_, flag) in SCREENS.items():
            eligible = [r for r in records if r['flat_floor_screen_applicable']]
            value['screens'][name] = dict(passed=sum(r[flag] is True for r in eligible),
                failed=sum(r[flag] is False for r in eligible), missing=sum(r[flag] is None for r in eligible),
                not_applicable=len(records)-len(eligible))
        return value

    per_case = []
    for case in cases:
        records = [keyed[case['id'], a['id'], s] for a in case['actors'] for s in case['seeds']]
        counts = group(records)
        per_case.append(dict(id=case['id'], family=case['family'], context=case['context'],
            actors=[a['id'] for a in case['actors']], seeds=list(case['seeds']), **counts,
            every_eligible_actor_seed_fails_mesh_floor=bool(counts['floor_applicable'] > 0
                and counts['screens']['mesh_floor']['failed'] == counts['floor_applicable'])))
    families = list(dict.fromkeys(case['family'] for case in cases))
    return dict(schema='strep-saved-breadth-failure-profile-v1', status='complete', totals=group(rows), cases=per_case,
        families=[dict(family=name, **group([r for r in rows if r['family'] == name])) for name in families],
        diagnostic_thresholds=thresholds, complete_saved_population=True, missing_rows_dropped=False,
        context_na_counted_as_pass=False, source_qualification=coverage.get('qualification'),
        source_held_out_claim=protocol.get('held_out_claim'), held_out_release_evidence=False,
        export_artifact_hashes_revalidated=False, new_motion_sampled=False, geometry_queries_rerun=False,
        engine_executed=False, human_reviewed=False, quality_approved=False, training_admitted=False, release_approved=False,
        scope='Complete caller-pinned unreviewed development metadata only. Stored diagnostics are not newly measured '
              'motion, artifact verification, scene/partner validity, semantic correctness or release acceptance.')


def run(protocol, coverage, execution, output, *, protocol_sha256, coverage_sha256, execution_sha256):
    inputs = [Path(p).resolve() for p in (protocol, coverage, execution)]
    output = Path(output).resolve()
    require(not output.exists() and not any(p.is_relative_to(output) for p in inputs), 'Fresh output outside every source input required')
    hashes = [protocol_sha256, coverage_sha256, execution_sha256]
    implementation = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    snapshots = []
    for path, expected in zip(inputs, hashes):
        require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected), 'Explicit input SHA256 required')
        require(path.is_file() and 0 < path.stat().st_size <= MAX_BYTES, 'Complete bounded local JSON input required')
        data = path.read_bytes()
        require(len(data) <= MAX_BYTES and hashlib.sha256(data).hexdigest() == expected, 'Changed saved JSON input')
        snapshots.append(data)
    value = reduce(*(json.loads(b) for b in snapshots))
    require(all(path.read_bytes() == data for path, data in zip(inputs, snapshots)), 'Saved metadata changed during reduction')
    value['inputs_sha256'] = {str(p): h for p, h in zip(inputs, hashes)}
    value['implementation_sha256'] = implementation
    output.mkdir(parents=True)
    for name, data in zip(('protocol.json', 'coverage.json', 'execution.json'), snapshots):
        (output/name).write_bytes(data)
    require(all(path.read_bytes() == data for path, data in zip(inputs, snapshots))
            and hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == implementation,
            'Saved metadata or implementation changed before completion; partial output preserved')
    (output/'result.json').write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'coverage', 'execution', 'output'):
        parser.add_argument(name, type=Path)
    for name in ('protocol', 'coverage', 'execution'):
        parser.add_argument('--'+name+'-sha256', required=True)
    args = parser.parse_args()
    result = run(args.protocol, args.coverage, args.execution, args.output,
        protocol_sha256=args.protocol_sha256, coverage_sha256=args.coverage_sha256, execution_sha256=args.execution_sha256)
    print(json.dumps(result['totals']))
