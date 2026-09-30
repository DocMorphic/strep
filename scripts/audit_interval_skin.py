"""Replay skin-motion interval bounds on explicitly bound clips and placements."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler
from skin_motion_bounds import SkinMotionBounds
from swept_surface_boxes import audit


def load_protocol(protocol_path):
    protocol_path = Path(protocol_path).resolve()
    protocol = read(protocol_path); inputs = {str(protocol_path): sha256(protocol_path)}
    intervals = np.asarray(protocol['intervals_s'], float)
    if intervals.ndim != 2 or intervals.shape[1:] != (2,) or not len(intervals) or not np.isfinite(intervals).all():
        raise ValueError('Finite nonempty interval pairs required')
    actors = []; names = []
    if not 1 <= len(protocol['actors']) <= 2: raise ValueError('One or two actors required')
    for entry in protocol['actors']:
        path = (protocol_path.parent/entry['path']).resolve()
        if sha256(path) != entry['sha256']: raise ValueError('Bound clip changed')
        inputs[str(path)] = entry['sha256']; names.append(entry['name'])
        rotation, translation = np.asarray(entry['rotation_xyzw'], float), np.asarray(entry['translation_m'], float)
        if rotation.shape != (4,) or translation.shape != (3,) or not np.isfinite(np.r_[rotation, translation]).all() or abs(np.linalg.norm(rotation)-1) > 1e-10:
            raise ValueError('Finite rigid scene placement required')
        rig = RigAsset.load(path); sampler = AnimationSampler(rig.document, rig.binary, 0)
        if len(rig.primitives) != 1: raise ValueError('Current pair-audit adapter requires one primitive')
        primitive = rig.primitives[0]; node = rig.document['nodes'][primitive['node']]
        mesh = rig.document['meshes'][node['mesh']]['primitives'][primitive['primitive']]
        faces = array(rig.document, rig.binary, mesh['indices']).reshape(-1, 3)
        actors.append(dict(rig=rig, sampler=sampler, bound=SkinMotionBounds(rig, sampler),
                           faces=faces, rotation=Rotation.from_quat(rotation).as_matrix(), translation=translation))
        if np.any(intervals[:, 0] < 0) or np.any(intervals[:, 1] > sampler.duration) or np.any(intervals[:, 0] >= intervals[:, 1]):
            raise ValueError('Intervals must be increasing and inside every clip')
    if len(set(names)) != len(names): raise ValueError('Unique actor names required')
    return protocol, inputs, intervals, names, actors


def run(protocol_path, output):
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Fresh output directory required')
    protocol, inputs, intervals, names, actors = load_protocol(protocol_path)
    output.mkdir(); (output/'implementation').mkdir()
    methods = ['audit_interval_skin.py', 'skin_motion_bounds.py', 'swept_surface_boxes.py',
               'rig_asset.py', 'rig_clip_import.py', 'gltf_tools.py', 'strep.py']
    digests = {}
    for name in methods:
        path = ROOT/'scripts'/name; digests[name] = sha256(path)
        shutil.copyfile(path, output/'implementation'/name)
    save(output/'request.json', dict(at=now(), inputs=inputs, implementation=digests, protocol=protocol,
        replay_samples_per_actor_interval=17, quality_approved=False))
    rows = []
    for start, end in intervals:
        bounds = []; observations = []
        for name, actor in zip(names, actors):
            bound = actor['bound'].interval(float(start), float(end))
            bound['center_vertices'] = bound['center_vertices']@actor['rotation'].T+actor['translation']
            maximum_ratio = 0.
            for stamp in np.linspace(start, end, 17):
                points = actor['rig'].vertices(actor['sampler'].sample(float(stamp)))@actor['rotation'].T+actor['translation']
                displacement = np.linalg.norm(points-bound['center_vertices'], axis=1)
                if np.any(displacement > bound['radius_m']): raise ValueError('Actual sampled skin exceeded interval bound')
                maximum_ratio = max(maximum_ratio, float((displacement/bound['radius_m']).max()))
            observations.append(dict(actor=name, vertices=len(bound['radius_m']), native_spans=bound['native_spans'],
                maximum_radius_m=float(bound['radius_m'].max()), maximum_observed_ratio=maximum_ratio,
                decoded_replay_samples=17, all_replayed_vertices_inside=True))
            bounds.append(bound)
        paired = audit(bounds[0], actors[0]['faces'], bounds[1], actors[1]['faces']) if len(actors) == 2 else None
        rows.append(dict(start_s=float(start), end_s=float(end), actors=observations, paired_surfaces=paired))
        save(output/'intervals.json', rows)
        print(dict(interval=[start, end], paired=None if paired is None else paired['outcome']), flush=True)
    for path, digest in inputs.items():
        if sha256(path) != digest: raise ValueError('Bound input changed during audit')
    for name, digest in digests.items():
        if sha256(ROOT/'scripts'/name) != digest or sha256(output/'implementation'/name) != digest:
            raise ValueError('Audit implementation changed')
    save(output/'result.json', dict(at=now(), status='complete', request_sha256=sha256(output/'request.json'),
        intervals_sha256=sha256(output/'intervals.json'), intervals=len(rows),
        actor_sample_replays=17*len(rows)*len(actors), collision_free_certified=False, quality_approved=False,
        scope='Replayed samples validate bound implementation but do not prove continuous correctness. Swept boxes bound surface separation under supported interpolation and declared floating padding; overlap is unresolved, not collision. No containment, self-collision, full-clock or quality approval.'))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with threadpool_limits(limits=1): run(args.protocol, args.output)
