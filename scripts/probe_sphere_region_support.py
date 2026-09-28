"""Enumerate declared palm-region anchors under exact sphere/full-hand geometry."""
import argparse
import itertools
import shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from build_soma_preview import ASSET
from grasp_pose_witness import PoseProblem
from grasp_orientation import align_direction
from paired_palm_region import region


def contact_triangle(points, ids, target, gap, limits):
    selected = np.flatnonzero((gap >= limits['clearance_m']-1e-6) & (gap <= limits['contact_gap_m']) & (np.linalg.norm(points-target, axis=1) <= limits['local_radius_m']))
    if len(selected) < 3: return None
    triples = np.array(list(itertools.combinations(selected, 3)), dtype=int)
    tri = points[triples]
    distance = np.minimum.reduce([np.linalg.norm(tri[:, 0]-tri[:, 1], axis=1), np.linalg.norm(tri[:, 1]-tri[:, 2], axis=1), np.linalg.norm(tri[:, 2]-tri[:, 0], axis=1)])
    area = np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1)/2
    error = np.linalg.norm(tri.mean(1)-target, axis=1)
    eligible = np.flatnonzero((distance >= limits['spacing_m']) & (area >= limits['area_m2']) & (error <= limits['centroid_error_m']))
    if not len(eligible): return None
    best = min(eligible, key=lambda i: (error[i], -area[i], tuple(ids[triples[i]])))
    return dict(vertices=ids[triples[best]].tolist(), minimum_spacing_m=float(distance[best]), area_m2=float(area[best]),
                centroid_error_m=float(error[best]), contact_gaps_m=gap[triples[best]].tolist())


def declared_azimuths(angles, tilt_ring_degrees):
    if angles is None: return list(range(0, 360, 45))
    if not tilt_ring_degrees or not len(angles) or not np.isfinite(angles).all() or any(a < 0 or a >= 360 for a in angles) or len(set(angles)) != len(angles):
        raise ValueError('Explicit azimuths require a nonzero tilt and unique finite angles in [0, 360)')
    return list(angles)


