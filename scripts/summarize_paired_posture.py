"""Verify a complete paired-posture audit and localize sampled failures.

Skin influence names describe vertices; they are not an anatomical classifier.
Consecutive failing sample runs do not certify collision between samples.
"""
import argparse
import copy
from pathlib import Path
import numpy as np
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset


def failing_runs(samples, threshold=.005):
    runs, current = [], []
    for sample in samples:
        if max(c['max_depth_m'] for c in sample['collision']) > threshold:
            current.append(sample['frame'])
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return [dict(first_frame=r[0], last_frame=r[-1], sample_count=len(r), frames=r) for r in runs]


def influences(rig, vertex):
    if vertex is None:
        return []
    for primitive in rig.primitives:
        if vertex >= len(primitive['positions']):
            vertex -= len(primitive['positions'])
            continue
        if primitive['joints'] is None:
            return [dict(node=primitive['node'], name=rig.document['nodes'][primitive['node']].get('name'), weight=1.)]
        weights = {}
        for joint, weight in zip(primitive['joints'][vertex], primitive['weights'][vertex]):
            node = int(rig.joints[joint])
            weights[node] = weights.get(node, 0.) + float(weight)
        return [dict(node=n, name=rig.document['nodes'][n].get('name'), weight=w)
                for n, w in sorted(weights.items(), key=lambda p: -p[1]) if w > 0]
    raise ValueError('Recorded vertex outside source skin')


