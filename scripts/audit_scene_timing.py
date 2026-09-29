"""Compare exported ground support and joint rates at matching motion phases."""
import argparse
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from strep import read, save, sha256
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from scene_runtime import local
from scene_constraints import pose


def rates(matrices, dt, names):
    if not np.isfinite(dt) or dt <= 0 or len(matrices) < 3:
        raise ValueError('At least three samples on a positive clock required')
    speed = np.linalg.norm(np.diff(matrices[:, :, :3, 3], axis=0)/dt, axis=-1)
    acceleration = np.linalg.norm(np.diff(matrices[:, :, :3, 3], n=2, axis=0)/dt**2, axis=-1)
    r = matrices[:, :, :3, :3]
    omega = Rotation.from_matrix((r[1:] @ r[:-1].transpose(0, 1, 3, 2)).reshape(-1, 3, 3)).as_rotvec().reshape(len(r)-1, len(names), 3)/dt
    angular = np.linalg.norm(omega, axis=-1)
    angular_acceleration = np.linalg.norm(np.diff(omega, axis=0)/dt, axis=-1)
    return [dict(joint=name, peak_speed_m_s=float(speed[:, j].max()),
                 peak_acceleration_m_s2=float(acceleration[:, j].max()),
                 peak_angular_speed_rad_s=float(angular[:, j].max()),
                 peak_angular_acceleration_rad_s2=float(angular_acceleration[:, j].max()))
            for j, name in enumerate(names)]


def feet(rig):
    names = [rig.document['nodes'][j].get('name', '') for j in rig.joints]
    result = {side+'Foot': [] for side in ['Left', 'Right']}
    offset = 0
    for p in rig.primitives:
        if p['joints'] is not None:
            dominant = p['joints'][np.arange(len(p['positions'])), p['weights'].argmax(1)]
            for side in ['Left', 'Right']:
                ids = [j for j, name in enumerate(names) if name.startswith((side+'Foot', side+'Toe'))]
                result[side+'Foot'].extend((np.flatnonzero(np.isin(dominant, ids))+offset).tolist())
        offset += len(p['positions'])
    if any(not ids for ids in result.values()):
        raise ValueError('Named left/right foot skin regions required for timing support review')
    return {k: np.array(v) for k, v in result.items()}


def support_edge(before, after, regions, dt):
    """Select on the source only; track one material point across each edge."""
    result = []
    a, b = before[0], after[0]
    for name, ids in regions.items():
        heights = [float(v[ids, 1].min()) for v in [a, b]]
        center_speed = np.linalg.norm((b[ids].mean(0)-a[ids].mean(0))[[0, 2]])/dt[0]
        if any(abs(h) > .025 for h in heights) or center_speed > .2:
            continue
        vertex = int(ids[a[ids, 1].argmin()])
        slip = [float(np.linalg.norm((y[vertex]-x[vertex])[[0, 2]])/step)
                for x, y, step in zip(before, after, dt)]
        result.append(dict(region=name, vertex=vertex, source_slide_m_s=slip[0], candidate_slide_m_s=slip[1]))
    return result


def check_package(folder):
    scene = read(folder/'portable-scene.json'); runtime = read(folder/'scene-runtime.json')
    if scene['fps'] != 30 or runtime['source_scene_sha256'] != sha256(folder/'portable-scene.json'):
        raise ValueError('Changed scene or unsupported clock')
    if set(scene['actors']) != set(runtime['actors']):raise ValueError('Runtime participants differ')
    paths = {}
    for name, actor in scene['actors'].items():
        path = local(folder, actor['preview_glb'])
        if sha256(path) != runtime['actors'][name]['sha256'] or actor['transform'] != runtime['actors'][name]['placement']:
            raise ValueError('Changed actor export or placement')
        paths[name] = path
    return scene, paths


