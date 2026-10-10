"""Source-bound material triangles for editable contacts on supplied GLB rigs.

Skin ownership proposes a region; it does not identify an anatomical palm.
Explicit patches retain original triangle winding and native vertex references.
"""
from pathlib import Path
import numpy as np
from rig_asset import RigAsset
from native_support_skin import NativeSupportSkin
from native_scene_geometry import faces_for, METHODS as GEOMETRY_METHODS
from strep import read, sha256

METHODS = tuple(dict.fromkeys(GEOMETRY_METHODS + ('rig_material_patch.py',)))
CANDIDATE_SCHEMA = 'strep-rig-material-candidates-v1'
PATCH_SCHEMA = 'strep-rig-material-patch-v1'
SCOPE = ('Material topology and normalized deformation ownership only. Winding normals are not '
         'anatomical or outward-volume inference. No contact schedule, target approval, '
         'motion feasibility, engine playback, interaction or release approval.')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def settings(children, weight, area, budget, *, upper):
    require(type(children) is bool, 'Explicit child-bone selection required')
    require(type(weight) in (int, float) and np.isfinite(weight) and 0 < weight <= 1,
            'Explicit minimum ownership in (0, 1] required')
    require(type(area) in (int, float) and np.isfinite(area) and 1e-16 <= area <= 1e-4,
            'Explicit positive twice-triangle-area threshold required')
    require(type(budget) is int and 1 <= budget <= upper, 'Bounded complete face budget required')


def point_attribution(rig, vertex_references):
    """Describe actual positive deformation weights; labels do not identify anatomy."""
    from native_scene_contacts import references
    skin = NativeSupportSkin(rig)
    ids = references(vertex_references, skin)
    rows = []
    for ref, vertex in zip(vertex_references, ids):
        weights = skin.weights[vertex]
        require(np.isfinite(weights).all() and np.all(weights >= 0), 'Finite nonnegative skin weights required')
        total = float(np.sum(weights, dtype=np.float64))
        require(total > 0 and abs(total-1) <= 1e-6, 'Normalized complete skin influence population required')
        combined = {}
        for node, weight in zip(skin.nodes[vertex], weights):
            node = int(node)
            require(0 <= node < len(rig.document['nodes']), 'Existing skin node required')
            if weight > 0:
                combined[node] = combined.get(node, 0.) + float(weight)/total
        influences = [dict(node=node, name=rig.document['nodes'][node].get('name'), normalized_weight=weight)
                      for node, weight in sorted(combined.items(), key=lambda item: (-item[1], item[0]))]
        rows.append(dict(vertex_reference=list(ref), influences=influences,
                         dominant_node=influences[0]['node'], dominant_weight=influences[0]['normalized_weight']))
    return dict(schema='strep-rig-contact-attribution-v1', vertices=rows,
                all_positive_influences_retained=True, repeated_slots_combined=True,
                anatomy_verified=False, contact_target_approved=False, quality_approved=False,
                release_approved=False, scope='Normalized skin deformation ownership of explicit original vertices. '
                'Joint names and dominant weights do not identify anatomical contact intent, normals, timing or motion feasibility.')


