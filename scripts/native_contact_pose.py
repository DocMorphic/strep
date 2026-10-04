"""Bounded single-pose contact diagnostics on explicit native rig channels.

This is a temporal relaxation, not an animation solver or a release decision.
Full triangle geometry, imported skin and anatomy need separate validation.
"""
import time
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from native_scene_contacts import fields, scalar
from native_surface_contact import policy_for
from native_scene_geometry import faces_for
from paired_guarded_temporal import world_from_local


def rotation_ball(raw, radians):
    raw = np.asarray(raw, float); radians = np.asarray(radians, float)
    if (raw.ndim != 2 or raw.shape[1] != 3 or radians.shape != (len(raw),)
            or not np.isfinite(raw).all() or np.max(abs(raw), initial=0) > 100
            or not np.isfinite(radians).all() or np.any(radians <= 0)):
        raise ValueError('Complete finite bounded rotation coordinates and positive limits required')
    return radians[:, None] * raw / np.sqrt(1 + np.sum(raw * raw, axis=1))[:, None]


class ContactPose:
    def __init__(self, scene, policy, digest, time_s, permissions):
        self.scene = scene; self.time = scalar(time_s, 0, scene.duration, 'pose time')
        self.limits, _ = policy_for(policy, scene, digest)
        fields(permissions, ('schema', 'contacts_sha256', 'actors'), 'pose permissions')
        if permissions['schema'] != 'strep-native-contact-pose-permissions-v1' or permissions['contacts_sha256'] != digest:
            raise ValueError('Pose permissions must bind the exact contacts')
        actors = permissions['actors']
        if not isinstance(actors, dict) or not actors or set(actors) - set(scene.actors):
            raise ValueError('Explicit permissions for existing actors required')
        self.source = {n: a['sampler'].sample(self.time) for n, a in scene.actors.items()}
        self.local = {}; self.edits = []; self.size = 0
        for name, declaration in actors.items():
            fields(declaration, ('rotation_tracks', 'maximum_joint_displacement_m'), 'pose actor permissions')
            displacement = scalar(declaration['maximum_joint_displacement_m'], 1e-6, .22, 'pose joint displacement')
            actor = scene.actors[name]; rig = actor['rig']; world = self.source[name]
            local = np.array([np.linalg.solve(world[parent], world[i]) if parent >= 0 else world[i]
                for i, parent in enumerate(rig.parents)])
            basis = local[:, :3, :3]
            if (not np.allclose(basis @ basis.transpose(0, 2, 1), np.eye(3), atol=1e-8, rtol=0)
                    or not np.allclose(np.linalg.det(basis), 1, atol=1e-8, rtol=0)):
                raise ValueError('Proper rigid source local bases required')
            self.local[name] = local
            tracks = declaration['rotation_tracks']; seen = set()
            if not isinstance(tracks, list) or not 1 <= len(tracks) <= 32:
                raise ValueError('Choose 1-32 explicit rotation tracks')
            for track in tracks:
                fields(track, ('node', 'maximum_change_degrees'), 'pose rotation permission')
                node = track['node']
                if type(node) is not int or node not in rig.joints or node in seen:
                    raise ValueError('Distinct existing skin-joint rotation nodes required')
                channels = [c for c in actor['sampler'].channels if c[:2] == (node, 'rotation')]
                if len(channels) != 1 or channels[0][4] != 'LINEAR':
                    raise ValueError('Existing LINEAR native rotation channel required')
                maximum = scalar(track['maximum_change_degrees'], 1e-6, 45, 'pose rotation change')
                self.edits.append(dict(actor=name, node=node, limit=np.deg2rad(maximum), displacement=displacement))
                seen.add(node); self.size += 3
        if self.size > 96:
            raise ValueError('Complete pose exceeds 96 controls; no truncation')
        self.faces = {n: faces_for(a['rig'])[0] for n, a in scene.actors.items()}
        self.rows = []
        for entry in scene.rows:
            row = entry['authored']
            if not row['interval_s'][0] <= self.time <= row['interval_s'][1]:
                continue
            def groups(name, ids, reduction):
                selected = [ids] if reduction == 'centroid' else [[int(i)] for i in ids]
                return [np.flatnonzero(np.isin(self.faces[name], g).any(1)) for g in selected]
            self.rows.append(dict(entry=entry, source_faces=groups(row['actor'], entry['ids'], row['reduction']),
                target_faces=groups(row['target']['actor'], entry['target_ids'], row['target']['reduction'])
                    if row['target']['space'] == 'actor' else None,
                normals=policy['contacts'][row['id']]['target_normal']))
        if not self.rows:
            raise ValueError('At least one active contact at the exact pose time required')

    def worlds(self, controls):
        controls = np.asarray(controls, float)
        if controls.shape != (self.size,):
            raise ValueError('Matching complete pose controls required')
        deltas = rotation_ball(controls.reshape(-1, 3), [e['limit'] for e in self.edits])
        locals_ = {n: a.copy() for n, a in self.local.items()}
        for delta, edit in zip(deltas, self.edits):
            name, node = edit['actor'], edit['node']
            locals_[name][node, :3, :3] = self.local[name][node, :3, :3] @ Rotation.from_rotvec(delta).as_matrix()
        return {n: world_from_local(locals_[n][None], self.scene.actors[n]['rig'].parents)[0]
            if n in locals_ else source.copy() for n, source in self.source.items()}, deltas

    def vertices(self, worlds):
        result = {}
        for name, actor in self.scene.actors.items():
            skin = actor['skin']; p, r = actor['placement']
            result[name] = np.einsum('vkij,vkj,vk->vi', worlds[name][skin.nodes, :3, :], skin.points, skin.weights) @ r.T + p
        return result

    def measure(self, controls):
        worlds, deltas = self.worlds(controls); vertices = self.vertices(worlds)
        cross = {}; areas = {}
        for name, faces in self.faces.items():
            tri = vertices[name][faces]; cross[name] = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); areas[name] = np.linalg.norm(cross[name], axis=1)
        def oriented(name, groups):
            values = []; available = []
            for ids in groups:
                summed = cross[name][ids].sum(0); length = np.linalg.norm(summed); total = areas[name][ids].sum()
                ok = bool(len(ids) and np.all(areas[name][ids] > self.limits['minimum_normal_area_m2'])
                    and length > self.limits['minimum_normal_area_m2'] and total > 0
                    and length / total >= self.limits['minimum_normal_coherence'])
                available.append(ok); values.append(summed / length if ok else np.zeros(3))
            return np.asarray(values), np.asarray(available)
        residuals = []; records = []
        chord = 2 * np.sin(np.deg2rad(self.limits['maximum_opposition_error_degrees']) / 2)
        for data in self.rows:
            entry = data['entry']; row = entry['authored']; target = row['target']; name = row['actor']
            left = vertices[name][entry['ids']]
            if row['reduction'] == 'centroid': left = left.mean(0, keepdims=True)
            na, good = oriented(name, data['source_faces'])
            if target['space'] == 'actor':
                right = vertices[target['actor']][entry['target_ids']]
                if target['reduction'] == 'centroid': right = right.mean(0, keepdims=True)
                nb, target_good = oriented(target['actor'], data['target_faces']); good &= target_good
            else:
                right = entry['target_ids'].copy(); nb = np.asarray(data['normals']['normals'], float)
                if target['space'] == 'object':
                    p, r = self.scene.object_poses(target['object'], [self.time]); right = right @ r[0].T + p[0]; nb = nb @ r[0].T
            error = np.linalg.norm(right - left, axis=1); direction = np.linalg.norm(na + nb, axis=1)
            source_side = np.einsum('ij,ij->i', na, right - left); target_side = np.einsum('ij,ij->i', -nb, right - left)
            residuals.extend(error / row['limits']['position_m'] - 1)
            residuals.extend(np.where(good, (direction - chord) / max(chord, .001), 100.))
            residuals.extend(np.where(good, (-source_side - self.limits['backface_allowance_m']) / .005, 100.))
            residuals.extend(np.where(good, (-target_side - self.limits['backface_allowance_m']) / .005, 100.))
            angles = np.rad2deg(np.arccos(np.clip(-np.einsum('ij,ij->i', na, nb), -1, 1)))
            records.append(dict(contact=row['id'], points=len(left), normals_available=good.tolist(),
                position_errors_m=error.tolist(), opposition_errors_degrees=[float(a) if ok else None for a, ok in zip(angles, good)],
                source_side_m=source_side.tolist(), target_side_m=target_side.tolist()))
        for name in self.local:
            ids = self.scene.actors[name]['rig'].joints
            limit = next(e['displacement'] for e in self.edits if e['actor'] == name)
            residuals.extend(np.linalg.norm(worlds[name][ids, :3, 3] - self.source[name][ids, :3, 3], axis=1) / limit - 1)
        return np.asarray(residuals), dict(contacts=records, rotation_changes_degrees=np.rad2deg(np.linalg.norm(deltas, axis=1)).tolist(),
            time_s=self.time, active_contacts=len(self.rows), maximum_normalized_violation=float(np.maximum(residuals, 0).max()),
            temporal_constraints_checked=False, anatomical_reviewed=False, quality_approved=False, release_approved=False), worlds, vertices


