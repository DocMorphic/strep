"""Portable complete hand-material candidates for all reserved neutral partners.

This prepares source-bound triangle inventories, never chooses palms or generates
reserved motion. Anatomy, authored interaction targets and human review are unset.
"""
import argparse
from pathlib import Path
import shutil
from reserved_partner_fixtures import verify as verify_fixtures, METHODS as FIXTURE_METHODS
from rig_material_patch import MaterialSurface, METHODS as MATERIAL_METHODS, require
from strep import ROOT, read, save, sha256, now

METHODS = tuple(dict.fromkeys(FIXTURE_METHODS + MATERIAL_METHODS + ('reserved_partner_materials.py',)))
ROLES = ('LeftHand', 'RightHand')
PARAMETERS = dict(include_children=True, minimum_weight=1., minimum_twice_area_m2=1e-12, maximum_faces=20000)
SCOPE = ('Complete default-pose triangle inventories for both hands on all six reserved partner '
         'instances; deformation ownership only. Shared decoder and known topology. '
         'No anatomical palm/facing review, selected patches, interaction targets, '
         'reserved motion, new engine execution or human/quality/release approval.')


def files(folder):
    result = {}
    for p in sorted(folder.rglob('*')):
        require(not p.is_symlink() and p.resolve().is_relative_to(folder), 'Portable material files must remain inside bundle')
        if p.is_file():
            result[p.relative_to(folder).as_posix()] = sha256(p)
    return result


def population(fixtures):
    result = read(fixtures/'result.json')
    rows = []
    for pair in result['pairings']:
        folder = fixtures/'pairs'/pair['id']; scene = read(folder/'scene.json')
        require(set(scene['actors']) == {'A', 'B'}, 'Complete reserved actor population required')
        for actor in ('A', 'B'):
            entry = scene['actors'][actor]
            for role in ROLES:
                rows.append(dict(pairing=pair['id'], actor=actor, rig_id=entry['rig_id'], role=role,
                    path=f"candidates/{pair['id']}/{actor}/{role}.json",
                    folder=folder, entry=entry))
    require(len(rows) == 12, 'All twelve reserved hand instances required')
    return rows


def candidate(row, cache):
    entry = row['entry']; folder = row['folder']
    a, b = entry['files']['character.glb'], entry['files']['rig-profile.json']
    key = a['sha256'], b['sha256']
    # Repeated rig instances share identical default-pose topology. Placements
    # remain separately bound in every unchanged portable scene.
    if key not in cache:
        cache[key] = MaterialSurface(folder/a['path'], folder/b['path'],
            character_sha256=a['sha256'], profile_sha256=b['sha256'])
    cache[key].check_inputs()
    return cache[key].candidates(row['role'], **PARAMETERS)


def identity(row, value, digest):
    return dict(pairing=row['pairing'], actor=row['actor'], rig_id=row['rig_id'], role=row['role'],
        path=row['path'], sha256=digest, eligible_faces=len(value['face_references']),
        degenerate_owned_faces=len(value['degenerate_face_references']),
        eligible_vertices=len(value['vertex_references']), selected_patches=0,
        anatomy_verified=False, contact_target_approved=False)


