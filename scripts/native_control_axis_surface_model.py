"""Complete local surface model with explicit control-aware triangle axes.

Rebuild witnesses at this model point. Differentiate complete referenced vertex
positions and original native norms on the same continuous stencils, then rank
finite triangle axes. All nine chosen-axis rows remain. Existing models and
acceptance are unchanged; this model is not a collision/quality certificate.
"""
import copy
import numpy as np
from scipy import sparse
from native_compact_surface_rows import build, CompactSurfaceRows, METHODS as ROW_METHODS
from native_pair_surface_model import PairSurfaceRows
from native_scene_norms import rows as native_rows
from native_surface_model import surface_points
from native_triangle_control_axis import choose

METHODS=tuple(dict.fromkeys(ROW_METHODS+('native_pair_surface_model.py','native_scene_norms.py',
    'native_surface_model.py','native_triangle_control_axis.py','native_control_axis_surface_model.py')))


def model(problem,value,scene,policy,digest,trust,*,decoded_worlds,step=.001,
          maximum_rows=400000,maximum_nonzeros=60000000,maximum_point_elements=60000000,progress=None):
    if (type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-6<=trust<=.02
            or type(step) not in (int,float) or not np.isfinite(step) or not 1e-6<=step<=.01
            or any(type(v) is not int or not 1<=v<=m for v,m in ((maximum_rows,400000),
                (maximum_nonzeros,60000000),(maximum_point_elements,60000000)))
            or (progress is not None and not callable(progress))):
        raise ValueError('Bounded explicit complete-model settings required')
    value=problem.edits.controls(value);n=len(value)
    if not 1<=n<=96 or np.any(value<problem.lower) or np.any(value>problem.upper):
        raise ValueError('Complete bounded model point with at most 96 controls required')
    compact=build(scene,policy,digest,clearance=0.,maximum_rows=min(maximum_rows,100000))
    PairSurfaceRows(compact,maximum_rows)  # Enforce the complete expanded budget before allocation.
    times=np.unique([r['time_s'] for r in compact.rows]);time_ids=np.searchsorted(problem.times,times)
    if np.any(time_ids==len(problem.times)) or not np.array_equal(problem.times[time_ids],times):
        raise ValueError('Every guide time must be in the complete original native clock')
    referenced={}
    for row in compact.rows:
        for side in ('left','right'):
            e=row[side]
            if e is not None:referenced.setdefault(e['actor'],set()).update(e['vertices'])
    ids={a:np.array(sorted(v),int) for a,v in referenced.items()}
    elements=sum(len(times)*len(v)*3*n for v in ids.values())
    if elements>maximum_point_elements:
        raise ValueError('Complete referenced-point derivative population exceeds budget; no subset returned')
    positions={a:problem.skin_points(a,v,decoded_worlds,time_ids,'vertices') for a,v in ids.items()}
    derivatives={a:np.empty((*p.shape,n)) for a,p in positions.items()}
    original=native_rows(problem,value,decoded_worlds)
    smooth_worlds=problem.worlds(value,quantized=False);smooth=native_rows(problem,value,smooth_worlds)
    smooth_points={a:problem.skin_points(a,ids[a],smooth_worlds,time_ids,'vertices') for a in ids}
    for a,p in positions.items():
        np.testing.assert_allclose(p,smooth_points[a],atol=2e-12,rtol=0)
    np.testing.assert_array_equal(smooth.caps,original.caps);np.testing.assert_array_equal(smooth.scales,original.scales)
    data=[];indices=[];pointers=[0];stencils=[]
    for c in range(n):
        room=problem.upper[c]-value[c] if problem.upper[c]-value[c]>=value[c]-problem.lower[c] else problem.lower[c]-value[c]
        h=float(np.copysign(min(step,abs(room)),room))
        if h==0:raise ValueError('No original finite-difference room')
        central=value[c]-step>=problem.lower[c] and value[c]+step<=problem.upper[c]
        offsets=[float(step),-float(step)] if central else [h]
        samples=[];points=[]
        for offset in offsets:
            other=value.copy();other[c]+=offset;worlds=problem.worlds(other,quantized=False)
            sample=native_rows(problem,other,worlds)
            np.testing.assert_array_equal(sample.caps,original.caps);np.testing.assert_array_equal(sample.scales,original.scales)
            if sample.vectors.shape!=original.vectors.shape:raise ValueError('Original norm population changed')
            samples.append(sample.vectors)
            points.append({a:problem.skin_points(a,v,worlds,time_ids,'vertices') for a,v in ids.items()})
        delta=(samples[0]-samples[1])/(2*step) if central else (samples[0]-smooth.vectors)/h
        column=delta.ravel();nonzero=np.flatnonzero(column)
        if not np.isfinite(column).all() or pointers[-1]+len(nonzero)>maximum_nonzeros:
            raise ValueError('Complete native derivative exceeds finite resource budget')
        data.append(column[nonzero]);indices.append(nonzero);pointers.append(pointers[-1]+len(nonzero))
        for a in ids:
            d=(points[0][a]-points[1][a])/(2*step) if central else (points[0][a]-smooth_points[a])/h
            if not np.isfinite(d).all():raise ValueError('Nonfinite complete point derivative')
            derivatives[a][...,c]=d
        stencils.append(offsets)
        if progress is not None:progress(c+1,n)
    native_jac=sparse.csc_matrix((np.concatenate(data),np.concatenate(indices),pointers),shape=(original.vectors.size,n))
    # Enclose the solver/authored box and its final roundoff projection. Ranking
    # over this expanded box remains heuristic, never a feasibility certificate.
    pad=64*np.finfo(float).eps*(1+abs(value)+trust)
    lo=np.nextafter(np.maximum(-trust,problem.lower-value)-pad,-np.inf)
    hi=np.nextafter(np.minimum(trust,problem.upper-value)+pad,np.inf)
    selected=[];blocks=copy.deepcopy(compact.rows);matrices=[];nonzeros=native_jac.nnz
    lookup={a:{int(v):i for i,v in enumerate(vs)} for a,vs in ids.items()}
    def entry(e,t):
        columns=[lookup[e['actor']][int(v)] for v in e['vertices']]
        return positions[e['actor']][t,columns],derivatives[e['actor']][t,columns]
    for block,row in enumerate(blocks):
        t=int(np.searchsorted(times,row['time_s']));left,dl=entry(row['left'],t)
        if row['kind']=='triangle-support-separation':
            right,dr=entry(row['right'],t)
            normal,choice=choose(left,right,dl,dr,lo,hi,baseline_normal=row['normal_world'])
            row['normal_world']=normal.tolist();selected.append(dict(block_index=block,**choice))
            column=np.einsum('ijkc,k->ijc',dl[:,None]-dr[None,:],normal).reshape(9,n)
        else:
            normal=np.array(row['normal_world']);column=np.einsum('v,vkc,k->c',row['left']['weights'],dl,normal)
            if row['right'] is not None:
                _,dr=entry(row['right'],t);column-=np.einsum('v,vkc,k->c',row['right']['weights'],dr,normal)
            column=column[None,:]
        matrix=sparse.csr_matrix(column);nonzeros+=matrix.nnz
        if not np.isfinite(column).all() or nonzeros>maximum_nonzeros:
            raise ValueError('Complete native/surface derivatives exceed finite resource budget; no subset returned')
        matrices.append(matrix)
    report=dict(compact.report,control_axis_choice=True,original_pose_axis_population_retained=True)
    guides=PairSurfaceRows(CompactSurfaceRows(scene,blocks,report),maximum_rows)
    gaps=guides.gaps(surface_points(problem,decoded_worlds))
    np.testing.assert_allclose(gaps,guides.gaps(),atol=2e-10,rtol=0)
    surface_jac=sparse.vstack(matrices,format='csc') if matrices else sparse.csc_matrix((0,n))
    identity=dict(schema='strep-native-control-axis-surface-model-v1',controls=n,original_norm_rows=len(original.caps),
        surface_rows=len(gaps),point_samples=len(times),referenced_vertices={a:v.tolist() for a,v in ids.items()},
        point_derivative_elements=elements,actual_difference_offsets=stencils,difference_step=step,
        native_nonzeros=native_jac.nnz,surface_nonzeros=surface_jac.nnz,maximum_nonzeros=maximum_nonzeros,
        axis_choices=selected,changed_axis_blocks=sum(r['changed_direction'] for r in selected),
        ranking_delta_lower=lo.tolist(),ranking_delta_upper=hi.tolist(),native_acceptance_unchanged=True,
        simultaneous_affine_feasibility_proven=False,quality_approved=False,release_approved=False,
        scope='All rebuilt witnesses and original native norms at the supplied stored-centered model point. '
              'Every referenced vertex/control derivative shares explicit continuous stencils. '
              'Triangle axes rank finite family optimistic independent-row box maxima; all nine selected-axis pairs remain. '
              'Projection of vertex differences is explicit, not claimed bitwise identical to differences of scalar gaps. '
              'No decoded geometry, native feasibility, full-range or quality certificate.')
    archive=dict(times_s=times,controls=value,delta_lower=lo,delta_upper=hi)
    for a in ids:archive.update({a+'_vertex_ids':ids[a],a+'_points':positions[a],a+'_point_jacobian':derivatives[a]})
    return original,native_jac,guides,gaps,surface_jac,identity,archive
