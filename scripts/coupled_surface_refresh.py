"""Refresh selected vertex bindings against complete exported partner meshes."""
import numpy as np
from rig_asset import RigAsset, array
from rig_clip_import import AnimationSampler


def query(problem, paths):
    # Lazy import keeps policy/source CI independent of the local geometry stack.
    import trimesh
    actors = []
    for actor, path in zip(problem.actors, paths):
        rig = RigAsset.load(path)
        faces = array(rig.document, rig.binary, rig.document['meshes'][0]['primitives'][0]['indices']).reshape(-1, 3)
        actors.append((rig, AnimationSampler(rig.document, rig.binary, 0), faces, actor))
    if len(actors) != 2:
        raise ValueError('Two exact actor exports required')
    result = {}
    for number, group in enumerate(problem.groups):
        count = len(group['ids'])
        result.update({f'{number}_'+key: np.empty(shape, dtype=dtype) for key, shape, dtype in [
            ('triangles', (count, 3), int), ('triangle_ids', (count,), int),
            ('bary', (count, 3), float), ('normals', (count, 3), float),
            ('signed_depth', (count,), float), ('closest', (count, 3), float),
            ('points', (count, 3), float)]})
        result[f'{number}_ids'] = group['ids'].copy()
        result[f'{number}_frames'] = np.array([r['frame'] for r in group['rows']])
    for frame in problem.request['frames']:
        selected = [np.flatnonzero(result[f'{n}_frames'] == frame) for n in range(2)]
        if not any(len(ids) for ids in selected):
            continue
        points = [rig.vertices(sampler.sample(frame/30)) @ actor['rotation'].T + actor['translation']
                  for rig, sampler, faces, actor in actors]
        meshes = [trimesh.Trimesh(p, a[2], process=False) for p, a in zip(points, actors)]
        if not all(m.is_watertight and m.is_winding_consistent for m in meshes):
            raise ValueError('Closed consistently wound meshes required')
        for number, (group, indices) in enumerate(zip(problem.groups, selected)):
            source, target = group['source'], group['target']
            for offset in range(0, len(indices), 32):
                rows = indices[offset:offset+32]
                p = points[source][group['ids'][rows]]
                closest, distance, triangles = trimesh.proximity.closest_point(meshes[target], p)
                signed = trimesh.proximity.signed_distance(meshes[target], p)
                vertices = actors[target][2][triangles]
                bary = trimesh.triangles.points_to_barycentric(points[target][vertices], closest)
                if not np.isfinite(bary).all() or bary.min() < -1e-6 or bary.max() > 1+1e-6:
                    raise ValueError('Invalid closest-point barycentric coordinates')
                bary = np.maximum(bary, 0); bary /= bary.sum(axis=1)[:, None]
                vector = p-closest
                normals = vector/np.maximum(distance, 1e-14)[:, None]
                normals *= np.where(signed > 0, -1, 1)[:, None]
                on = distance < 1e-12
                normals[on] = meshes[target].face_normals[triangles[on]]
                np.testing.assert_allclose(np.einsum('ni,ni->n', vector, normals), -signed, atol=1e-8, rtol=0)
                for key, value in [('triangles', vertices), ('triangle_ids', triangles), ('bary', bary),
                                   ('normals', normals), ('signed_depth', signed), ('closest', closest), ('points', p)]:
                    result[f'{number}_{key}'][rows] = value
    if not all(np.isfinite(a).all() for a in result.values()):
        raise ValueError('Nonfinite surface refresh')
    return result


def install(problem, bindings, caps_by_frame):
    for number, group in enumerate(problem.groups):
        np.testing.assert_array_equal(group['ids'], bindings[f'{number}_ids'])
        np.testing.assert_array_equal([r['frame'] for r in group['rows']], bindings[f'{number}_frames'])
        for key in ['triangles', 'bary', 'normals']:
            group[key] = bindings[f'{number}_{key}'].copy()
        group['caps'] = np.array([caps_by_frame[r['frame']] for r in group['rows']])


def per_time_depths(problem, bindings):
    frames = np.concatenate([bindings[f'{n}_frames'] for n in range(2)])
    depths = np.maximum(0., np.concatenate([bindings[f'{n}_signed_depth'] for n in range(2)]))
    return np.array([depths[frames == frame].max(initial=0.) for frame in problem.request['frames']])
