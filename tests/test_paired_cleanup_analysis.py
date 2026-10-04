"""Synthetic ratings/times only; never release or human evidence."""
import copy
import json
from pathlib import Path
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import paired_cleanup_analysis as analysis
import developer_packet_review as developer
import review_session as independent
from strep import read, save, sha256


def cleanup(status='completed', seconds=100):
    return dict(status=status, active_seconds=None if status == 'not_performed' else seconds,
                operations='' if status == 'not_performed' else 'Synthetic edit fixture',
                time_limit_seconds=60 if status == 'time_limit' else None)


@pytest.mark.parametrize('b,c,absolute,relative', [
    (cleanup(seconds=100), cleanup(seconds=60), (40, 40), (.4, .4)),
    (cleanup(seconds=100), cleanup('time_limit', 74), (None, 26), (None, .26)),
    (cleanup('time_limit', 100), cleanup(seconds=60), (40, None), (.4, 1)),
    (cleanup('time_limit', 100), cleanup('time_limit', 74), (None, None), (None, 1)),
    (cleanup('time_limit', 100), cleanup(seconds=0), (100, None), (1, 1)),
    (cleanup(seconds=0), cleanup(seconds=60), (-60, -60), None),
    (cleanup(seconds=0), cleanup(seconds=0), (0, 0), None),
    (cleanup(seconds=100), cleanup('abandoned', 20), None, None),
    (cleanup('not_performed'), cleanup(seconds=60), None, None),
    (None, cleanup(seconds=60), None, None),
])
def test_completion_bounds_preserve_censoring_and_missingness(b, c, absolute, relative):
    result = analysis.compare(b, c)
    for name, expected in [('completion_difference_seconds', absolute), ('reduction_fraction', relative)]:
        value = result[name]
        if expected is None:
            assert value is None
        else:
            for side, target in zip(('lower', 'upper'), expected):
                assert value[side] is None if target is None else value[side] == pytest.approx(target)
                assert value[side + '_unbounded'] == (target is None)
    json.dumps(result, allow_nan=False)


def test_finite_extreme_times_cannot_produce_false_infinite_point_estimate():
    with pytest.raises(ValueError, match='overflow'):
        analysis.compare(cleanup(seconds=1e-300), cleanup(seconds=1e300))
    assert analysis._median([-1e308, -1e308]) == -1e308


def test_median_bounds_are_conditional_and_do_not_fill_abandonment_with_zero():
    rows = [dict(comparison=analysis.compare(cleanup(), c)) for c in
            [cleanup(seconds=50), cleanup('time_limit', 74), cleanup('abandoned', 0), cleanup('not_performed'), None]]
    result = analysis.summarize(rows)
    assert result['expected_reviewer_pairs'] == 5 and result['completed_pairs'] == 1
    assert result['completed_pair_only_median_reduction_fraction'] == .5
    assert result['relative_unavailable_pairs'] == 3
    assert result['conditional_median_reduction_bounds']['lower'] is None
    assert result['conditional_median_reduction_bounds']['upper'] == pytest.approx(.38)
    assert result['status_counts']['candidate'] == dict(completed=1, time_limit=1, abandoned=1, not_performed=1, missing=1)


