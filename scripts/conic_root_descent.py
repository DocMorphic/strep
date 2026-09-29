"""Norm-preserving affine proposals with exact serialized acceptance."""
import sys
import numpy as np
from scipy import sparse
from strep import ROOT,read,sha256
from root_release_block import root_pair


def solver_module():
    meta=read(ROOT/'reports/conic-solver-bootstrap-v1.json');vendor=ROOT/meta['vendor']
    for name,digest in meta['files'].items():
        if sha256(vendor/name)!=digest:raise ValueError('Pinned conic solver changed')
    if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
    import clarabel
    if clarabel.__version__!=meta['version']:raise ValueError('Conic solver version differs')
    return clarabel


def affine_constraints(p,x,quantized=True):
    values=p.values(x);points=p.centers.copy();jac=np.zeros((*points.shape,p.width));linear=[];linear_jac=[];cones=[]
    for i,f in enumerate(p.frames):
        pos,derivative=p.fitter.surface_jacobian(int(f),values[f])
        if quantized:pos=p.fitter.rig.vertices(p.evaluator.pose(p.fitter.pose(int(f),values[f])[0]))
        sl=slice(i*len(p.free),(i+1)*len(p.free))
        points[f]=[pos[ids].mean(axis=0) for ids in p.patches]
        jac[f,:,:,sl]=np.array([derivative[ids].mean(axis=0)[:,p.free] for ids in p.patches])
        linear.extend((pos[:,1]+.005)/.005);rows=np.zeros((len(pos),p.width));rows[:,sl]=derivative[:,1,p.free]/.005;linear_jac.extend(rows)
        for side,ids in enumerate(p.patches):
            if p.envelope['active_frames'][f][side]:
                vertex=ids[int(np.argmin(pos[ids,1]))];linear.append((p.envelope['hover_caps_m'][f][side]-pos[vertex,1])/.01)
                row=np.zeros(p.width);row[sl]=-derivative[vertex,1,p.free]/.01;linear_jac.append(row)
    def add(vector,derivative,cap,scale_floor,kind):
        scale=max(float(cap),scale_floor)
        cones.append(dict(vector=np.asarray(vector),jacobian=np.asarray(derivative),cap=float(cap),scale=scale,kind=kind))
    acc=np.diff(points,n=2,axis=0)*p.fps**2;aj=np.diff(jac,n=2,axis=0)*p.fps**2
    for index in p.acceleration_indices:
        for side in range(len(p.patches)):add(acc[index,side],aj[index,side],p.acceleration_caps[index,side],1.,'foot_acceleration')
    velocity=np.diff(points[:,:,[0,2]],axis=0)*p.fps;vj=np.diff(jac[:,:,[0,2]],axis=0)*p.fps
    for index in p.speed_indices:
        for side in range(len(p.patches)):
            if p.envelope['support_steps'][index][side]:add(velocity[index,side],vj[index,side],p.envelope['support_speed_caps_m_s'][index][side],.01,'support_speed')
    lookup={int(f):i for i,f in enumerate(p.frames)};edges=sorted({end for f in p.frames for end in (f,f+1) if 1<=end<len(values)})
    for end in edges:
        for column in range(0,values.shape[1],3):
            radius=p.fitter.spec['limits']['root_step_m'] if column==0 else np.radians(p.fitter.spec['limits']['joint_step_degrees'])
            derivative=np.zeros((3,p.width))
            for frame,sign in [(end,1),(end-1,-1)]:
                if frame in lookup:
                    for j,free in enumerate(p.free):
                        if column<=free<column+3:derivative[free-column,lookup[frame]*len(p.free)+j]=sign
            add(values[end,column:column+3]-values[end-1,column:column+3],derivative,radius,radius,'adjacent_edit')
    world=np.array([p.evaluator.pose(w) for w in p.world]) if quantized else p.world.copy()
    for f in p.frames:
        w=p.fitter.pose(int(f),values[f])[0];world[f]=p.evaluator.pose(w) if quantized else w
    positions,rj=root_pair(world,p.frames,p.free,p.root,p.width);acc=np.diff(positions,n=2,axis=0)*p.fps**2;rj=np.diff(rj,n=2,axis=0)*p.fps**2
    for index in p.acceleration_indices:add(acc[index],rj[index],p.envelope['root_safety_caps_m_s2'][index],1.,'root_acceleration')
    return np.asarray(linear),np.asarray(linear_jac),cones


def cone_rows(vector,jacobian,cap,scale,trust):
    return sparse.csc_matrix(np.vstack([np.zeros(jacobian.shape[1]),-jacobian*trust])/scale),np.r_[cap,vector]/scale


def tightened_cap(item,buffers):
    requested=float((buffers or {}).get(item['kind'],0.))
    if not np.isfinite(requested) or requested<0:raise ValueError('Finite nonnegative proposal buffer required')
    if not np.any(item['jacobian']):return item['cap']
    return item['cap']-min(requested,.5*item['cap'])


