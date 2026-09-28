"""Check independent correction runs and original generation-time source hashes."""
import argparse
from pathlib import Path

import numpy as np

from strep import read, save, sha256, now


def main(reference, reproduction):
    reference, reproduction = Path(reference).resolve(), Path(reproduction).resolve()
    first, second = read(reference / 'summary.json'), read(reproduction / 'summary.json')
    for key in ('source_commit', 'config_sha256', 'implementation_sha256', 'acceptance_rubric_sha256'):
        if first[key] != second[key]:
            raise RuntimeError(f'Provenance differs: {key}')
    by_seed = {trial['seed']: trial for trial in second['trials']}
    if sorted(by_seed) != sorted(trial['seed'] for trial in first['trials']):
        raise RuntimeError('Seed sets differ')
    results = []
    for trial in first['trials']:
        seed = trial['seed']
        folder = f'seed-{seed}'
        other = by_seed[seed]
        for key in ('source_start_frame', 'cycle_frames', 'blend_frames', 'root_mode',
                    'loop_screen_repeated', 'regressions', 'numerically_accepted'):
            if trial[key] != other[key]:
                raise RuntimeError(f'Seed {seed}: {key} differs')
        if read(reference / folder / 'candidates.json') != read(reproduction / folder / 'candidates.json'):
            raise RuntimeError(f'Seed {seed}: candidate metrics differ')
        with np.load(reference / folder / 'corrected.npz', allow_pickle=False) as a, np.load(reproduction / folder / 'corrected.npz', allow_pickle=False) as b:
            if set(a.files) != set(b.files) or not all(np.array_equal(a[key], b[key]) for key in a.files):
                raise RuntimeError(f'Seed {seed}: arrays differ')
        source = Path(trial['source'])
        original = read(source.parent.parent / 'record.json')['source_motion_file_and_hash']['sha256']
        if sha256(source).lower() != original.lower() or trial['source_sha256'].lower() != original.lower():
            raise RuntimeError(f'Seed {seed}: original source hash differs')
        results.append({'seed': seed, 'arrays_exactly_equal': True, 'all_candidate_metrics_equal': True,
                        'selection_equal': True, 'original_generation_hash_preserved': True})
    report = {'checked_at': now(), 'reference': str(reference), 'reproduction': str(reproduction),
              'status': 'passed', 'scope': 'Same machine and installed versions; no cross-platform claim.',
              'trials': results}
    save(reference / 'reproducibility.json', report)
    print(f'PASS: all {len(results)} seeds exactly reproduced; original sources unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('reproduction', type=Path)
    args = parser.parse_args()
    main(args.reference, args.reproduction)
