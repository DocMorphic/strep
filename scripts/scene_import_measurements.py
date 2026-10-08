"""Contacts and complete-vertex primitive diagnostics from bound imported skins.

This is not triangle penetration, partner collision, CCD, physics or quality
approval. Keep these measured screens separate from complete geometry gates.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from native_scene_imported_skin import ImportedSceneSkin
from native_scene_geometry import faces_for
from native_engine_contacts import matrices
from object_geometry import scene_geometry
from scene_import_clock import verify_scene


def scalar(value, label, low=0., high=1.):
    if type(value) not in (int, float) or not np.isfinite(value) or not low <= value <= high:
        raise ValueError('Invalid ' + label)
    return float(value)


def vector(value, label):
    a = np.asarray(value, float)
    if a.shape != (3,) or not np.isfinite(a).all():
        raise ValueError('Finite vector required: ' + label)
    return a


def point(descriptor, name, vertices, worlds, actors):
    if name not in actors:
        raise ValueError('Existing contact actor required')
    if 'surface_vertex' in descriptor:
        vertex = descriptor['surface_vertex']
        if type(vertex) is not int or not 0 <= vertex < len(vertices[name]):
            raise ValueError('Existing integer source surface vertex required')
        return vertices[name][vertex]
    rig = actors[name][0]
    names = [rig.document['nodes'][n]['name'] for n in rig.joints]
    if descriptor.get('joint') not in names:
        raise ValueError('Existing contact joint required')
    m = worlds[name][names.index(descriptor['joint'])]
    return m[:3, 3] + m[:3, :3] @ vector(descriptor.get('offset_m'), 'joint-local offset')


def surface_normal(descriptor, name, vertices, faces):
    if 'surface_vertex' not in descriptor:
        return None
    selected = faces[name][np.any(faces[name] == descriptor['surface_vertex'], axis=1)]
    if not len(selected):
        return None
    tri = vertices[name][selected]
    normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]).sum(axis=0)
    length = np.linalg.norm(normal)
    return None if length <= 1e-12 else normal / length


def measure(scene, request, observed, actors, objects, *, floor_y_m=0., penetration_limit_m=.005):
    """Stream full skins, retain small reproducible contact/geometry tracks."""
    floor_y_m = scalar(floor_y_m, 'declared floor height', -1e6, 1e6)
    limit = scalar(penetration_limit_m, 'vertex penetration screen', 0., 1.)
    pose_check = verify_scene(request, observed, actors, objects)
    if not pose_check['all_precision_screens_passed']:
        raise ValueError('Passing source-bound scene pose audit required before skin measurements')
    times = np.asarray(request['sample_times_s'], float)
    if scene['id'] != request['id'] or set(actors) != set(scene['actors']) or set(objects) != set(scene['objects']):
        raise ValueError('Complete unchanged measurement scene required')
    skins = {name: ImportedSceneSkin(rig, observed['actors'][name]) for name, (rig, _, _) in actors.items()}
    faces = {name: faces_for(rig)[0] for name, (rig, _, _) in actors.items()}
    geometry = {name: scene_geometry(o) for name, o in scene['objects'].items()}
    # Bone matrices in the engine report already include actor placement.
    # Undo it for the raw-weight sum, then apply placement once after skinning.
    placements = {}
    for name, (_, _, pose) in actors.items():
        transform = np.eye(4)
        transform[:3, :3] = Rotation.from_quat(pose['rotation_xyzw']).as_matrix()
        transform[:3, 3] = pose['translation_m']
        placements[name] = transform
    contacts = scene['contacts']; contact_ids = [c['id'] for c in contacts]
    if len(set(contact_ids)) != len(contact_ids):
        raise ValueError('Distinct scene contact IDs required')
    masks = {}; tolerances = {}
    for c in contacts:
        a, b = c['start_frame'], c['end_frame']
        if type(a) is not int or type(b) is not int or not 0 <= a <= b < scene['frame_count']:
            raise ValueError('Contact interval within scene required')
        mask = (times >= a / 30) & (times <= b / 30)
        if not mask.any() or a / 30 not in times or b / 30 not in times:
            raise ValueError('Complete requested contact boundaries required')
        masks[c['id']] = mask
        tolerances[c['id']] = scalar(c.get('tolerance_m', .03), 'authored point tolerance', 1e-12, 1e6)
    arrays = dict(times_s=times)
    floors = {n: [] for n in actors}; vertex_errors = {n: [] for n in actors}
    depths = {(a, o): [] for a in actors for o in objects}
    floor_witness = {n: [] for n in actors}; depth_witness = {key: [] for key in depths}
    tracks = {c['id']: dict(actual=[], target=[], errors=[], normal_angles=[]) for c in contacts}
    maximum_object_projection = {n: 0. for n in objects}
    for i, time in enumerate(times):
        vertices = {}; worlds = {}; poses = {}
        for name, (rig, sampler, _) in actors.items():
            skin = skins[name]
            found = matrices(observed['frames'][i][name])
            world = np.empty_like(found); world[skin.bone_map] = found
            worlds[name] = world
            native = np.linalg.inv(placements[name]) @ world
            p, r = placements[name][:3, 3], placements[name][:3, :3]
            vertices[name] = skin.vertices(native) @ r.T + p
            expected = rig.vertices(sampler.sample(float(time))) @ r.T + p
            vertex_errors[name].append(float(np.linalg.norm(vertices[name] - expected, axis=1).max()))
            height = vertices[name][:, 1] - floor_y_m
            index = int(height.argmin()); floor_witness[name].append(index)
            floors[name].append(max(0., -float(height[index])))
        for name in objects:
            m = matrices([observed['object_frames'][i][name]])[0]
            r = Rotation.from_matrix(m[:3, :3]).as_matrix()
            drift = float(abs(r - m[:3, :3]).max())
            if drift > 1e-5:
                raise ValueError('Imported object basis is not rigid within its existing pose screen')
            maximum_object_projection[name] = max(maximum_object_projection[name], drift)
            poses[name] = (m[:3, 3], r)
        for (actor, obj) in depths:
            depth = geometry[obj].penetration_depth(vertices[actor], *poses[obj])
            j = int(depth.argmax()); depth_witness[(actor, obj)].append(j)
            depths[(actor, obj)].append(float(depth[j]))
        for c in contacts:
            actor = c['actor']; target = c['target']; space = target['space']
            actual = point(c['effector'], actor, vertices, worlds, actors)
            if space == 'world':
                desired = vector(target['point_m'], 'world point')
            elif space == 'object' and target.get('object') in objects:
                p, r = poses[target['object']]
                desired = p + r @ vector(target['point_m'], 'object-local point')
            elif space == 'actor' and target.get('actor') in actors and target['actor'] != actor:
                desired = point(target, target['actor'], vertices, worlds, actors)
            else:
                raise ValueError('Existing world/object/partner target required')
            track = tracks[c['id']]
            track['actual'].append(actual); track['target'].append(desired)
            track['errors'].append(float(np.linalg.norm(actual - desired)))
            normal = surface_normal(c['effector'], actor, vertices, faces)
            desired_normal = None
            normal_target = c.get('normal_target')
            if normal_target:
                direction = vector(normal_target['direction'], 'authored normal')
                if abs(np.linalg.norm(direction) - 1) > 1e-6:
                    raise ValueError('Unit authored normal required')
                if normal_target['space'] == 'world': desired_normal = direction
                elif normal_target['space'] == 'object' and normal_target.get('object') in objects:
                    desired_normal = poses[normal_target['object']][1] @ direction
                else: raise ValueError('Existing world/object normal target required')
            elif space == 'actor':
                other = surface_normal(target, target['actor'], vertices, faces)
                desired_normal = None if other is None else -other
            elif space == 'object':
                try:
                    desired_normal = -poses[target['object']][1] @ geometry[target['object']].local_surface_normal(target['point_m'])
                except ValueError:
                    # An interior/edge target still has a valid point error;
                    # it does not define a unique surface-orientation target.
                    desired_normal = None
            angle = (float(np.rad2deg(np.arccos(np.clip(normal @ desired_normal, -1, 1))))
                     if normal is not None and desired_normal is not None else np.nan)
            track['normal_angles'].append(angle)
    rows = []
    for index, c in enumerate(contacts):
        track = tracks[c['id']]; mask = masks[c['id']]; errors = np.asarray(track['errors'])
        valid = mask & (errors <= tolerances[c['id']]); angles = np.asarray(track['normal_angles'])[mask]
        nearest = int(errors.argmin()); first = float(times[np.flatnonzero(valid)[0]]) if valid.any() else None
        unsupported = [k for k in ('region_contact', 'tangent_target') if k in c]
        normal_available = bool(np.isfinite(angles).all())
        rows.append(dict(id=c['id'], actor=c['actor'], target_space=c['target']['space'],
            tolerance_m=tolerances[c['id']], interval_s=[c['start_frame']/30, c['end_frame']/30],
            contact_samples=int(mask.sum()), maximum_position_error_m=float(errors[mask].max()),
            samples_over_tolerance=int(np.sum(errors[mask] > tolerances[c['id']])),
            first_valid_time_s=first, first_valid_offset_s=None if first is None else first-c['start_frame']/30,
            nearest_time_s=float(times[nearest]), nearest_distance_m=float(errors[nearest]),
            point_samples_passed=bool(valid[mask].all()),
            normal_samples_available=normal_available,
            normal_maximum_error_degrees=float(angles.max()) if normal_available else None,
            normal_diagnostic_limit_degrees=15.,
            normal_diagnostic_passed=bool(normal_available and np.all(angles <= 15.)),
            unsupported_authored_requirements=unsupported,
            authored_requirements_fully_measured=bool(not unsupported and (normal_available or 'normal_target' not in c))))
        for key, value in track.items(): arrays[f'contact_{index}_{key}'] = np.asarray(value)
        arrays[f'contact_{index}_interval_mask'] = mask
    floor_rows = []; object_rows = []
    for index, name in enumerate(actors):
        depth = np.asarray(floors[name]); witness = np.asarray(floor_witness[name]); worst = int(depth.argmax())
        floor_rows.append(dict(actor=name, vertices=len(skins[name].nodes), samples=len(times),
            maximum_depth_m=float(depth[worst]), worst_time_s=float(times[worst]), worst_source_vertex=int(witness[worst]),
            samples_over_limit=int(np.sum(depth > limit)), passed=bool(np.all(depth <= limit)),
            maximum_imported_source_vertex_error_m=max(vertex_errors[name])))
        arrays[f'actor_{index}_floor_depth_m'] = depth
        arrays[f'actor_{index}_floor_witness'] = witness
        arrays[f'actor_{index}_imported_source_vertex_error_m'] = np.asarray(vertex_errors[name])
    for index, ((actor, obj), values) in enumerate(depths.items()):
        depth = np.asarray(values); witness = np.asarray(depth_witness[(actor, obj)]); worst = int(depth.argmax())
        object_rows.append(dict(actor=actor, object=obj, geometry=geometry[obj].record(), vertices=len(skins[actor].nodes),
            samples=len(times), maximum_vertex_depth_m=float(depth[worst]), worst_time_s=float(times[worst]),
            worst_source_vertex=int(witness[worst]), samples_over_limit=int(np.sum(depth > limit)), passed=bool(np.all(depth <= limit))))
        arrays[f'actor_object_{index}_vertex_depth_m'] = depth
        arrays[f'actor_object_{index}_vertex_witness'] = witness
    return dict(scene_id=scene['id'], status='complete', samples=len(times), contacts=rows,
        imported_skins={n: s.report for n, s in skins.items()}, floor=floor_rows, actor_objects=object_rows,
        declared_floor_y_m=floor_y_m, vertex_penetration_limit_m=limit,
        point_contact_samples_passed=bool(rows and all(r['point_samples_passed'] for r in rows)),
        authored_requirements_fully_measured=all(r['authored_requirements_fully_measured'] for r in rows),
        object_raw_basis_projection_error=maximum_object_projection,
        raw_imported_weights_renormalized=False, actor_placement_applied_after_skin=True,
        collision_verified=False, partner_collision_verified=False,
        triangle_penetration_verified=False, continuous_collision_certified=False,
        quality_approved=False, release_approved=False,
        scope='Complete imported bind/weight/triangle identity followed by CPU all-influence skin. '
              'All declared point contacts and all actor vertices against the declared floor and every primitive at the shared finite clock. '
              'Normals are area-weighted source-winding diagnostics; 15 degrees is provisional. '
              'No triangle/object interior queries, partner collision, object containment, GPU skin rendering, physics, anatomy or motion approval.'), arrays
