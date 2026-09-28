"""Verify unchanged cleanup cases when extending a frozen population snapshot."""
import argparse
import difflib
from pathlib import Path
from strep import read, save, sha256, now
from audit_authoring_intent import check_files
from study_whole_support_breadth import check_engine


def verified(study):
    plan, done = read(study/'protocol.json'), read(study/'completion.json')
    if sha256(study/'protocol.json') != done['protocol_sha256']:
        raise ValueError('Completion protocol mismatch')
    check_files(study, done['files'])
    check_files(study/'implementation', plan['implementation'])
    if sha256(study/'engine/verification.json') != done['engine_verification_sha256']:
        raise ValueError('Engine evidence changed')
    if check_engine(read(study/'engine/verification.json'), read(study/'manifest.json')['cases']) != done['engine_actor_frames']:
        raise ValueError('Engine population changed')
    if [c['id'] for c in plan['cases']] != [r['id'] for r in done['rows']]:
        raise ValueError('Completion population changed')
    for row in done['rows']:
        if 'selected' in row and sha256(row['selected']) != row['selected_sha256']:
            raise ValueError('Selected output changed')
    return plan, done


def compare(before, after, output):
    if output.exists():
        raise ValueError('Preserve earlier comparison')
    ap, ad = verified(before); bp, bd = verified(after)
    for key in ('policy', 'solver_bootstrap_sha256'):
        if ap[key] != bp[key]:
            raise ValueError('Extension changed method: '+key)
    changed = []
    for name in sorted(set(ap['implementation']) | set(bp['implementation'])):
        if ap['implementation'].get(name) != bp['implementation'].get(name):
            a, b = before/'implementation'/name, after/'implementation'/name
            changed.append(dict(file=name, before_sha256=ap['implementation'].get(name),
                after_sha256=bp['implementation'].get(name), diff=''.join(difflib.unified_diff(
                    a.read_text(encoding='utf-8-sig').splitlines(True) if a.exists() else [],
                    b.read_text(encoding='utf-8-sig').splitlines(True) if b.exists() else [],
                    fromfile=str(a), tofile=str(b)))))
    if [c['id'] for c in ap['cases']] != [c['id'] for c in bp['cases']]:
        raise ValueError('Extension changed declared population')
    rows = []
    for a, b, old, new in zip(ap['cases'], bp['cases'], ad['rows'], bd['rows']):
        row = dict(id=a['id'], before_status=old['status'], after_status=new['status'])
        if a['status'] == 'complete':
            if a != b:
                raise ValueError('Existing case source changed: '+a['id'])
            row.update(repeated=True,
                       same_selection_status=old['status'] == new['status'],
                       same_selected_bytes=old.get('selected_sha256') == new.get('selected_sha256'))
        else:
            row.update(repeated=False, source_became_complete=b['status'] == 'complete')
        rows.append(row)
    repeated = [r for r in rows if r['repeated']]
    result = dict(at=now(), before=str(before), after=str(after),
        before_completion_sha256=sha256(before/'completion.json'),
        after_completion_sha256=sha256(after/'completion.json'),
        rows=rows, repeated_cases=len(repeated), extended_cases=len(rows)-len(repeated),
        implementation_changes=changed, identical_implementation=not changed,
        all_repeated_selections_identical=all(r['same_selection_status'] and r['same_selected_bytes'] for r in repeated),
        implementation_sha256=sha256(__file__), quality_approved=False,
        scope='Selected-output reproducibility and population extension only. All snapshot changes are disclosed; identical outputs do not prove identical implementations. No semantic or motion-quality acceptance.')
    save(output, result)
    print({k: result[k] for k in ('repeated_cases', 'extended_cases', 'all_repeated_selections_identical')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', type=Path); parser.add_argument('after', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    compare(args.before.resolve(), args.after.resolve(), args.output.resolve())
