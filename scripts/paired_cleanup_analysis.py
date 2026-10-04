"""Compare bound human cleanup attempts without inventing completion times."""
import argparse
import copy
import json
import math
from pathlib import Path

from strep import now, save, sha256
from review_session import validate as independent_validate
from developer_packet_review import validate as developer_validate


def _read(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON field')
            result[key] = value
        return result

    def constant(value):
        raise ValueError('Nonfinite JSON constant: ' + value)

    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      object_pairs_hook=pairs, parse_constant=constant)


def _fields(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError('Invalid ' + label + ' fields')


def _identifier(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError('Nonempty unpadded identifier required')
    return value


def _path(base, value):
    if not isinstance(value, str) or not value:
        raise ValueError('Input path required')
    return (base / value).resolve()


def _bound_file(path, digest, bindings):
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('Lowercase SHA-256 binding required')
    if sha256(path) != digest:
        raise ValueError('Changed bound input: ' + str(path))
    if path in bindings and bindings[path] != digest:
        raise ValueError('Conflicting input binding')
    bindings[path] = digest


def _finite(value):
    if not math.isfinite(value):
        raise ValueError('Cleanup arithmetic overflow')
    return value


def _interval(lower, upper):
    # None explicitly means unbounded, never zero or a missing point estimate.
    return dict(lower=lower, upper=upper, lower_unbounded=lower is None,
                upper_unbounded=upper is None)


def compare(baseline, candidate):
    """Time limits bound eventual completion; abandonment is not censoring."""
    result = dict(baseline_status=baseline['status'] if baseline else 'missing',
                  candidate_status=candidate['status'] if candidate else 'missing',
                  completion_difference_seconds=None, reduction_fraction=None,
                  completed_pair=False, relative_unavailable_reason=None)
    if baseline is None or candidate is None:
        result['relative_unavailable_reason'] = 'missing_review'
        return result
    usable = {'completed', 'time_limit'}
    if baseline['status'] not in usable or candidate['status'] not in usable:
        result['relative_unavailable_reason'] = 'abandoned_or_not_performed'
        return result
    b, c = baseline['active_seconds'], candidate['active_seconds']
    bc, cc = baseline['status'] == 'completed', candidate['status'] == 'completed'
    delta = _finite(b - c)
    result['completed_pair'] = bc and cc
    result['completion_difference_seconds'] = _interval(delta if cc else None, delta if bc else None)
    if b == 0:
        result['relative_unavailable_reason'] = 'zero_baseline_elapsed'
        return result
    reduction = _finite(1 - _finite(c / b))
    if bc and cc:
        result['reduction_fraction'] = _interval(reduction, reduction)
    elif bc:
        result['reduction_fraction'] = _interval(None, reduction)
    elif cc:
        result['reduction_fraction'] = _interval(reduction, 1.0)
    else:
        result['reduction_fraction'] = _interval(None, 1.0)
    return result


def _median(values):
    if not values:
        return None
    values = sorted(values)
    n = len(values)
    if n % 2:
        return values[n // 2]
    return values[n // 2 - 1] / 2 + values[n // 2] / 2


def _median_bound(intervals, side):
    # An even median with either middle endpoint unbounded stays unbounded.
    # Lower unbounded is -infinity; upper unbounded is +infinity.
    values = sorted((i[side] for i in intervals),
                    key=lambda v: (-math.inf if side == 'lower' else math.inf) if v is None else v)
    n = len(values)
    middle = [values[n // 2]] if n % 2 else values[n // 2 - 1:n // 2 + 1]
    return None if any(v is None for v in middle) else _median(middle)


def summarize(rows):
    exact = [r['comparison']['reduction_fraction']['lower'] for r in rows
             if r['comparison']['completed_pair'] and r['comparison']['reduction_fraction'] is not None]
    intervals = [r['comparison']['reduction_fraction'] for r in rows
                 if r['comparison']['reduction_fraction'] is not None]
    statuses = {}
    for side in ('baseline', 'candidate'):
        statuses[side] = {status: sum(r['comparison'][side + '_status'] == status for r in rows)
                          for status in ('completed', 'time_limit', 'abandoned', 'not_performed', 'missing')}
    return dict(expected_reviewer_pairs=len(rows), completed_pairs=sum(r['comparison']['completed_pair'] for r in rows),
                completed_positive_baseline_pairs=len(exact), status_counts=statuses,
                relative_unavailable_pairs=sum(r['comparison']['reduction_fraction'] is None for r in rows),
                completed_pair_only_median_reduction_fraction=_median(exact),
                completed_or_censored_positive_baseline_pairs=len(intervals),
                conditional_median_reduction_bounds=(
                    _interval(_median_bound(intervals, 'lower'), _median_bound(intervals, 'upper')) if intervals else None))


def analyze(config_path, output):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Preserve existing analysis')
    bindings = {config_path: sha256(config_path)}
    config = _read(config_path)
    _fields(config, ('schema', 'design', 'packets', 'imports'), 'analysis configuration')
    if config['schema'] != 'strep-paired-cleanup-analysis-v1':
        raise ValueError('Unknown analysis schema')
    _fields(config['design'], ('path', 'sha256'), 'design binding')
    design_path = _path(config_path.parent, config['design']['path'])
    _bound_file(design_path, config['design']['sha256'], bindings)
    design = _read(design_path)
    _fields(design, ('schema', 'pairs'), 'paired design')
    if design['schema'] != 'strep-paired-cleanup-design-v1' or not isinstance(design['pairs'], list) or not design['pairs']:
        raise ValueError('Nonempty explicit paired design required')
    if not isinstance(config['packets'], list) or not config['packets'] or not isinstance(config['imports'], list):
        raise ValueError('Packet and import inventories required')
    packets, roots = {}, [config_path.parent, design_path.parent]
    for entry in config['packets']:
        _fields(entry, ('path', 'manifest_sha256'), 'packet binding')
        path = _path(config_path.parent, entry['path'])
        roots.append(path)
        _bound_file(path / 'manifest.json', entry['manifest_sha256'], bindings)
        manifest = _read(path / 'manifest.json')
        identifier = _identifier(manifest.get('packet_id'))
        role = manifest.get('review_type', 'independent')
        if manifest.get('schema') != 'strep-review-packet-v1' or role not in ('independent', 'developer') or identifier in packets:
            raise ValueError('Distinct valid review packets required')
        cases = manifest.get('cases')
        if not isinstance(cases, list) or not cases:
            raise ValueError('Packet cases required')
        seen, paths = set(), set()
        for case in cases:
            if not isinstance(case, dict):
                raise ValueError('Invalid packet case')
            clip = _identifier(case.get('id'))
            clip_path = _path(path, case.get('path'))
            if clip in seen or clip_path in paths or not clip_path.is_relative_to(path):
                raise ValueError('Repeated or escaping clip')
            _bound_file(clip_path, case.get('sha256'), bindings)
            seen.add(clip)
            paths.add(clip_path)
        packets[identifier] = dict(manifest=manifest, digest=entry['manifest_sha256'], role=role, clips=seen)
    identifiers, used, pairs = set(), set(), []
    for pair in design['pairs']:
        _fields(pair, ('id', 'family', 'baseline', 'candidate'), 'design pair')
        identifier, family = _identifier(pair['id']), _identifier(pair['family'])
        if identifier in identifiers:
            raise ValueError('Duplicate design pair')
        identifiers.add(identifier)
        refs = []
        for side in ('baseline', 'candidate'):
            ref = pair[side]
            _fields(ref, ('packet_id', 'clip_id'), 'clip reference')
            packet, clip = _identifier(ref['packet_id']), _identifier(ref['clip_id'])
            if packet not in packets or clip not in packets[packet]['clips']:
                raise ValueError('Unknown paired clip')
            refs.append((packet, clip))
        if refs[0] == refs[1] or any(ref in used for ref in refs):
            raise ValueError('Distinct clips used once per design required')
        if packets[refs[0][0]]['role'] != packets[refs[1][0]]['role']:
            raise ValueError('Do not pair developer and independent review')
        used.update(refs)
        pairs.append(dict(id=identifier, family=family, role=packets[refs[0][0]]['role'],
                          baseline=refs[0], candidate=refs[1]))
    imported, observations, reviewers = set(), {}, {'developer': set(), 'independent': set()}
    for entry in config['imports']:
        _fields(entry, ('path', 'response_sha256'), 'import binding')
        path = _path(config_path.parent, entry['path'])
        roots.append(path)
        _bound_file(path / 'response.json', entry['response_sha256'], bindings)
        validation_path = path / 'validation.json'
        bindings[validation_path] = sha256(validation_path)
        data, validation = _read(path / 'response.json'), _read(validation_path)
        if not isinstance(data, dict) or not isinstance(validation, dict):
            raise ValueError('Invalid imported response or validation')
        packet = data.get('packet_id')
        if packet not in packets:
            raise ValueError('Imported review references unknown packet')
        info = packets[packet]
        checked = (developer_validate if info['role'] == 'developer' else independent_validate)(
            data, info['manifest'], info['digest'])
        if validation.get('response_sha256') != entry['response_sha256'] or any(
                validation.get(key) != value for key, value in checked.items()):
            raise ValueError('Imported validation differs from revalidation')
        if validation.get('release_approved', False) is not False:
            raise ValueError('Review import cannot grant release approval')
        reviewer = data['reviewer_id'].strip()
        if (packet, reviewer) in imported:
            raise ValueError('Repeated reviewer/packet import; conflicting revisions require a new design')
        imported.add((packet, reviewer))
        if any(ref[0] == packet for ref in used):
            reviewers[info['role']].add(reviewer)
        for row in data['reviews']:
            observations[(info['role'], reviewer, packet, row['clip_id'])] = copy.deepcopy(row['cleanup'])
    if any(output.is_relative_to(root) or root.is_relative_to(output) for root in roots):
        raise ValueError('Use a fresh output separate from all input directories')
    rows = []
    for pair in pairs:
        for reviewer in sorted(reviewers[pair['role']]):
            b = observations.get((pair['role'], reviewer, *pair['baseline']))
            c = observations.get((pair['role'], reviewer, *pair['candidate']))
            rows.append(dict(pair_id=pair['id'], family=pair['family'], review_type=pair['role'], reviewer_id=reviewer,
                             baseline=dict(packet_id=pair['baseline'][0], clip_id=pair['baseline'][1], cleanup=b),
                             candidate=dict(packet_id=pair['candidate'][0], clip_id=pair['candidate'][1], cleanup=c),
                             comparison=compare(b, c)))
    strata = {}
    for role in ('developer', 'independent'):
        selected = [r for r in rows if r['review_type'] == role]
        families = sorted({p['family'] for p in pairs if p['role'] == role})
        strata[role] = dict(reviewers_observed=len(reviewers[role]), design_pairs=sum(p['role'] == role for p in pairs),
                            **summarize(selected), families={f: summarize([r for r in selected if r['family'] == f]) for f in families})
    unpaired = [dict(review_type=role, reviewer_id=reviewer, packet_id=packet, clip_id=clip, cleanup=cleanup)
                for (role, reviewer, packet, clip), cleanup in sorted(observations.items()) if (packet, clip) not in used]
    result = dict(schema='strep-paired-cleanup-result-v1', created_at=now(),
                  design_pairs=len(pairs), imports_revalidated=len(imported), comparisons=rows, strata=strata,
                  unpaired_imported_reviews=unpaired,
                  input_bindings=[dict(path=str(p), sha256=d) for p, d in sorted(bindings.items())],
                  quality_approved=False, release_approved=False,
                  scope='Human-entered attestations; identities, independence, design freezing, protocol order and actual editing are not machine verified. Completed-only medians may have selection bias; missing, abandoned and unperformed pairs are excluded from completion estimates and retained in coverage counts. Censored bounds assume eventual finite completion and apply only to reported completed/censored positive-baseline pairs. Unpaired imported attempts are retained separately. No pooled developer/independent estimate, inferential confidence interval or release gate is computed.')
    for path, digest in bindings.items():
        if sha256(path) != digest:
            raise ValueError('Input changed during analysis')
    output.mkdir(parents=True)
    save(output / 'result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.config, args.output)
    print(json.dumps(dict(output=str(args.output), design_pairs=result['design_pairs'],
                          imports_revalidated=result['imports_revalidated'], quality_approved=False, release_approved=False)))