def run(audit, output, pose_study=None):
    audit, output = Path(audit).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Preserve earlier summary')
    if read(audit/'pipeline.json')['status'] != 'complete':
        raise ValueError('Require complete scene audit')
    request, completion = read(audit/'request.json'), read(audit/'completion.json')
    study = Path(request['source'])
    verified = {}

    def verify(path, expected):
        path = Path(path)
        digest = sha256(path)
        if digest != expected:
            raise ValueError('Changed evidence: ' + str(path))
        verified[str(path)] = digest

    verify(study/'request.json', request['source_request_sha256'])
    verify(audit/'results.json', completion['results_sha256'])
    verify(study/'manifest.json', completion['source_manifest_sha256'])
    verify(study/'engine-audit/verification.json', completion['source_engine_sha256'])
    for name, digest in request['implementation'].items():
        verify(audit/'implementation'/name, digest)
    source_request = read(study/'request.json')
    for name, digest in source_request['implementation'].items():
        verify(study/'implementation'/name, digest)
    target_path = ROOT/'reports/paired-contact-target-plan-v3/scene.json'
    if 'target_scene_sha256' in source_request:
        target_digest = source_request['target_scene_sha256']
    else:
        if pose_study is None:
            raise ValueError('Provide the source pose study to resolve target provenance')
        pose_study = Path(pose_study).resolve()
        verify(pose_study/'request.json', source_request['pose_request_sha256'])
        verify(pose_study/'results.json', source_request['pose_results_sha256'])
        pose_request = read(pose_study/'request.json')
        for name, digest in pose_request['implementation'].items():
            verify(pose_study/'implementation'/name, digest)
        target_digest = pose_request['target_scene_sha256']
    verify(target_path, target_digest)
    target_scene = read(target_path)['scene']
    methods = ['raw', 'body_fit', 'body_fit_posture']
    seeds = [1301, 2089, 3253, 4099, 5101]
    expected = {f'{m}-seed-{s}' for m in methods for s in seeds}
    results = read(audit/'results.json')['rows']
    manifest = read(study/'manifest.json')
    engine = read(study/'engine-audit/verification.json')['checks']
    frames = sorted(set(range(150)) | {60+i*.5 for i in range(61)})
    if request['frames'] != frames or completion['samples_per_scene'] != len(frames):
        raise ValueError('Changed sample population')
    for rows, key in [(results, 'id'), (manifest['scenes'], 'id')]:
        if len(rows) != 15 or {r[key] for r in rows} != expected:
            raise ValueError('Incomplete scene population')
    if len(engine) != 30 or {(e['scene_id'], e['actor']) for e in engine} != {(s, a) for s in expected for a in ['A', 'B']}:
        raise ValueError('Incomplete engine population')
    if any(e['frames'] != 150 for e in engine) or completion['engine_actor_frames'] != 4500 or completion['scenes'] != 15:
        raise ValueError('Incomplete engine frames')
    for relative, entry in manifest['assets'].items():
        verify(study/relative, entry['sha256'])
    rows = []
    for result in results:
        item = next(i for i in manifest['scenes'] if i['id'] == result['id'])
        scene = read(study/item['variants']['palm'])['scene']
        if scene['id'] != result['id']:
            raise ValueError('Scene identifier mismatch')
        expected_scene = copy.deepcopy(target_scene)
        expected_scene['id'] = scene['id']
        for label in ['A', 'B']:
            for key in ['motion', 'source_sha256', 'preview_glb']:
                expected_scene['actors'][label][key] = scene['actors'][label][key]
        if scene != expected_scene:
            raise ValueError('Scene clock, placement or contact specification changed')
        verified[str(study/item['variants']['palm'])] = sha256(study/item['variants']['palm'])
        rigs = []
        for label in ['A', 'B']:
            actor = scene['actors'][label]
            glb, motion = study/actor['preview_glb'], ROOT/actor['motion']
            verify(glb, result['source_files'][label]['glb_sha256'])
            verify(motion, result['source_files'][label]['motion_sha256'])
            check = next(e for e in engine if (e['scene_id'], e['actor']) == (result['id'], label))
            if check['source_sha256'] != sha256(motion) or check['glb_sha256'] != sha256(glb) or actor['source_sha256'] != sha256(motion):
                raise ValueError('Engine sources differ')
            rigs.append(RigAsset.load(glb))
        sample_path = audit/result['id']/'samples.json'
        verify(sample_path, result['samples_sha256'])
        samples = read(sample_path)['rows']
        if [s['frame'] for s in samples] != frames:
            raise ValueError('Incomplete scene samples')
        if any(len(s['collision']) != 2 or len(s['floor_depth_m']) != 2 for s in samples):
            raise ValueError('Incomplete actor geometry')
        numeric = [v for s in samples for v in [s['gap_m'], *s['floor_depth_m'], *[c['max_depth_m'] for c in s['collision']]]]
        if not np.isfinite(numeric).all() or min(numeric) < 0:
            raise ValueError('Invalid geometry measurements')
        event = next(s for s in samples if s['frame'] == 75)
        peak = max(samples, key=lambda s: max(c['max_depth_m'] for c in s['collision']))
        depth = max(c['max_depth_m'] for c in peak['collision'])
        floor = max(max(s['floor_depth_m']) for s in samples)
        if event != result['event'] or depth != result['max_depth_m'] or floor != result['floor_max_depth_m']:
            raise ValueError('Recorded extrema/event mismatch')
        directions = event['region']['directions']
        if len(directions) != 2:
            raise ValueError('Incomplete region directions')
        region_pass = all(d['within_tolerance_count'] >= 3 and min(d['source_area_witness']['area_m2'], d['target_area_witness']['area_m2']) >= 2.5e-5 for d in directions)
        if region_pass != result['region_pass']:
            raise ValueError('Region summary mismatch')
        peaks = []
        for label, rig, collision in zip(['A', 'B'], rigs, peak['collision']):
            peaks.append(dict(actor=label, vertex=collision['deepest_vertex'], depth_m=collision['max_depth_m'],
                              skin_influences=influences(rig, collision['deepest_vertex'])))
        rows.append(dict(id=result['id'], event_gap_m=event['gap_m'], event_region_pass=region_pass,
                         peak_frame=peak['frame'], peak_vertices=peaks, max_depth_m=depth, floor_max_depth_m=floor,
                         collision_pass=depth <= .005, floor_pass=floor <= .005,
                         failing_sample_runs=failing_runs(samples),
                         failures_outside_60_90=[s['frame'] for s in samples if not 60 <= s['frame'] <= 90 and max(c['max_depth_m'] for c in s['collision']) > .005]))
    output.mkdir()
    save(output/'summary.json', dict(at=now(), audit=str(audit), completion_sha256=sha256(audit/'completion.json'),
         verifier_sha256=sha256(__file__), verified_files=verified, rows=rows, engine_actor_frames=4500,
         quality_approved=False, scope='Complete development population; existing sampled geometry rechecked against bound evidence. Skin influences localize vertices, not anatomy. Runs are consecutive failing samples, not continuous collision intervals. No human or semantic approval.'))
    lines = ['# Complete posture comparison and collision localization', '',
             '15 scenes, 180 decoded samples per scene, 4,500 actual engine actor-frames. Every recorded asset, sample and engine proof hash checked.', '',
             '| Scene | Event gap (mm) | Peak depth (mm) | Peak frame | Dominant source skin influences | Floor depth (mm) |',
             '|---|---:|---:|---:|---|---:|']
    for row in rows:
        names = ', '.join(p['skin_influences'][0]['name'] if p['skin_influences'] else 'none' for p in row['peak_vertices'])
        lines.append(f"| {row['id']} | {row['event_gap_m']*1000:.2f} | {row['max_depth_m']*1000:.2f} | {row['peak_frame']} | {names} | {row['floor_max_depth_m']*1000:.2f} |")
    lines += ['', 'Contact-event improvement does not establish a collision-free approach or recovery. Time ranges in summary.json describe sampled failures only. Unedited floor failures require a separate support correction. No release gate is passed by this report.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(dict(scenes=len(rows), collision_passes=sum(r['collision_pass'] for r in rows), floor_passes=sum(r['floor_pass'] for r in rows)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('audit', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pose-study', type=Path)
    args = parser.parse_args()
    run(args.audit, args.output, args.pose_study)
