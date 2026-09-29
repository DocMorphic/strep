"""Plan a regional edit from existing export evidence; never widen it silently."""
import argparse
import math
from pathlib import Path

from audit_scene_edit_window import summarize
from strep import ROOT, read, save, sha256


def plan(rows, window, frames, floor_clearance, object_clearance, *, preserve_boundary_keys=False):
    """Flag immutable sampled failures and suggest a conservative key envelope.

    The envelope covers both interpolation keys of every failing sample. It is
    a scope suggestion, not a feasibility claim or a change to solver limits.
    """
    summarize([dict(frame=r['frame'], joint_position_error_m=0., basis_error=0.,
                    skin_position_error_m=0.) for r in rows], window, frames)
    if type(preserve_boundary_keys) is not bool:
        raise ValueError('Explicit boundary preservation policy required')
    for value in (floor_clearance, object_clearance):
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('Finite nonnegative clearance required')
    failures = []
    start, end = window
    def locked(key):
        return key < start or key > end or (preserve_boundary_keys and
            ((key == start and start > 0) or (key == end and end < frames-1)))
    for row in rows:
        values = [row['minimum_floor_m'], *row['object_clearances_m'].values()]
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError('Finite measured clearances required')
        causes = []
        if row['minimum_floor_m'] < floor_clearance-1e-6:
            causes.append('floor')
        causes += ['object:'+name for name, value in row['object_clearances_m'].items()
                   if value < object_clearance-1e-6]
        if not causes:
            continue
        frame = row['frame']
        group = ('edited_window' if start <= frame <= end else
                 'locked_segments' if math.ceil(frame) < start or math.floor(frame) > end
                 else 'boundary_segments')
        failures.append(dict(frame=frame, group=group, causes=causes,
                             immutable=locked(math.floor(frame)) and locked(math.ceil(frame)),
                             minimum_floor_m=row['minimum_floor_m'],
                             object_clearances_m=row['object_clearances_m']))
    groups = {name: [r for r in failures if r['group'] == name]
              for name in ['locked_segments', 'boundary_segments', 'edited_window']}
    envelope = [min(start, *(math.floor(r['frame']) for r in failures)),
                max(end, *(math.ceil(r['frame']) for r in failures))] if failures else list(window)
    if preserve_boundary_keys and failures:
        # Make both keys of every observed failure editable, including failures
        # exactly on a selected endpoint; clip endpoints need no outside guard.
        envelope = [min(start, max(0, min(math.floor(r['frame']) for r in failures)-1)),
                    max(end, min(frames-1, max(math.ceil(r['frame']) for r in failures)+1))]
    return dict(requested_window=list(window), frames=frames,
                preserve_boundary_keys=preserve_boundary_keys,
                immutable_geometry_failures=sum(r['immutable'] for r in failures),
                sampled_failures=len(failures),
                failure_counts={name: len(values) for name, values in groups.items()},
                locked_geometry_conflict=bool(groups['locked_segments']),
                suggested_geometry_envelope=envelope,
                changes_requested_scope=envelope != list(window), failures=failures,
                scope='Sampled geometry only. Locked segments cannot change under exact outside-key preservation. Suggested envelope covers both keys of observed failures; it does not guarantee solvability, between-sample safety, contacts, support, timing or naturalness. No edit scope is changed automatically.')


def boundary_policy(study):
    """Read the executed policy, retaining native-key-only behavior for old fits."""
    study=Path(study);result=read(study/'result.json')
    if sha256(study/'recipe.json')!=result['recipe_sha256']:
        raise ValueError('Fitting recipe changed')
    localization=read(study/'recipe.json').get('localization') or {}
    return 'locked_boundary_keys' in localization


def run(study, audit_path, window, output):
    study, audit_path, output = [Path(p).resolve() for p in (study, audit_path, output)]
    if output.exists() or not output.is_relative_to(ROOT/'reports'):
        raise ValueError('Fresh local report path required')
    result, protocol, scene = [read(study/name) for name in
                               ['result.json', 'protocol.json', 'authored-scene.json']]
    audit = read(audit_path)
    if result.get('status') != 'complete' or audit['result_sha256'] != sha256(study/'result.json'):
        raise ValueError('Matching completed seed audit required')
    for name, key in [('protocol.json', 'protocol_sha256'), ('authored-scene.json', 'authored_scene_sha256'),
                      ('candidate.glb', 'candidate_glb_sha256'), ('motion.npz', 'candidate_sha256')]:
        if sha256(study/name) != result[key]:
            raise ValueError('Changed seed artifact: '+name)
    if audit['protocol_sha256'] != sha256(study/'protocol.json') or audit['variants']['candidate']['glb_sha256'] != sha256(study/'candidate.glb'):
        raise ValueError('Seed audit identity mismatch')
    config = protocol['config']
    report = plan(audit['variants']['candidate']['rows'], window, scene['frame_count'],
                  config['clearance_m'], config['object_clearance_m'],
                  preserve_boundary_keys=boundary_policy(study))
    report.update(inputs={str(p): sha256(p) for p in [study/'result.json', study/'protocol.json',
                      study/'authored-scene.json', study/'candidate.glb', study/'motion.npz', audit_path]},
                  planner_sha256=sha256(__file__), quality_approved=False)
    save(output, report)
    print({k: report[k] for k in ['failure_counts', 'locked_geometry_conflict', 'suggested_geometry_envelope']})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('study', type=Path)
    parser.add_argument('audit', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--window', type=int, nargs=2, required=True)
    args = parser.parse_args()
    run(args.study, args.audit, args.window, args.output)
