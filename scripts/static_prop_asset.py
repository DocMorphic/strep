"""Static GLB prop geometry and explicit triangle landmarks, without repair.

Geometry uses the selected scene's default hierarchy in glTF metre/Y-up space.
This intake is separate from articulated character import. It does not supply
collision, outward-normal, mass, grasp, scene-solver or engine approval.
"""
import hashlib
from pathlib import Path
import tempfile
import numpy as np
from gltf_tools import local_matrix, global_matrices
from rig_asset import read_asset, array, index, parents_of

MAX_BYTES = 32 * 1024**2
MAX_NODES = 512
MAX_VERTICES = 200000
MAX_FACES = 400000
MAX_SURFACES = 512


class StaticPropAsset:
    def __init__(self, document, binary, *, source_sha256=None):
        self.document, self.binary = document, bytes(binary)
        self.source_sha256 = source_sha256
        try:
            self._initialize()
        except (KeyError, TypeError, IndexError, AttributeError) as error:
            raise ValueError('Malformed static prop structure') from error

    @classmethod
    def load(cls, path):
        # Decode an exact bounded byte snapshot; avoid hashing a separate read.
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Static prop GLB exceeds 32 MiB')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(raw)
            document, binary = read_asset(temporary)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return cls(document, binary, source_sha256=hashlib.sha256(raw).hexdigest())

    def _initialize(self):
        if self.document.get('skins') or self.document.get('animations'):
            raise ValueError('Static prop intake requires no skins or animations')
        nodes = self.document['nodes']
        if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
            raise ValueError('Static props require 1–512 nodes')
        self.parents = parents_of(self.document)
        for node in nodes:
            if 'skin' in node or node.get('weights'):
                raise ValueError('Skinned/morphed props unsupported')
            if 'matrix' in node and any(k in node for k in ('translation', 'rotation', 'scale')):
                raise ValueError('Prop node combines matrix and TRS')
            for key,width in (('translation',3),('scale',3),('rotation',4),('matrix',16)):
                if key in node:
                    values = np.asarray(node[key])
                    if values.shape != (width,) or values.dtype.kind not in 'fiu' or not np.isfinite(values).all():
                        raise ValueError('Invalid prop node transform')
            if 'rotation' in node and abs(np.linalg.norm(node['rotation']) - 1) > 1e-5:
                raise ValueError('Prop node quaternion must be normalized')
            matrix = local_matrix(node)
            if not np.isfinite(matrix).all() or not np.allclose(matrix[3], [0,0,0,1], rtol=0, atol=1e-12):
                raise ValueError('Invalid affine prop node transform')
            # Local glTF matrices must decompose to TRS. World shear produced
            # by nonuniform scale above a rotated child is retained exactly.
            lengths = np.linalg.norm(matrix[:3,:3], axis=0)
            present = lengths > 0
            basis = matrix[:3,:3][:,present] / lengths[present]
            if not np.allclose(basis.T @ basis, np.eye(sum(present)), rtol=0, atol=1e-5):
                raise ValueError('Local glTF prop matrix contains shear')
        self.reference = global_matrices(self.document)
        if not np.isfinite(self.reference).all():
            raise ValueError('Non-finite composed prop transforms')
        scene = index(self.document.get('scenes',[]), self.document.get('scene',0), 'scene')
        roots = scene.get('nodes',[])
        if not isinstance(roots,list) or not roots or len(roots)!=len(set(roots)):
            raise ValueError('Distinct selected prop scene roots required')
        active = set()
        def visit(number):
            node = index(nodes,number,'scene node')
            if number in active:
                raise ValueError('Duplicate active prop node')
            active.add(number)
            for child in node.get('children',[]): visit(child)
        for number in roots:
            index(nodes,number,'scene root')
            if self.parents[number] != -1:
                raise ValueError('Prop scene root is not a hierarchy root')
            visit(number)
        self.surfaces = []; positions = []; triangles = []; vertex_count = face_count = 0
        for number in sorted(active):
            node = nodes[number]
            if 'mesh' not in node: continue
            mesh = index(self.document.get('meshes',[]),node['mesh'],'mesh')
            if mesh.get('weights'):
                raise ValueError('Morph weights unsupported in static props')
            for primitive_number,primitive in enumerate(mesh['primitives']):
                if len(self.surfaces) >= MAX_SURFACES:
                    raise ValueError('Static prop exceeds 512 visible surfaces')
                if type(primitive.get('mode',4)) is not int or primitive.get('mode',4) != 4 or primitive.get('targets'):
                    raise ValueError('Unmorphed triangle primitives required')
                attributes = primitive['attributes']
                if any(name.startswith(('JOINTS_','WEIGHTS_')) for name in attributes):
                    raise ValueError('Skin attributes unsupported in static props')
                accessor = index(self.document['accessors'],attributes['POSITION'],'position accessor')
                count = accessor.get('count')
                if type(count) is not int or count < 3 or vertex_count + count > MAX_VERTICES:
                    raise ValueError('Invalid/excessive static prop vertex population')
                if accessor['componentType'] != 5126 or accessor['type'] != 'VEC3' or accessor.get('normalized'):
                    raise ValueError('Prop positions require unnormalized float VEC3')
                local = array(self.document,self.binary,attributes['POSITION'])
                if 'indices' in primitive:
                    entry = index(self.document['accessors'],primitive['indices'],'index accessor')
                    if (entry['type'] != 'SCALAR' or entry['componentType'] not in (5121,5123,5125)
                            or entry.get('normalized') or type(entry['count']) is not int
                            or entry['count'] < 3 or entry['count'] % 3 or entry['count']//3 + face_count > MAX_FACES):
                        raise ValueError('Invalid/excessive unsigned triangle index population')
                    indices = array(self.document,self.binary,primitive['indices']).astype(np.int64)
                else:
                    if count % 3 or count//3 + face_count > MAX_FACES:
                        raise ValueError('Unindexed triangle population invalid/excessive')
                    indices = np.arange(count,dtype=np.int64)
                if np.any(indices < 0) or np.any(indices >= count):
                    raise ValueError('Prop triangle index outside primitive vertices')
                with np.errstate(over='ignore',invalid='ignore'):
                    world = (self.reference[number] @ np.column_stack([local,np.ones(count)]).T).T[:,:3]
                    faces = indices.reshape(-1,3)
                    cross = np.cross(world[faces[:,1]]-world[faces[:,0]],world[faces[:,2]]-world[faces[:,0]])
                    areas = np.linalg.norm(cross,axis=1)
                if not np.isfinite(world).all() or not np.isfinite(areas).all() or np.any(areas <= 0):
                    raise ValueError('Non-finite or degenerate transformed prop triangles')
                self.surfaces.append(dict(node=number,mesh=node['mesh'],primitive=primitive_number,
                    vertices=count,faces=len(faces),vertex_start=vertex_count,face_start=face_count))
                positions.append(world);triangles.append(faces+vertex_count)
                vertex_count += count;face_count += len(faces)
        if not positions:
            raise ValueError('Selected scene has no static triangle geometry')
        self.vertices_m = np.concatenate(positions).astype('<f8')
        self.faces = np.concatenate(triangles).astype('<i8')
        self.vertices_m.setflags(write=False);self.faces.setflags(write=False)
        self.geometry_sha256 = hashlib.sha256(self.vertices_m.tobytes()+self.faces.tobytes()).hexdigest()

    def surface_point(self, face, barycentric):
        if type(face) is not int or not 0 <= face < len(self.faces):
            raise ValueError('Explicit existing prop triangle required')
        raw = np.asarray(barycentric)
        if (raw.shape != (3,) or raw.dtype.kind not in 'fiu'
                or any(isinstance(x,(bool,np.bool_)) for x in barycentric)
                or not np.isfinite(raw).all() or np.any(raw < 0) or np.any(raw > 1)
                or abs(float(raw.sum())-1) > 1e-10):
            raise ValueError('Three finite nonnegative unit-sum barycentric weights required')
        triangle = self.vertices_m[self.faces[face]]
        normal = np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0]);normal /= np.linalg.norm(normal)
        return dict(face=face,barycentric=raw.astype(float).tolist(),position_m=(raw @ triangle).tolist(),
            winding_normal=normal.tolist(),source_sha256=self.source_sha256,geometry_sha256=self.geometry_sha256,
            space='Selected default scene in glTF metre/Y-up asset coordinates; no placement offset',
            outward_normal_verified=False,contact_verified=False)

    def inventory(self):
        return dict(schema='strep-static-prop-intake-v1',source_sha256=self.source_sha256,
            geometry_sha256=self.geometry_sha256,vertices=len(self.vertices_m),faces=len(self.faces),surfaces=self.surfaces,
            bounds_min_m=self.vertices_m.min(axis=0).tolist(),bounds_max_m=self.vertices_m.max(axis=0).tolist(),
            hierarchy_transforms_applied=True,source_scale_retained=True,source_payload_unchanged=True,
            space='Selected default scene in glTF metre/Y-up asset coordinates; no placement offset',
            watertightness_verified=False,collision_verified=False,mass_or_inertia_verified=False,
            scene_solver_integrated=False,engine_import_verified=False,quality_approved=False,release_approved=False)