def run(construction, output):
    construction, output = Path(construction).resolve(), Path(output).resolve()
    require(not output.exists() and not output.is_relative_to(construction), 'Fresh separate material bundle required')
    require(not any(p.is_symlink() for p in construction.rglob('*')), 'Material bundle cannot copy symlink inputs')
    verify_fixtures(construction)
    source = files(construction)
    methods = {n: sha256(ROOT/'scripts'/n) for n in METHODS}
    output.mkdir(parents=True)
    try:
        shutil.copytree(construction, output/'fixtures')
        require(files(output/'fixtures') == source, 'Complete neutral bundle changed during copying')
        for name in METHODS:
            target = output/'implementation'/name; target.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT/'scripts'/name, target)
        save(output/'request.json', dict(schema='strep-reserved-partner-material-request-v1', at=now(),
            source_bundle_result_sha256=sha256(construction/'result.json'),
            fixture_file_sha256=source, implementation_sha256=methods, parameters=PARAMETERS,
            reserved_motion_trials_executed=0))
        save(output/'pipeline.json', dict(status='processing', reserved_motion_trials_executed=0))
        cache = {}; manifests = []
        for row in population(output/'fixtures'):
            value = candidate(row, cache)
            save(output/row['path'], value)
            manifests.append(identity(row, value, sha256(output/row['path'])))
        require(files(construction) == source, 'Original neutral bundle changed')
        require(all(sha256(ROOT/'scripts'/n) == sha256(output/'implementation'/n) == h
                    for n, h in methods.items()), 'Material method changed')
        save(output/'result.json', dict(schema='strep-reserved-partner-materials-v1', status='complete',
            request_sha256=sha256(output/'request.json'), hands=manifests, reserved_motion_trials_executed=0,
            selected_patches=0, anatomy_verified=False, contact_targets_bound=False,
            engine_executed=False, quality_approved=False, release_approved=False, scope=SCOPE))
        checked = verify(output)
        save(output/'pipeline.json', dict(status='complete', reserved_motion_trials_executed=0))
        return checked
    except Exception as exc:
        save(output/'pipeline.json', dict(status='failed', error=str(exc), reserved_motion_trials_executed=0))
        raise


def verify(output):
    """Rebuild every complete candidate from portable assets without original paths."""
    output = Path(output).resolve(); request = read(output/'request.json'); result = read(output/'result.json')
    require(request.get('schema') == 'strep-reserved-partner-material-request-v1'
            and result.get('schema') == 'strep-reserved-partner-materials-v1'
            and result.get('status') == 'complete' and result['request_sha256'] == sha256(output/'request.json'),
            'Complete bound material request/result required')
    require(request['parameters'] == PARAMETERS and type(request['reserved_motion_trials_executed']) is int
            and request['reserved_motion_trials_executed'] == 0,
            'Preserve explicit complete neutral material settings')
    require(type(result['reserved_motion_trials_executed']) is int and result['reserved_motion_trials_executed'] == 0
            and type(result['selected_patches']) is int and result['selected_patches'] == 0
            and all(result[k] is False for k in ('anatomy_verified', 'contact_targets_bound', 'engine_executed',
                    'quality_approved', 'release_approved')) and result['scope'] == SCOPE,
            'Material inventory cannot grant contact or motion approval')
    require(set(request['implementation_sha256']) == set(METHODS), 'Every material method must be bound')
    require(all(sha256(ROOT/'scripts'/n) == sha256(output/'implementation'/n) == h
                for n, h in request['implementation_sha256'].items()), 'Archived material method changed')
    require(files(output/'fixtures') == request['fixture_file_sha256']
            and sha256(output/'fixtures/result.json') == request['source_bundle_result_sha256'],
            'Complete copied neutral evidence changed')
    verify_fixtures(output/'fixtures')
    rows = population(output/'fixtures')
    require([h['path'] for h in result['hands']] == [row['path'] for row in rows],
            'Complete directed pair/actor/hand population required')
    require({p.relative_to(output).as_posix() for p in (output/'candidates').rglob('*') if p.is_file()}
            == {row['path'] for row in rows}, 'Exact complete candidate file population required')
    cache = {}
    for row, manifest in zip(rows, result['hands']):
        value = candidate(row, cache)
        require(value == read(output/row['path']), 'Complete material candidate replay differs')
        require(identity(row, value, sha256(output/row['path'])) == manifest, 'Candidate identity or reduction changed')
    require(files(output/'fixtures') == request['fixture_file_sha256'], 'Neutral fixture changed during material replay')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('build'); build.add_argument('construction', type=Path); build.add_argument('output', type=Path)
    check = sub.add_parser('verify'); check.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'build':
        run(args.construction, args.output)
    else:
        verify(args.output)
