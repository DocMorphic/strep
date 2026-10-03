"""Complete imported skin-function and triangle-population correspondence.

Match raw imported weights/binds, never nearest animated vertices. Equivalent
duplicates can share a correspondence; distinct source functions cannot be
silently merged. Triangles preserve multiplicity and cyclic orientation, with
one explicitly reported global winding reversal allowed for engine convention.
"""
from collections import Counter
import numpy as np
from scipy.spatial import cKDTree
from native_engine_contacts import features, packed_weights, matrices, IDENTITY_TOLERANCE
from native_support_skin import NativeSupportSkin
from native_scene_geometry import faces_for
from rig_asset import array


def godot_normalize(weights):
    """Godot 4.7.2 glTF loader's sequential Float32 sum/divide, identity only.

    The version-pinned loader sums slots in order. NumPy's reduction can use a
    different addition tree and change a subsequent unsigned-16 quantization.
    Native motion measurements and raw observed engine weights stay unchanged.
    """
    values = np.asarray(weights,np.float32)
    if values.ndim!=2 or values.shape[1] not in (4,8) or not np.isfinite(values).all() or np.any(values<0):
        raise ValueError('Finite nonnegative four/eight source weights required')
    total = np.zeros(len(values),np.float32)
    for slot in range(values.shape[1]): total = np.add(total,values[:,slot],dtype=np.float32)
    if np.any(total<=0): raise ValueError('Positive source weight sums required')
    return np.divide(values,total[:,None],dtype=np.float32)


def source_engine_weights(rig):
    result = []
    for p in rig.primitives:
        primitive = rig.document['meshes'][rig.document['nodes'][p['node']]['mesh']]['primitives'][p['primitive']]
        attributes = primitive['attributes']
        raw = np.concatenate([array(rig.document,rig.binary,attributes[k]) for k in ('WEIGHTS_0','WEIGHTS_1') if k in attributes],axis=1)
        if len(raw)!=len(p['positions']): raise ValueError('Source raw weight population differs')
        result.append(godot_normalize(raw))
    width = max(r.shape[1] for r in result)
    return np.concatenate([np.pad(r,((0,0),(0,width-r.shape[1]))) for r in result])


def triangle_keys(faces, groups, reverse=False):
    faces = np.asarray(faces)
    if faces.ndim != 2 or faces.shape[1] != 3 or not len(faces) or faces.dtype.kind not in 'iu':
        raise ValueError('Nonempty integer triangle population required')
    if faces.min() < 0 or faces.max() >= len(groups): raise ValueError('Triangle index outside imported population')
    result = []
    for face in faces:
        row = tuple(int(i) for i in np.asarray(groups)[face])
        if reverse: row = row[::-1]
        result.append(min(row, row[1:]+row[:1], row[2:]+row[:2]))
    return Counter(result)


