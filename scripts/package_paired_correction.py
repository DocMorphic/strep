"""Publish bound paired GLB corrections as editable Studio scenes and runtime ZIPs."""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from strep import ROOT, read, save, sha256, now
from gltf_tools import read_glb
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from retime_scene import native_motion
from scene_constraints import evaluate
from scene_region_job import JOBS, bundle
from scene_runtime import package
from build_soma_preview import ASSET
from floor_contact import Surface
from paired_review_summary import partner_summary


def verified_variant(study, geometry, engine, scene_path):
    study, geometry, engine, scene_path = [Path(p).resolve() for p in (study, geometry, engine, scene_path)]
    request, result = read(study/'request.json'), read(study/'result.json')
    gr, gp = read(geometry/'verification.json'), read(geometry/'request.json')
    if result['status'] != 'complete' or result['selected'] is None or result['request_sha256'] != sha256(study/'request.json'):
        raise ValueError('Completed bound pair required')
    if gr['request_sha256'] != sha256(geometry/'request.json') or gr['samples_sha256'] != sha256(geometry/'samples.json') or gr['fresh_directional_queries'] != 2*gr['samples']:
        raise ValueError('Completed bound geometry audit required')
    if gp['inputs'].get(str(scene_path)) != sha256(scene_path):
        raise ValueError('Geometry placement is for another scene')
    engine_path = engine/'verification.json'
    if gp['inputs'].get(str(engine_path)) != sha256(engine_path):
        raise ValueError('Geometry and engine evidence differ')
    selected = {r['actor']: r for r in result['selected']['actors']}
    if set(selected) != {'A', 'B'}:
        raise ValueError('Two distinct reviewed actors required')
    actors = {}; frames = read(scene_path)['scene']['frame_count']
    for actor, row in selected.items():
        path = study/'candidate'/(actor+'.glb'); digest = sha256(path)
        if digest != row['sha256'] or gp['inputs'].get(str(path)) != digest:
            raise ValueError('Geometry belongs to another actor export')
        checks = [c for c in read(engine_path)['checks'] if c['id'] == 'candidate-'+actor]
        if len(checks) != 1 or checks[0]['source_sha256'] != digest or checks[0]['frames'] != frames or checks[0]['bones'] != 77 or checks[0]['imported_skinned_surfaces'] < 1 or max(checks[0]['max_position_error_m'], checks[0]['max_basis_element_error']) > 1e-4:
            raise ValueError('Matching all-frame skinned engine evidence required')
        actors[actor] = path
    rows = read(geometry/'samples.json')['rows']
    if len(rows) != gr['samples'] or [r['frame'] for r in rows] != gp['frames']:
        raise ValueError('Geometry population differs')
    summary = partner_summary(rows)
    if summary['pairs'][0]['max_depth_m'] != gr['candidate_peak_m'] or summary['pairs'][0]['frames_over_tolerance'] != gr['candidate_screen_failures']:
        raise ValueError('Geometry summary differs from samples')
    inputs = {**request['inputs'], **gp['inputs']}
    for p in [study/'request.json', study/'result.json', geometry/'request.json', geometry/'verification.json', geometry/'samples.json', engine_path, *actors.values()]:
        inputs[str(p)] = sha256(p)
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Reviewed input changed')
    return actors, summary, inputs