def study(tmp_path, roles=('developer',), no_imports=False):
    root = tmp_path / 'inputs'
    root.mkdir()
    config = dict(schema='strep-paired-cleanup-analysis-v1', design={}, packets=[], imports=[])
    design = dict(schema='strep-paired-cleanup-design-v1', pairs=[])
    for role in roles:
        for side in ('baseline', 'candidate'):
            packet_id = role + '-' + side
            packet = root / packet_id
            cases = []
            for n in (1, 2):
                path = packet / f'clips/clip-{n:03d}.glb'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'SYNTHETIC NOT A MOTION ' + str(n).encode())
                cases.append(dict(id=f'clip-{n:03d}', path=f'clips/clip-{n:03d}.glb', sha256=sha256(path)))
            manifest = dict(schema='strep-review-packet-v1', packet_id=packet_id, review_type=role, cases=cases)
            save(packet / 'manifest.json', manifest)
            digest = sha256(packet / 'manifest.json')
            config['packets'].append(dict(path=packet_id, manifest_sha256=digest))
            if no_imports:
                continue
            for reviewer in ('synthetic-one', 'synthetic-two'):
                data = dict(schema='strep-human-review-v1', packet_id=packet_id,
                            manifest_sha256=digest, reviewer_id=reviewer, independent_human=True, reviews=[])
                if role == 'developer':
                    data.update(schema='strep-developer-packet-review-v1', human_review=True, independent_human=False,
                                review_type='developer', quality_approved=False, release_approved=False)
                for n in (1, 2):
                    if side == 'candidate' and reviewer == 'synthetic-two' and n == 2:
                        continue
                    c = cleanup(seconds=100 if side == 'baseline' else 50)
                    if side == 'candidate' and n == 2:
                        c = cleanup('time_limit', 74)
                    data['reviews'].append(dict(clip_id=f'clip-{n:03d}', scores={k: 4 for k in independent.CATEGORIES},
                                                not_applicable={}, major_defect=False, confidence='medium',
                                                notes='Synthetic fixture, not a human rating', cleanup=c))
                response = root / (packet_id + '-' + reviewer + '.json')
                save(response, data)
                imported = root / (packet_id + '-' + reviewer + '-import')
                (developer.import_reviews if role == 'developer' else independent.import_reviews)(packet, response, imported)
                config['imports'].append(dict(path=imported.name, response_sha256=sha256(imported / 'response.json')))
        for n in (1, 2):
            design['pairs'].append(dict(id=role + f'-pair-{n}', family='arbitrary-new-family-' + str(n),
                                        baseline=dict(packet_id=role + '-baseline', clip_id=f'clip-{n:03d}'),
                                        candidate=dict(packet_id=role + '-candidate', clip_id=f'clip-{n:03d}')))
    save(root / 'design.json', design)
    config['design'] = dict(path='design.json', sha256=sha256(root / 'design.json'))
    save(root / 'config.json', config)
    return root, root / 'config.json'


def test_bound_imports_pair_packet_and_clip_with_separate_roles_and_preserved_sources(tmp_path):
    root, config_path = study(tmp_path, ('developer', 'independent'))
    before = {p: sha256(p) for p in root.rglob('*') if p.is_file()}
    result = analysis.analyze(config_path, tmp_path / 'result')
    assert result['design_pairs'] == 4 and result['imports_revalidated'] == 8
    assert len(result['comparisons']) == 8
    assert not result['quality_approved'] and not result['release_approved']
    for role in ('developer', 'independent'):
        s = result['strata'][role]
        assert s['reviewers_observed'] == 2 and s['expected_reviewer_pairs'] == 4
        assert s['completed_positive_baseline_pairs'] == 2
        assert s['completed_pair_only_median_reduction_fraction'] == .5
        assert s['status_counts']['candidate']['time_limit'] == 1
        assert s['status_counts']['candidate']['missing'] == 1
        assert s['families']['arbitrary-new-family-2']['completed_pairs'] == 0
    assert {p: sha256(p) for p in before} == before
    assert read(tmp_path / 'result/result.json') == result
    with pytest.raises(ValueError, match='Preserve'):
        analysis.analyze(config_path, tmp_path / 'result')


def test_no_imports_produces_no_invented_ratings_or_zero_median(tmp_path):
    _, config_path = study(tmp_path, no_imports=True)
    result = analysis.analyze(config_path, tmp_path / 'result')
    assert result['comparisons'] == [] and result['imports_revalidated'] == 0
    assert result['strata']['developer']['design_pairs'] == 2
    assert result['strata']['developer']['reviewers_observed'] == 0
    assert result['strata']['developer']['completed_pair_only_median_reduction_fraction'] is None


@pytest.mark.parametrize('failure', ['changed_clip', 'changed_response', 'changed_manifest', 'changed_design',
                                    'changed_validation', 'duplicate_import', 'same_clip', 'reused_clip',
                                    'unknown_clip', 'duplicate_pair', 'mixed_roles', 'approval', 'forged_completed',
                                    'escaping_clip', 'duplicate_json', 'nan_json', 'extra_config', 'input_output'])
