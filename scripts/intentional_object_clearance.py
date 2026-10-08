"""Explicit hand/foot contact buffers; physical penetration is never exempted.

Region membership comes from dominant skin joints, not anatomical approval.
Only the named object and inclusive solver contact keys lose their buffer.
"""
import copy
import numpy as np
from floor_contact import Surface
from object_geometry import scene_geometry

SCHEMA = 'strep-intentional-object-clearance-v1'
REGIONS = {'LeftHand', 'RightHand', 'LeftFoot', 'RightFoot'}


def validate(policy, skin, primitives):
    if (not isinstance(policy, dict) or set(policy) != {'schema', 'frame_count', 'contacts'}
            or policy['schema'] != SCHEMA or type(policy['frame_count']) is not int
            or not 3 <= policy['frame_count'] <= 1800 or not isinstance(policy['contacts'], list)
            or len(policy['contacts']) > 4096):
        raise ValueError('Complete explicit intentional-contact policy required')
    regions = Surface(skin).regions
    objects = {entry['id']: geometry for geometry, entry in primitives}
    if len(objects) != len(primitives):raise ValueError('Distinct primitive identities required')
    ids = set()
    for row in policy['contacts']:
        if not isinstance(row, dict) or set(row) != {'id', 'region', 'object', 'geometry', 'point_m',
                'anchor_vertex', 'region_vertices', 'authored_frames', 'solver_frames'}:
            raise ValueError('Invalid intentional-contact record')
        if not isinstance(row['id'], str) or not row['id'] or row['id'] in ids:
            raise ValueError('Distinct intentional contact ids required')
        ids.add(row['id'])
        if (not isinstance(row['region'],str) or not isinstance(row['object'],str)
                or row['region'] not in REGIONS or row['object'] not in objects):
            raise ValueError('Intentional contact requires a declared hand/foot and object')
        expected = regions[row['region']].tolist()
        if (not isinstance(row['region_vertices'],list) or any(type(v) is not int for v in row['region_vertices'])
                or row['region_vertices'] != expected or not expected or type(row['anchor_vertex']) is not int
                or row['anchor_vertex'] not in expected):
            raise ValueError('Exact complete skin region and its anchor required')
        geometry = objects[row['object']]
        if row['geometry'] != geometry.record():raise ValueError('Intentional object geometry changed')
        point = row['point_m']
        if (not isinstance(point, list) or len(point) != 3
                or any(type(v) not in (int, float) or not np.isfinite(v) for v in point)):
            raise ValueError('Finite object-local contact point required')
        distance = geometry.distance_gradient(np.asarray([point]), np.zeros(3), np.eye(3))[0][0]
        if abs(distance) > 1e-9:raise ValueError('Intentional point must lie on the physical object surface')
        authored = row['authored_frames']; solver = row['solver_frames']
        if (not isinstance(authored, list) or len(authored) != 2
                or any(type(f) is not int for f in authored)
                or not 0 <= authored[0] <= authored[1] < policy['frame_count']):
            raise ValueError('Intentional contact interval outside clock')
        original = list(range(authored[0], authored[1]+1))
        if solver != original and solver != original + [authored[1]+1]:
            raise ValueError('Keep complete contact keys and at most the immediate release key')
        if any(type(f) is not int or not 0 <= f < policy['frame_count'] for f in solver):
            raise ValueError('Intentional solver keys outside clock')
    return policy


