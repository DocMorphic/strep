"""Measure foot drift separately from sampled native support-height acceptance."""
from pathlib import Path
import argparse
import numpy as np
from contact_rate_path import ProjectedSkin
from native_support_clock import NativeSupportSampler
from native_support_skin import NativeSupportSkin
from native_support_spec import validate
from native_leg_floor import foot_region
from rig_asset import RigAsset
from strep import read, save, sha256


def patch_metrics(points, normal, offset, times, patch):
    """Track fixed vertex identities; changing lowest vertices cannot hide drift."""
    points, normal, times = map(lambda a: np.asarray(a, float), (points, normal, times))
    patch = np.asarray(patch)
    if (points.ndim != 3 or points.shape[2] != 3 or times.shape != (len(points),)
            or normal.shape != (3,) or abs(np.linalg.norm(normal)-1) > 1e-8
            or not np.isfinite(points).all() or not np.isfinite(normal).all()
            or not np.isfinite(times).all() or not np.isfinite(offset)
            or len(times) < 2 or np.any(np.diff(times) <= 0)
            or patch.ndim != 1 or patch.dtype.kind not in 'iu' or not len(patch)
            or len(np.unique(patch)) != len(patch)
            or patch.min() < 0 or patch.max() >= points.shape[1]):
        raise ValueError('Finite foot points, unit normal, increasing clock and fixed patch required')
    selected = points[:, patch]
    relative = selected-selected[0]
    tangent = relative-(relative@normal)[..., None]*normal
    velocity = np.diff(selected, axis=0)/np.diff(times)[:, None, None]
    tangent_velocity = velocity-(velocity@normal)[..., None]*normal
    heights = points@normal+offset
    return dict(maximum_patch_vertex_tangential_drift_m=float(np.linalg.norm(tangent, axis=2).max()),
        maximum_patch_vertex_tangential_speed_m_s=float(np.linalg.norm(tangent_velocity, axis=2).max()),
        minimum_region_height_m=float(heights.min()),
        maximum_lowest_region_height_m=float(heights.min(axis=1).max()),
        maximum_sampled_region_penetration_m=float(max(0., -heights.min())),
        planted_contact_certified=False)


def measure(source, candidate, spec):
    """Compare identical rig geometry on a stance clock, without adding a gate."""
    source, candidate = Path(source), Path(candidate)
    bindings = {str(p.resolve()): sha256(p) for p in (source, candidate)}
    rig, changed = RigAsset.load(source), RigAsset.load(candidate)
    for key in ('nodes', 'meshes', 'skins', 'materials', 'images', 'textures'):
        if rig.document.get(key) != changed.document.get(key):
            raise ValueError('Contact diagnostics require identical rig geometry and identities')
    old = NativeSupportSampler(rig.document, rig.binary, 0)
    new = NativeSupportSampler(changed.document, changed.binary, 0)
    if len(rig.document.get('animations', [])) != 1 or len(changed.document.get('animations', [])) != 1:
        raise ValueError('One chosen animation per contact diagnostic required')
    if old.duration != new.duration or len(old.channels) != len(new.channels):
        raise ValueError('Matching contact diagnostic duration/channels required')
    for a, b in zip(old.channels, new.channels):
        if a[:2] != b[:2] or a[4] != b[4] or not np.array_equal(a[2], b[2]):
            raise ValueError('Matching native channel identities and clocks required')
    # Equal accessor identities alone do not prove unchanged mesh/bind payloads.
    if len(rig.primitives) != len(changed.primitives) or rig.joints != changed.joints:
        raise ValueError('Matching skin/primitive populations required')
    if not np.array_equal(rig.inverse, changed.inverse):
        raise ValueError('Contact diagnostic skin binds changed')
    for a, b in zip(rig.primitives, changed.primitives):
        for key in ('positions', 'joints', 'weights'):
            if not np.array_equal(a[key], b[key]):
                raise ValueError('Contact diagnostic mesh payload changed')
    _, rows = validate(spec, rig, old, bindings[str(source.resolve())])
    skin = NativeSupportSkin(rig)
    supports = []
    for row in rows:
        start, end = row['stance_s']
        uniform = np.arange(int(np.floor(start*120)), int(np.ceil(end*120))+1)/120
        times = np.unique(np.r_[start, uniform[(uniform > start)&(uniform < end)], end])
        before = np.array([old.sample(float(t)) for t in times])
        after = np.array([new.sample(float(t)) for t in times])
        region = foot_region(skin, rig.parents, row['chain'][-1])
        projections = [ProjectedSkin(skin, region, axis) for axis in np.eye(3)]
        source_points = np.stack([projection.evaluate(before) for projection in projections], axis=2)
        candidate_points = np.stack([projection.evaluate(after) for projection in projections], axis=2)
        heights = source_points[0]@row['up']+row['offset']
        patch = np.flatnonzero(heights <= heights.min()+.003)
        supports.append(dict(id=row['id'], foot=row['foot'], samples=len(times), times_s=times.tolist(),
            patch_rule='Fixed source vertices within 3 mm of the lowest region vertex at stance start',
            source_patch_vertex_references=skin.vertex_references[region[patch]].tolist(),
            region_vertices=len(region), patch_vertices=len(patch),
            source=patch_metrics(source_points, row['up'], row['offset'], times, patch),
            candidate=patch_metrics(candidate_points, row['up'], row['offset'], times, patch)))
    if any(sha256(path) != digest for path, digest in bindings.items()):
        raise ValueError('Contact diagnostic inputs changed during measurement')
    return dict(schema='strep-native-contact-diagnostics-v1', inputs_sha256=bindings, supports=supports,
        sample_rate_hz=120, stance_boundary_samples_included=True, changes_acceptance_gates=False,
        planted_contact_certified=False, continuous_collision_certified=False, quality_approved=False,
        scope='CPU skin positions of a fixed lower foot patch during authored stance; not force, balance, semantic contact or human realism evidence')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'candidate', 'spec', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh contact diagnostic file')
    digest = sha256(args.spec)
    result = measure(args.source, args.candidate, read(args.spec))
    if sha256(args.spec) != digest:
        raise ValueError('Contact diagnostic draft changed')
    result['spec_sha256'] = digest
    save(args.output, result)