class MaterialSurface:
    def __init__(self, character, profile_path, *, character_sha256, profile_sha256):
        self.character, self.profile_path = Path(character).resolve(), Path(profile_path).resolve()
        self.inputs = {str(self.character): character_sha256, str(self.profile_path): profile_sha256}
        self.check_inputs()
        self.rig = RigAsset.load(self.character)
        self.profile = read(self.profile_path)
        require(self.profile.get('schema') == 'strep-rig-profile-v1'
                and self.profile.get('reference_pose') == 'default_nodes'
                and self.profile.get('character_sha256') == character_sha256,
                'Matching default-node rig profile required')
        offset = self.profile.get('world_offset_m')
        require(isinstance(offset, list) and len(offset) == 3
                and all(type(v) in (int, float) and v == 0 for v in offset),
                'Explicit zero profile offset required')
        mapping = self.profile.get('mapping')
        require(isinstance(mapping, dict) and bool(mapping)
                and all(isinstance(k, str) and k and type(v) is int and v in self.rig.joints
                        for k, v in mapping.items()) and len(set(mapping.values())) == len(mapping),
                'Distinct mapped skin joints required')
        require(all(p['joints'] is not None for p in self.rig.primitives),
                'Material contact surface requires every primitive to use the validated skin')
        self.faces, population = faces_for(self.rig)
        count = sum(len(p['positions']) for p in self.rig.primitives)
        require(count <= 250000 and len(self.faces) <= 500000,
                'Complete surface exceeds fixed vertex/triangle resource bounds')
        self.skin = NativeSupportSkin(self.rig)
        self.face_references = np.asarray([(p['node'], p['primitive'], i)
            for p in population for i in range(p['faces'])], dtype=np.int64)
        self.face_index = {tuple(ref): i for i, ref in enumerate(self.face_references.tolist())}
        self.points = self.rig.vertices(self.rig.reference)
        require(self.points.shape == (count, 3) and np.isfinite(self.points).all(),
                'Complete finite reference surface required')
        self.source = dict(character_sha256=character_sha256, profile_sha256=profile_sha256,
                           reference_pose='default_nodes', weight_normalization='RigAsset per-vertex sum')
        self.check_inputs()

    def check_inputs(self):
        require(all(sha256(p) == h for p, h in self.inputs.items()), 'Material surface source changed')

    def ownership(self, role, children):
        require(isinstance(role, str) and role in self.profile['mapping'], 'Existing explicit mapped role required')
        node = self.profile['mapping'][role]
        selected = {node}
        if children:
            for joint in self.rig.joints:
                ancestor = joint
                while ancestor >= 0 and ancestor != node:
                    ancestor = self.rig.parents[ancestor]
                if ancestor == node:
                    selected.add(joint)
        weights = np.where(np.isin(self.skin.nodes, sorted(selected)), self.skin.weights, 0).sum(axis=1)
        # Summing normalized eight-slot weights can differ from one by an ULP.
        # A pure subtree has the identical numerator and denominator, exactly 1.
        weights = weights/self.skin.weights.sum(axis=1)
        return sorted(selected), weights

    def candidates(self, role, *, include_children, minimum_weight, minimum_twice_area_m2=1e-12,
                   maximum_faces=20000):
        settings(include_children, minimum_weight, minimum_twice_area_m2, maximum_faces, upper=500000)
        self.check_inputs()
        nodes, weights = self.ownership(role, include_children)
        owned = np.all(weights[self.faces] >= minimum_weight, axis=1)
        ids = np.flatnonzero(owned)
        require(len(ids) <= maximum_faces, 'Complete candidate population exceeds face budget; no subset returned')
        triangles = self.points[self.faces[ids]]
        areas = np.linalg.norm(np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0]), axis=1)
        degenerate = ids[areas <= minimum_twice_area_m2]
        ids = ids[areas > minimum_twice_area_m2]
        vertices = np.unique(self.faces[ids])
        self.check_inputs()
        return dict(schema=CANDIDATE_SCHEMA, source=dict(self.source), role=role,
            mapped_node=self.profile['mapping'][role], selected_nodes=nodes,
            selector=dict(include_children=include_children, minimum_weight=minimum_weight,
                          minimum_twice_area_m2=minimum_twice_area_m2, maximum_faces=maximum_faces),
            complete_surface_faces=len(self.faces), complete_surface_vertices=len(self.points),
            owned_face_count=int(owned.sum()), face_references=self.face_references[ids].tolist(),
            degenerate_face_references=self.face_references[degenerate].tolist(),
            vertex_references=self.skin.vertex_references[vertices].tolist(),
            reference_positions_m=self.points[vertices].tolist(),
            vertex_ownership=weights[vertices].tolist(), requires_explicit_selection=True,
            anatomy_verified=False, contact_target_approved=False, quality_approved=False,
            release_approved=False, scope=SCOPE)

    def patch(self, role, face_references, *, include_children, minimum_weight,
              minimum_twice_area_m2=1e-12, maximum_faces=512, maximum_vertices=256):
        settings(include_children, minimum_weight, minimum_twice_area_m2, maximum_faces, upper=512)
        require(type(maximum_vertices) is int and 3 <= maximum_vertices <= 256,
                'Explicit patch vertex budget within native contact limits required')
        require(isinstance(face_references, list) and 1 <= len(face_references) <= maximum_faces,
                'Explicit nonempty bounded material triangle selection required')
        ids = []
        for ref in face_references:
            require(isinstance(ref, list) and len(ref) == 3 and all(type(i) is int for i in ref)
                    and tuple(ref) in self.face_index, 'Existing [mesh node, primitive, face] references required')
            ids.append(self.face_index[tuple(ref)])
        require(len(set(ids)) == len(ids), 'Distinct material triangles required')
        self.check_inputs()
        nodes, ownership = self.ownership(role, include_children)
        faces = self.faces[ids]; vertices = np.unique(faces)
        require(len(vertices) <= maximum_vertices, 'Complete patch exceeds native contact vertex budget')
        require(np.all(ownership[vertices] >= minimum_weight), 'Patch includes vertices outside declared ownership')
        # Edge connectivity preserves one surface patch across shared indices.
        # Coincident vertices on disconnected seams are not silently welded.
        adjacent = {i: set() for i in range(len(faces))}; edges = {}
        for i, face in enumerate(faces):
            for a, b in zip(face, np.roll(face, -1)):
                edge = tuple(sorted((int(a), int(b))))
                for other in edges.get(edge, []):
                    adjacent[i].add(other); adjacent[other].add(i)
                edges.setdefault(edge, []).append(i)
        seen = set(); pending = [0]
        while pending:
            i = pending.pop()
            if i not in seen:
                seen.add(i); pending.extend(adjacent[i]-seen)
        require(len(seen) == len(faces), 'One edge-connected material patch required; seams are not welded')
        normals = self.measure(self.points, faces, minimum_twice_area_m2)
        require(not normals['degenerate_local_faces'], 'Selected material triangle is degenerate')
        self.check_inputs()
        return dict(schema=PATCH_SCHEMA, source=dict(self.source), role=role,
            mapped_node=self.profile['mapping'][role], selected_nodes=nodes,
            selector=dict(include_children=include_children, minimum_weight=minimum_weight,
                          minimum_twice_area_m2=minimum_twice_area_m2,
                          maximum_faces=maximum_faces, maximum_vertices=maximum_vertices),
            face_references=[list(r) for r in face_references],
            vertices=self.skin.vertex_references[vertices].tolist(),
            reference_positions_m=self.points[vertices].tolist(), vertex_ownership=ownership[vertices].tolist(),
            winding=normals, requires_anatomical_review=True, anatomy_verified=False,
            contact_target_approved=False, quality_approved=False, release_approved=False, scope=SCOPE)

    @staticmethod
    def measure(points, faces, minimum_twice_area_m2):
        triangles = points[faces]
        cross = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
        require(np.isfinite(cross).all(), 'Finite material triangle winding required')
        area = np.linalg.norm(cross, axis=1)
        length = float(np.linalg.norm(cross.sum(axis=0))); total = float(area.sum())
        reliable = bool(np.all(area > minimum_twice_area_m2) and length > minimum_twice_area_m2)
        return dict(triangle_twice_areas_m2=area.tolist(), summed_twice_area_m2=total,
            normal_coherence=length/total if total > 0 else 0., normal_available=reliable,
            area_weighted_winding_normal=(cross.sum(axis=0)/length).tolist() if reliable else None,
            degenerate_local_faces=np.flatnonzero(area <= minimum_twice_area_m2).tolist())

    def posed(self, patch, worlds):
        """Measure selected original material triangles under supplied node worlds.

        This is not an animation sampler or a motion/contact/engine acceptance gate.
        """
        require(isinstance(patch, dict) and patch.get('schema') == PATCH_SCHEMA
                and patch.get('source') == self.source, 'Matching source-bound material patch required')
        require(isinstance(patch.get('selector'), dict) and set(patch['selector']) == {
            'include_children', 'minimum_weight', 'minimum_twice_area_m2', 'maximum_faces', 'maximum_vertices'},
            'Explicit complete patch selector required')
        expected = self.patch(patch.get('role'), patch.get('face_references'), **patch['selector'])
        require(patch == expected, 'Material patch payload changed')
        worlds = np.asarray(worlds, dtype=float)
        require(worlds.shape == self.rig.reference.shape and np.isfinite(worlds).all()
                and np.all(worlds[:, 3] == [0, 0, 0, 1]), 'Complete finite affine node worlds required')
        ids = [self.face_index[tuple(r)] for r in patch['face_references']]
        faces = self.faces[ids]; vertices = np.unique(faces)
        points = self.rig.vertices(worlds)
        require(np.isfinite(points).all(), 'Posed material surface is nonfinite')
        measure = self.measure(points, faces, patch['selector']['minimum_twice_area_m2'])
        self.check_inputs()
        return dict(vertices=patch['vertices'], positions_m=points[vertices].tolist(),
                    triangles_m=points[faces].tolist(), winding=measure, scope=SCOPE,
                    quality_approved=False, release_approved=False)