def run(source, candidate, output, first=0, last=None):
    source, candidate, output = map(lambda p: Path(p).resolve(), [source, candidate, output])
    if output.exists():raise ValueError('Fresh timing review path required')
    a, ap = check_package(source); b, bp = check_package(candidate)
    last = a['frame_count']-1 if last is None else last
    if any(type(n) is not int for n in [first, last]) or not 0 <= first < last < a['frame_count']:
        raise ValueError('Integer source phase range required')
    if set(ap) != set(bp):raise ValueError('Matching actor identities required')
    inputs = {str(p): sha256(p) for p in [source/'portable-scene.json', source/'scene-runtime.json',
              candidate/'portable-scene.json', candidate/'scene-runtime.json', *ap.values(), *bp.values()]}
    times = [np.arange((last-first)*4+1)/120+first/30,
             np.linspace(0, (b['frame_count']-1)/30, (last-first)*4+1)]
    dt = [float(t[1]-t[0]) for t in times]; actors = {}
    with threadpool_limits(limits=1):
        for name in ap:
            rigs = [RigAsset.load(p) for p in [ap[name], bp[name]]]
            if not np.array_equal(rigs[0].inverse,rigs[1].inverse):raise ValueError('Timing edit changed inverse binds')
            for key in ['meshes','skins','nodes','materials']:
                if rigs[0].document.get(key) != rigs[1].document.get(key):raise ValueError('Timing edit changed rig or mesh')
            if a['actors'][name]['transform'] != b['actors'][name]['transform']:raise ValueError('Timing edit changed placement')
            for p, q in zip(rigs[0].primitives, rigs[1].primitives):
                if any(not np.array_equal(p[k], q[k]) for k in ['positions', 'joints', 'weights']):raise ValueError('Timing edit changed skin data')
            samplers = [AnimationSampler(r.document, r.binary, 0) for r in rigs]
            for sampler, scene in zip(samplers, [a, b]):
                if abs(sampler.duration-(scene['frame_count']-1)/30)>1e-5:raise ValueError('Export duration differs from scene')
            position, rotation = pose(a['actors'][name]['transform'])
            placement = np.eye(4);placement[:3,:3] = rotation;placement[:3,3] = position
            regions = feet(rigs[0]); previous = None; joints = [[], []]; floor = [[], []]; rows = []; maximum_error = 0.
            for i in range(len(times[0])):
                worlds = [s.sample(float(t[i])) for s, t in zip(samplers, times)]
                vertices = [r.vertices(w) @ rotation.T+position for r, w in zip(rigs, worlds)]
                maximum_error = max(maximum_error, float(np.linalg.norm(vertices[1]-vertices[0], axis=1).max()))
                for v in range(2):
                    joints[v].append((placement @ worlds[v])[rigs[v].joints])
                    floor[v].append(max(0., -float(vertices[v][:,1].min())))
                if previous is not None:
                    for row in support_edge(previous, vertices, regions, dt):
                        row.update(source_time_s=float((times[0][i]+times[0][i-1])/2),
                                   candidate_time_s=float((times[1][i]+times[1][i-1])/2));rows.append(row)
                previous = vertices
            variants = {}
            names = [rigs[0].document['nodes'][j]['name'] for j in rigs[0].joints]
            for v, label in enumerate(['source','candidate']):
                slip = [r[label+'_slide_m_s'] for r in rows]
                variants[label] = dict(joints=rates(np.array(joints[v]), dt[v], names),
                    maximum_floor_depth_m=max(floor[v]), floor_samples_over_1cm=sum(d>.01 for d in floor[v]),
                    inferred_ground_edges=len(slip), ground_slide_p95_m_s=float(np.percentile(slip,95)) if slip else None,
                    ground_slide_max_m_s=max(slip) if slip else None,
                    ground_edges_over_5cm_s=sum(s>.05 for s in slip))
            actors[name] = dict(samples=len(times[0]), maximum_same_phase_skin_error_m=maximum_error,
                                variants=variants, ground_edges=rows)
    if any(sha256(p)!=digest for p,digest in inputs.items()):raise ValueError('Timing review inputs changed')
    report = dict(schema='strep-scene-timing-review-v1', inputs=inputs,
        implementation={n:sha256(Path(__file__).parent/n) for n in ['audit_scene_timing.py','rig_asset.py','rig_clip_import.py','gltf_tools.py','scene_constraints.py']},
        source_range_frames=[first,last], candidate_frames=b['frame_count'], actors=actors,
        thresholds=dict(ground_height_band_m=.025, source_patch_speed_max_m_s=.2, diagnostic_slide_m_s=.05, diagnostic_floor_depth_m=.01),
        quality_approved=False, scope='Matched phases at source 120 Hz; candidate dt scales with duration. World-space full skin floor depth and per-joint linear/angular finite differences. Source low/slow foot patches select ground hypotheses; the same material vertex is tracked across each edge in both versions. Counts are diagnostic, not certified contacts. No minimum stance duration, moving-platform support, force, balance, continuous collision or human quality approval. STEP discontinuities yield sampling-dependent finite differences.')
    save(output, report)
    return report


def summary(report):
    parts=[]
    for name, actor in report['actors'].items():
        a,b=[actor['variants'][label] for label in ['source','candidate']]
        peak=lambda v:max(j['peak_acceleration_m_s2'] for j in v['joints'])
        slide='no inferred ground-support edges' if not a['inferred_ground_edges'] else f"ground slide p95 {a['ground_slide_p95_m_s']:.3f} to {b['ground_slide_p95_m_s']:.3f} m/s over {a['inferred_ground_edges']} source-inferred edges"
        parts.append(f"{name}: {slide}; peak joint acceleration {peak(a):.2f} to {peak(b):.2f} m/s2; candidate floor depth {b['maximum_floor_depth_m']*1000:.2f} mm.")
    return ' '.join(parts)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','candidate','output']:p.add_argument(name,type=Path)
    p.add_argument('--first',type=int,default=0);p.add_argument('--last',type=int)
    args=p.parse_args();run(args.source,args.candidate,args.output,args.first,args.last)
