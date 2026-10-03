"""CPU reconstruction of Godot's local skin followed by mesh world transform.

Raw imported weights need not sum to one after UNORM16 quantization. Moving
the outer actor then contributes translation once, rather than weight-scaling
it. This check retains every imported surface vertex, including duplicates.
It is shader algebra on CPU observations, not GPU readback evidence.
"""
import numpy as np
from native_engine_contacts import matrices
from native_engine_clock import clock_echo_matches


class AffineSkin:
    def __init__(self, observed):
        self.names = observed['bone_names']; self.surfaces = []
        for mesh in observed['meshes']:
            vertices = np.asarray(mesh['positions'], dtype='<f8')
            slots = np.asarray(mesh['bones'], dtype=np.int64).reshape(len(vertices), -1)
            weights = np.asarray(mesh['weights'], dtype='<f8').reshape(slots.shape)
            binds = matrices([b['pose'] for b in mesh['binds']])
            bones = np.asarray([b['bone'] for b in mesh['binds']], dtype=np.int64)[slots]
            points = np.einsum('vkij,vj->vki', binds[slots], np.c_[vertices, np.ones(len(vertices))])
            self.surfaces.append((mesh['node'], bones, weights, points))
        self.nodes = set(m['node'] for m in observed['meshes'])
        self.vertices = sum(len(s[1]) for s in self.surfaces)

    def transforms(self, frame):
        if set(frame['mesh_world']) != self.nodes:
            raise ValueError('Complete imported mesh world population required')
        skeleton = matrices(frame['skeleton_world'])
        meshes = {n: matrices(frame['mesh_world'][n]) for n in self.nodes}
        if skeleton.shape != (4, 4) or abs(np.linalg.det(skeleton[:3, :3])) < 1e-12:
            raise ValueError('Invertible skeleton world transform required')
        return skeleton, meshes

    def positions(self, frame):
        skeleton, meshes = self.transforms(frame)
        bones = matrices(frame['bones'])
        if bones.shape != (len(self.names), 4, 4):
            raise ValueError('Whole affine skin bone population required')
        local = np.linalg.inv(skeleton) @ bones
        result = []
        for node, ids, weights, points in self.surfaces:
            skinned = np.einsum('vkij,vkj,vk->vi', local[ids, :3, :], points, weights)
            mesh = meshes[node]
            result.append(skinned @ mesh[:3, :3].T + mesh[:3, 3])
        return np.concatenate(result)


def compare(reference, observed, embedded, frames, previews, times, limit):
    if reference['bone_names'] != observed['bone_names'] or reference['meshes'] != observed['meshes']:
        raise ValueError('Complete raw surface ordering/data must survive root modes')
    skin = AffineSkin(observed)
    errors = np.asarray([np.linalg.norm(skin.positions(a)-skin.positions(b), axis=1).max()
                         for a, b in zip(embedded, frames)], dtype='<f8')
    preview_errors = []
    for preview in previews:
        ids = [i for i, t in enumerate(times) if clock_echo_matches(t, preview['time_s'])]
        if len(ids) != 1:
            raise ValueError('Exact affine skin preview clock required')
        preview_errors.append(float(np.linalg.norm(skin.positions(preview)-skin.positions(frames[ids[0]]), axis=1).max()))
    nodes = sorted(skin.nodes)
    arrays = {'affine_skin_errors_m': errors,
              'affine_skin_preview_errors_m': np.asarray(preview_errors, dtype='<f8'),
              'skeleton_world': matrices([f['skeleton_world'] for f in frames]),
              'mesh_world': np.asarray([[matrices(f['mesh_world'][n]) for n in nodes] for f in frames], dtype='<f8')}
    maximum = float(errors.max()); preview_maximum = max(preview_errors, default=0.)
    return dict(imported_vertices=skin.vertices, mesh_nodes=nodes,
                maximum_mode_affine_skin_difference_m=maximum, maximum_preview_affine_skin_difference_m=preview_maximum,
                limit_m=limit, passed=max(maximum, preview_maximum) <= limit,
                weights_renormalized=False, gpu_readback_verified=False), arrays
