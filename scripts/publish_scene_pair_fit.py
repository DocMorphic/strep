"""Publish verified scene-derived paired exports, or retain the uncorrected source."""
import copy
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now


def reviewed_variants(folder):
    folder = Path(folder); fit = folder/'fit'; result = read(fit/'result.json')
    if result['status'] != 'complete' or result['request_sha256'] != sha256(fit/'request.json'):
        raise ValueError('Completed bound fitting result required')
    proof = read(folder/'replay/verification.json'); protocol = read(folder/'replay/request.json')
    if proof['request_sha256'] != sha256(folder/'replay/request.json') or protocol['study_result_sha256'] != sha256(fit/'result.json') or protocol['study_request_sha256'] != sha256(fit/'request.json'):
        raise ValueError('Matching independent replay required')
    manifest = read(fit/'manifest.json')
    if result['manifest_sha256'] != sha256(fit/'manifest.json'): raise ValueError('Fit manifest changed')
    if result['source_index_sha256'] != sha256(fit/'source-index.json'): raise ValueError('Source geometry index changed')
    for name, digest in read(fit/'source-index.json').items():
        path = (fit/'source'/name).resolve()
        if not path.is_relative_to((fit/'source').resolve()) or sha256(path) != digest:
            raise ValueError('Source geometry changed')
    engine = read(folder/'engine/verification.json')['checks']; records = []
    prepared = read(folder/'request.json'); actors = list(prepared['actors'])
    versions = [('source', 'input')]+([('candidate', result['selected'])] if result['selected'] else [])
    if len(manifest['cases']) != len(versions)*len(actors): raise ValueError('Unexpected exported clip population')
    for version, label in versions:
        paths = {}
        for name in actors:
            entries = [c for c in manifest['cases'] if c['id'] == label+'-'+name]
            if len(entries) != 1: raise ValueError('Missing distinct actor export')
            case = entries[0]; path = (fit/case['path']).resolve()
            if not path.is_relative_to(fit.resolve()) or sha256(path) != case['sha256']: raise ValueError('Export changed')
            checks = [c for c in engine if c['id'] == case['id']]
            if len(checks) != 1: raise ValueError('Missing distinct engine observation')
            check = checks[0]
            if check['source_sha256'] != case['sha256'] or check['frames'] != case['frames'] or check['bones'] != 77 or check['imported_skinned_surfaces'] < 1 or max(check['max_position_error_m'], check['max_basis_element_error']) > 1e-4:
                raise ValueError('Actor engine import not verified')
            if version == 'source' and case['sha256'] != prepared['actors'][name]['sha256']:
                raise ValueError('Published source differs from immutable input')
            paths[name] = path
        records.append((version, paths))
    if result['selected']:
        trials = read(fit/'trials.json')
        if result['trials_sha256'] != sha256(fit/'trials.json'): raise ValueError('Trial report changed')
        selected = [t for t in trials if t['folder'] == result['selected']]
        if len(selected) != 1 or not selected[0]['accepted_local_step'] or selected[0]['reasons'] or not selected[0]['geometry']:
            raise ValueError('No accepted exported local step')
        reviewed = [r for r in proof['trials'] if r['folder'] == result['selected']]
        if len(reviewed) != 1 or any(a['rates']['failures'] for a in reviewed[0]['actors']):
            raise ValueError('Selected export has no passing independent motion replay')
        trial = selected[0]
        if set(a['actor'] for a in trial['actors']) != set(actors) or set(a['actor'] for a in reviewed[0]['actors']) != set(actors):
            raise ValueError('Replay participants differ')
        from scene_angular_publication import require_angular_replay
        require_angular_replay(folder, result, trial, prepared)
        candidate_paths = dict(records)['candidate']
        for actor in trial['actors']:
            if sha256(candidate_paths[actor['actor']]) != actor['sha256']:
                raise ValueError('Published candidate differs from reviewed trial')
        geometry_path = fit/result['selected']/'geometry.json'
        if sha256(geometry_path) != trial['geometry']['geometry_sha256']:
            raise ValueError('Candidate geometry changed')
    return records, result


