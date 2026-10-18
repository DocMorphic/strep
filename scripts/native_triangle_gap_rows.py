"""All supplied triangle-pair rows with shared world-control derivatives.

Exact extrema remain physical rows; conservative smooth rows supply guidance.
Normals are fixed explicit directions. Callers bind rigs, clocks, skin maps,
source permissions and independent saved/full-mesh checks. No contact inferred.
"""
import numpy as np
from native_support_gap import triangle_support_gaps, MAXIMUM_PAIRS

MAXIMUM_ARRAY_BYTES = 64 * 1024**2
MAXIMUM_COLUMNS = 768


def triangle_gap_rows(left, right, normals, *, left_jacobian=None,
                      right_jacobian=None, minimum_gap_m=2e-5,
                      length_scale_m=.01, temperature_m=1e-5,
                      maximum_array_bytes=MAXIMUM_ARRAY_BYTES):
    for value,low,high in [(minimum_gap_m,0.,.1),(length_scale_m,1e-6,1.),(temperature_m,1e-9,.1)]:
        if type(value) not in (int,float) or not np.isfinite(value) or not low<=value<=high:
            raise ValueError('Explicit finite bounded gap, scale and temperature required')
    if type(maximum_array_bytes) is not int or not 1<=maximum_array_bytes<=MAXIMUM_ARRAY_BYTES:
        raise ValueError('Explicit complete array budget up to64MiB required')
    geometry=[np.asarray(v) for v in (left,right,normals)]
    a,b,n=geometry
    if (a.ndim!=3 or a.shape[1:]!=(3,3) or not 1<=len(a)<=MAXIMUM_PAIRS
            or b.shape!=a.shape or n.shape!=(len(a),3)):
        raise ValueError('Complete aligned triangle populations and fixed normals required')
    matrices=[None if v is None else np.asarray(v) for v in (left_jacobian,right_jacobian)]
    columns=0
    for matrix in matrices:
        if matrix is None:continue
        if (matrix.ndim!=4 or matrix.shape[:3]!=a.shape or not 1<=matrix.shape[-1]<=MAXIMUM_COLUMNS
                or columns and matrix.shape[-1]!=columns):
            raise ValueError('Every supplied vertex and identical shared derivative columns required')
        columns=matrix.shape[-1]
    # Includes conservative conversion, geometry workspace, gradients and outputs.
    # Reject the complete population before finite checks or kernel allocation.
    estimated=8*(128*len(a)+3*sum(m.size for m in matrices if m is not None)+3*len(a)*columns)
    if estimated>maximum_array_bytes:
        raise ValueError('Complete input/output/workspace budget exceeded; no pair or column removed')
    for value in geometry+[m for m in matrices if m is not None]:
        if value.dtype.kind not in 'fiu' or value.dtype.itemsize>8 or not np.isfinite(value).all():
            raise ValueError('Complete finite real geometry and derivative arrays required')
    a,b,n=[v.astype(float,copy=False) for v in geometry]
    matrices=[None if m is None else m.astype(float,copy=False) for m in matrices]
    result=triangle_support_gaps(a,b,n,temperature_m=temperature_m)
    exact=(result['projected_gap_m']-minimum_gap_m)/length_scale_m
    smooth=(result['smooth_gap_m']-minimum_gap_m)/length_scale_m
    jacobian=None
    if columns:
        jacobian=np.zeros((len(a),columns))
        with np.errstate(over='ignore',invalid='ignore'):
            for side,matrix in zip(('left','right'),matrices):
                if matrix is not None:
                    jacobian+=np.einsum('pvi,pvic->pc',result[side+'_gradient'],matrix)/length_scale_m
    if (not np.isfinite(exact).all() or not np.isfinite(smooth).all()
            or jacobian is not None and not np.isfinite(jacobian).all()):
        raise ValueError('Nonfinite complete pair output')
    return dict(exact_margins=exact,smooth_margins=smooth,jacobian=jacobian,
        report=dict(schema='strep-native-triangle-gap-rows-v1',rows=len(a),columns=columns,
            both_sides_share_column_space=True,all_pairs_vertices_and_columns_retained=True,
            normals_are_fixed=True,normal_derivatives_included=False,estimated_array_bytes=estimated,
            maximum_array_bytes=maximum_array_bytes,physical_margin_tolerance_added=0.,
            quality_approved=False,release_approved=False,
            scope='Exact original triangle support margins and conservative smooth guidance only. '
                  'Shared-column contributions from both sides accumulate, including self pairs. '
                  'No inferred contacts, saved-motion, intersection, realism or release approval.'))
