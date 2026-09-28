"""Locate every release regression in a completed guarded direction probe.

This only measures retained clips. Release windows and tolerances are inherited
unchanged from the original comparison; it never selects or edits a motion.
"""
import argparse
from pathlib import Path
import numpy as np
from strep import read, save, sha256, now
from support_release_metrics import measure
from study_whole_support_breadth import check_engine


def run(study, audit, engine, output):
    if output.exists():
        raise ValueError('Preserve prior audit')
    request = read(study / 'request.json')
    done = read(study / 'completion.json')
    independent = read(audit)
    if independent['completion_sha256'] != sha256(study / 'completion.json'):
        raise ValueError('Independent audit binding differs')
    if done['results_sha256'] != sha256(study / 'results.json'):
        raise ValueError('Completed results changed')
    manifest = read(engine / 'manifest.json')
    if manifest['completion_sha256'] != sha256(study / 'completion.json') or manifest['independent_audit_sha256'] != sha256(audit):
        raise ValueError('Engine selection binding differs')
    engine_frames = check_engine(read(engine / 'audit/verification.json'), manifest['cases'])
    for item in manifest['cases']:
        if sha256(item['path']) != item['sha256']:
            raise ValueError('Engine clip changed')
    for path, digest in request['inputs'].items():
        if sha256(path) != digest:
            raise ValueError('Original evidence changed: ' + path)
    held = Path(request['held'])
    baseline = read(held / 'release-dynamics.json')
    spec = read(held / 'spec.json')
    support = read(held / 'request.json')['support']
    results = read(study / 'results.json')['rows']
    rows = []
    for index, result in enumerate(results):
        if not result['guarded_improvement'] and result['alpha'] != 0:
            continue
        clip = study / f'step-{index:02d}/candidate/character.glb'
        recorded = {Path(name).as_posix(): digest for name, digest in result['files'].items()}
        if sha256(clip) != recorded['candidate/character.glb']:
            raise ValueError('Retained probe clip changed')
        decoded = measure(clip, spec, support)
        events = []
        for side in spec['patches']:
            tracks = [baseline[v]['feet'][side] for v in ['input', 'prior', 'candidate']]
            tracks.append(decoded['feet'][side])
            if len({len(track['releases']) for track in tracks}) != 1:
                raise ValueError('Release population changed')
            for releases in zip(*(t['releases'] for t in tracks)):
                if len({r['release_frame'] for r in releases}) != 1:
                    raise ValueError('Release clock changed')
                raw, prior, held_event, candidate = releases
                limit = max(raw['acceleration_max_m_s2'], prior['acceleration_max_m_s2']) + 1e-5
                frames = np.asarray(candidate['acceleration_frames'], dtype=int)
                acceleration = np.asarray(tracks[-1]['acceleration_m_s2'])[frames - 1]
                peak = int(frames[np.argmax(np.linalg.norm(acceleration, axis=1))])
                events.append(dict(side=side, release_frame=candidate['release_frame'], peak_center_frame=peak,
                    acceleration_frames=frames.tolist(), limit_m_s2=limit,
                    raw_m_s2=raw['acceleration_max_m_s2'], prior_m_s2=prior['acceleration_max_m_s2'],
                    held_m_s2=held_event['acceleration_max_m_s2'], candidate_m_s2=candidate['acceleration_max_m_s2'],
                    excess_m_s2=max(0., candidate['acceleration_max_m_s2'] - limit),
                    held_passed=held_event['acceleration_max_m_s2'] <= limit,
                    candidate_passed=candidate['acceleration_max_m_s2'] <= limit))
            counted = sum(not e['candidate_passed'] for e in events if e['side'] == side)
            if counted != result['full_decision']['feet'][side]['release_acceleration_regressions']:
                raise ValueError('Independent release count differs')
        rows.append(dict(alpha=result['alpha'], source_sha256=sha256(clip), events=events,
            regressions=sum(not e['candidate_passed'] for e in events),
            newly_failing_from_held=sum(e['held_passed'] and not e['candidate_passed'] for e in events),
            resolved_from_held=sum(not e['held_passed'] and e['candidate_passed'] for e in events)))
    save(output, dict(at=now(), completion_sha256=sha256(study / 'completion.json'),
        independent_audit_sha256=sha256(audit), engine_manifest_sha256=sha256(engine / 'manifest.json'),
        engine_proof_sha256=sha256(engine / 'audit/verification.json'), engine_actor_frames=engine_frames,
        implementation_sha256=sha256(__file__), rows=rows, quality_approved=False,
        scope='Fresh decoded release windows for held and all guarded fractions, plus engine binding. Aggregate energy improvement may introduce new individual release failures; no new optimization or acceptance thresholds.'))
    for row in rows:
        print({key: value for key, value in row.items() if key not in ['events', 'source_sha256']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['study', 'audit', 'engine', 'output']:
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    run(args.study, args.audit, args.engine, args.output)
