"""Relative vertex/target-face vectors for conservative local partner depth guards."""
import copy
import numpy as np
from scipy import sparse
from native_partner_surface_rows import SurfaceRows
from native_scene_geometry import faces_for
from native_surface_key_jacobian import linearize as scalar_linearize
from native_scene_norms import NormRows


def _expanded(surface,indices,maximum_vectors):
    ids=np.asarray(indices)
    if (type(maximum_vectors) is not int or not 1<=maximum_vectors<=33333 or ids.ndim!=1 or not len(ids) or len(ids)>maximum_vectors
            or ids.dtype.kind not in 'iu' or np.any(ids<0) or np.any(ids>=len(surface.rows)) or np.any(np.diff(ids.astype(np.int64))<=0)
            or any(isinstance(v,(bool,np.bool_)) for v in np.asarray(indices,dtype=object).flat)):
        raise ValueError('Complete sorted distinct declared vector indices within budget required')
    faces={};rows=[]
    for index in ids:
        row=surface.rows[int(index)];left=row.get('left');right=row.get('right');triangle=row.get('target_triangle')
        if (row.get('kind')!='penetrating-vertex' or not isinstance(left,dict) or not isinstance(right,dict)
                or left.get('actor') not in surface.scene.actors or right.get('actor') not in surface.scene.actors or left['actor']==right['actor']
                or left.get('weights')!=[1.] or not isinstance(left.get('vertices'),list) or len(left['vertices'])!=1
                or type(left['vertices'][0]) is not int or not 0<=left['vertices'][0]<len(surface.scene.actors[left['actor']]['skin'].nodes)
                or type(triangle) is not int or row.get('constant_m')!=0):raise ValueError('Distinct partner vertex and explicit target-face material point required')
        name=right['actor']
        if name not in faces:faces[name]=faces_for(surface.scene.actors[name]['rig'])[0]
        if not 0<=triangle<len(faces[name]) or right.get('vertices')!=faces[name][triangle].tolist():raise ValueError('Canonical target triangle vertex order required')
        weights=np.asarray(right.get('weights'),float)
        if weights.shape!=(3,) or not np.isfinite(weights).all() or np.any(weights<0) or abs(weights.sum()-1)>1e-10:raise ValueError('Convex target triangle weights required')
        for axis in np.eye(3):
            value=copy.deepcopy(row);value['normal_world']=axis.tolist();value['right']['weights']=(weights/weights.sum()).tolist();rows.append(value)
    return SurfaceRows(surface.scene,rows,{}),ids.astype(int)


def evaluate(surface,indices,vertices=None,*,maximum_vectors=33333):
    expanded,_=_expanded(surface,indices,maximum_vectors)
    return expanded.gaps(vertices).reshape(-1,3)


def linearize(surface,indices,layouts,*,value=None,maximum_nonzeros=6000000,maximum_vectors=33333):
    expanded,ids=_expanded(surface,indices,maximum_vectors)
    if type(maximum_nonzeros) is not int or not 1<=maximum_nonzeros<=6000000:raise ValueError('Complete bounded sparse budget required')
    values,jac,meta=scalar_linearize(expanded,layouts,value=value,maximum_nonzeros=maximum_nonzeros)
    meta.update(vector_rows=len(ids),source_row_indices=ids.tolist(),canonical_target_faces_verified=True,convex_weight_sum_tolerance=1e-10,accepted_weights_normalized=True,
        scope='Relative source-vertex/target-face material vectors and exact-key local Jacobians. '
            'For an exact convex face point, nearest-surface distance is at most this vector norm. '
            'Only declared source vertices are covered; floating arithmetic, nonlinear pose, new vertices, full mesh and actual acceptance still require checking.')
    return values.reshape(-1,3),jac,meta


def insert_guards(system,jacobian,hard_rows,vectors,vector_jacobian,limits_m,*,scale_m=.005,maximum_nonzeros=6000000):
    if not isinstance(system,NormRows) or type(hard_rows) is not int or not 0<=hard_rows<=len(system.caps):raise ValueError('Complete base norm population and hard prefix required')
    if type(scale_m) not in (int,float) or not np.isfinite(scale_m) or scale_m<=0 or type(maximum_nonzeros) is not int or not 1<=maximum_nonzeros<=6000000:raise ValueError('Positive scale and complete sparse budget required')
    vectors=np.asarray(vectors,float);limits=np.asarray(limits_m,float);jac=sparse.csr_matrix(jacobian);gj=sparse.csr_matrix(vector_jacobian)
    guards=NormRows(vectors,limits,np.full(len(limits),scale_m))
    if (np.any(limits<0) or jac.shape[0]!=system.vectors.size or gj.shape!=(guards.vectors.size,jac.shape[1])
            or not np.isfinite(jac.data).all() or not np.isfinite(gj.data).all() or np.any(system.residual()[:hard_rows]>1e-8) or np.any(guards.residual()>0)):
        raise ValueError('Complete matching Jacobians and original-bound feasible anchor required')
    result=NormRows(np.r_[system.vectors[:hard_rows],guards.vectors,system.vectors[hard_rows:]],np.r_[system.caps[:hard_rows],guards.caps,system.caps[hard_rows:]],np.r_[system.scales[:hard_rows],guards.scales,system.scales[hard_rows:]])
    matrix=sparse.vstack([jac[:3*hard_rows],gj,jac[3*hard_rows:]],format='csc')
    if matrix.nnz>maximum_nonzeros:raise ValueError('Complete vector-guard matrix exceeds budget; no subset returned')
    return result,matrix,dict(original_hard_rows=hard_rows,material_vector_rows=len(limits),hard_rows=hard_rows+len(limits),total_rows=len(result.caps),combined_nonzeros=matrix.nnz,all_original_rows_caps_scales_retained=True,original_selected=True,quality_approved=False,release_approved=False,scope='Additional local full-vector material bounds. No original row is removed or relaxed; decoded material distances and complete mesh acceptance remain required.')
