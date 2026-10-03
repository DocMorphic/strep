"""Inspect fixed support-patch weights and source-local foot articulation.

This is read-only evidence for choosing edit permissions, not a correction,
causal diagnosis, contact/engine certificate or automatic permission change.
"""
import argparse
from pathlib import Path
import shutil
import sys
import numpy as np
import scipy
from scipy.spatial.transform import Rotation
from strep import read, save, sha256, now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_support_spec import validate
from native_support_skin import NativeSupportSkin
from native_leg_floor import foot_region
from native_foot_plant import patch_geometry
from paired_temporal_neighbor import rotation_channels
from elbow_swivel import descendants


def local_track(clock, quaternions, stance):
    """SLERP angle from the exact stance start and overlapping native speeds.

    Speed is measured on original adjacent native key intervals, never on
    a union of nearly coincident stance boundaries and native key clocks.
    """
    a, b = stance
    clock = np.asarray(clock)
    q = np.asarray(quaternions, float)
    if (clock.ndim != 1 or len(clock) < 1 or q.shape != (len(clock), 4)
            or not np.isfinite(clock).all() or not np.isfinite(q).all()
            or np.any(np.diff(clock) <= 0) or np.any(np.linalg.norm(q, axis=1) < 1e-8)
            or not np.isfinite([a, b]).all() or not 0 <= a < b or clock[0] < 0):
        raise ValueError('Ordered nonnegative native rotation keys and stance required')
    seconds = clock.astype(float)
    times = np.concatenate((np.array([a], float), seconds[(seconds > a) & (seconds < b)], np.array([b], float)))
    samples = np.array([NativeSupportSampler.value('rotation', clock, q, 'LINEAR', float(t)) for t in times])
    angles = (Rotation.from_quat(samples[0]).inv() * Rotation.from_quat(samples)).magnitude()
    segments = (seconds[:-1] < b) & (seconds[1:] > a)
    native_angles = ((Rotation.from_quat(q[:-1]).inv() * Rotation.from_quat(q[1:])).magnitude()
                     if len(clock) > 1 else np.empty(0))
    speed = native_angles[segments] / np.diff(seconds)[segments]
    return dict(stance_angle_sample_times_s=times.tolist(), native_clock_bounds_s=[float(seconds[0]), float(seconds[-1])],
        clamped_before_first_key_s=max(0., min(b, float(seconds[0])) - a),
        clamped_after_last_key_s=max(0., b - max(a, float(seconds[-1]))),
        maximum_sampled_local_angle_from_stance_start_degrees=float(np.rad2deg(angles).max()),
        native_segments_overlapping_stance=int(np.count_nonzero(segments)),
        maximum_overlapping_native_local_speed_rad_s=float(speed.max(initial=0)),
        scope='Native SLERP local rotation only; sampled angles, not world-motion or acceleration limits')


def inspect(rig, reader, rows):
    skin = NativeSupportSkin(rig)
    channels = rotation_channels(rig.document, rig.binary)
    supports = []
    for row in rows:
        foot = row['chain'][-1]
        region = foot_region(skin, rig.parents, foot)
        _, _, patch, references = patch_geometry(rig, reader, row)
        vertices = region[patch]
        branch = descendants(rig.parents, foot)
        items = []
        protected_weight = np.zeros(len(vertices))
        for node in np.flatnonzero(branch):
            # Sum repeated node slots without dropping any positive influence.
            weights = np.where(skin.nodes[vertices] == node, skin.weights[vertices], 0).sum(axis=1)
            editable = int(node) in row['chain']
            if not editable:
                protected_weight += weights
            item = dict(node=int(node), name=rig.document['nodes'][node].get('name'),
                editable_under_original_leg_contract=editable,
                patch_vertices_with_positive_weight=int(np.count_nonzero(weights > 0)),
                patch_weight_by_vertex=weights.tolist(), rotation_channel=int(node) in channels,
                local_rotation=None)
            if node in channels:
                item['local_rotation'] = local_track(channels[node][1], channels[node][2], row['stance_s'])
            items.append(item)
        supports.append(dict(id=row['id'], foot_node=foot, stance_s=row['stance_s'],
            edit_keys=row['edit_keys'], original_editable_rotation_nodes=row['chain'],
            fully_foot_bound_region_vertices=len(region), fixed_patch_vertices=len(patch),
            patch_vertex_references=references, protected_patch_weight_by_vertex=protected_weight.tolist(),
            foot_descendants=items))
    return dict(schema='strep-native-support-articulation-v1', supports=supports,
        skin_weight_semantics='RigAsset validates then normalizes each vertex weight sum; inspector sums repeated node slots without further normalization or dropping influences',
        permissions_changed=False, correction_generated=False,
        quality_approved=False, training_admitted=False, release_approved=False,
        scope='Original 3 mm lowest fixed patch and all positive source skin influences; local tracks only. '
              'Weight or motion does not prove a frozen joint causes a failure or should be editable.')


def run(source, draft, output):
    source, draft, output = map(lambda p: Path(p).resolve(), (source, draft, output))
    if output.exists():
        raise ValueError('Choose a fresh articulation report directory')
    inputs = {str(p): sha256(p) for p in (source, draft)}
    rig = RigAsset.load(source)
    reader = NativeSupportSampler(rig.document, rig.binary, 0)
    _, rows = validate(read(draft), rig, reader, inputs[str(source)])
    from native_review_support import method_names
    names = set(method_names()) | {'native_support_articulation.py', 'native_foot_plant.py', 'strep.py'}
    methods = {str(Path(__file__).resolve().parent / n): sha256(Path(__file__).resolve().parent / n) for n in sorted(names)}
    result = inspect(rig, reader, rows)
    output.mkdir()
    archive = output / 'implementation'
    archive.mkdir()
    for p in methods:
        shutil.copyfile(p, archive / Path(p).name)
    save(output / 'pipeline.json', dict(status='processing'))
    try:
        if any(sha256(p) != h for p, h in {**inputs, **methods}.items()):
            raise ValueError('Articulation inputs or methods changed')
        result.update(status='complete', at=now(), inputs_sha256=inputs, implementation_sha256=methods,
                      python=sys.version, numpy=np.__version__, scipy=scipy.__version__)
        save(output / 'result.json', result)
        save(output / 'pipeline.json', dict(status='complete'))
        return result
    except Exception as exc:
        save(output / 'pipeline.json', dict(status='failed', error=str(exc)))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'draft', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):
        result = run(args.source, args.draft, args.output)
    print(dict(status=result['status'], supports=len(result['supports']), permissions_changed=False))
