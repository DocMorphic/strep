"""Read-only audit of completed rows in a frozen component experiment."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(study, output):
    study, output = study.resolve(), output.resolve()
    if output.exists():
        raise ValueError('Use a new audit directory')
    request = read(study / 'request.json')
    summary_path = study / 'summary.json'
    # Retain the exact bytes read even if the live worker appends another state.
    summary_bytes = summary_path.read_bytes()
    summary = json.loads(summary_bytes)
    source_root = Path(__file__).resolve().parent
    for name, expected in request['implementation'].items():
        if digest(study / 'implementation' / name) != expected or digest(source_root / name) != expected:
            raise ValueError('Changed experiment implementation: ' + name)
    for name, expected in request['inputs'].items():
        if digest(Path(name)) != expected:
            raise ValueError('Changed experiment input: ' + name)
    expected_ids = [s['id'] for s in request['states']]
    actual_ids = [s['id'] for s in summary['rows']]
    if actual_ids != expected_ids[:len(actual_ids)] or len(actual_ids) > len(expected_ids):
        raise ValueError('Completed states do not match the frozen ordered population')
    raw = {r['frame']: r for r in read(Path(request['audit']) / 'geometry/raw/samples.json')['rows']}
    final = {r['frame']: r for r in read(Path(request['audit']) / 'geometry/candidate/samples.json')['rows']}
    rows = []
    for state, recorded in zip(request['states'], summary['rows']):
        path = study / (state['id'] + '.json')
        if digest(path) != recorded['samples_sha256']:
            raise ValueError('Changed completed state: ' + state['id'])
        samples = read(path)['rows']
        if [r['frame'] for r in samples] != request['frames']:
            raise ValueError('Incomplete or reordered sample clock')
        for sample in samples:
            if len(sample['collision']) != 2:
                raise ValueError('Expected two collision directions')
        depths = [max(c['max_depth_m'] for c in s['collision']) for s in samples]
        regressions = [s['frame'] for s, depth in zip(samples, depths)
                       if depth > max(.005, max(c['max_depth_m'] for c in raw[s['frame']]['collision'])) + 2e-6]
        events = [s for s in samples if 'region' in s]
        if len(events) != 1:
            raise ValueError('Expected one measured contact event')
        event = events[0]['region']
        counts = [d['within_tolerance_count'] for d in event['directions']]
        for direction in event['directions']:
            if direction['within_tolerance_count'] != len(direction['within_tolerance_vertices']):
                raise ValueError('Event-region membership count differs')
        recomputed = dict(max_depth_m=max(depths), samples_over_5mm=sum(d > .005 for d in depths),
                          raw_cap_regressions=regressions, event_region_counts=counts,
                          event_opposing_normal_degrees=event['opposing_normal_degrees'])
        for key, value in recomputed.items():
            if recorded[key] != value:
                raise ValueError('Recorded metric differs: ' + key)
        reference = raw if state['id'] == 'raw' else final if state['id'] == 'combined_100' else None
        error = None if reference is None else max(abs(d - max(c['max_depth_m'] for c in reference[s['frame']]['collision']))
                                                    for d, s in zip(depths, samples))
        if error is not None and (error > request['endpoint_depth_tolerance_m'] or error != recorded['endpoint_max_error_m']):
            raise ValueError('Endpoint consistency failed')
        rows.append(dict(**state, **recomputed, endpoint_max_error_m=error,
                         samples_sha256=recorded['samples_sha256']))
    complete = False
    if (study / 'completion.json').exists():
        completion = read(study / 'completion.json')
        if completion['summary_sha256'] != hashlib.sha256(summary_bytes).hexdigest():
            raise ValueError('Completion raced the snapshot; rerun with a new output')
        if completion['states'] != len(expected_ids) or len(rows) != len(expected_ids):
            raise ValueError('Incomplete completion population')
        if completion['samples_per_state'] != len(request['frames']):
            raise ValueError('Completion clock differs')
        if completion['preflight_sha256'] != digest(study / 'preflight.json'):
            raise ValueError('Preflight differs')
        complete = True
    result = dict(at=datetime.now(timezone.utc).isoformat(), study=str(study),
                  request_sha256=digest(study / 'request.json'),
                  source_summary_sha256=hashlib.sha256(summary_bytes).hexdigest(),
                  implementation_sha256=digest(Path(__file__)),
                  complete=complete, completed_states=len(rows), expected_states=len(expected_ids),
                  unfinished_states=expected_ids[len(rows):], frames_per_state=len(request['frames']),
                  rows=rows, quality_approved=False,
                  scope='Read-only recomputation of fixed diagnostic samples; no new geometry, selection, export or full-clock approval.')
    lines = ['# Contact component audit', '',
             f'{len(rows)}/{len(expected_ids)} states recorded. Experiment complete: {complete}. No quality approval.', '',
             '| State | Peak depth (mm) | Samples >5 mm | Raw-cap regressions | Event-region vertices A/B |',
             '|---|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['id']} | {r['max_depth_m']*1000:.6f} | {r['samples_over_5mm']}/{len(request['frames'])} | "
                     f"{len(r['raw_cap_regressions'])} | {'/'.join(map(str,r['event_region_counts']))} |")
    lines += ['', 'Only the frozen development clock is measured. Event proximity is not anatomical contact or motion-quality approval.',
              'Unfinished states: ' + (', '.join(result['unfinished_states']) or 'none') + '.', '']
    output.mkdir(parents=True)
    (output / 'source-summary.json').write_bytes(summary_bytes)
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    (output / 'comparison.md').write_text('\n'.join(lines), encoding='utf8')
    print(json.dumps({k: result[k] for k in ['complete', 'completed_states', 'expected_states', 'unfinished_states']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('study', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    summarize(args.study, args.output)
