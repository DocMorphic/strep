"""Opt-in checked precision packages from completed Studio scene/game assets.

Retain the original package, intent and original-skin reference. Every new
package needs fresh engine/geometry, precision and inherited surface checks.
"""
import argparse
import copy
import hashlib
import os
from pathlib import Path
import shutil
from types import SimpleNamespace
import zipfile
import numpy as np
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256, now
from native_scene_contacts import SceneContacts, fields
from native_scene_authoring_job import plan, run as author, METHODS as AUTHOR_METHODS
from native_scene_engine import EngineObservations
from godot_weight_derivative import derivative
from weight_derivative_fidelity import measure_original, METHODS as FIDELITY_METHODS
import studio_surface_export as sources
import studio_native_scene as scenes
import studio_native_scene_game as games
import native_imported_surface_contact as surfaces

SCHEMA = 'strep-studio-precision-export-v1'
NAMESPACE = 'precision-export-jobs'
SCRIPT_ROOT = Path(__file__).resolve().parent
METHODS = tuple(dict.fromkeys(AUTHOR_METHODS + FIDELITY_METHODS + surfaces.METHODS + sources.METHODS +
    ('verify_native_actor_scene_engine.py', 'native_scene_game_tracks.py',
     'godot_scene_game_events.gd', 'godot_scene_game_event_audit.gd', 'studio_precision_export.py')))
FALSE_FLAGS = ('studio_selection_changed', 'quality_approved', 'release_approved',
               'training_admitted', 'physics_verified', 'gpu_render_checked', 'continuous_collision_certified')


def require(ok, message):
    if not ok: raise ValueError(message)


def folder_for(job):
    require(isinstance(job, str) and scenes.NAME.fullmatch(job), 'Invalid precision export job')
    base = (ROOT/'reports'/NAMESPACE).resolve(); folder = (base/job).resolve()
    require(folder.parent == base, 'Precision job escapes namespace'); return folder


def source(kind, job):
    selected = sources.source(kind, job)
    m, scene_folder, game_folder, contacts, policy, package, scene, members = selected
    require(not m['normal_origins'] or m['inherited_surface'] is not None,
            'Resolve inherited normal intent in the source scene before precision export')
    engine = Path(read(scene_folder/'prepared.json')['engine_path']).resolve()
    request = read(scene_folder/'authoring/actors-engine/request.json')
    spec = read(contacts)
    m = copy.deepcopy(m)
    m.update(engine_sha256=sha256(engine), source_clock_sha256=sha256(scene_folder/'authoring/actors-engine/request.json'),
             actor_count=len(scene.actors), original_selected=True, **{k: False for k in FALSE_FLAGS})
    return m, selected, engine, request, spec


def metadata(kind, job): return source(kind, job)[0]


def validate_request(payload):
    fields(payload, ('schema', 'source'), 'precision export request')
    fields(payload['source'], ('kind', 'job', 'result_sha256'), 'precision source')
    require(payload['schema'] == SCHEMA, 'Explicit precision export schema required')
    values = source(payload['source']['kind'], payload['source']['job'])
    require(payload['source'] == values[0]['source'], 'Source package changed; bind again')
    return values


