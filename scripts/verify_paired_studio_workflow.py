"""Real saved paired-scene retime/trim jobs, offline routes and shared Godot playback."""
import argparse
from pathlib import Path
import shutil
from types import SimpleNamespace
import numpy as np
from strep import ROOT, read, save, sha256, now
from action_studio_server import Handler, allowed_file
from scene_trim_job import JOBS, metadata, prepare, run as edit
from study_scene_runtime import verify
from probe_godot_render import run_engine


def run(collection, output, existing_retime=None):
    collection, output = Path(collection).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Preserve earlier workflow evidence')
    provenance = read(collection/'provenance.json')
    if read(collection/'pipeline.json')['status'] != 'complete':
        raise ValueError('Completed paired review required')
    for name, digest in provenance['files'].items():
        if sha256(collection/name) != digest:
            raise ValueError('Published review changed')
    output.mkdir(); implementation = output/'implementation'; implementation.mkdir()
    for name in ['verify_paired_studio_workflow.py', 'study_scene_runtime.py', 'godot_scene_clock.gd', 'godot_scene_clock_audit.gd']:
        shutil.copyfile(ROOT/'scripts'/name, implementation/name)
    name = collection.relative_to(ROOT/'reports').as_posix()
    observed = []
    # Invoke the same request handler without opening a socket or browser.
    handler = SimpleNamespace(headers={'Host': '127.0.0.1:8768'}, server=SimpleNamespace(allowed_hosts={'127.0.0.1:8768'}),
                              path='/api/scene-collections', respond=lambda status, value: observed.append((status, value)))
    Handler.do_GET(handler)
    if observed[0][0] != 200 or name not in observed[0][1]['collections']:
        raise ValueError('Pair is not discoverable through the Studio collection handler')
    routes = 0
    for row in read(collection/'manifest.json')['scenes']:
        for relative in [*row['variants'].values(), *[d['path'] for d in row['downloads']]]:
            expected = collection/relative
            if allowed_file('/files/'+name+'/'+relative) != expected or not expected.is_file():
                raise ValueError('Published scene route is unavailable')
            routes += 1
    cases = []
    for variant in ['source', 'candidate']:
        folder = collection/variant/'portable'; data = read(folder/'scene-runtime.json')
        cases.append(dict(id=variant, folder=str(folder), frames=data['frames'], metadata_sha256=sha256(folder/'scene-runtime.json')))
    # Execute the production jobs, preserving their input snapshots and generated artifacts.
    url = '/files/'+name+'/candidate.json'; jobs = []
    for operation in ['retime', 'trim']:
        info = metadata(url); folder = JOBS/(output.name+'-'+operation)
        payload = dict(source_url=url, revision=info['revision'], label='Paired correction · '+operation)
        if operation == 'retime':
            payload.update(operation='retime', frames=225)
        else:
            payload.update(first=50, last=160)
        if operation == 'retime' and existing_retime is not None:
            folder = Path(existing_retime).resolve()
            if folder.parent != JOBS.resolve() or read(folder/'pipeline.json')['status'] != 'complete':
                raise ValueError('Only a completed exact saved timing job can be reused')
            saved = read(folder/'request.json')
            if saved['authored'] != payload:
                raise ValueError('Completed retime belongs to a different request')
            for relative, digest in saved['files'].items():
                if sha256(folder/relative) != digest:
                    raise ValueError('Completed retime input snapshot changed')
        else:
            prepare(payload, folder); edit(folder)
        if read(folder/'pipeline.json')['status'] != 'complete':
            raise ValueError('Saved-scene editing job failed')
        target = folder/('retimed' if operation == 'retime' else 'trimmed'); data = read(target/'scene-runtime.json')
        cases.append(dict(id=operation, folder=str(target), frames=data['frames'], metadata_sha256=sha256(target/'scene-runtime.json')))
        item = next(s for s in read(folder/'manifest.json')['scenes'] if s['id'] == 'candidate')
        published = (folder/item['variants']['palm']).resolve()
        if not published.is_relative_to(folder) or published.suffix != '.json':
            raise ValueError('Published scene escapes job')
        url = '/files/'+published.relative_to(ROOT/'reports').as_posix()
        jobs.append(dict(operation=operation, folder=str(folder), request_sha256=sha256(folder/'request.json'), output_bundle=str(published), output_bundle_sha256=sha256(published)))
    original = read(collection/'candidate.json')['scene']; trimmed = read(jobs[-1]['output_bundle'])['scene']
    if original['actors']['A']['transform'] != trimmed['actors']['A']['transform'] or original['actors']['B']['transform'] != trimmed['actors']['B']['transform']:
        raise ValueError('Shared scene placement changed through timing edits')
    # Both original hand contacts describe the same event; exact endpoints must
    # survive retime then trim independently of the native integer enclosure.
    precise = read(Path(cases[-1]['folder'])/'retime-contact-windows.json')['windows']
    for contact in original['contacts']:
        row = next(r for r in precise if r['id'] == contact['id'])
        np.testing.assert_allclose(row['exact_output_frames'], np.array([contact['start_frame'], contact['end_frame']])*(224/149)-50, atol=1e-10, rtol=0)
    project = output/'project'; project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep paired authoring workflow"\n', encoding='utf8')
    for name in ['godot_scene_clock.gd', 'godot_scene_clock_audit.gd']:
        shutil.copyfile(ROOT/'scripts'/name, project/name)
    engine = ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    if sha256(engine) != read(engine.parent/'acquisition.json')['executables'][engine.name]:
        raise ValueError('Engine identity changed')
    command = [str(engine), '--headless', '--path', str(project), '--fixed-fps', '60', '--script', 'godot_scene_clock_audit.gd', '--', str(output/'request.json'), str(output/'engine-output.json')]
    request = dict(at=now(), cases=cases, controls=[], command=command, engine_sha256=sha256(engine),
                   implementation={p.name: sha256(p) for p in implementation.iterdir()}, quality_approved=False)
    save(output/'request.json', request)
    run_engine(command, output/'engine.log', timeout=180)
    passed, checks = verify(request, read(output/'engine-output.json'), output)
    for name, digest in provenance['files'].items():
        if sha256(collection/name) != digest:
            raise ValueError('Original published pair changed during edits')
    save(output/'workflow.json', dict(at=now(), passed=passed, collection=str(collection), routed_files=routes,
        collection_handler_verified=True, jobs=jobs, exact_contact_windows=precise, shared_actor_placements_preserved=True,
        engine_verification_sha256=sha256(output/'verification.json'), quality_approved=False,
        scope='Direct Studio handler invocation, actual saved-scene production workers, retained source assets and exact event mapping, four paired versions under shared Godot playback. No HTTP, rendered/browser or human review; prior collision proof is not re-used as a quality approval for retimed/trimmed motion.'))
    print(dict(passed=passed, routed_files=routes, engine_cases=len(checks), pose_observations=sum(c['pose_observations'] for c in checks)), flush=True)
    if not passed:
        raise ValueError('Shared engine playback failed')


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('collection', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--existing-retime', type=Path); a = p.parse_args()
    with threadpool_limits(limits=1):
        run(a.collection, a.output, a.existing_retime)
