"""Original-bound native affine pose rows for explicit surface halfspaces.

Pose bounds are shared with the surface-independent evaluator. Every supplied
region vertex remains a row; these conditions do not accept motion or meshes.
"""
import numpy as np
from native_affine_pose_bounds import PoseBoundsRows, MAXIMUM_ROWS, MAXIMUM_JACOBIAN_BYTES


class RegionPoseRows(PoseBoundsRows):
    def __init__(self, model, time_s, base_controls, active_nodes, world_caps_m, regions,
                 *, length_scale_m=.01, maximum_rows=MAXIMUM_ROWS,
                 maximum_jacobian_bytes=MAXIMUM_JACOBIAN_BYTES):
        if (type(length_scale_m) not in (int,float) or not np.isfinite(length_scale_m)
                or not 0 < length_scale_m <= 1):
            raise ValueError('Positive finite bounded length scale required')
        super().__init__(model,time_s,base_controls,active_nodes,world_caps_m,
                         maximum_rows=maximum_rows,maximum_jacobian_bytes=maximum_jacobian_bytes)
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
        count=self.hard_rows+sum(len(r['vertices']) for r in checked);required=count*self.size*8
        if count>maximum_rows or required>maximum_jacobian_bytes:
            raise ValueError('Complete pose row/Jacobian budget exhausted; no vertices or rows discarded')
        self.regions=checked;self.scale=float(length_scale_m)
        self.report.update(schema='strep-native-affine-region-pose-rows-v1',region_rows=count-self.hard_rows,
            rows=count,jacobian_bytes=required,
            scope='Constructor-bound original affine pose, fixed controls and explicit surface halfspaces. '
                  'Caller must bind source files/clock/permissions and independently check saved motion, '
                  'interpolation, dynamics, contacts, full mesh geometry, engine and human quality.')

    def _rows(self,full,frame):
        values,matrix,world,points,full=super()._rows(full,frame)
        derivative=np.einsum('ij,vjc->vic',self.placement[1],frame[2])
        rows=[values];jac=[matrix]
        for region in self.regions:
            ids=region['vertices'];normal=region['normal_world'];sign=region['sign']
            rows.append((sign*(points[ids]@normal-region['offset_m'])-region['minimum_gap_m'])/self.scale)
            jac.append(sign*np.einsum('i,vic->vc',normal,derivative[ids])/self.scale)
        values=np.concatenate(rows);matrix=np.vstack(jac)
        if not np.isfinite(values).all() or not np.isfinite(matrix).all():
            raise ValueError('Nonfinite native pose condition or derivative')
        return values,matrix,world,points,full
