"""Source-bound release evidence inventory. Never grants asset/release approval."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            value.update(chunk)
    return value.hexdigest()


def unique_fields(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('Duplicate JSON field: ' + name)
        result[name] = value
    return result


def reject_nonfinite(value):
    raise ValueError('Nonfinite JSON value: ' + value)


def local_reference(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Portable relative evidence reference required')
    path = Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Evidence must stay inside the project')
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('Evidence link escapes the project')
    return resolved


def inventory(root, matrix_path):
    root = Path(root).resolve()
    matrix_path = Path(matrix_path).resolve()
    if not matrix_path.is_relative_to(root) or not matrix_path.is_file():
        raise ValueError('Existing in-project matrix required')
    binding = digest(matrix_path)
    implementation_binding = digest(__file__)
    matrix = json.loads(matrix_path.read_bytes(), object_pairs_hook=unique_fields,
                        parse_constant=reject_nonfinite)
    capabilities = matrix.get('capabilities')
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError('Complete capability inventory required')
    design = matrix.get('evaluation_design'); gates = matrix.get('gates')
    completion = matrix.get('completion')
    if not all(isinstance(v, dict) for v in [design, gates, completion]):
        raise ValueError('Evaluation, gate and completion declarations required')
    if type(completion.get('achieved')) is not bool:
        raise ValueError('Explicit Boolean completion declaration required')
    bindings = {matrix_path.relative_to(root).as_posix(): binding}
    rows = []; ids = set(); gaps = []
    for item in capabilities:
        if not isinstance(item, dict):
            raise ValueError('Capability records required')
        name = item.get('id'); status = item.get('status')
        if not isinstance(name, str) or not name or name in ids or not isinstance(status, str) or not status:
            raise ValueError('Unique capability identifiers and declared statuses required')
        ids.add(name)
        release = item.get('release_evidence'); development = item.get('development_evidence')
        if not all(isinstance(v, list) and all(isinstance(p, str) for p in v) for v in [release, development]):
            raise ValueError('Separate development and release evidence lists required')
        if len(release) != len(set(release)):
            raise ValueError('Duplicate release evidence cannot inflate coverage')
        evidence = []
        for ref in release:
            path = local_reference(root, ref)
            if path.suffix.lower() not in ['.json', '.md', '.txt']:
                raise ValueError('Release evidence must reference a report or document')
            exists = path.is_file()
            checksum = digest(path) if exists else None
            if exists: bindings[ref] = checksum
            else: gaps.append(dict(kind='missing_release_file', capability=name, reference=ref))
            evidence.append(dict(reference=ref, exists=exists, sha256=checksum, contents_validated=False))
        if not release: gaps.append(dict(kind='no_release_evidence', capability=name))
        rows.append(dict(id=name, declared_status=status, development_references=len(development),
                         release_references=len(release), release_evidence=evidence, approval_verified=False))
    fixture = design.get('held_out_fixtures')
    fixture_record = None
    if fixture is None:
        gaps.append(dict(kind='held_out_fixtures_unbound'))
    else:
        path = local_reference(root, fixture)
        if path.suffix.lower() != '.json':
            raise ValueError('Fixture manifest must be JSON')
        exists = path.is_file(); checksum = digest(path) if exists else None
        fixture_record = dict(reference=fixture, exists=exists, sha256=checksum, contents_validated=False)
        if exists: bindings[fixture] = checksum
        else: gaps.append(dict(kind='missing_fixture_manifest', reference=fixture))
    unset = sorted(k for k, value in gates.items() if value is None)
    gaps.extend(dict(kind='unset_acceptance_gate', gate=k) for k in unset)
    # A declared status, complete file inventory or syntactically non-null gate
    # is insufficient to authenticate reviewer identities or numeric decisions.
    if completion['achieved']:
        gaps.append(dict(kind='completion_claim_requires_independent_validation'))
    for ref, checksum in bindings.items():
        if digest(local_reference(root, ref)) != checksum:
            raise ValueError('Evidence changed during inventory')
    if digest(__file__) != implementation_binding:
        raise ValueError('Inventory implementation changed')
    return dict(schema='strep-project-release-status-v1', status='inventory_only',
                matrix_sha256=binding, implementation_sha256=implementation_binding, inputs_sha256=bindings,
                declared_project_status=matrix.get('status'), declared_complete=completion['achieved'],
                capability_count=len(rows), capabilities=rows,
                evaluation_status=design.get('status'), gate_status=gates.get('status'),
                held_out_fixtures=fixture_record, unset_gates=unset, gaps=gaps,
                quality_approved=False, release_approved=False,
                scope='Configuration and report-file inventory only. Development evidence is counted without approval. Report contents, method freeze, held-out exposure, semantics, numerical gates, engine fidelity, reviewer independence and cleanup are not validated. No motion/action whitelist or approval is inferred.')


def write_inventory(root, matrix_path, output):
    root = Path(root).resolve(); output = Path(output).resolve()
    if not output.is_relative_to(root / 'reports') or output == root / 'reports' or output.exists():
        raise ValueError('Fresh in-project report file required')
    result = inventory(root, matrix_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf8') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--matrix', type=Path, default=Path('benchmarks/project-release-v1.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = write_inventory(args.root, args.root / args.matrix, args.root / args.output)
    print(json.dumps(dict(capabilities=result['capability_count'],
                          missing_release_evidence=sum(not c['release_references'] for c in result['capabilities']),
                          unset_gates=result['unset_gates'], gaps=len(result['gaps']),
                          status=result['status'], quality_approved=False, release_approved=False)))
