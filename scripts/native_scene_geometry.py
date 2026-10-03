"""Read-only, source-bound sampled scene geometry for arbitrary humanoid actions.

All actor surfaces, actor/object pairs, actor pairs and explicitly declared
world planes are included. No inferred floor, chosen body patch or preview
primitive tessellation. Sampled checks never select a correction or certify
continuous motion, self-collision, engine playback or animation quality.
"""
import argparse
import hashlib
from itertools import combinations
from pathlib import Path
import shutil
import sys
import numpy as np
import scipy
import trimesh
from action_worker_lock import worker_lock
from threadpoolctl import threadpool_limits
from strep import ROOT, read, save, sha256
from rig_asset import array
from native_scene_contacts import SceneContacts, fields, scalar, vector, METHODS as CONTACT_METHODS
from engine_contact_sampling import frame_populations, contract_sha256
from triangle_primitive_depth import query
from triangle_crossing import audit as crossings
from convex_partner_surface import penetration

METHODS = tuple(dict.fromkeys(CONTACT_METHODS + ('native_scene_geometry.py', 'triangle_primitive_depth.py',
    'triangle_crossing.py', 'convex_partner_surface.py', 'action_worker_lock.py')))


def faces_for(rig):
    """Read original indexed/nonindexed topology in RigAsset.vertices order."""
    faces = []; offset = 0; population = []
    for p in rig.primitives:
        node = rig.document['nodes'][p['node']]
        primitive = rig.document['meshes'][node['mesh']]['primitives'][p['primitive']]
        count = len(p['positions'])
        if 'indices' in primitive:
            accessor = rig.document['accessors'][primitive['indices']]
            if (accessor['type'] != 'SCALAR' or accessor['componentType'] not in (5121, 5123, 5125)
                    or accessor.get('normalized')): raise ValueError('Unsigned scalar triangle indices required')
            indices = array(rig.document, rig.binary, primitive['indices']).reshape(-1)
        else: indices = np.arange(count)
        if not len(indices) or len(indices) % 3 or indices.min() < 0 or indices.max() >= count:
            raise ValueError('Complete existing triangle indices required')
        triangles = indices.reshape(-1, 3).astype(np.int64)
        faces.append(triangles + offset)
        population.append(dict(node=p['node'], primitive=p['primitive'], vertices=count,
            faces=len(triangles), first_vertex=offset, first_face=sum(len(f) for f in faces[:-1])))
        offset += count
    return np.concatenate(faces), population


def policy_for(value, scene, digest):
    fields(value, ('schema', 'contacts_sha256', 'clock', 'limits', 'planes'), 'native scene geometry policy')
    if value['schema'] != 'strep-native-scene-geometry-v1' or value['contacts_sha256'] != digest:
        raise ValueError('Geometry policy must bind the exact contacts JSON')
    clock = value['clock']; fields(clock, ('mode', 'times_s'), 'geometry clock')
    if clock['mode'] not in ('explicit', 'native-and-frame-populations'):
        raise ValueError('Explicit or native-and-frame-populations clock required')
    if not isinstance(clock['times_s'], list) or not 2 <= len(clock['times_s']) <= 10000:
        raise ValueError('Explicit finite clock with both clip endpoints required')
    times = np.array([scalar(t, 0, scene.duration, 'geometry time') for t in clock['times_s']])
    if times[0] != 0 or times[-1] != scene.duration or np.any(np.diff(times) <= 0):
        raise ValueError('Sorted unique geometry times must include exact clip endpoints')
    populations = []
    if clock['mode'] == 'native-and-frame-populations':
        populations = frame_populations([0, scene.duration])
        extras = [channel[2] for a in scene.actors.values() for channel in a['sampler'].channels]
        extras += [o['times'] for o in scene.objects.values()]
        extras += [np.array(row['authored']['interval_s']) for row in scene.rows]
        times = np.unique(np.concatenate([times] + extras + [p['times_s'] for p in populations]))
    limits = value['limits']
    fields(limits, ('penetration_m', 'depth_resolution_m', 'surface_tolerance_m'), 'geometry limits')
    scalar(limits['penetration_m'], 0, .1, 'penetration limit')
    resolution = scalar(limits['depth_resolution_m'], 1e-9, .01, 'depth resolution')
    scalar(limits['surface_tolerance_m'], 1e-9, 1e-4, 'surface tolerance')
    if not isinstance(value['planes'], dict) or len(value['planes']) > 32:
        raise ValueError('Explicit named world planes required; an empty dictionary declares none')
    for name, plane in value['planes'].items():
        SceneContacts.name(name); fields(plane, ('normal_world', 'offset_m'), 'world plane')
        normal = vector(plane['normal_world'], 3, 'plane normal')
        if abs(np.linalg.norm(normal) - 1) > 1e-8: raise ValueError('Unit plane normal required')
        scalar(plane['offset_m'], -1e6, 1e6, 'plane offset')
    return times, populations, resolution


