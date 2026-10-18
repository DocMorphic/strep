"""Complete interpolated pose balls, retaining transverse vector information.

Rotation vectors are normalized controls with radius one. Joint vectors stay
in metres with original radii, preserving the legacy squared-margin arithmetic.
Local affine cones never replace original raw/saved pose and geometry checks.
"""
import numpy as np
from native_basis_pose_rows import BasisPoseRows


class BasisPoseNormRows(BasisPoseRows):
    def evaluate_vectors(self,value,*,jacobian=True,encoded=False):
        if type(jacobian) is not bool or type(encoded) is not bool or jacobian and encoded:
            raise ValueError('Explicit raw derivatives or value-only encoded mode required')
        rows=self.report['rows'];columns=self.columns
        extra=8*(6*rows+((4*rows+self._model.size)*columns if jacobian else 0))
        if self.report['estimated_owned_array_bytes']+extra>self._maximum_working_bytes:
            raise ValueError('Complete pose vector/chain workspace exceeds budget; no row or column removed')
        response=super().evaluate(value,jacobian=jacobian,encoded=encoded)
        self._check();world=response['world'];full=response['full_controls'];rotation_rows=self.report['rotation_rows']
        delta=world[self._joints,:3,3]-self._map['source'][self._joints,:3,3]
        vectors=np.vstack([full.reshape(-1,3),delta]);radii=np.r_[np.ones(rotation_rows),self._caps]
        canonical=1-np.sum(vectors*vectors,axis=1)/radii**2
        if canonical.tobytes()!=response['margins'].tobytes():
            raise ValueError('Complete norm vectors differ from original squared-margin arithmetic')
        matrix=None
        if jacobian:
            endpoints,basis_jac=self._basis.endpoint_map(value,self._mapper.bracket.tolist(),jacobian=True)
            controls,local=self._mapper.evaluate(endpoints.ravel())
            if controls.tobytes()!=full.tobytes():raise ValueError('Repeated original pose-map chain changed controls')
            control_jac=local@basis_jac
            matrix=np.concatenate([control_jac.reshape(rotation_rows,3,columns),response['world_jacobian'][self._joints,:3,3,:]])
            projected=-2*np.einsum('ri,ric->rc',vectors,matrix)/radii[:,None]**2
            if not np.all(np.abs(projected-response['jacobian'])<=1e-10*(1+np.abs(response['jacobian']))):
                raise ValueError('Complete scalar and vector pose derivatives differ')
        if (vectors.shape!=(rows,3) or not np.isfinite(vectors).all()
                or matrix is not None and (matrix.shape!=(rows,3,columns) or not np.isfinite(matrix).all())):
            raise ValueError('Complete finite pose vectors and every derivative column required')
        self._check()
        return dict(vectors=vectors,jacobian=matrix,radii=radii,canonical_margins=canonical,
            world=world,world_jacobian=response['world_jacobian'],full_controls=full,
            report=dict(schema='strep-native-basis-pose-norm-rows-v1',rows=rows,columns=columns,rotation_rows=rotation_rows,
                joint_rows=rows-rotation_rows,rotation_units='normalized original rotation controls',joint_units='metres',
                canonical_margins_byte_identical=True,all_rows_and_columns_retained=True,encoded=encoded,
                estimated_additional_array_bytes=extra,physical_margin_tolerance_added=0.,quality_approved=False,release_approved=False,
                scope='Original native-basis pose vectors with complete raw Jacobians, fixed original radii and canonical squared margins. '
                      'Encoded mode is value-only interpolation, not independent saved-file approval. '
                      'Affine cones do not certify nonlinear/Float32 poses, full geometry, dynamics or motion quality.'))