def direction(p,x,trust,buffers=None,constraint_builder=None):
    clarabel=solver_module();evaluation=p.evaluate(x);g=evaluation[1]
    if not np.isfinite(g).all() or np.max(np.abs(g))==0:return None,dict(status='ZeroGradient',trust=trust)
    c,j,cones=(constraint_builder or affine_constraints)(p,x);bounds=np.tile(p.fitter.bounds[p.free],len(p.frames))
    lower=np.maximum(-1.,(-bounds-x)/trust);upper=np.minimum(1.,(bounds-x)/trust)
    mats=[-sparse.csc_matrix(j*trust),sparse.eye(len(x),format='csc'),-sparse.eye(len(x),format='csc')]
    rhs=[c,upper,-lower];types=[clarabel.NonnegativeConeT(len(c)+2*len(x))]
    for item in cones:
        a,b=cone_rows(item['vector'],item['jacobian'],tightened_cap(item,buffers),item['scale'],trust);mats.append(a);rhs.append(b);types.append(clarabel.SecondOrderConeT(len(b)))
    settings=clarabel.DefaultSettings();settings.verbose=False;settings.max_iter=100;settings.time_limit=30.
    settings.tol_gap_abs=settings.tol_gap_rel=settings.tol_feas=1e-10
    if hasattr(settings,'max_threads'):settings.max_threads=1
    solver=clarabel.DefaultSolver(sparse.eye(len(x),format='csc')*1e-4,g/np.max(np.abs(g)),sparse.vstack(mats,format='csc'),np.concatenate(rhs),types,settings)
    result=solver.solve();delta=np.asarray(result.x)*trust
    record=dict(status=str(result.status),iterations=result.iterations,trust=trust,linear_rows=len(c),norm_cones=len(cones),
        predicted_objective_change=float(g@delta),max_coordinate_step=float(np.abs(delta).max()),proposal_buffers=buffers or {},
        tightened_cones=int(sum(tightened_cap(t,buffers)<t['cap'] for t in cones)))
    # A solver status is proposal metadata, never final animation acceptance.
    if str(result.status) not in ['Solved','AlmostSolved'] or not np.isfinite(delta).all() or np.abs(delta).max()>trust+1e-12:return None,record
    record['predicted_linear_minimum']=float((c+j@delta).min())
    record['predicted_norm_max_excess']=max(float(np.linalg.norm(t['vector']+t['jacobian']@delta)-t['cap'])/t['scale'] for t in cones)
    record['predicted_buffered_norm_max_excess']=max(float(np.linalg.norm(t['vector']+t['jacobian']@delta)-tightened_cap(t,buffers))/t['scale'] for t in cones)
    return delta,record


def solve(p,steps=12,trusts=(1e-4,1e-5,1e-6),progress=None,buffers=None,constraint_builder=None):
    x=p.initial[np.ix_(p.frames,p.free)].ravel();initial=x.copy();before=p.evaluate(x);history=[]
    if before[2].min()<-1e-8 or not p.geometric_guard(before[5]):raise ValueError('Strictly feasible source required')
    for iteration in range(steps):
        current=p.evaluate(x)
        if current[0]==0.:break
        attempts=[];accepted=False
        for trust in trusts:
            delta,record=direction(p,x,trust,buffers,constraint_builder);record['trials']=[]
            if delta is not None and record['predicted_objective_change']<0:
                record['proposed_delta']=delta.tolist()
                for index in range(8):
                    alpha=.5**index;trial=p.evaluate(x+alpha*delta)
                    feasible=bool(np.isfinite(trial[0]) and np.isfinite(trial[2]).all() and trial[2].min()>=-1e-8)
                    geometry=p.geometric_guard(trial[5]) if feasible else False;good=bool(feasible and geometry and trial[0]<current[0]-1e-9)
                    record['trials'].append(dict(fraction=alpha,objective=trial[0],minimum_constraint=float(trial[2].min()),geometry=geometry,accepted=good))
                    if good:x+=alpha*delta;accepted=True;break
            attempts.append(record)
            if accepted:break
        history.append(dict(iteration=iteration+1,objective_before=current[0],attempts=attempts,accepted=accepted))
        if progress:progress(dict(iteration=iteration+1,accepted=accepted,objective=p.evaluate(x)[0]))
        if not accepted:break
    final=p.evaluate(x)
    return p.values(x),dict(method='conic_descent',steps_limit=steps,trusts=list(trusts),proposal_buffers=buffers or {},history=history,
        starting_coordinates=initial.tolist(),final_coordinates=x.tolist(),variable_frames=p.frames.tolist(),free_columns=p.free.tolist(),
        objective_before=before[0],objective_after=final[0],minimum_constraint=float(final[2].min()),target_satisfied=final[0]==0.,quality_approved=False)