def volume_state(vertices, faces):
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    valid = bool(mesh.is_volume)
    return mesh, dict(watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
        outward_positive_volume=valid, topology_modified=False,
        self_intersection_checked=False, containment_available=valid)


def evaluate(scene, policy, digest, progress=None, *, actor_vertices=None, object_poses=None):
    times, populations, resolution = policy_for(policy, scene, digest)
    faces = {}; topology = {}
    for name, actor in scene.actors.items():
        faces[name], primitives = faces_for(actor['rig'])
        topology[name] = dict(vertices=sum(len(p['positions']) for p in actor['rig'].primitives),
            faces=len(faces[name]), faces_sha256=hashlib.sha256(faces[name].astype('<i8').tobytes()).hexdigest(),
            primitives=primitives)
    limit = policy['limits']['penetration_m']; tol = policy['limits']['surface_tolerance_m']
    object_query = scene.object_poses if object_poses is None else object_poses
    poses = {n: object_query(n, times) for n in scene.objects}
    samples = []; arrays = dict(times_s=times); passed = True
    for frame, time in enumerate(times):
        vertices = {}; meshes = {}; states = {}; degenerate = {}
        for name, actor in scene.actors.items():
            p, r = actor['placement']
            vertices[name] = (actor['rig'].vertices(actor['sampler'].sample(float(time))) @ r.T + p
                if actor_vertices is None else np.asarray(actor_vertices(name,float(time)),float))
            if vertices[name].shape != (topology[name]['vertices'],3) or not np.isfinite(vertices[name]).all():
                raise ValueError('Complete finite actor surface population required')
            meshes[name], states[name] = volume_state(vertices[name], faces[name])
            tri = vertices[name][faces[name]]
            degenerate[name] = np.flatnonzero(np.linalg.norm(np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]), axis=1) <= tol**2).tolist()
        objects = []; pairs = []; planes = []
        for name in scene.actors:
            for other, obj in scene.objects.items():
                p, r = poses[other][0][frame], poses[other][1][frame]
                depth = query(vertices[name][faces[name]], obj['geometry'], p, r, resolution_m=resolution)
                i = int(depth['lower_m'].argmax()); hi = float(depth['upper_m'].max()); lo = float(depth['lower_m'].max())
                containment = dict(status='unavailable', signed_center_distance_m=None)
                if states[name]['containment_available']:
                    value = float(trimesh.proximity.signed_distance(meshes[name], p[None])[0])
                    containment = dict(status='inside' if value > tol else ('outside' if value < -tol else 'near-surface'),
                        signed_center_distance_m=value)
                ok = bool(hi <= limit and not degenerate[name] and not len(depth['degenerate_faces']) and containment['status'] == 'outside')
                objects.append(dict(actor=name, object=other, maximum_depth_lower_m=lo, maximum_depth_upper_m=hi,
                    peak_lower_face=i, peak_lower_witness_world_m=depth['witnesses_world_m'][i].tolist(),
                    candidate_faces=int(depth['candidate_faces'].sum()), total_faces=len(faces[name]),
                    floating_reserve_m=depth['floating_reserve_m'], containment=containment, passed=ok))
                arrays[f'frame_{frame}_{name}_{other}_depth_lower_m'] = depth['lower_m']
                arrays[f'frame_{frame}_{name}_{other}_depth_upper_m'] = depth['upper_m']
                arrays[f'frame_{frame}_{name}_{other}_witness_world_m'] = depth['witnesses_world_m']
            for plane_name, plane in policy['planes'].items():
                distances = vertices[name] @ np.array(plane['normal_world']) - plane['offset_m']
                # Only referenced surface vertices; loose unused vertices are not surfaces.
                used = np.unique(faces[name]); j = int(used[distances[used].argmin()]); maximum = max(0., -float(distances[j]))
                planes.append(dict(actor=name, plane=plane_name, maximum_depth_m=maximum, peak_vertex=j,
                    passed=bool(maximum <= limit and not degenerate[name])))
        for left, right in combinations(scene.actors, 2):
            surface = crossings(vertices[left], faces[left], vertices[right], faces[right], tolerance_m=tol)
            depths = []
            for a, b in ((left, right), (right, left)):
                if states[b]['containment_available']:
                    measure = penetration(vertices[a], vertices[b], faces[b], tolerance_m=max(limit, 1e-12))
                    depths.append(dict(source=a, target=b, available=True, count_tolerance_m=max(limit, 1e-12), **measure))
                else: depths.append(dict(source=a, target=b, available=False))
            ok = bool(not surface['records'] and not any(surface['degenerate_faces']) and
                all(d['available'] and d['max_depth_m'] <= limit for d in depths))
            pairs.append(dict(actors=[left, right], surface=surface, vertex_containment=depths, passed=ok))
        conditions = objects + pairs + planes
        available = bool(conditions)
        ok = bool(available and all(c['passed'] for c in conditions) and not any(degenerate.values()))
        passed &= ok
        samples.append(dict(time_s=float(time), volumes=states, degenerate_faces=degenerate,
            actor_objects=objects, actor_pairs=pairs, world_planes=planes, conditions_available=available, passed=ok))
        if progress: progress(dict(status='processing', completed_samples=frame+1, total_samples=len(times), time_s=float(time)))
    return dict(schema='strep-native-scene-geometry-result-v1', status='complete', samples=samples,
        sampled_conditions_pass=bool(passed), topology=topology, clock_mode=policy['clock']['mode'], times_s=times.tolist(),
        frame_populations=[dict(id=p['id'], rate_hz=p['rate_hz'], phase_offset_frames=p['phase_offset_frames'],
            times_s=p['times_s'].tolist()) for p in populations], frame_contract_sha256=contract_sha256(),
        limits=policy['limits'], declared_planes=list(policy['planes']),
        original_selected=True, collision_verified=False, continuous_collision_certified=False,
        self_collision_verified=False, engine_playback_verified=False, quality_approved=False,
        training_admitted=False, release_approved=False,
        scope='All loaded actor triangles and declared scene pairs at declared sample times only. '
            'Depth brackets are floating-point diagnostics. Actor/object center containment requires an '
            'unmodified closed outward-volume mesh; unavailable/near-surface results fail the sampled conditions. '
            'Partner crossings and vertex containment are separate; near/coplanar outcomes remain unresolved. '
            'No object/object, self-collision, continuous-time, exact-arithmetic, engine or quality certification.'), arrays


