"""Necessary rigid-point contact checks from metadata, without poses or anatomy.

This tests fixed-distance pairs, not joint reach, collision, contact normals,
temporal feasibility or model response. No contradiction is not feasibility.
"""
from fractions import Fraction
from itertools import combinations
import math
from pathlib import Path
from strep import ROOT, read, sha256

SCHEMA = 'strep-scene-contact-consistency-v1'
MAXIMUM_PAIR_POPULATION = 4096


def number(value):
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        raise ValueError('Contact coordinates and tolerances must be finite numbers')
    return Fraction(value)


def point(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('Contact point requires three coordinates')
    return tuple(number(v) for v in value)


def squared_distance(a, b):
    return sum((x-y)**2 for x, y in zip(a, b))


def record(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def distances_conflict(a, b, tolerance):
    """Exact |sqrt(a)-sqrt(b)| > tolerance for nonnegative rationals.

    With large=max(a,b), small=min(a,b), q=large-small-tolerance**2,
    this is q>0 and q**2>4*tolerance**2*small. No approximate square root.
    """
    if min(a, b, tolerance) < 0:
        raise ValueError('Nonnegative squared distances and tolerance required')
    small, large = sorted([a, b]); q = large-small-tolerance**2
    return q > 0 and q**2 > 4*tolerance**2*small


def source_point(contact):
    effector = contact.get('effector', {})
    if ('region_contact' in contact or 'surface_vertex' in effector
            or not {'joint', 'offset_m'} <= set(effector)):
        return None
    return point(effector['offset_m'])


def target_point(contact):
    target = contact.get('target', {}); space = target.get('space')
    if 'surface_vertex' in target:return None
    if space == 'world' and {'space', 'point_m'} <= set(target):
        return ('world',), point(target['point_m'])
    if space == 'object' and {'space', 'object', 'point_m'} <= set(target):
        return ('object', target['object']), point(target['point_m'])
    if space == 'actor' and {'space', 'actor', 'joint', 'offset_m'} <= set(target):
        return ('actor', target['actor'], target['joint']), point(target['offset_m'])
    return None


def diagnose(scene):
    """Retain every overlapping same-joint pair, with explicit exclusions."""
    count = scene.get('frame_count'); contacts = scene.get('contacts'); actors = scene.get('actors')
    if (type(count) is not int or not 3 <= count <= 1800 or not isinstance(actors, dict)
            or not isinstance(contacts, list) or not 1 <= len(contacts) <= 4096):
        raise ValueError('Complete bounded scene clock, actors and contacts required')
    groups = {}; ungrouped = []
    for index, contact in enumerate(contacts):
        if not isinstance(contact, dict) or contact.get('actor') not in actors:
            raise ValueError('Named contact actor required')
        if not isinstance(contact.get('effector', {}), dict) or not isinstance(contact.get('target', {}), dict):
            raise ValueError('Contact effector and target must be dictionaries')
        start, end = contact.get('start_frame'), contact.get('end_frame')
        if type(start) is not int or type(end) is not int or not 0 <= start <= end < count:
            raise ValueError('Contact interval outside authored clock')
        effector = contact.get('effector', {}); joint = effector.get('joint')
        if not isinstance(joint, str) or not joint:
            ungrouped.append(dict(contact_index=index, contact_id=contact.get('id'), reason='No declared source joint; mesh/region rigidity is not inferred'))
            continue
        groups.setdefault((contact['actor'], joint), []).append(index)
    population = sum(len(indices)*(len(indices)-1)//2 for indices in groups.values())
    if population > MAXIMUM_PAIR_POPULATION:
        raise ValueError('Contact diagnostic pair population exceeds 4096; no pairs were thinned')
    pairs = []; disjoint = 0
    for (actor, joint), indices in groups.items():
        for i, j in combinations(indices, 2):
            first, second = contacts[i], contacts[j]
            start = max(first['start_frame'], second['start_frame']); end = min(first['end_frame'], second['end_frame'])
            if start > end:
                disjoint += 1; continue
            row = dict(contact_indices=[i,j], contact_ids=[first.get('id'),second.get('id')],
                       actor=actor, joint=joint, overlap_frames=[start,end])
            source = [source_point(c) for c in [first,second]]
            target = [target_point(c) for c in [first,second]]
            if None in source or None in target or 'tolerance_m' not in first or 'tolerance_m' not in second:
                row.update(status='unassessed', reason='Needs explicit joint offsets, point targets and tolerances; no mesh/region proxy substitution')
            elif target[0][0] != target[1][0]:
                row.update(status='unassessed', reason='Target points are in different rigid frames; world pose tracks are not loaded')
            else:
                tolerances = [number(c['tolerance_m']) for c in [first,second]]
                if min(tolerances) < 0:raise ValueError('Contact tolerances must be nonnegative')
                source_d2 = squared_distance(*source); target_d2 = squared_distance(target[0][1],target[1][1]); total = sum(tolerances)
                conflict = distances_conflict(source_d2,target_d2,total)
                row.update(status='contradiction' if conflict else 'necessary_distance_condition_not_contradicted',
                    target_rigid_frame=list(target[0][0]), source_separation_squared_m2=record(source_d2),
                    target_separation_squared_m2=record(target_d2), tolerance_sum_m=record(total),
                    arithmetic='Exact rational values of the supplied integer/binary-float coordinates; strict square-root inequality without rounding')
            pairs.append(row)
    conflicts = [r['contact_indices'] for r in pairs if r['status']=='contradiction']
    return dict(schema=SCHEMA, frame_count=count, same_joint_pair_population=population,
        disjoint_pair_count=disjoint, overlapping_pairs=pairs, ungrouped_contacts=ungrouped,
        conflicting_pairs=conflicts, has_proven_pair_conflict=bool(conflicts),
        complete_declared_pair_population_retained=True,
        assumptions='Ideal rigid transforms for declared joint-local offsets and world/object/same-partner-joint point targets; tolerance balls in metres.',
        scope='Necessary pairwise fixed-distance check only. Mesh/region contacts and target points in different frames are not assessed. No source pose, anatomy, reach, normals, collision, timing dynamics or model accuracy checked.',
        source_pose_geometry_checked=False, feasibility_approved=False, quality_approved=False, release_approved=False)


def validate_prepared(folder, freeze, scene):
    folder = Path(folder); artifact = folder/'contact-consistency.json'; snapshot = folder/'source-snapshot/scene_contact_consistency.py'
    digest = freeze.get('contact_consistency_sha256')
    if digest is None:
        if artifact.exists() or snapshot.exists():raise ValueError('Contact-consistency binding was dropped')
        return None
    if (not artifact.is_file() or not snapshot.is_file() or sha256(artifact) != digest
            or sha256(snapshot) != freeze.get('contact_consistency_method_sha256')
            or sha256(ROOT/'scripts/scene_contact_consistency.py') != freeze.get('contact_consistency_method_sha256')):
        raise ValueError('Missing or changed contact-consistency audit or method')
    result = read(artifact)
    if result != diagnose(scene) or result['has_proven_pair_conflict']:
        raise ValueError('Rebound or conflicting contact-consistency audit')
    return result
