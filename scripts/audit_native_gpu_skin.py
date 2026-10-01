"""Verify imported native skin data and GPU silhouettes against original CPU skin."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from probe_godot_render import engine_command, run_engine, project_file
from audit_godot_gpu_skin import masks
from imported_skin_evidence import compare_surface


def run(engine_audit, output):
    engine_audit, output = Path(engine_audit).resolve(), Path(output).resolve()
    if output.exists() or output.parent != ROOT/'reports': raise ValueError('Fresh immediate reports folder required')
    eq, er = read(engine_audit/'request.json'), read(engine_audit/'result.json')
    if er['status'] != 'complete' or not eq['native_tracks']: raise ValueError('Completed native-resource audit required; strict clock failure remains separate')
    files = dict(eq['inputs'])
    for name, digest in er['outputs'].items():
        path = (engine_audit/name).resolve()
        if not path.is_relative_to(engine_audit): raise ValueError('Escaping evidence path')
        if str(path) in files and files[str(path)] != digest: raise ValueError('Conflicting evidence')
        files[str(path)] = digest
    files[str(engine_audit/'result.json')] = sha256(engine_audit/'result.json')
    def bound(path):
        path = Path(path).resolve()
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound GPU input')
        return read(path)
    def unchanged():
        for path, digest in files.items():
            if sha256(path) != digest: raise ValueError('Changed GPU evidence')
    unchanged()
    intent = bound(Path(eq['study'])/'request.json'); pose = intent; seen = set()
    while 'baseline' not in pose:
        path = Path(pose['source'])/'request.json'
        if path in seen or len(seen) >= 32: raise ValueError('Invalid provenance chain')
        seen.add(path); pose = bound(path)
    region = bound(Path(pose['source'])/'request.json'); prepared = bound(Path(region['prepared'])/'request.json')
    if list(prepared['actors']) != ['A','B'] or len(eq['cases']) != 2: raise ValueError('Matched A/B development fixture required')
    cases, rigs = [], []
    output.mkdir(); project = output/'project'; project.mkdir(); project_file(project/'project.godot')
    archive = output/'implementation'; archive.mkdir()
    method_names = ('audit_native_gpu_skin.py','native_gpu_skin_audit.gd','imported_skin_evidence.py','audit_godot_gpu_skin.py',
                    'probe_godot_render.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','strep.py')
    methods = {ROOT/'scripts'/n:sha256(ROOT/'scripts'/n) for n in method_names}
    for path, digest in methods.items():
        target = archive/path.name; shutil.copyfile(path,target); files[str(target)] = digest
    shutil.copyfile(archive/'native_gpu_skin_audit.gd',project/'native_gpu_skin_audit.gd')
    for i, actor in enumerate(('A','B')):
        path = Path(eq['cases'][i]['path']); animation = engine_audit/f'actor-{i}-animation.res'
        if any(files.get(str(p)) != sha256(p) for p in (path,animation)): raise ValueError('Unbound native asset')
        rig = RigAsset.load(path); sampler = AnimationSampler(rig.document,rig.binary,0)
        if len(rig.primitives) != 1 or rig.primitives[0]['joints'] is None: raise ValueError('GPU fixture requires one skinned primitive')
        primitive = rig.primitives[0]; mesh = rig.document['meshes'][rig.document['nodes'][primitive['node']]['mesh']]['primitives'][primitive['primitive']]
        indices = array(rig.document,rig.binary,mesh['indices']).astype(int).tolist()
        placement = prepared['actors'][actor]['placement']; rotation = Rotation.from_quat(placement['rotation_xyzw']).as_matrix()
        translation = np.asarray(placement['translation_m']); vertex = intent['selected_contact']['effector' if i == 0 else 'target']['surface_vertex']
        times = [0.,1.1897090673446655,intent['window_s'][0],intent['event_time_s']-.05,intent['event_time_s'],intent['event_time_s']+.05,sampler.duration]
        samples = []
        for index, time in enumerate(times):
            points = rig.vertices(sampler.sample(time))@rotation.T+translation; lo,hi = points.min(axis=0),points.max(axis=0)
            samples.append(dict(index=index,time_s=time,is_event=time == intent['event_time_s'],vertices=points.tolist(),
                body_center=((lo+hi)/2).tolist(),body_size=float(np.linalg.norm(hi-lo)*1.2),hand_center=points[vertex].tolist()))
        reference = output/f'actor-{i}-reference.json'; save(reference,dict(samples=samples,indices=indices)); files[str(reference)] = sha256(reference)
        cases.append(dict(id=f'actor-{i}',path=str(path),animation=str(animation),reference=str(reference),placement=placement))
        names = [rig.document['nodes'][j]['name'] for j in rig.joints]
        weights = np.zeros((len(primitive['positions']),len(names)))
        for column in range(primitive['joints'].shape[1]): np.add.at(weights,(np.arange(len(weights)),primitive['joints'][:,column]),primitive['weights'][:,column])
        rigs.append((rig,names,weights))
    limits = dict(minimum_pixels=500,minimum_iou=.995,maximum_boundary_distance_pixels=1.5,
                  rest_position_tolerance_m=1e-6,bind_matrix_tolerance=1e-5,weight_tolerance=1/65535+1e-7)
    save(output/'request.json',dict(at=now(),inputs=files,engine_audit=str(engine_audit),cases=cases,
        views=[[0,.15,1],[1,.15,0],[1,.25,1]],limits=limits,
        scope='Two native actor assets, seven fixed times and three views, full body and 30 cm hand crop. Event-only hand negative controls shift the forearm inverse bind by 5 cm. Solid double-sided GPU silhouettes, not animation-quality or contact certification.'))
    save(output/'pipeline.json',dict(status='rendering'))
    try:
        run_engine(engine_command('native_gpu_skin_audit.gd',project,output/'request.json',output),output/'engine.log',timeout=300)
        observed = read(output/'engine-output.json')
        if not observed['adapter'] or observed['driver'] != 'opengl3' or len(observed['cases']) != 2: raise ValueError('Unexpected graphics backend/population')
        checks, skin_checks = [], []
        for case, actual, (rig,names,weights) in zip(cases,observed['cases'],rigs):
            if case['id'] != actual['id'] or len(actual['records']) != 45 or len(actual['surfaces']) != 1: raise ValueError('Incomplete GPU/skin population')
            skin_checks.append(dict(actor=case['id'],**compare_surface(rig.primitives[0]['positions'],weights,names,rig.inverse,actual['surfaces'][0])))
            expected = {(s,f,v,False) for s in range(7) for f in ('body','hand') for v in range(3)} | {(4,'hand',v,True) for v in range(3)}
            found = {(r['sample'],r['framing'],r['view'],r['broken']) for r in actual['records']}
            if found != expected: raise ValueError('Missing/duplicate GPU comparisons')
            for row in actual['records']:
                prefix = row['prefix']
                if '/' in prefix or '\\' in prefix or not prefix.startswith(case['id']+'-'): raise ValueError('Invalid image path')
                metric = masks(output/(prefix+'-gpu.png'),output/(prefix+'-reference.png'))
                passed = min(metric['gpu_pixels'],metric['reference_pixels']) >= limits['minimum_pixels'] and metric['intersection_over_union'] >= limits['minimum_iou'] and metric['maximum_silhouette_distance_pixels'] <= limits['maximum_boundary_distance_pixels'] and (row['framing']=='hand' or not metric['clipped_at_border'])
                checks.append(dict(actor=case['id'],**row,**metric,passed=bool(passed)))
        positives = [c for c in checks if not c['broken']]; negatives = [c for c in checks if c['broken']]
        passed = all(c['passed'] for c in positives) and all(not c['passed'] and c['changed_binds'] > 0 for c in negatives) and all(c['passed'] and c['influences']==8 for c in skin_checks)
        unchanged()
        if any(sha256(path) != digest for path,digest in methods.items()): raise ValueError('GPU method changed during run')
        save(output/'verification.json',dict(at=now(),passed=bool(passed),checks=checks,skin_checks=skin_checks,
            positive_comparisons=len(positives),negative_controls=len(negatives),gpu_skin_scope='Only declared sampled, finite-resolution silhouettes on the recorded OpenGL backend. Hand framing intentionally crops the body. No continuous 3D vertex/contact/collision or human-quality guarantee.',
            engine_clock_failure_unchanged=True,quality_approved=False,selected_for_studio=False))
        save(output/'result.json',dict(at=now(),status='complete',passed=bool(passed),
            outputs={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file() and p.name != 'pipeline.json'},quality_approved=False,selected_for_studio=False))
        save(output/'pipeline.json',dict(status='complete',passed=bool(passed)))
        print(dict(passed=bool(passed),positives=len(positives),positive_failures=sum(not c['passed'] for c in positives),negative_controls=len(negatives),skin=skin_checks),flush=True)
        return passed
    except Exception as error:
        save(output/'pipeline.json',dict(status='failed',reason=str(error))); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('engine_audit',type=Path); parser.add_argument('output',type=Path)
    args = parser.parse_args()
    if not run(args.engine_audit,args.output): raise SystemExit(2)