def prepare(payload, folder):
    m, selected, engine, clock, spec = validate_request(payload)
    folder = Path(folder).resolve()
    require(folder == folder_for(folder.name) and not folder.exists(), 'Fresh precision export job required')
    folder.mkdir(parents=True)
    try:
        save(folder/'request.json', payload); save(folder/'source.json', m)
        save(folder/'original-contacts.json', spec); save(folder/'original-policy.json', read(selected[4]))
        shutil.copyfile(selected[5], folder/'original-assets.zip')
        require(sha256(folder/'original-assets.zip') == m['package_sha256'], 'Original package changed')
        bindings = {str(selected[3]): sha256(selected[3]), str(selected[4]): sha256(selected[4]),
                    str(selected[5]): sha256(selected[5]), str(engine): sha256(engine)}
        bindings.update(selected[6].inputs)
        if selected[2] is not None:
            path = selected[2]/'request.json'; bindings[str(path)] = sha256(path)
        methods = {n: sha256(SCRIPT_ROOT/n) for n in METHODS}
        for n in methods:
            dest = folder/'implementation'/n; dest.parent.mkdir(exist_ok=True); shutil.copyfile(SCRIPT_ROOT/n, dest)
        snapshots = {}
        for i, (name, entry) in enumerate(spec['actors'].items()):
            path = (selected[3].parent/entry['glb']).resolve()
            dest = folder/'original'/f'{i}.glb'; dest.parent.mkdir(exist_ok=True); shutil.copyfile(path, dest)
            require(sha256(dest) == entry['sha256'], 'Original actor snapshot changed')
            snapshots[name] = dict(path=dest.relative_to(folder).as_posix(), sha256=sha256(dest))
        save(folder/'prepared.json', dict(schema=SCHEMA, engine_path=str(engine), bindings=bindings,
            source_files_sha256={n: sha256(folder/n) for n in ('request.json', 'source.json',
                'original-contacts.json', 'original-policy.json', 'original-assets.zip')},
            original_actors=snapshots, implementation_sha256=methods, original_selected=True,
            **{k: False for k in FALSE_FLAGS}))
        frozen(folder); save(folder/'pipeline.json', dict(status='starting', original_selected=True))
    except Exception as error:
        save(folder/'pipeline.json', dict(status='failed', error=str(error), original_selected=True)); raise


def frozen(folder, *, current_methods=True):
    p = read(folder/'prepared.json'); m, values, engine, clock, spec = validate_request(read(folder/'request.json'))
    require(p['schema'] == SCHEMA and p['original_selected'] is True and all(p[k] is False for k in FALSE_FLAGS),
            'Unapproved precision preparation required')
    require(read(folder/'source.json') == m and str(engine) == p['engine_path'], 'Precision source changed')
    require(all(sha256(a) == b for a,b in p['bindings'].items()), 'Precision original input changed')
    require(set(p['source_files_sha256']) == {'request.json', 'source.json', 'original-contacts.json',
        'original-policy.json', 'original-assets.zip'}, 'Complete source snapshots required')
    require(all(sha256(folder/a) == b for a,b in p['source_files_sha256'].items()), 'Precision source snapshot changed')
    require(set(p['original_actors']) == set(spec['actors']), 'Complete original actor population required')
    for name, entry in p['original_actors'].items():
        path = (folder/entry['path']).resolve()
        require(path.is_relative_to(folder/'original') and sha256(path) == entry['sha256'] == spec['actors'][name]['sha256'],
                'Original actor snapshot changed')
    require(set(p['implementation_sha256']) == set(METHODS), 'Complete precision method population required')
    for n,h in p['implementation_sha256'].items():
        require(sha256(folder/'implementation'/n) == h, 'Precision method archive changed')
        if current_methods: require(sha256(SCRIPT_ROOT/n) == h, 'Precision method changed')
    return p, m, values, clock, spec


