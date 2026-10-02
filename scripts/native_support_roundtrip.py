"""Model the editable FP32-matrix/native-preview rotation boundary explicitly."""
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.sparse import vstack
from native_support_orientation import SupportOrientationProblem


def preview_values(values, channels):
    """Preserve unchanged stored keys; convert changed keys through FP32 matrices.

    native_review_support reconstructs only changed quaternion keys into its
    FP32 local matrices. native_candidate_preview then extracts quaternions
    with continuity signs and stores them as FP32. This is a proposal model,
    not the actual NPZ/preview exporter or a native acceptance certificate.
    """
    result={}
    for node,value in values.items():
        stored=np.asarray(value,dtype=np.float32)
        original=np.asarray(channels[node][2],dtype=np.float32)
        if (stored.ndim!=2 or stored.shape[1]!=4 or stored.shape!=original.shape
                or not np.isfinite(stored).all() or not np.isfinite(original).all()
                or np.any(np.linalg.norm(stored,axis=1)<1e-12)
                or np.any(np.linalg.norm(original,axis=1)<1e-12)):
            raise ValueError('Matching finite native quaternion keys required')
        changed=np.any(stored!=original,axis=1)
        q=stored.astype(float)
        if changed.any():
            matrices=Rotation.from_quat(stored[changed]).as_matrix().astype(np.float32)
            q[changed]=Rotation.from_matrix(matrices).as_quat()
            # Match exporter continuity while retaining unchanged source signs.
            for frame in range(1,len(q)):
                if q[frame]@q[frame-1]<0:q[frame]*=-1
        result[node]=q.astype(np.float32).astype(float)
    return result


class SupportRoundtripProblem(SupportOrientationProblem):
    """Use the same authored controls with raw and preview constraint populations."""
    native_roundtrip=True

    def sparsity(self):
        single=super().sparsity()
        return vstack([single,single],format='csr')
