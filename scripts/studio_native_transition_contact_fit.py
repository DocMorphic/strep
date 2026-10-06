"""Studio reserve-guided jobs and review/export, preserving the selected scene."""
import argparse
import copy
from pathlib import Path
import shutil

import native_transition_contact_fit as workflow
import native_transition_contact_package as packaging
import studio_native_transition_scene_fit as legacy
from native_contact_reserve import SCHEMA as RESERVE_SCHEMA, guided_problem
from native_scene_contacts import fields
from strep import ROOT, read, save, sha256, now

NAMESPACE = 'native-transition-contact-fit-jobs'
PREFIX = '/files/' + NAMESPACE + '/'
SCHEMA = 'strep-studio-native-transition-contact-fit-v1'
SCRIPT_ROOT = Path(__file__).resolve().parent
METHODS = tuple(dict.fromkeys(workflow.METHODS + legacy.METHODS + (
    'native_transition_contact_package.py', 'studio_native_transition_contact_fit.py')))
require, equal = workflow.require, workflow.equal


def folder_for(job):
    require(isinstance(job, str) and legacy.NAME.fullmatch(job), 'Exact reserve-guided job required')
    base = (ROOT / 'reports' / NAMESPACE).resolve()
    folder = (base / job).resolve()
    require(folder.parent == base, 'Reserve-guided job escapes reports')
    return folder


def catalog(binding):
    folder, result = legacy.transitions.source(binding)
    contacts = read(folder / 'scene.json')['contacts']
    return dict(schema='strep-studio-transition-contact-reserve-catalog-v1', source=copy.deepcopy(binding),
                contacts_sha256=sha256(folder / 'scene.json'), contacts=contacts,
                source_checks=result['checks'], original_selected=True, quality_approved=False, release_approved=False)


def validate_request(payload):
    fields(payload, ('schema', 'bridge', 'reserves_m', 'seed'), 'Studio reserve-guided bridge')
    require(payload['schema'] == SCHEMA, 'Studio reserve-guided schema required')
    require(payload['bridge']['resume_from'] is None, 'Reserve guidance starts a new epoch; disable optimizer continuation')
    recipe = legacy.recipe_for(payload['bridge'])
    problem = legacy.correction.Problem(recipe, ROOT)
    reserve = dict(schema=RESERVE_SCHEMA, contacts_sha256=sha256(problem.folder / 'scene.json'),
                   reserves_m=copy.deepcopy(payload['reserves_m']))
    seed = None
    if payload['seed'] is not None:
        seed_folder = legacy.contained(payload['seed'])
        result = read(seed_folder / 'result.json')
        if result['schema'] == legacy.correction.SCHEMA:
            legacy.validate_request(dict(copy.deepcopy(payload['bridge']), resume_from=payload['seed']))
            seed_recipe = read(seed_folder / 'recipe.json')
            seed = seed_folder / 'fit/probes/final/probe.json'
        elif result['schema'] == workflow.SCHEMA:
            request = read(seed_folder / 'request.json')
            request_path = Path(read(seed_folder / 'prepared.json')['request_original']).resolve()
            require(request_path.is_relative_to((ROOT / 'reports').resolve()), 'Seed request outside reports')
            recipe_path = workflow.bound_file(request['recipe'], request_path.parent)
            require(recipe_path.is_relative_to((ROOT / 'reports').resolve()), 'Seed recipe outside reports')
            if request['seed'] is not None:
                require(workflow.bound_file(request['seed'], request_path.parent).is_relative_to((ROOT / 'reports').resolve()),
                        'Seed controls outside reports')
            workflow.verify(seed_folder)
            seed_recipe = read(seed_folder / 'recipe.json')
            seed = seed_folder / 'probes/final/probe.json'
        else:
            raise ValueError('Completed compatible correction seed required')
        omitted = ('iterations', 'label')
        require(equal({k: v for k, v in seed_recipe.items() if k not in omitted},
                      {k: v for k, v in recipe.items() if k not in omitted}), 'Seed source, permissions, geometry or query budget differ')
    guided_problem(problem.motion, reserve, reserve['contacts_sha256'],
                   initial=None if seed is None else read(seed)['controls'])
    return recipe, reserve, seed


def prepare(payload, folder):
    folder = Path(folder).resolve()
    require(folder == folder_for(folder.name) and not folder.exists(), 'Fresh reserve-guided Studio job required')
    recipe, reserve, seed = validate_request(payload)
    folder.mkdir(parents=True)
    try:
        save(folder / 'studio-request.json', payload)
        save(folder / 'recipe.json', recipe)
        if seed is not None: shutil.copyfile(seed, folder / 'seed.json')
        request = dict(schema=workflow.SCHEMA, recipe=dict(path='recipe.json', sha256=sha256(folder / 'recipe.json')),
                       reserve=reserve, seed=None if seed is None else dict(path='seed.json', sha256=sha256(folder / 'seed.json')))
        save(folder / 'workflow-request.json', request)
        (folder / 'implementation').mkdir()
        methods = {n: sha256(SCRIPT_ROOT / n) for n in METHODS}
        for n in METHODS: shutil.copyfile(SCRIPT_ROOT / n, folder / 'implementation' / n)
        save(folder / 'prepared.json', dict(schema=SCHEMA, at=now(), request_sha256=sha256(folder / 'studio-request.json'),
             recipe_sha256=sha256(folder / 'recipe.json'), workflow_request_sha256=sha256(folder / 'workflow-request.json'),
             seed_sha256=None if seed is None else sha256(seed), implementation_sha256=methods))
        save(folder / 'pipeline.json', dict(status='starting', original_selected=True))
        return read(folder / 'prepared.json')
    except Exception as exc:
        save(folder / 'pipeline.json', dict(status='failed', error=str(exc), original_selected=True))
        raise