def package(folder, portable, policy, author_result, fidelity, game, surface_result):
    files = {'scene.json': folder/'portable-scene.json', 'geometry-policy.json': folder/'portable-policy.json',
             'precision-audit.json': folder/'fidelity.json', 'precision-source.json': folder/'source.json'}
    for i, name in enumerate(portable['actors']):
        files[f'actors/{i}.glb'] = folder/'actors'/f'{i}.glb'
        files[f'animations/{name}.res'] = folder/f'authoring/actors-engine/{name}-animation.res'
        files[f'precision/{i}.weights.json'] = Path(str(files[f'actors/{i}.glb'])+'.weights.json')
    if portable['objects']:
        files['objects.glb'] = folder/'authoring/objects-common/objects.glb'
        files['animations/objects.res'] = folder/'authoring/objects-engine/native-animation.res'
    if surface_result is not None:
        files['surface-policy.json'] = folder/'portable-surface-policy.json'
        files['surface-audit.json'] = folder/'surface/result.json'
    if game:
        for n in ('root-motion.json', 'contacts.json', 'events.json'):
            files[n] = folder/'tracks'/n
        files['runtime/events.gd'] = folder/'implementation/godot_scene_game_events.gd'
        files['runtime/native_engine_clock.gd'] = folder/'implementation/native_engine_clock.gd'
    # The complete original package preserves licenses, correction histories,
    # original root/event data and failed evidence without implying that its old
    # receipts describe the new current assets.
    files['original-assets.zip'] = folder/'original-assets.zip'
    receipts = {n: sha256(p) for n,p in files.items()}
    save(folder/'package.json', dict(schema=SCHEMA, files_sha256=receipts,
        original_package_sha256=sha256(folder/'original-assets.zip'), source=read(folder/'request.json')['source'],
        selected_animations={n:a['animation_index'] for n,a in portable['actors'].items()},
        root_event_tracks_included=game, root_application_mode='reference-only-motion-remains-embedded',
        all_declared_samples_pass=True, original_selected=True, **{k:False for k in FALSE_FLAGS}))
    files['package.json'] = folder/'package.json'
    with zipfile.ZipFile(folder/'checked-assets.zip', 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, path in files.items(): z.write(path, name)
    with zipfile.ZipFile(folder/'checked-assets.zip') as z:
        require(set(z.namelist()) == set(files) and len(z.namelist()) == len(files), 'Complete precision ZIP required')
        require(all(hashlib.sha256(z.read(n)).hexdigest() == sha256(p) for n,p in files.items()), 'Precision ZIP changed')


def run(folder):
    folder = Path(folder).resolve()
    require(folder == folder_for(folder.name) and read(folder/'pipeline.json')['status'] == 'starting', 'Fresh prepared precision worker required')
    try:
        import psutil
        save(folder/'worker.json', dict(pid=os.getpid(), created_at=psutil.Process().create_time()))
        prepared, m, selected, old_clock, spec = frozen(folder)
        original_scene = selected[6]; proposal = copy.deepcopy(spec)
        save(folder/'pipeline.json', dict(status='processing', stage='weight-derivatives', original_selected=True))
        for i, (name, actor) in enumerate(proposal['actors'].items()):
            original = folder/prepared['original_actors'][name]['path']; dest = folder/'actors'/f'{i}.glb'
            receipt = derivative(original, dest, source_sha256=actor['sha256'])
            actor.update(glb=str(dest), sha256=receipt['output_sha256'])
        save(folder/'contacts.json', proposal); geometry = read(folder/'original-policy.json')
        geometry['contacts_sha256'] = sha256(folder/'contacts.json'); save(folder/'policy.json', geometry)
        plan(folder/'contacts.json', folder/'policy.json', prepared['engine_path'], folder/'recipe.json')
        save(folder/'pipeline.json', dict(status='processing', stage='fresh-scene-import', original_selected=True))
        authored = author(folder/'recipe.json', folder/'authoring'); frozen(folder)
        scene = SceneContacts(proposal, folder); actor_dir = folder/'authoring/actors-engine'
        request = read(actor_dir/'request.json'); times = np.asarray(request['sample_times_s'], float)
        require(np.array_equal(times, np.asarray(old_clock['sample_times_s'], float)), 'Complete original scene clock required')
        observed = EngineObservations(scene, read(actor_dir/'engine-output.json'), request['cases'], times)
        adapter = SimpleNamespace(times=times, actors=scene.actors, actor_vertices=observed.actor_vertices)
        rows = []; arrays = dict(times_s=times)
        with threadpool_limits(limits=1):
            for i, (name, original) in enumerate(original_scene.actors.items()):
                row, errors, witnesses = measure_original(original['rig'], original['sampler'], adapter, name)
                rows.append(row); arrays[f'actor_{i}_errors_m'] = errors; arrays[f'actor_{i}_witnesses'] = witnesses
        fidelity = dict(status='complete', actors=rows, original_skin_samples_passed=all(r['position_samples_passed'] for r in rows),
            quality_approved=False, release_approved=False)
        save(folder/'fidelity.json', fidelity); np.savez_compressed(folder/'fidelity.npz', **arrays)
        portable = copy.deepcopy(proposal)
        for i, (name, actor) in enumerate(portable['actors'].items()): actor['glb'] = f'actors/{i}.glb'
        save(folder/'portable-scene.json', portable); portable_geometry = copy.deepcopy(geometry)
        portable_geometry['contacts_sha256'] = sha256(folder/'portable-scene.json'); save(folder/'portable-policy.json', portable_geometry)
        surface = None
        if m['inherited_surface'] is not None:
            normal = dict(schema='strep-native-surface-contact-v1', contacts_sha256=sha256(folder/'contacts.json'), **m['inherited_surface'])
            save(folder/'surface-policy.json', normal)
            surface = surfaces.run(folder/'contacts.json', folder/'surface-policy.json',
                folder/'authoring/objects-common/common-policy.json' if scene.objects else folder/'policy.json',
                actor_dir, folder/'surface', object_dir=folder/'authoring/objects-engine' if scene.objects else None)
            normal['contacts_sha256'] = sha256(folder/'portable-scene.json'); save(folder/'portable-surface-policy.json', normal)
        game = selected[2] is not None; roots = events = None
        if game:
            root_request = read(selected[2]/'request.json')['request']
            contact_path = folder/'authoring/combined-engine/native-authoring-contacts.json' if scene.objects else actor_dir/'result.json'
            measured = read(contact_path); measured = measured if scene.objects else measured['imported_contacts']
            roots = games.export_tracks(scene, root_request, times, observed.worlds, measured, folder/'tracks',
                source_spec=proposal, portable_scene_sha256=sha256(folder/'portable-scene.json'), contact_report_sha256=sha256(contact_path))
            events = games.engine_audit(folder/'tracks/events.json', folder/'runtime-events', Path(prepared['engine_path']))
        passed = bool(authored['sampled_conditions_pass'] and fidelity['original_skin_samples_passed']
                      and (surface is None or surface['native_and_imported_surface_contacts_pass'])
                      and (not game or roots['all_root_samples_pass'] and events['gameplay_event_dispatch_verified']))
        frozen(folder)
        if passed: package(folder, portable, portable_geometry, authored, fidelity, game, surface)
        result = dict(schema=SCHEMA, status='complete', source=m['source'], samples=len(times), actor_count=len(rows),
            original_skin_samples_passed=fidelity['original_skin_samples_passed'], scene_samples_passed=authored['sampled_conditions_pass'],
            inherited_surface_checked=surface is not None, inherited_surface_samples_passed=None if surface is None else surface['native_and_imported_surface_contacts_pass'],
            root_event_tracks_included=game, root_samples_passed=None if roots is None else roots['all_root_samples_pass'],
            event_dispatch_verified=None if events is None else events['gameplay_event_dispatch_verified'],
            checked_package_available=passed, original_selected=True, **{k:False for k in FALSE_FLAGS})
        save(folder/'result.json', result)
        outputs = ['result.json', 'original-assets.zip', 'fidelity.json', 'fidelity.npz']
        for i in range(len(rows)): outputs.extend([f'actors/{i}.glb', f'actors/{i}.glb.weights.json'])
        if passed: outputs.append('checked-assets.zip')
        save(folder/'completion.json', dict(result_sha256=sha256(folder/'result.json'), downloads={n:sha256(folder/n) for n in outputs},
            produced_files_sha256={p.relative_to(folder).as_posix():sha256(p) for p in folder.rglob('*') if p.is_file()
                and p.name not in ('completion.json', 'pipeline.json', 'worker.json', 'supervisor.log', 'engine.log')}))
        save(folder/'pipeline.json', dict(status='complete', finished_at=now(), original_selected=True)); return result
    except Exception as error:
        save(folder/'pipeline.json', dict(status='failed', error=str(error), original_selected=True)); raise


def manifest(job):
    from contact_edit_job import observed_state
    folder = folder_for(job); state = observed_state(folder)
    m = dict(id=job, status=state['status'], stage=state.get('stage'), error=state.get('error'), downloads=[], original_selected=True,
             quality_approved=False, release_approved=False)
    if state['status'] != 'complete': return m
    prepared,metadata,selected,old_clock,spec=frozen(folder, current_methods=False)
    r = read(folder/'result.json'); c = read(folder/'completion.json')
    require(r['schema'] == SCHEMA and r['status'] == 'complete' and r['original_selected'] is True
            and all(r[k] is False for k in FALSE_FLAGS) and sha256(folder/'result.json') == c['result_sha256'], 'Precision result changed')
    for n,h in c['produced_files_sha256'].items():
        p = (folder/n).resolve(); require(p.is_relative_to(folder) and sha256(p) == h, 'Precision evidence changed')
    require(set(c['produced_files_sha256'])=={p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()
        and p.name not in ('completion.json','pipeline.json','worker.json','supervisor.log','engine.log')},
        'Complete precision evidence population required')
    require(all(type(r[k]) is bool for k in ('original_skin_samples_passed','scene_samples_passed',
        'inherited_surface_checked','root_event_tracks_included','checked_package_available')),
        'Typed precision stage decisions required')
    require(r['inherited_surface_checked'] is (metadata['inherited_surface'] is not None)
        and r['root_event_tracks_included'] is (metadata['source']['kind']=='game'),
        'Original inherited surface/game intent required')
    require(('checked-assets.zip' in c['downloads']) is r['checked_package_available'], 'Precision package decision changed')
    authored=read(folder/'authoring/result.json');fidelity=read(folder/'fidelity.json')
    surface=read(folder/'surface/result.json') if r['inherited_surface_checked'] else None
    roots=read(folder/'tracks/result.json') if r['root_event_tracks_included'] else None
    events=read(folder/'runtime-events/result.json') if r['root_event_tracks_included'] else None
    request=read(folder/'authoring/actors-engine/request.json');times=np.asarray(request['sample_times_s'],float)
    require(np.array_equal(times,np.asarray(old_clock['sample_times_s'],float)), 'Original complete precision clock required')
    require(r['source']==read(folder/'request.json')['source'] and r['samples']==len(times)
            and r['actor_count']==len(fidelity['actors'])==len(read(folder/'prepared.json')['original_actors']),
            'Precision result source/population changed')
    with np.load(folder/'fidelity.npz',allow_pickle=False) as saved:
        expected={'times_s'}|{f'actor_{i}_{name}' for i in range(r['actor_count']) for name in ('errors_m','witnesses')}
        require(set(saved.files)==expected and np.array_equal(saved['times_s'],times),'Complete original fidelity clock/archive required')
        for i,row in enumerate(fidelity['actors']):
            errors=saved[f'actor_{i}_errors_m'];witness=saved[f'actor_{i}_witnesses']
            require(errors.shape==witness.shape==times.shape and np.isfinite(errors).all() and np.all(errors>=0)
                    and witness.dtype.kind in 'iu' and np.all((witness>=0)&(witness<row['vertices'])), 'Invalid complete fidelity population')
            require(row['samples']==len(times) and row['tolerance_m']==.0001
                    and row['maximum_position_error_m']==float(errors.max())
                    and row['samples_over_tolerance']==int(np.sum(errors>.0001))
                    and row['position_samples_passed'] is bool(np.all(errors<=.0001)), 'Original-skin precision decision differs from numeric observations')
            name=list(spec['actors'])[i]
            require(row['actor']==name and row['vertices']==sum(len(p['positions']) for p in selected[6].actors[name]['rig'].primitives)
                and row['original_skin_reference_preserved'] is True and row['imported_weights_renormalized'] is False,
                'Complete original skin reference required')
    require(fidelity['original_skin_samples_passed'] is all(a['position_samples_passed'] for a in fidelity['actors']),
        'Complete original-skin fidelity gate required')
    passed=bool(authored['sampled_conditions_pass'] and all(a['position_samples_passed'] for a in fidelity['actors'])
                and (surface is None or surface['native_and_imported_surface_contacts_pass'])
                and (roots is None or roots['all_root_samples_pass'] and events['gameplay_event_dispatch_verified']))
    require(r['original_skin_samples_passed'] is fidelity['original_skin_samples_passed']
            and r['scene_samples_passed'] is authored['sampled_conditions_pass'] and r['checked_package_available'] is passed,
            'Precision result differs from measured stage decisions')
    require(r['inherited_surface_samples_passed'] is (None if surface is None else surface['native_and_imported_surface_contacts_pass'])
            and r['root_samples_passed'] is (None if roots is None else roots['all_root_samples_pass'])
            and r['event_dispatch_verified'] is (None if events is None else events['gameplay_event_dispatch_verified']),
            'Precision inherited/game decisions differ from saved observations')
    expected_downloads={'result.json','original-assets.zip','fidelity.json','fidelity.npz'}|{
        f'actors/{i}{suffix}' for i in range(r['actor_count']) for suffix in ('.glb','.glb.weights.json')}
    if passed:expected_downloads.add('checked-assets.zip')
    require(set(c['downloads'])==expected_downloads,'Complete fixed precision downloads required')
    require(all(sha256(folder/n) == h for n,h in c['downloads'].items()), 'Precision downloads changed')
    if passed:
        packed=read(folder/'package.json')
        require(packed['source']==r['source'] and packed['original_package_sha256']==metadata['package_sha256']
                and packed['original_selected'] is True and all(packed[k] is False for k in FALSE_FLAGS),
                'Unapproved original-bound precision package required')
        with zipfile.ZipFile(folder/'checked-assets.zip') as z:
            require(set(z.namelist())==set(packed['files_sha256'])|{'package.json'}
                    and len(z.namelist())==len(packed['files_sha256'])+1
                    and z.read('package.json')==(folder/'package.json').read_bytes(), 'Complete precision ZIP population required')
            for n,h in packed['files_sha256'].items():
                require(hashlib.sha256(z.read(n)).hexdigest()==h,'Precision ZIP payload changed')
    m.update(r, result_sha256=c['result_sha256'], downloads=[dict(label=n,url=f'/files/{NAMESPACE}/{job}/{n}',sha256=h)
        for n,h in c['downloads'].items()]); return m


def listing():
    from contact_edit_job import observed_state
    return dict(jobs=[dict(id=p.name, status=observed_state(p)['status']) for p in sorted((ROOT/'reports'/NAMESPACE).glob('*'), reverse=True)
        if p.is_dir() and scenes.NAME.fullmatch(p.name) and (p/'pipeline.json').is_file()])


def served_file(relative):
    parts = Path(relative).parts
    if len(parts)<3 or parts[0]!=NAMESPACE: return None
    try:
        folder=folder_for(parts[1]);target=(ROOT/'reports'/relative).resolve()
        require(target.is_relative_to(folder), 'Precision download escapes job')
        return target if any(d['url']=='/files/'+relative for d in manifest(parts[1])['downloads']) else None
    except (ValueError,TypeError,KeyError,OSError,zipfile.BadZipFile): return None


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    run(parser.parse_args().folder)