def fit(problem, *, evaluations=60, geometry_penetration_m=.005, maximum_seconds=240., maximum_calls=10000):
    """All vertices guide primitive avoidance; full triangles decide separately."""
    if type(evaluations) is not int or not 1 <= evaluations <= 300:
        raise ValueError('Choose 1-300 explicit pose evaluations')
    tolerance = scalar(geometry_penetration_m, 0, .1, 'pose geometry guide penetration')
    maximum_seconds = scalar(maximum_seconds, 1, 3600, 'pose search time budget')
    if type(maximum_calls) is not int or not 1 <= maximum_calls <= 50000:
        raise ValueError('Explicit complete objective-call budget required')
    history = []; best = None; best_score = None; started = time.monotonic()
    class BudgetExhausted(Exception): pass
    def objective(value):
        nonlocal best, best_score
        if history and (len(history) >= maximum_calls or time.monotonic() - started >= maximum_seconds):
            raise BudgetExhausted()
        residual, report, _, vertices = problem.measure(value)
        geometric = []
        for name, obj in problem.scene.objects.items():
            p, r = problem.scene.object_poses(name, [problem.time])
            for points in vertices.values():
                geometric.extend((obj['geometry'].penetration_depth(points, p[0], r[0]) - tolerance) / max(tolerance, .001))
        positive = np.maximum(np.r_[residual, geometric], 0)
        score = (float(positive.max()), float(positive @ positive))
        if best_score is None or score < best_score: best_score = score; best = value.copy()
        history.append(dict(call=len(history) + 1, maximum_violation=score[0], squared_violation=score[1]))
        return np.r_[positive, .0001 * value]
    initial = np.zeros(problem.size)
    try:
        result = least_squares(objective, initial, bounds=(-20, 20), max_nfev=evaluations, ftol=1e-10, xtol=1e-10, gtol=1e-10)
        exhausted = bool(result.status == 0)
        solver = dict(solver_success=bool(result.success), solver_message=str(result.message), evaluations=int(result.nfev),
            budget_exhausted=exhausted, evaluation_budget_exhausted=exhausted, time_or_call_budget_exhausted=False)
    except BudgetExhausted:
        solver = dict(solver_success=False, solver_message='Explicit pose time or objective-call budget exhausted', evaluations=None,
            budget_exhausted=True, evaluation_budget_exhausted=False, time_or_call_budget_exhausted=True)
    return best, dict(**solver, elapsed_s=time.monotonic()-started,
        objective_calls=len(history), history=history, selected_score=list(best_score),
        vertex_geometry_guide_only=True, full_triangle_geometry_checked=False, quality_approved=False, release_approved=False)