def frozen(folder):
    prepared = read(folder / 'prepared.json')
    require(prepared['schema'] == SCHEMA and set(prepared['implementation_sha256']) == set(METHODS), 'Complete reserve job methods required')
    for n, h in prepared['implementation_sha256'].items():
        require(sha256(SCRIPT_ROOT / n) == sha256(folder / 'implementation' / n) == h, 'Reserve job methods changed')
    require(prepared['request_sha256'] == sha256(folder / 'studio-request.json')
            and prepared['recipe_sha256'] == sha256(folder / 'recipe.json')
            and prepared['workflow_request_sha256'] == sha256(folder / 'workflow-request.json'), 'Reserve job inputs changed')
    recipe, reserve, seed = validate_request(read(folder / 'studio-request.json'))
    require(equal(recipe, read(folder / 'recipe.json')), 'Reserve job source recipe changed')
    expected = dict(schema=workflow.SCHEMA, recipe=dict(path='recipe.json', sha256=sha256(folder / 'recipe.json')),
                    reserve=reserve, seed=None if seed is None else dict(path='seed.json', sha256=sha256(seed)))
    require(equal(read(folder / 'workflow-request.json'), expected)
            and prepared['seed_sha256'] == (None if seed is None else sha256(seed)), 'Reserve or seed binding changed')
    if seed is not None: require(sha256(folder / 'seed.json') == sha256(seed), 'Seed snapshot changed')
    return prepared


def download_names(folder):
    names = ['candidate-bundle.zip', 'proposal/result.json', 'proposal/reserve-binding.json',
             'proposal/candidate/scene.json', 'proposal/candidate/contacts-audit.json', 'proposal/candidate/geometry.json',
             'proposal/candidate/tracks/root-motion.json', 'proposal/candidate/tracks/events.json', 'proposal/candidate/tracks/contacts.json']
    names += ['proposal/candidate/actors/' + str(i) + '.glb'
              for i in range(len(read(folder / 'proposal/candidate/scene.json')['actors']))]
    return names


def completion(folder, result):
    return dict(schema=SCHEMA, status='complete', prepared_sha256=sha256(folder / 'prepared.json'),
                proposal_result_sha256=sha256(folder / 'proposal/result.json'), checks=result['checks'],
                all_declared_samples_pass=result['all_declared_samples_pass'], reserve_binding=result['binding'],
                actual_primary_iterations=result['actual_primary_iterations'], samples=result['samples'],
                original_selected=True, studio_selection_changed=False, native_roots_only=True,
                engine_playback_verified=False, quality_approved=False, training_admitted=False, release_approved=False,
                files_sha256={n: sha256(folder / n) for n in download_names(folder)})


def run(folder):
    folder = Path(folder).resolve()
    require(folder == folder_for(folder.name), 'Contained reserve-guided worker required')
    with legacy.job_lock(folder):
        frozen(folder)
        state = read(folder / 'pipeline.json')
        if state['status'] == 'complete': return manifest(folder.name)
        require(state['status'] == 'starting', 'Only a prepared reserve job can run')
        save(folder / 'pipeline.json', dict(status='processing', original_selected=True))
        try:
            result = workflow.run(folder / 'workflow-request.json', folder / 'proposal')
            frozen(folder)
            packaging.build(folder / 'proposal', folder / 'candidate-bundle.zip', validated=result)
            save(folder / 'completion.json', completion(folder, result))
            save(folder / 'pipeline.json', dict(status='complete', original_selected=True))
            return manifest(folder.name)
        except Exception as exc:
            save(folder / 'pipeline.json', dict(status='failed', error=str(exc), original_selected=True))
            raise


def manifest(job):
    folder = folder_for(job)
    state = read(folder / 'pipeline.json')
    base = dict(id=job, status=state['status'], error=state.get('error'), downloads=[],
                original_selected=True, studio_selection_changed=False, quality_approved=False, release_approved=False)
    if state['status'] != 'complete': return base
    frozen(folder)
    result = workflow.verify(folder / 'proposal')
    packaging.verify(folder / 'proposal', folder / 'candidate-bundle.zip', validated=result)
    completed = completion(folder, result)
    require(equal(read(folder / 'completion.json'), completed)
            and equal(state, dict(status='complete', original_selected=True)), 'Reserve completion decisions changed')
    return dict(base, **{k: v for k, v in completed.items() if k not in ('schema', 'status', 'original_selected', 'studio_selection_changed', 'quality_approved', 'release_approved')},
                result_sha256=sha256(folder / 'completion.json'),
                authoring_request=read(folder / 'studio-request.json'),
                downloads=[dict(label=n, url=PREFIX + job + '/' + n, sha256=h) for n, h in completed['files_sha256'].items()])


def listing():
    rows = []
    for folder in sorted((ROOT / 'reports' / NAMESPACE).glob('*')):
        if folder.is_dir() and legacy.NAME.fullmatch(folder.name):
            try: rows.append(dict(id=folder.name, status=read(folder / 'pipeline.json')['status']))
            except (OSError, ValueError): pass
    return dict(jobs=rows)


def served_file(relative):
    parts = relative.split('/')
    require(len(parts) >= 3 and parts[0] == NAMESPACE and all(x not in ('', '.', '..') for x in parts)
            and not any(c in relative for c in ('\\', '%', '?', '#')), 'Contained reserve artifact required')
    result = manifest(parts[1])
    name = '/'.join(parts[2:])
    require(name in result.get('files_sha256', {}), 'Unpublished reserve artifact')
    path = (folder_for(parts[1]) / name).resolve()
    require(path.is_relative_to(folder_for(parts[1])) and sha256(path) == result['files_sha256'][name], 'Reserve artifact changed or escaped')
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    run(parser.parse_args().folder)
