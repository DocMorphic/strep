"""Observed engine skin at hypothetical native FK for correction calculations.

This view preserves raw imported weights and every source vertex/reference.
It does not predict engine pose arithmetic or validate a future export.
"""
import copy
import numpy as np
from native_scene_contacts import SceneContacts
from native_scene_engine import EngineObservations
from native_support_skin import NativeSupportSkin
from paired_approach_basis import BoundSkin


class EngineSkinView(BoundSkin):
    def __init__(self, observations, actor):
        if not isinstance(observations, EngineObservations) or actor not in observations.scene.actors:
            raise ValueError('Validated engine observations and an existing actor required')
        source = observations.scene.actors[actor]['rig']
        imported = observations.skins[actor]
        native = NativeSupportSkin(source)
        if (imported.report['source_vertices'] != len(native.nodes)
                or not imported.report['triangle_population_pass']
                or not imported.report['source_vertex_coverage']):
            raise ValueError('Complete imported source correspondence required')
        self.nodes = np.asarray(source.joints, int)[imported.nodes].copy()
        self.weights = imported.weights.copy()
        self.points = imported.points.copy()
        self.vertex_references = native.vertex_references.copy()
        self.primitive_offsets = list(native.primitive_offsets)
        self.node_count = len(source.document['nodes'])
        for value in (self.nodes, self.weights, self.points, self.vertex_references):
            value.setflags(write=False)
        self.report = dict(model='observed-engine-skin-at-native-FK',
                           source_vertices=len(self.nodes), source_faces=imported.report['source_faces'],
                           raw_imported_weights_renormalized=False, source_vertex_coverage=True,
                           future_engine_pose_verified=False, quality_approved=False, release_approved=False)

    def vertices(self, world):
        world = np.asarray(world, float)
        if world.shape != (self.node_count, 4, 4) or not np.isfinite(world).all():
            raise ValueError('Complete finite native node worlds required')
        return np.einsum('vkij,vkj,vk->vi', world[self.nodes, :3, :], self.points, self.weights)


class _RigView:
    def __init__(self, source, skin): self.source = source; self.skin = skin
    def __getattr__(self, name): return getattr(self.source, name)
    def vertices(self, world): return self.skin.vertices(world)


class EngineSkinScene(SceneContacts):
    """Read-only scene view usable by SceneProblem and full geometry queries.

    Callers must bind the actual raw observations and supporting receipts.
    Checking those supplied file hashes is not an authenticity/release audit.
    Source clips, targets, geometry clocks, permissions and limits stay intact.
    """
    def __init__(self, scene, observations, engine_bindings):
        if (not isinstance(scene, SceneContacts) or not isinstance(observations, EngineObservations)
                or observations.scene is not scene or set(observations.skins) != set(scene.actors)):
            raise ValueError('Complete engine observations for this exact source scene required')
        if (not isinstance(engine_bindings, dict) or not engine_bindings
                or any(not isinstance(p, str) or not p or not isinstance(h, str)
                       or len(h) != 64 or any(c not in '0123456789abcdef' for c in h)
                       for p, h in engine_bindings.items())):
            raise ValueError('Explicit raw-engine evidence file bindings required')
        if any(p in scene.inputs and scene.inputs[p] != h for p, h in engine_bindings.items()):
            raise ValueError('Engine evidence cannot replace a source binding')
        self.source = scene
        self.duration = scene.duration
        self.inputs = {**scene.inputs, **engine_bindings}
        self.objects = copy.deepcopy(scene.objects)
        self.rows = copy.deepcopy(scene.rows)
        self.actors = {}
        for name, actor in scene.actors.items():
            skin = EngineSkinView(observations, name)
            self.actors[name] = dict(actor, skin=skin, rig=_RigView(actor['rig'], skin))
        self.check_inputs()

    def evaluate(self, **kwargs):
        result, arrays = super().evaluate(**kwargs)
        result.update(loaded_skin_weights_normalized=False,
                      measurement_source='Observed raw engine skin at hypothetical native FK; source object poses',
                      future_engine_pose_verified=False)
        return result, arrays
