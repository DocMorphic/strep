"""Portable candidate assets and explicit, bounded reserve-fit history."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

import native_transition_contact_fit as workflow
from strep import read, sha256

SCHEMA = 'strep-native-transition-contact-package-v1'
require = workflow.require


def materials(folder, result):
    folder = Path(folder).resolve()
    paths = {}
    def add(name, relative):
        require(not PurePosixPath(name).is_absolute() and all(p not in ('', '.', '..') for p in name.split('/')),
                'Contained package member required')
        path = (folder / relative).resolve()
        require(path.is_relative_to(folder) and path.is_file() and name not in paths, 'Existing distinct package file required')
        paths[name] = path
    for name in ('request.json', 'recipe.json', 'prepared.json', 'reserve-binding.json',
                 'source-rate-caps.npz', 'optimization.json', 'result.json', 'completion.json'):
        add('history/' + name, name)
    if read(folder / 'prepared.json')['seed_sha256'] is not None:
        add('history/seed.json', 'seed.json')
    for name in result['candidate_files_sha256']:
        add('candidate/' + name, 'candidate/' + name)
    for name in result['probe_files_sha256']:
        add('history/probes/' + name, 'probes/' + name)
    for name in workflow.METHODS:
        add('history/implementation/' + name, 'implementation/' + name)
    original = folder / 'original-transition'
    prepared = read(original / 'prepared.json')
    declared = {'recipe.json', 'prepared.json', 'result.json'} | set(read(original / 'result.json')['files_sha256'])
    declared |= {v['path'] for v in prepared['inputs'].values()}
    declared |= {'implementation/' + n for n in prepared['implementation_sha256']}
    for name in declared:
        add('history/original-transition/' + name, 'original-transition/' + name)
    require(len(paths) <= 4096 and sum(p.stat().st_size for p in paths.values()) <= 768 * 1024**2,
            'Complete selected package exceeds its budget; no truncation')
    return paths


def record(folder, result, paths):
    return dict(schema=SCHEMA, result_sha256=sha256(Path(folder) / 'result.json'),
                files_sha256={n: sha256(p) for n, p in sorted(paths.items())},
                checks=result['checks'], all_declared_samples_pass=result['all_declared_samples_pass'],
                reserve_binding=result['binding'], original_selected=True,
                original_clip_libraries_included=True, raw_optimizer_probes_included=True,
                original_rate_caps_and_permissions_included=True, unconfirmed_tracks_included=True,
                complete_external_source_graph_included=False, standalone_solver_reproduction=False,
                root_application_mode='reference-only-motion-remains-embedded',
                engine_playback_verified=False, quality_approved=False, training_admitted=False, release_approved=False,
                scope='Self-contained candidate GLBs/scene/native tracks with selected source/history snapshots. '
                      'Historical absolute input references are provenance only; external parent graphs and runtime dependencies '
                      'are not bundled. Native geometry failures remain binding; no approval or event dispatch.')


def build(folder, output, *, validated=None):
    folder, output = Path(folder).resolve(), Path(output).resolve()
    require(not output.exists() and not output.is_relative_to(folder), 'Fresh separate candidate ZIP required')
    result = workflow.verify(folder) if validated is None else validated
    require(workflow.equal(read(folder / 'result.json'), result), 'Selected verified result changed')
    paths = materials(folder, result)
    manifest = record(folder, result, paths)
    output.parent.mkdir(parents=True, exist_ok=True)
    scratch = output.with_suffix(output.suffix + '.tmp')
    require(not scratch.exists(), 'Fresh package scratch path required')
    try:
        with zipfile.ZipFile(scratch, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, path in sorted(paths.items()):
                with path.open('rb') as source, archive.open(name, 'w') as target:
                    while chunk := source.read(8 * 1024**2):
                        target.write(chunk)
            archive.writestr('package.json', json.dumps(manifest, indent=2, allow_nan=False) + '\n')
        verify(folder, scratch, validated=result)
        scratch.replace(output)
        return manifest
    except Exception:
        if scratch.exists(): scratch.unlink()
        raise


def verify(folder, archive, *, validated=None):
    result = workflow.verify(folder) if validated is None else validated
    paths = materials(folder, result)
    expected = record(folder, result, paths)
    with zipfile.ZipFile(archive) as package:
        require(len(package.namelist()) == len(paths) + 1
                and set(package.namelist()) == set(paths) | {'package.json'}, 'Complete exact package population required')
        require(package.getinfo('package.json').file_size <= 4 * 1024**2
                and all(package.getinfo(n).file_size == p.stat().st_size for n, p in paths.items()),
                'Exact bounded uncompressed package sizes required')
        require(workflow.equal(json.loads(package.read('package.json')), expected), 'Candidate package decisions changed')
        for name, path in paths.items():
            digest = hashlib.sha256()
            with package.open(name) as member:
                while chunk := member.read(8 * 1024**2): digest.update(chunk)
            require(digest.hexdigest() == sha256(path) == expected['files_sha256'][name], 'Candidate package payload changed')
    require(all(sha256(p) == expected['files_sha256'][n] for n, p in paths.items()), 'Inputs changed during package replay')
    return expected