def test_invalid_bindings_designs_and_responses_fail_before_output(tmp_path, failure):
    root, config_path = study(tmp_path, ('developer', 'independent'))
    config = read(config_path)
    design_path = root / 'design.json'
    design = read(design_path)
    packet = root / 'developer-baseline'
    imported = root / config['imports'][0]['path']
    output = tmp_path / 'bad-result'
    if failure == 'changed_clip':
        (packet / 'clips/clip-001.glb').write_bytes(b'changed')
    elif failure == 'changed_response':
        (imported / 'response.json').write_text('{}')
    elif failure == 'changed_manifest':
        (packet / 'manifest.json').write_text('{}')
    elif failure == 'changed_design':
        design_path.write_text('{}')
    elif failure in ('changed_validation', 'approval'):
        validation = read(imported / 'validation.json')
        validation['reviewed' if failure == 'changed_validation' else 'release_approved'] = 100 if failure == 'changed_validation' else True
        save(imported / 'validation.json', validation)
    elif failure == 'duplicate_import':
        config['imports'].append(copy.deepcopy(config['imports'][0]))
    elif failure == 'forged_completed':
        data = read(imported / 'response.json')
        data['reviews'][0]['cleanup'] = cleanup('completed', None)
        save(imported / 'response.json', data)
        config['imports'][0]['response_sha256'] = sha256(imported / 'response.json')
    elif failure == 'escaping_clip':
        manifest = read(packet / 'manifest.json')
        manifest['cases'][0]['path'] = '../outside.glb'
        save(packet / 'manifest.json', manifest)
        config['packets'][0]['manifest_sha256'] = sha256(packet / 'manifest.json')
    elif failure in ('duplicate_json', 'nan_json'):
        config_path.write_text('{"schema":"x","schema":"x"}' if failure == 'duplicate_json' else '{"schema":NaN}')
    elif failure == 'extra_config':
        config['quality_approved'] = True
    elif failure == 'input_output':
        output = root / 'bad-result'
    else:
        if failure == 'same_clip':
            design['pairs'][0]['candidate'] = copy.deepcopy(design['pairs'][0]['baseline'])
        elif failure == 'reused_clip':
            design['pairs'][1]['baseline'] = copy.deepcopy(design['pairs'][0]['baseline'])
        elif failure == 'unknown_clip':
            design['pairs'][0]['candidate']['clip_id'] = 'missing'
        elif failure == 'duplicate_pair':
            design['pairs'][1]['id'] = design['pairs'][0]['id']
        elif failure == 'mixed_roles':
            design['pairs'][0]['candidate']['packet_id'] = 'independent-candidate'
        save(design_path, design)
        config['design']['sha256'] = sha256(design_path)
    if failure not in ('duplicate_json', 'nan_json'):
        save(config_path, config)
    with pytest.raises(ValueError):
        analysis.analyze(config_path, output)
    assert not output.exists()


def test_missing_reviewer_on_one_side_stays_missing_instead_of_cross_person_pair(tmp_path):
    _, config_path = study(tmp_path)
    config = read(config_path)
    # Baseline only for reviewer one; candidate only for reviewer two.
    config['imports'] = [config['imports'][0], config['imports'][3]]
    save(config_path, config)
    result = analysis.analyze(config_path, tmp_path / 'result')
    assert result['strata']['developer']['completed_pairs'] == 0
    assert result['strata']['developer']['expected_reviewer_pairs'] == 4
    assert all(row['baseline']['cleanup'] is None or row['candidate']['cleanup'] is None for row in result['comparisons'])


def test_unpaired_attempts_are_retained_and_cannot_enter_completed_pair_median(tmp_path):
    root, config_path = study(tmp_path)
    config = read(config_path)
    design = read(root / 'design.json')
    design['pairs'] = design['pairs'][:1]
    save(root / 'design.json', design)
    config['design']['sha256'] = sha256(root / 'design.json')
    save(config_path, config)
    result = analysis.analyze(config_path, tmp_path / 'result')
    assert len(result['unpaired_imported_reviews']) == 3
    assert any(r['cleanup']['status'] == 'time_limit' for r in result['unpaired_imported_reviews'])
    assert result['strata']['developer']['expected_reviewer_pairs'] == 2
    assert result['strata']['developer']['completed_pairs'] == 2


def test_mid_analysis_mutation_is_rejected(tmp_path, monkeypatch):
    root, config_path = study(tmp_path)
    original = analysis.summarize
    def mutate(rows):
        (root / 'developer-baseline/clips/clip-001.glb').write_bytes(b'changed during analysis')
        return original(rows)
    monkeypatch.setattr(analysis, 'summarize', mutate)
    with pytest.raises(ValueError, match='during analysis'):
        analysis.analyze(config_path, tmp_path / 'result')
    assert not (tmp_path / 'result').exists()