def publish(folder):
    import numpy as np
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from retime_scene import native_motion
    from scene_region_job import bundle
    from scene_constraints import evaluate
    from floor_contact import Surface
    from build_soma_preview import ASSET
    folder = Path(folder).resolve(); versions, result = reviewed_variants(folder); job = read(folder/'job.json')
    if sha256(folder/'request.json') != job['prepared_request_sha256']: raise ValueError('Prepared publication source changed')
    prepared = read(folder/'request.json')
    if sha256(folder/'input/scene.json') != prepared['scene_snapshot']['sha256']: raise ValueError('Original scene snapshot changed')
    if sha256(ASSET) != job['asset_sha256']: raise ValueError('Review skin changed')
    for name, digest in job['files'].items():
        if sha256(folder/name) != digest: raise ValueError('Review metadata changed')
    output = ROOT/'reports/scene-region-jobs'/('paired-'+folder.name)
    if output.exists(): raise ValueError('Preserve earlier paired publication')
    output.mkdir(parents=True); source = read(folder/'input/scene.json')['scene']; frames = source['frame_count']
    skin = dict(np.load(ASSET, allow_pickle=False)); surface = Surface(skin); scenes = []; evidence = []
    samples = [read(folder/'fit/source'/name) for name in read(folder/'fit/source-index.json')]
    source_depths = [max(d['maximum_depth_m'] for d in s['directions']) for s in samples]
    for version, paths in versions:
        scene = copy.deepcopy(source); scene['id'] = version; target = output/version; target.mkdir()
        for index, (name, actor) in enumerate(scene['actors'].items()):
            sub = target/str(index); sub.mkdir(); glb = sub/'actor.glb'; shutil.copyfile(paths[name], glb)
            rig = RigAsset.load(glb); sampler = AnimationSampler(rig.document, rig.binary, 0)
            with np.load(folder/job['native'][name], allow_pickle=False) as saved:
                native = dict(saved)
            motion = native_motion(native, rig.document, rig.binary, frames, frames); maximum = 0.
            for frame in range(frames):
                expected = rig.vertices(sampler.sample(frame/30))
                found = surface.vertices(motion['global_rot_mats'][frame], motion['posed_joints'][frame])
                np.testing.assert_allclose(found, expected, atol=2e-6, rtol=0)
                maximum = max(maximum, float(np.abs(found-expected).max()))
            np.savez_compressed(sub/'motion.npz', **motion)
            actor.update(motion=(sub/'motion.npz').relative_to(ROOT).as_posix(), source_sha256=sha256(sub/'motion.npz'),
                         preview_glb=glb.relative_to(output).as_posix())
            evidence.append(dict(version=version, actor=name, copied_glb_sha256=sha256(glb), source_glb_sha256=sha256(paths[name]),
                native_sha256=sha256(sub/'motion.npz'), full_skin_maximum_error_m=maximum, frames=frames))
        data = bundle(scene, evaluate(scene, skin), skin)
        if version == 'candidate':
            rows = read(folder/'fit'/result['selected']/'geometry.json'); depths = [r['candidate_depth_m'] for r in rows]
        else: depths = source_depths
        times = [s['time_s']*30 for s in samples]
        data['partner'] = dict(tolerance_m=.005, frames_checked=times, pairs=[dict(actors=list(paths),
            frames=[dict(frame=t, max_depth_m=d) for t, d in zip(times, depths)], max_depth_m=max(depths),
            frames_over_tolerance=sum(d > .005 for d in depths))], quality_approved=False)
        data['quality_approved'] = False
        data['motion_provenance'] = 'Exact exported GLB transforms; foot-contact estimates inherited from the input. No new contact detection or quality approval.'
        for filename in ['events.json', 'retime-contact-windows.json']:
            original = folder/'review-input'/filename
            if original.exists(): shutil.copyfile(original, target/filename)
        if (target/'events.json').exists(): data['events_file'] = version+'/events.json'
        save(output/(version+'.json'), data)
        note = ('Local correction accepted. ' if version == 'candidate' else 'Original retained. ')+f'{sum(d > .005 for d in depths)}/{len(depths)} local sampled times exceed 5 mm. Full-clip collisions, floor quality and human review remain unresolved.'
        if result['selected'] is None: note = 'No correction passed the local fitting checks. '+note
        scenes.append(dict(id=version, label=job['label']+' · '+('After' if version == 'candidate' else 'Before'),
            variants=dict(palm=version+'.json'), review_note=note, downloads=[dict(label='Actor '+name+' GLB', path=scene['actors'][name]['preview_glb']) for name in paths]))
    shutil.copyfile(folder/'review-input/SOMA-LICENSE.txt', output/'SOMA-preview-LICENSE.txt')
    # Bind all final exports, geometry and review metadata again before discovery.
    reviewed_variants(folder)
    for name, digest in job['files'].items():
        if sha256(folder/name) != digest: raise ValueError('Review metadata changed during publication')
    save(output/'manifest.json', dict(scenes=scenes, quality_approved=False))
    save(output/'provenance.json', dict(at=now(), fit_result_sha256=sha256(folder/'fit/result.json'),
        replay_sha256=sha256(folder/'replay/verification.json'), engine_sha256=sha256(folder/'engine/verification.json'), records=evidence,
        angular_replay_sha256=sha256(folder/'angular-replay/verification.json') if result['selected'] else None,
        files={p.relative_to(output).as_posix(): sha256(p) for p in output.rglob('*') if p.is_file()}, quality_approved=False))
    save(output/'pipeline.json', dict(status='complete', stage='Paired correction comparison', quality_approved=False))
    return output.relative_to(ROOT/'reports').as_posix()