def compile_policy(scene, actor, contact_ids, skin, release_guards=()):
    if (actor not in scene['actors'] or not isinstance(contact_ids, list)
            or len(set(contact_ids)) != len(contact_ids)):
        raise ValueError('Select distinct actor contacts')
    contacts = scene['contacts']; selected = [c for c in contacts if c['id'] in contact_ids]
    if len(selected) != len(contact_ids) or any(c['actor'] != actor for c in selected):
        raise ValueError('Intentional contacts must belong to the declared actor')
    regions = Surface(skin).regions; rows = []
    for contact in selected:
        target = contact['target']
        if target['space'] != 'object':continue
        if 'region_contact' in contact:raise ValueError('Distributed regions require their separate fitter')
        region = contact['effector'].get('joint'); vertex = contact['effector'].get('surface_vertex')
        if region not in REGIONS:raise ValueError('Intentional clearance supports declared hands and feet')
        a, b = contact['start_frame'], contact['end_frame']
        if type(a) is not int or type(b) is not int or not 0<=a<=b<scene['frame_count']:
            raise ValueError('Intentional contact interval outside clock')
        keys = list(range(a, b+1))
        matching = [g for g in release_guards if g['contact_id'] == contact['id']]
        if matching:
            if (len(matching) != 1 or matching[0]['frame'] != b+1
                    or matching[0]['region'] != region or matching[0]['vertex_id'] != vertex):
                raise ValueError('Release guard does not match intentional contact')
            keys.append(b+1)
        rows.append(dict(id=contact['id'], region=region, object=target['object'],
            geometry=scene_geometry(scene['objects'][target['object']]).record(), point_m=copy.deepcopy(target['point_m']),
            anchor_vertex=vertex, region_vertices=regions[region].tolist(), authored_frames=[a,b], solver_frames=keys))
    policy = dict(schema=SCHEMA, frame_count=scene['frame_count'], contacts=rows)
    primitives = [(scene_geometry(obj),dict(id=name)) for name,obj in scene['objects'].items()]
    return validate(policy, skin, primitives)


def validate_constraints(policy, spec, primitives):
    """Bind each buffer change to the exact explicit target track being fitted."""
    objects = {entry['id']:entry for _,entry in primitives}
    for row in policy['contacts']:
        if spec is None or spec.get('frame_count')!=policy['frame_count']:
            raise ValueError('Intentional clearance requires matching point constraints')
        region=spec['regions'].get(row['region'])
        if region is None or region['mode']!='explicit':raise ValueError('Intentional region must have explicit targets')
        matches=[s for s in region['segments'] if s['start_frame']==row['authored_frames'][0]
                 and s['end_frame']==row['solver_frames'][-1] and s.get('vertex_id')==row['anchor_vertex']]
        if len(matches)!=1 or matches[0]['space']!='track':raise ValueError('Intentional interval or anchor differs from point constraints')
        obj=objects[row['object']];clock=row['solver_frames']
        rotations=np.asarray(obj['rotations']);positions=np.asarray(obj['positions_m'])
        if rotations.shape!=(policy['frame_count'],3,3) or positions.shape!=(policy['frame_count'],3):
            raise ValueError('Complete intentional object clock required')
        expected=positions[clock]+np.einsum('fij,j->fi',rotations[clock],row['point_m'])
        actual=np.asarray(matches[0]['positions_m'])
        if actual.shape!=expected.shape or not np.allclose(actual,expected,atol=1e-9,rtol=0):
            raise ValueError('Intentional object targets differ from fitted point tracks')
    return policy


def margin_tracks(policy, object_id, selected, default):
    """Dense exact population: never drop a contact key or selected vertex."""
    if type(default) not in (int,float) or not np.isfinite(default) or default < 0:
        raise ValueError('Finite nonnegative buffer required')
    selected = np.asarray(selected)
    if selected.ndim != 1 or selected.dtype.kind not in 'iu' or not np.array_equal(selected,np.unique(selected)):
        raise ValueError('Sorted distinct selected vertex identities required')
    margins = np.full((policy['frame_count'],len(selected)), default, dtype=float)
    for row in policy['contacts']:
        if row['object'] != object_id:continue
        columns = np.flatnonzero(np.isin(selected,row['region_vertices']))
        if len(columns) != len(row['region_vertices']):raise ValueError('Complete intentional skin region must be sampled')
        margins[np.ix_(row['solver_frames'],columns)] = 0.
    return margins
