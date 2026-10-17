"""Original-bound native affine pose rows for explicit surface halfspaces.

Only supplied native controls become variables. Fixed controls, every joint
displacement band and every declared region vertex retain their rows. These
are pose proposal conditions, not motion or mesh-collision acceptance.
"""
import numpy as np
from native_partitioned_affine_pose import PartitionedAffineKeyPose


MAXIMUM_ROWS = 100000
MAXIMUM_JACOBIAN_BYTES = 64*1024**2


class RegionPoseRows:
    def __init__(self, model, time_s, base_controls, active_nodes, world_caps_m, regions,
                 *, length_scale_m=.01, maximum_rows=MAXIMUM_ROWS,
                 maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
        if (not isinstance(model, PartitionedAffineKeyPose)
                or type(time_s) not in (int, float) or not np.isfinite(time_s)
                or not 0 <= time_s <= model.actor['sampler'].duration
                or not isinstance(active_nodes, list) or not active_nodes
                or any(type(n) is not int or n not in model.nodes for n in active_nodes)
                or len(set(active_nodes)) != len(active_nodes)
                or type(length_scale_m) not in (int, float)
                or not np.isfinite(length_scale_m) or not 0 < length_scale_m <= 1
                or type(maximum_rows) is not int or not 1 <= maximum_rows <= MAXIMUM_ROWS
                or type(maximum_jacobian_bytes) is not int
                or not 1 <= maximum_jacobian_bytes <= MAXIMUM_JACOBIAN_BYTES):
            raise ValueError('Qualified native pose, time, distinct active nodes and bounded row settings required')
        if not np.array_equal(model.source, model.actor['sampler'].sample(float(time_s))):
            raise ValueError('Pose and declared time must share the unchanged source reference')
        base = np.asarray(base_controls); caps = np.asarray(world_caps_m)
        if (base.dtype.kind not in 'fiu' or base.shape != (model.size,)
                or not np.isfinite(base).all()
                or caps.dtype.kind not in 'fiu' or caps.shape != (len(model.rig.joints),)
                or not np.isfinite(caps).all() or np.any(caps < 1e-6) or np.any(caps > 1)):
            raise ValueError('Complete finite original-relative controls and positive per-joint bands required')
        base = base.astype(float)
        with np.errstate(over='ignore', invalid='ignore'):
            norms = np.linalg.norm(base.reshape(-1, 3), axis=1)
        if not np.isfinite(norms).all() or np.any(norms > 1):
            raise ValueError('Initial original-relative controls must fit every rotation ball')
        if not isinstance(regions, list) or not 1 <= len(regions) <= 32:
            raise ValueError('One to 32 explicit bounded surface regions required')
        checked = []
        for region in regions:
            if not isinstance(region, dict) or set(region) != {
                    'vertices', 'normal_world', 'offset_m', 'sign', 'minimum_gap_m'}:
                raise ValueError('Complete explicit surface halfspace fields required')
            ids = region['vertices']; normal = np.asarray(region['normal_world'])
            if (not isinstance(ids, list) or not ids or len(ids) > len(model.skin.nodes)
                    or any(type(i) is not int or not 0 <= i < len(model.skin.nodes) for i in ids)
                    or len(set(ids)) != len(ids)
                    or normal.dtype.kind not in 'fiu' or normal.shape != (3,)
                    or not np.isfinite(normal).all() or abs(np.linalg.norm(normal)-1) > 1e-8
                    or type(region['sign']) is not int or region['sign'] not in (-1, 1)
                    or any(type(region[k]) not in (int, float) or not np.isfinite(region[k])
                           for k in ('offset_m', 'minimum_gap_m'))
                    or abs(region['offset_m']) > 1e6 or not 0 <= region['minimum_gap_m'] <= .1):
                raise ValueError('Distinct existing region vertices, unit axis, sign and finite distances required')
            checked.append(dict(vertices=np.array(ids, int), normal_world=normal.astype(float).copy(),
                                offset_m=float(region['offset_m']), sign=region['sign'],
                                minimum_gap_m=float(region['minimum_gap_m'])))
        self.size = 3*len(active_nodes)
        if self.size > model.maximum_derivative_controls:
            raise ValueError('Complete active pose derivative request exceeds its declared model budget')
        self.hard_rows = len(model.nodes)+len(model.rig.joints)
        count = self.hard_rows+sum(len(r['vertices']) for r in checked)
        required = count*self.size*8
        if count > maximum_rows or required > maximum_jacobian_bytes:
            raise ValueError('Complete pose row/Jacobian budget exhausted; no vertices or rows discarded')
        self.model = model; self.base = base.copy(); self.caps = caps.astype(float).copy()
        self.source = model.source.copy(); self.local = model.local.copy()
        self.rotation_caps = model.caps.copy(); self.nodes = tuple(model.nodes)
        self.derivative_limit = model.maximum_derivative_controls
        self.placement = tuple(np.array(v, float).copy() for v in model.actor['placement'])
        self.node_indices = np.array([model.nodes.index(n) for n in active_nodes])
        self.coordinates = (3*self.node_indices[:, None]+np.arange(3)).ravel()
        self.regions = checked; self.scale = float(length_scale_m)
        for value in (self.base, self.caps, self.source, self.local, self.coordinates,
                      self.rotation_caps, self.node_indices, *self.placement):
            value.setflags(write=False)
        self.report = dict(schema='strep-native-affine-region-pose-rows-v1', time_s=float(time_s),
            complete_rotation_rows=len(model.nodes), complete_joint_rows=len(model.rig.joints),
            region_rows=count-self.hard_rows, rows=count, active_controls=self.size,
            jacobian_bytes=required, maximum_rows=maximum_rows,
            maximum_jacobian_bytes=maximum_jacobian_bytes,
            quality_approved=False, release_approved=False,
            scope='Constructor-bound original affine pose, fixed controls and explicit surface halfspaces. '
                  'Caller must bind source files/clock/permissions and independently check saved motion, '
                  'interpolation, dynamics, contacts, full mesh geometry, engine and human quality.')

    def _controls(self, value):
        value = np.asarray(value)
        if value.dtype.kind not in 'fiu' or value.shape != (self.size,) or not np.isfinite(value).all():
            raise ValueError('Complete finite active pose coordinates required')
        if (not np.array_equal(self.model.source, self.source) or not np.array_equal(self.model.local, self.local)
                or not np.array_equal(self.model.caps, self.rotation_caps) or tuple(self.model.nodes) != self.nodes
                or self.model.maximum_derivative_controls != self.derivative_limit
                or any(not np.array_equal(a, b) for a, b in zip(self.model.actor['placement'], self.placement))):
            raise ValueError('Constructor-bound original pose reference changed')
        full = self.base.copy(); full[self.coordinates] = value
        return full

    def _rows(self, full, frame):
        """Internal row assembly from this model's freshly computed native frame."""
        world, points, derivative, joint_jac = frame
        position, rotation = self.placement
        points = points@rotation.T+position
        derivative = np.einsum('ij,vjc->vic', rotation, derivative)
        balls = full.reshape(-1, 3); ball_jac = np.zeros((len(balls), self.size))
        for i, node in enumerate(self.node_indices):
            ball_jac[node, 3*i:3*i+3] = -2*balls[node]
        delta = world[self.model.rig.joints, :3, 3]-self.source[self.model.rig.joints, :3, 3]
        rows = [1-np.sum(balls*balls, axis=1), 1-np.sum(delta*delta, axis=1)/self.caps**2]
        jac = [ball_jac, -2*np.einsum('ji,jic->jc', delta, joint_jac)/self.caps[:, None]**2]
        for region in self.regions:
            ids = region['vertices']; normal = region['normal_world']; sign = region['sign']
            rows.append((sign*(points[ids]@normal-region['offset_m'])-region['minimum_gap_m'])/self.scale)
            jac.append(sign*np.einsum('i,vic->vc', normal, derivative[ids])/self.scale)
        values = np.concatenate(rows); matrix = np.vstack(jac)
        if not np.isfinite(values).all() or not np.isfinite(matrix).all():
            raise ValueError('Nonfinite native pose condition or derivative')
        return values, matrix, world, points, full

    def evaluate(self, value):
        full = self._controls(value)
        return self._rows(full, self.model.evaluate_columns(full,self.coordinates))