class ImportedSceneSkin:
    def __init__(self, rig, observed):
        names = [rig.document['nodes'][n].get('name') for n in rig.joints]
        if any(not isinstance(n,str) or not n for n in names) or len(set(names)) != len(names):
            raise ValueError('Unique named source bones required for scene engine audit')
        found = observed['bone_names']
        if len(found) != len(names) or len(set(found)) != len(found) or set(found) != set(names):
            raise ValueError('Complete unchanged imported bone population required')
        self.bone_map = np.array([names.index(n) for n in found]); self.names = names
        skin = NativeSupportSkin(rig)
        source_nodes = np.array([rig.joints.index(n) for n in skin.nodes.ravel()]).reshape(skin.nodes.shape)
        expected = features(source_nodes, packed_weights(source_engine_weights(rig)), skin.points, len(names), quantized=True)
        width = 8; nodes = []; weights = []; points = []; triangles = []; refs = []; offset = 0
        if not isinstance(observed['meshes'],list) or not observed['meshes']: raise ValueError('All imported surfaces required')
        seen = set()
        for mesh in observed['meshes']:
            key = (mesh['node'],mesh['surface'])
            if not isinstance(key[0],str) or type(key[1]) is not int or key[1]<0 or key in seen:
                raise ValueError('Distinct imported mesh/surface references required')
            seen.add(key); vertices = np.asarray(mesh['positions'],float)
            ids = np.asarray(mesh['bones']); w = np.asarray(mesh['weights'],float)
            if vertices.ndim != 2 or vertices.shape[1] != 3 or not len(vertices) or not np.isfinite(vertices).all():
                raise ValueError('Finite imported positions required')
            if ids.ndim != 1 or ids.dtype.kind not in 'iu' or ids.size not in (len(vertices)*4,len(vertices)*8) or w.shape != ids.shape:
                raise ValueError('Four/eight complete imported influences required')
            ids = ids.reshape(len(vertices),-1); w = w.reshape(ids.shape)
            binds = mesh['binds']; bones = np.asarray([b['bone'] for b in binds])
            if bones.dtype.kind not in 'iu' or not len(bones) or bones.min()<0 or bones.max()>=len(names) or ids.min()<0 or ids.max()>=len(binds):
                raise ValueError('Existing imported bind/bone references required')
            inverse = matrices([b['pose'] for b in binds])
            p = np.einsum('vkij,vj->vki',inverse[ids],np.c_[vertices,np.ones(len(vertices))])
            n = self.bone_map[bones[ids]]
            features(n,w,p,len(names),quantized=True)  # Validate raw weights; never normalize.
            padding = width-ids.shape[1]
            nodes.append(np.pad(n,((0,0),(0,padding))))
            weights.append(np.pad(w,((0,0),(0,padding))))
            points.append(np.pad(p,((0,0),(0,padding),(0,0))))
            index = np.asarray(mesh['indices'])
            if mesh['primitive_type'] != 3: raise ValueError('Imported triangle primitives required')
            if index.ndim != 1 or len(index)%3 or len(index) and (index.dtype.kind not in 'iu' or index.min()<0 or index.max()>=len(vertices)):
                raise ValueError('Complete valid imported triangle indices required')
            if not len(index): index = np.arange(len(vertices))
            if len(index)%3 or not len(index): raise ValueError('Complete nonindexed imported triangles required')
            triangles.append(index.reshape(-1,3).astype(np.int64)+offset)
            refs.extend([mesh['node'],mesh['surface'],i] for i in range(len(vertices)))
            offset += len(vertices)
        n,w,p = np.concatenate(nodes),np.concatenate(weights),np.concatenate(points)
        actual = features(n,w,p,len(names),quantized=True)
        # Exact equivalent source functions form groups; a near match to two
        # different functions remains ambiguous rather than choosing a best fit.
        unique, source_groups = np.unique(expected.reshape(len(expected),-1),axis=0,return_inverse=True)
        canonical = unique.reshape(-1,len(names),4); tree = cKDTree(canonical.sum(axis=1))
        actual_groups = []; errors = []
        for entry in actual:
            ids = tree.query_ball_point(entry.sum(axis=0), IDENTITY_TOLERANCE*len(names)*2)
            valid = [(i,float(abs(canonical[i]-entry).max())) for i in ids if abs(canonical[i]-entry).max()<=IDENTITY_TOLERANCE]
            if len(valid) != 1: raise ValueError('Unique complete imported skin-function correspondence required')
            actual_groups.append(valid[0][0]); errors.append(valid[0][1])
        actual_groups = np.array(actual_groups,dtype=int)
        if set(actual_groups) != set(source_groups): raise ValueError('Source skin functions lost during import')
        first = np.full(len(unique),len(actual_groups),dtype=int)
        np.minimum.at(first,actual_groups,np.arange(len(actual_groups)))
        if not np.array_equal(actual,actual[first[actual_groups]]):
            raise ValueError('Distinct imported functions cannot share a source vertex representative')
        mapping = first[source_groups]
        source_faces,_ = faces_for(rig); imported_faces = np.concatenate(triangles)
        source_keys = triangle_keys(source_faces,source_groups); imported_keys = triangle_keys(imported_faces,actual_groups)
        if source_keys == imported_keys: winding = 'unchanged'
        elif source_keys == triangle_keys(imported_faces,actual_groups,reverse=True): winding = 'globally-reversed'
        else: raise ValueError('Imported triangle population, multiplicity or winding changed')
        self.mapping = mapping; self.nodes = n[mapping]; self.weights = w[mapping]; self.points = p[mapping]
        self.imported_faces = imported_faces; self.actual_groups = actual_groups; self.source_groups = source_groups
        self.report = dict(source_vertices=len(expected),imported_vertices=len(actual),source_faces=len(source_faces),
            imported_faces=len(imported_faces),imported_surfaces=len(observed['meshes']),
            distinct_skin_functions=len(unique),maximum_bind_function_error=max(errors),
            bind_function_tolerance=IDENTITY_TOLERANCE,triangle_population_pass=True,winding=winding,
            expected_import_encoding='Raw source accessors; sequential Float32 normalize; Float32 unsigned-16 truncate/divide',
            raw_imported_weights_renormalized=False,source_vertex_coverage=True,
            source_mapping=mapping.tolist(),imported_references=[refs[i] for i in mapping])

    def vertices(self, world, ids=None):
        world = np.asarray(world,float)
        if world.shape != (len(self.names),4,4) or not np.isfinite(world).all(): raise ValueError('Complete finite imported world bones required')
        if ids is None: ids = np.arange(len(self.nodes))
        return np.einsum('vkij,vkj,vk->vi',world[self.nodes[ids],:3,:],self.points[ids],self.weights[ids])