def build(scene_path, before, after, output, label):
    scene_path, output = Path(scene_path).resolve(), Path(output).resolve()
    if output.parent != JOBS.resolve() or output.exists():
        raise ValueError('Fresh scene-region-jobs collection required')
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 100:
        raise ValueError('Comparison label required')
    source = read(scene_path)['scene']
    if source['fps'] != 30 or set(source['actors']) != {'A', 'B'} or source['objects']:
        raise ValueError('Current publisher supports actor-only A/B SOMA scenes')
    prepared = [verified_variant(*paths, scene_path) for paths in [before, after]]
    inputs = {str(scene_path): sha256(scene_path), str(ASSET): sha256(ASSET)}
    for _, _, files in prepared:
        inputs.update(files)
    native = {}
    for actor, entry in source['actors'].items():
        path = ROOT/entry['motion']
        if sha256(path) != entry['source_sha256']:
            raise ValueError('Original native metadata changed')
        inputs[str(path)] = sha256(path)
        with np.load(path, allow_pickle=False) as saved:
            native[actor] = dict(saved)
    output.mkdir(parents=True); methods = output/'implementation'; methods.mkdir()
    names = ['package_paired_correction.py', 'paired_review_summary.py', 'retime_scene.py', 'scene_runtime.py', 'scene_region_job.py',
             'scene_constraints.py', 'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'inspect_motion.py', 'floor_contact.py']
    for name in names:
        shutil.copyfile(ROOT/'scripts'/name, methods/name)
    with np.load(ASSET, allow_pickle=False) as saved:
        skin = dict(saved)
    surface = Surface(skin); records = []; scenes = []
    for version, (paths, (actors, partner, _)) in zip(['source', 'candidate'], zip([before, after], prepared)):
        folder = output/version; folder.mkdir(); scene = copy.deepcopy(source); scene['id'] = version
        for actor, path in actors.items():
            target = folder/actor; target.mkdir(); glb = target/'actor.glb'; shutil.copyfile(path, glb)
            doc, binary = read_glb(glb); motion = native_motion(native[actor], doc, binary, source['frame_count'], source['frame_count'])
            np.testing.assert_array_equal(motion['foot_contacts'], native[actor]['foot_contacts'])
            # Validate canonical native skin reconstruction against the actual GLB,
            # rather than merely assuming compatible joint names imply the same mesh.
            rig = RigAsset.load(glb); sampler = AnimationSampler(doc, binary, 0); maximum = 0.
            for frame in range(source['frame_count']):
                points = surface.vertices(motion['global_rot_mats'][frame], motion['posed_joints'][frame])
                expected = rig.vertices(sampler.sample(frame/30))
                np.testing.assert_allclose(points, expected, atol=2e-6, rtol=0)
                maximum = max(maximum, float(np.abs(points-expected).max()))
            np.savez_compressed(target/'motion.npz', **motion)
            scene['actors'][actor].update(motion=(target/'motion.npz').relative_to(ROOT).as_posix(), source_sha256=sha256(target/'motion.npz'),
                                          preview_glb=version+'/'+actor+'/actor.glb')
            records.append(dict(version=version, actor=actor, source_glb_sha256=sha256(path), copied_glb_sha256=sha256(glb),
                                native_sha256=sha256(target/'motion.npz'), frames=source['frame_count'], full_skin_maximum_error_m=maximum))
        data = bundle(scene, evaluate(scene, skin), skin); data['partner'] = partner
        data['quality_approved'] = False
        data['motion_provenance'] = 'Body and authored finger transforms decoded from the exact reviewed GLBs. Foot-contact channels inherited as model predictions, not new stance labels.'
        save(output/(version+'.json'), data)
        for name in ['samples.json', 'verification.json']:
            shutil.copyfile(Path(paths[1])/name, folder/('geometry-'+name))
        shutil.copyfile(Path(paths[2])/'verification.json', folder/'engine-verification.json')
        package(output/(version+'.json'), folder/'portable')
        peak = partner['pairs'][0]['max_depth_m']; failures = partner['pairs'][0]['frames_over_tolerance']
        note = f'{failures}/{len(partner["frames_checked"])} sampled times exceed 5 mm; peak {peak*1000:.3f} mm. Geometry covers frames {partner["frames_checked"][0]:g}–{partner["frames_checked"][-1]:g}, not the whole clip. Contact/floor defects and developer review remain unresolved. No quality approval.'
        scenes.append(dict(id=version, label=label+' · '+('Before' if version == 'source' else 'After'), variants=dict(palm=version+'.json'), review_note=note,
            downloads=[dict(label='Paired scene + Godot playback', path=version+'/portable/scene-runtime.zip'),
                       dict(label='Geometry samples', path=version+'/geometry-samples.json'),
                       *[dict(label='Actor '+actor+' GLB', path=version+'/'+actor+'/actor.glb') for actor in actors]]))
    shutil.copyfile(ROOT/'vendor/kimodo/LICENSE', output/'SOMA-preview-LICENSE.txt')
    save(output/'manifest.json', dict(scenes=scenes, quality_approved=False, review_mode='non_blind_developer'))
    for path, digest in inputs.items():
        if sha256(path) != digest:
            raise ValueError('Source changed during publication')
    save(output/'provenance.json', dict(at=now(), inputs=inputs, records=records,
        implementation={n: sha256(methods/n) for n in names}, files={p.relative_to(output).as_posix(): sha256(p) for p in sorted(output.rglob('*')) if p.is_file()},
        quality_approved=False, scope='Exact reviewed GLB copies, native reconstruction for continued authoring, preserved actor placements/contact intent, partial-interval collision evidence, portable finite playback. Not new generation or human review.'))
    save(output/'pipeline.json', dict(status='complete', stage='Paired correction ready for developer review and timing edits', quality_approved=False))
    print(dict(collection=output.relative_to(ROOT/'reports').as_posix(), actor_frames=sum(r['frames'] for r in records), maximum_native_skin_error_m=max(r['full_skin_maximum_error_m'] for r in records)), flush=True)


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['scene', 'before_study', 'before_geometry', 'before_engine', 'after_study', 'after_geometry', 'after_engine', 'output']:
        p.add_argument(name, type=Path)
    p.add_argument('--label', required=True); a = p.parse_args()
    with threadpool_limits(limits=1):
        build(a.scene, [a.before_study, a.before_geometry, a.before_engine], [a.after_study, a.after_geometry, a.after_engine], a.output, a.label)