def run(study, seed_report, output, tilt_ring_degrees=0., hand='LeftHand', azimuth_degrees=None):
    azimuths = declared_azimuths(azimuth_degrees, tilt_ring_degrees)
    study, seed_report, output = [Path(s).resolve() for s in (study, seed_report, output)]
    fit = study/'fit'; summary = read(fit/'summary.json'); seed_result = read(seed_report/'result.json'); seed_protocol = read(seed_report/'protocol.json')
    if sha256(fit/'summary.json') != seed_protocol['fit_summary_sha256'] or sha256(ASSET) != summary['mesh_sha256'] or sha256(seed_report/'pose.npz') != seed_result['pose_sha256']: raise ValueError('Study or seed changed')
    for name, digest in seed_protocol['inputs'].items():
        if sha256(ROOT/name) != digest: raise ValueError('Input changed')
    p = PoseProblem(fit/'assets'/summary['trials'][0]['id']/'A', dict(np.load(ASSET, allow_pickle=False)), seed_protocol['frame'])
    seed = np.array(seed_result['parameters']); audit, motion = p.independent(seed)
    if not audit['rotation_norm_bounds_passed']: raise ValueError('Original pose edit limits failed')
    if hand not in ('LeftHand', 'RightHand'): raise ValueError('Mapped hand required')
    vertices = p.surface.vertices(motion['global_rot_mats'][0], motion['posed_joints'][0]); patch = region(p.skin, hand); patch_ids = np.array(patch['vertices'])
    contact = next(c for c in p.contacts if c['region'] == hand); target_n = next(n[2].numpy() for n in p.normals if n[0] == ('left-grip' if hand == 'LeftHand' else 'right-grip')); target = np.array(contact['target'])
    wrist = p.names.index(hand); descendants = []
    for j in range(len(p.parents)):
        while j >= 0 and j != wrist: j = p.parents[j]
        descendants.append(j == wrist)
    hand_ids = np.flatnonzero(np.all(np.array(descendants)[p.skin['lbs_indices']] | (p.skin['lbs_weights'] == 0), axis=1))
    original_patch = patch
    face_ids = np.array(patch['face_ids'])
    face_ids = face_ids[np.isin(p.skin['faces'][face_ids], hand_ids).all(axis=1)]
    if len(face_ids) < 3: raise ValueError('Insufficient region triangles wholly in hand subtree')
    patch_ids = np.unique(p.skin['faces'][face_ids])
    patch = dict(patch, vertices=patch_ids.tolist(), face_ids=face_ids.tolist(), additional_rule='Every positive skin influence of every triangle vertex belongs to the hand subtree')
    faces = p.skin['faces'][face_ids]; tri = vertices[faces]; normal = np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]).sum(0); normal /= np.linalg.norm(normal)
    sphere, _, center, _ = p.objects[0]
    if sphere.shape != 'sphere': raise ValueError('Sphere required')
    rotation = align_direction(normal, target_n)
    if not np.isfinite(tilt_ring_degrees) or not 0 <= tilt_ring_degrees < p.config['normal_tolerance_degrees']:
        raise ValueError('Tilt ring must lie strictly within original normal tolerance')
    orientations = [(0., 0., rotation)]
    if tilt_ring_degrees:
        basis = np.cross(target_n, np.eye(3)[np.argmin(np.abs(target_n))]); basis /= np.linalg.norm(basis)
        second = np.cross(target_n, basis)
        for azimuth in azimuths:
            axis = np.cos(np.deg2rad(azimuth))*basis+np.sin(np.deg2rad(azimuth))*second
            orientations.append((tilt_ring_degrees, float(azimuth), Rotation.from_rotvec(np.deg2rad(tilt_ring_degrees)*axis).as_matrix()@rotation))
    limits = dict(clearance_m=p.config['object_clearance_m'], placement_gap_m=.0021, contact_gap_m=.003, spacing_m=.006,
                  area_m2=.000025, centroid_error_m=.005, local_radius_m=.020)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), output/Path(__file__).name)
    save(output/'protocol.json', dict(at=now(), study=study.relative_to(ROOT).as_posix(), frame=p.frame,
         seed_result_sha256=sha256(seed_report/'result.json'), seed_protocol_sha256=sha256(seed_report/'protocol.json'), inputs=seed_protocol['inputs'],
         mesh_sha256=sha256(ASSET), original_region=original_patch, patch=patch, limits=limits, implementation_sha256=sha256(Path(__file__)), region_source_sha256=sha256(ROOT/'scripts/paired_palm_region.py'),
         orientations=[dict(tilt_degrees=t, azimuth_degrees=a, rotation_from_source=r.tolist()) for t, a, r in orientations],
         selection='Enumerate every declared palm-region vertex at every declared orientation. Require entire hand clearance and three separated near-sphere region contacts with area and world-grip centroid checks. Rank passing anchors by contact centroid error, then area, vertex ID and orientation.',
         scope='New explicit region-contact condition. Area-weighted region normal replaces tiny local point normal; old fixed vertex14712 constraint is not claimed. No finger changes or skeleton projection; other body, self-collision, anatomy, temporal quality and release remain unverified.', quality_approved=False))
    rows = []
    for tilt, azimuth, rotation in orientations:
      for anchor in patch_ids:
        q = target-limits['placement_gap_m']*target_n
        placed = (vertices[hand_ids]-vertices[anchor])@rotation.T+q
        gaps = np.linalg.norm(placed-center.numpy()[0], axis=1)-sphere.dimensions[0]
        full_pass = gaps.min() >= limits['clearance_m']-1e-6
        positions = (vertices[patch_ids]-vertices[anchor])@rotation.T+q
        region_gaps = np.linalg.norm(positions-center.numpy()[0], axis=1)-sphere.dimensions[0]
        triangle = contact_triangle(positions, patch_ids, target, region_gaps, limits) if full_pass else None
        rows.append(dict(anchor=int(anchor), tilt_degrees=tilt, azimuth_degrees=azimuth, rotation_from_source=rotation.tolist(), minimum_hand_clearance_m=float(gaps.min()), full_hand_clearance_passed=bool(full_pass), contact_triangle=triangle,
                         region_condition_passed=bool(full_pass and triangle is not None)))
    eligible = [r for r in rows if r['region_condition_passed']]
    best = min(eligible, key=lambda r: (r['contact_triangle']['centroid_error_m'], -r['contact_triangle']['area_m2'], r['anchor'], r['tilt_degrees'], r['azimuth_degrees'])) if eligible else None
    save(output/'result.json', dict(at=now(), rows=rows, best=best, rotation_from_source=None if best is None else best['rotation_from_source'], desired_anchor_point=(target-limits['placement_gap_m']*target_n).tolist(),
         desired_region_normal=target_n.tolist(), hand_clearance_pass_count=sum(r['full_hand_clearance_passed'] for r in rows), region_pass_count=len(eligible),
         skeleton_pose_generated=False, quality_approved=False))
    print(dict(anchors=len(rows), hand_clearance_passes=sum(r['full_hand_clearance_passed'] for r in rows), region_passes=len(eligible), best=best))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('study', type=Path); parser.add_argument('seed_report', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--tilt-ring-degrees', type=float, default=0.)
    parser.add_argument('--hand', choices=['LeftHand', 'RightHand'], default='LeftHand')
    parser.add_argument('--azimuth-degrees', type=float, nargs='+', help='Explicit tilt directions; default is the original eight-angle ring')
    args = parser.parse_args(); run(args.study, args.seed_report, args.output, args.tilt_ring_degrees, args.hand, args.azimuth_degrees)