def run(contacts_path, policy_path, output):
    contacts_path, policy_path, output = [Path(p).resolve() for p in (contacts_path, policy_path, output)]
    if output.exists(): raise ValueError('Fresh geometry audit output required')
    with worker_lock(), threadpool_limits(limits=1):
        bindings = {str(p): sha256(p) for p in (contacts_path, policy_path)}
        scene = SceneContacts(read(contacts_path), contacts_path.parent)
        policy = read(policy_path); policy_for(policy, scene, bindings[str(contacts_path)])
        methods = {n: sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True); archive = output/'implementation'; archive.mkdir()
        for n in methods: shutil.copyfile(ROOT/'scripts'/n, archive/n)
        snapshots = {}
        for i, (path, expected) in enumerate({**bindings, **scene.inputs}.items()):
            dest = output/'input'/f'{i}{Path(path).suffix}'; dest.parent.mkdir(exist_ok=True)
            shutil.copyfile(path, dest)
            if sha256(dest) != expected: raise ValueError('Geometry input snapshot differs')
            snapshots[path] = dict(path=dest.relative_to(output).as_posix(), sha256=expected)
        save(output/'pipeline.json', dict(status='processing'))
        try:
            result, arrays = evaluate(scene, policy, bindings[str(contacts_path)],
                lambda p: save(output/'pipeline.json', p))
            for path, snapshot in snapshots.items():
                if sha256(path) != snapshot['sha256'] or sha256(output/snapshot['path']) != snapshot['sha256']:
                    raise ValueError('Geometry source or snapshot changed')
            if any(sha256(ROOT/'scripts'/n) != h or sha256(archive/n) != h for n, h in methods.items()):
                raise ValueError('Geometry implementation changed')
            np.savez_compressed(output/'observations.npz', **arrays)
            result.update(source_snapshots=snapshots, implementation_sha256=methods,
                contacts_sha256=bindings[str(contacts_path)], policy_sha256=bindings[str(policy_path)],
                observations_sha256=sha256(output/'observations.npz'),
                runtime=dict(python=sys.version, numpy=np.__version__, scipy=scipy.__version__, trimesh=trimesh.__version__))
            save(output/'result.json', result); save(output/'pipeline.json', dict(status='complete', original_selected=True))
            return result
        except Exception as exc:
            save(output/'pipeline.json', dict(status='failed', error=str(exc), original_selected=True)); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('contacts', 'policy', 'output'): p.add_argument(name, type=Path)
    a = p.parse_args(); run(a.contacts, a.policy, a.output)
