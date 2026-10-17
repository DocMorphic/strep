"""Original-bound native-key interpolation into complete affine pose rows.

The interpolation map uses central differences; the pose Jacobian remains
analytic. No native key, skin influence or declared constraint is discarded.
Authoring permissions, source-file bindings and saved-clip acceptance belong
to the caller. This module does not approve motion or choose editable keys.
"""
import numpy as np
from scipy.spatial.transform import Rotation
from native_support_clock import NativeSupportSampler
from native_partitioned_affine_pose import PartitionedAffineKeyPose
from native_affine_region_pose import RegionPoseRows

MAXIMUM_KEYS = 4096
MAXIMUM_CONTROLS = 768
MAXIMUM_ROWS = 100000
MAXIMUM_JACOBIAN_BYTES = 64*1024**2


class KeyPoseMap:
    def __init__(self, model, time_s, seed_controls, active_pairs, *,
                 difference_step=1e-6, maximum_keys=MAXIMUM_KEYS,
                 maximum_controls=MAXIMUM_CONTROLS,
                 maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
        if (not isinstance(model, PartitionedAffineKeyPose)
                or not isinstance(model.actor['sampler'], NativeSupportSampler)
                or type(time_s) not in (int, float) or not np.isfinite(time_s)
                or not 0 <= time_s <= model.actor['sampler'].duration
                or type(difference_step) not in (int, float)
                or not np.isfinite(difference_step) or not 1e-8 <= difference_step <= 1e-4
                or type(maximum_keys) is not int or not 1 <= maximum_keys <= MAXIMUM_KEYS
                or type(maximum_controls) is not int or not 1 <= maximum_controls <= MAXIMUM_CONTROLS
                or type(maximum_jacobian_bytes) is not int
                or not 1 <= maximum_jacobian_bytes <= MAXIMUM_JACOBIAN_BYTES):
            raise ValueError('Qualified native affine pose, time and complete bounded map settings required')
        sampler = model.actor['sampler']
        if not np.array_equal(model.source, sampler.sample(float(time_s))):
            raise ValueError('Map and pose must share the unchanged original source time')
        channels = []
        for node in model.nodes:
            found = [c for c in sampler.channels if c[:2] == (node, 'rotation')]
            if len(found) != 1 or found[0][4] != 'LINEAR':
                raise ValueError('One original LINEAR quaternion channel per declared node required')
            channels.append(found[0])
        clock = np.asarray(channels[0][2]); seed = np.asarray(seed_controls)
        if (clock.ndim != 1 or not 1 <= len(clock) <= maximum_keys
                or not np.isfinite(clock).all() or np.any(np.diff(clock) <= 0)
                or seed.dtype.kind not in 'fiu' or seed.shape != (len(clock), len(model.nodes), 3)
                or not np.isfinite(seed).all()
                or np.any(np.linalg.norm(seed, axis=2) > 1)):
            raise ValueError('Complete original-clock bounded seed controls required')
        for c in channels:
            if (not np.array_equal(c[2], clock) or np.asarray(c[3]).shape != (len(clock), 4)
                    or not np.isfinite(c[3]).all() or np.any(np.linalg.norm(c[3], axis=1) < 1e-8)):
                raise ValueError('Complete matching original clocks and finite nonzero quaternions required')
        if (not isinstance(active_pairs, list) or not active_pairs
                or any(not isinstance(p, (list, tuple)) or len(p) != 2
                       or any(type(v) is not int for v in p)
                       or not 0 <= p[0] < len(clock) or p[1] not in model.nodes
                       for p in active_pairs)
                or len(set(map(tuple, active_pairs))) != len(active_pairs)):
            raise ValueError('Distinct explicit existing native-key/node pairs required')
        size = 3*len(active_pairs); required = model.size*size*8
        if size > maximum_controls or required > maximum_jacobian_bytes:
            raise ValueError('Complete interpolation map budget exhausted; no controls discarded')
        self.model = model; self.time_s = float(time_s); self.nodes = tuple(model.nodes)
        self.size = size; self.step = float(difference_step); self.maximum_bytes = maximum_jacobian_bytes
        self.clock = clock.astype(float).copy(); self.seed = seed.astype(float).copy()
        self.caps = model.caps.copy(); self.source = model.source.copy(); self.local = model.local.copy()
        self.placement = tuple(np.array(v, float).copy() for v in model.actor['placement'])
        self.duration = sampler.duration; self.pairs = tuple(map(tuple, active_pairs))
        self.track_ids = np.array([self.nodes.index(n) for _, n in self.pairs])
        self.original_quaternions = np.array([c[3] for c in channels], float)
        self.fixed_quaternions = self.original_quaternions.copy()
        for j in range(len(self.nodes)):
            changed = np.any(self.seed[:, j] != 0, axis=1)
            if np.any(changed):
                original = self.original_quaternions[j, changed]
                q = (Rotation.from_quat(original)*Rotation.from_rotvec(self.seed[changed, j]*self.caps[j])).as_quat()
                q[np.sum(q*original, axis=1) < 0] *= -1
                self.fixed_quaternions[j, changed] = q
        self.fixed_quaternions = self.fixed_quaternions.astype(np.float32).astype(float)
        key = int(np.searchsorted(self.clock, self.time_s, side='left'))
        if key == 0: bracket = [0]
        elif key == len(self.clock): bracket = [len(self.clock)-1]
        elif self.clock[key] == self.time_s: bracket = [key]
        else: bracket = [key-1, key]
        self.bracket = np.array(bracket, int)
        self.dependent = tuple(i for i, (k, _) in enumerate(self.pairs) if k in bracket)
        original = np.array([sampler.value('rotation', self.clock, q, 'LINEAR', self.time_s)
                             for q in self.original_quaternions])
        self.original_inverse = Rotation.from_quat(original).inv()
        self.initial = np.array([self.seed[k, j] for (k, _), j in zip(self.pairs, self.track_ids)]).ravel()
        for a in (self.clock, self.seed, self.caps, self.source, self.local,
                  self.track_ids, self.original_quaternions, self.fixed_quaternions,
                  self.bracket, self.initial, *self.placement):
            a.setflags(write=False)
        self.report = dict(schema='strep-native-key-pose-map-v1', time_s=self.time_s,
                           native_keys=len(self.clock), selected_nodes=len(self.nodes),
                           active_pairs=[list(p) for p in self.pairs], active_controls=self.size,
                           sampled_endpoint_keys=bracket, dependent_pairs=list(self.dependent),
                           map_jacobian_bytes=required, maximum_jacobian_bytes=self.maximum_bytes,
                           maximum_composed_rows=MAXIMUM_ROWS, difference_step=self.step,
                           fixed_endpoint_encoding='Float32, identical to native initializer export',
                           derivative='Central-difference local-control map; analytic native-ball rows',
                           normalized_proposal_component_domain=[-2.,2.],
                           physical_native_rotation_ball_limit=1.,
                           quality_approved=False, release_approved=False,
                           scope='Original-bound interpolation and explicit native rotation balls. '
                                 'Caller binds file/rig/permission provenance and checks saved motion, '
                                 'contacts, complete geometry, dynamics, engine and human quality.')

    def _value(self, value):
        value = np.asarray(value)
        if value.dtype.kind not in 'fiu' or value.shape != (self.size,) or not np.isfinite(value).all() or np.any(np.abs(value) > 2):
            raise ValueError('Complete finite selected native-key proposal coordinates within [-2,2] required')
        return value.astype(float, copy=True)

    def _check(self):
        model = self.model; sampler = model.actor['sampler']
        if not isinstance(sampler, NativeSupportSampler):
            raise ValueError('Constructor-bound native sampler changed')
        if (tuple(model.nodes) != self.nodes or not np.array_equal(model.caps, self.caps)
                or not np.array_equal(model.source, self.source) or not np.array_equal(model.local, self.local)
                or sampler.duration != self.duration
                or any(not np.array_equal(a, b) for a, b in zip(model.actor['placement'], self.placement))
                or not np.array_equal(sampler.sample(self.time_s), self.source)):
            raise ValueError('Constructor-bound original pose, placement or caps changed')
        for j, node in enumerate(self.nodes):
            channels = [c for c in sampler.channels if c[:2] == (node, 'rotation')]
            if (len(channels) != 1 or channels[0][4] != 'LINEAR'
                    or not np.array_equal(channels[0][2], self.clock)
                    or not np.array_equal(channels[0][3], self.original_quaternions[j])):
                raise ValueError('Constructor-bound original native curve changed')

    def _controls(self, value, quantized=False):
        q = self.fixed_quaternions[:, self.bracket].copy(); vectors = value.reshape(-1, 3)
        for p in self.dependent:
            key, _ = self.pairs[p]; track = self.track_ids[p]
            original = self.original_quaternions[track, key]; changed = original.copy()
            if np.any(vectors[p]):
                changed = (Rotation.from_quat(original)*Rotation.from_rotvec(vectors[p]*self.caps[track])).as_quat()
                if changed@original < 0: changed *= -1
            if quantized: changed = changed.astype(np.float32).astype(float)
            q[track, int(np.flatnonzero(self.bracket == key)[0])] = changed
        local_clock = self.clock[self.bracket]
        sampled = np.array([NativeSupportSampler.value('rotation', local_clock, v, 'LINEAR', self.time_s) for v in q])
        return (self.original_inverse*Rotation.from_quat(sampled)).as_rotvec().ravel()/np.repeat(self.caps, 3)

    def controls(self, value, *, quantized=False):
        if type(quantized) is not bool: raise ValueError('Explicit Boolean endpoint quantization required')
        self._check()
        full = self._controls(self._value(value), quantized)
        if not np.isfinite(full).all(): raise ValueError('Nonfinite complete interpolated local controls')
        return full

    def evaluate(self, value):
        self._check(); value = self._value(value); full = self._controls(value)
        jac = np.zeros((self.model.size, self.size))
        for p in self.dependent:
            for axis in range(3):
                column = 3*p+axis; delta = np.zeros(self.size); delta[column] = self.step
                jac[:, column] = (self._controls(value+delta)-self._controls(value-delta))/(2*self.step)
        if not np.isfinite(full).all() or not np.isfinite(jac).all():
            raise ValueError('Nonfinite complete native-key map or Jacobian')
        return full, jac

    def native_rows(self, value):
        self._check(); value = self._value(value); vectors = value.reshape(-1, 3)
        jac = np.zeros((len(self.pairs), self.size))
        for i, v in enumerate(vectors): jac[i, 3*i:3*i+3] = -2*v
        return 1-np.sum(vectors*vectors, axis=1), jac

    def region_rows(self, problem, value):
        if (not isinstance(problem, RegionPoseRows) or problem.model is not self.model
                or problem.report['time_s'] != self.time_s
                or not np.array_equal(problem.coordinates, np.arange(self.model.size))):
            raise ValueError('Same original pose/time with every local control in source order required')
        total = problem.report['rows']+len(self.pairs)
        if total > MAXIMUM_ROWS or total*self.size*8 > self.maximum_bytes:
            raise ValueError('Complete composed row/Jacobian budget exhausted; no rows discarded')
        full, mapping = self.evaluate(value); rows, jac, world, points, full = problem.evaluate(full)
        native, native_jac = self.native_rows(value)
        return np.r_[rows, native], np.vstack([jac@mapping, native_jac]), world, points, full
