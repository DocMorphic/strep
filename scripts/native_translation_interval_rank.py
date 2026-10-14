"""Chunked positional motion scoring for translation proposals, never approval."""
import copy
import numpy as np
from native_support_clock import NativeSupportSampler
from native_translation_stencil_search import plan as local_plan,apply_stencil
from native_component_storage_repair import ComponentAdjustedEdits
from native_rotation_storage_search import search as checked_search


def scores(candidates,current_keys,weights,parent_linear,positions,source_positions,affected,
           speed_caps,acceleration_caps,baseline_dynamic,fixed_residual,*,dt,displacement,tolerance,chunk_size=32):
    """Score all uniform times/joints in bounded chunks, including stencil edges.

    Translate descendants affinely with the observed parent matrix. Displacement,
    speed and acceleration use their original caps; remaining rows stay fixed
    for this motion-only heuristic. Contacts/geometry/serialization still need
    full independent checks. Inputs may be a bounded subset; the caller binds
    the complete proposal population separately.
    """
    arrays=[np.asarray(x,float) for x in (candidates,current_keys,weights,parent_linear,positions,source_positions,speed_caps,acceleration_caps,baseline_dynamic,fixed_residual)]
    candidates,current,weights,parent,points,source,speed_caps,acc_caps,baseline,fixed=arrays
    if (type(chunk_size) is not int or not 1<=chunk_size<=128
            or candidates.ndim!=3 or not 1<=len(candidates)<=19683 or candidates.shape[2]!=3
            or not 1<=candidates.shape[1]<=3):raise ValueError('Bounded complete candidate shapes and explicit chunk size required')
    f,j=points.shape[:2] if points.ndim==3 else (0,0);k=candidates.shape[1]
    affected=np.asarray(affected)
    if (f<3 or j<1 or points.shape!=(f,j,3) or source.shape!=points.shape
            or current.shape!=(k,3) or weights.shape!=(f,k) or parent.shape!=(f,3,3)
            or affected.shape!=(j,) or affected.dtype!=np.dtype(bool)
            or speed_caps.shape!=(f-1,j) or acc_caps.shape!=(f-2,j)
            or baseline.shape!=((3*f-3)*j,) or fixed.ndim!=1
            or any(not np.isfinite(a).all() for a in arrays)
            or np.any(speed_caps<0) or np.any(acc_caps<0)
            or np.any(weights<0) or np.any(weights>1) or np.any(weights.sum(1)>1+1e-12)):
        raise ValueError('Complete finite uniform positional observations and original row populations required')
    if any(type(v) not in (int,float) or not np.isfinite(v) for v in (dt,displacement,tolerance)) or dt<=0 or displacement<=0 or tolerance<0:
        raise ValueError('Positive uniform step/displacement and nonnegative original tolerance required')
    fixed_positive=np.maximum(fixed,0);fixed_max=float(fixed_positive.max(initial=0));fixed_square=float(fixed_positive@fixed_positive)
    fixed_failed=int((fixed>0).sum());maxima=[];squares=[];failed=[];introduced=[]
    for start in range(0,len(candidates),chunk_size):
        delta=np.einsum('fk,nkc->nfc',weights,candidates[start:start+chunk_size]-current)
        shift=np.einsum('fij,nfj->nfi',parent,delta)
        moved=points[None]+shift[:,:,None,:]*affected[None,None,:,None]
        with np.errstate(over='ignore',divide='ignore',invalid='ignore'):
            # The established displacement audit uses joint-major advanced
            # indexing; positional rates use frame-major features. Preserve
            # both exact row orders when comparing against saved failures.
            displacement_rows=((np.linalg.norm(moved-source[None],axis=3)-displacement)/displacement).transpose(0,2,1).reshape(len(moved),-1)
            speed=((np.linalg.norm(np.diff(moved,axis=1)/dt,axis=3)-speed_caps-tolerance)/np.maximum(speed_caps,.001)).reshape(len(moved),-1)
            acceleration=((np.linalg.norm(np.diff(moved,n=2,axis=1)/dt**2,axis=3)-acc_caps-tolerance)/np.maximum(acc_caps,.001)).reshape(len(moved),-1)
        dynamic=np.concatenate([displacement_rows,speed,acceleration],axis=1)
        if not np.isfinite(dynamic).all():raise ValueError('Finite complete interval predictions required')
        positive=np.maximum(dynamic,0)
        maxima.extend(np.maximum(fixed_max,positive.max(axis=1)).tolist())
        squares.extend((fixed_square+np.sum(positive*positive,axis=1)).tolist())
        failed.extend((fixed_failed+np.sum(dynamic>0,axis=1)).tolist())
        introduced.extend(np.sum((dynamic>0)&(baseline[None]<=0),axis=1).tolist())
    return dict(maximum_excess=np.asarray(maxima),squared_positive=np.asarray(squares),
        failed_rows=np.asarray(failed),introduced_positional_rows=np.asarray(introduced),
        positional_rows=len(baseline),fixed_rows=len(fixed),population=len(candidates),chunk_size=chunk_size,
        proposal_only=True,geometry_assessed=False,quality_approved=False,release_approved=False)


def interval_order(problem,worlds,corrections,value,policy,name,root,keys,ranked):
    editor=ComponentAdjustedEdits(problem.edits,policy,corrections)
    track=next(e for e in problem.edits.actors[name]['tracks'] if (e['node'],e['path'])==(root,'translation'))
    clock=track['clock'];weights=np.zeros((len(problem.uniform),len(keys)))
    for i,key in enumerate(keys):
        basis=np.zeros((len(clock),3));basis[key,0]=1
        weights[:,i]=[NativeSupportSampler.value('translation',clock,basis,'LINEAR',float(t))[0] for t in problem.uniform]
    actor=problem.scene.actors[name];joints=actor['rig'].joints;parents=actor['rig'].parents;affected=[]
    for node in joints:
        current=node
        while current>=0 and current!=root:current=parents[current]
        affected.append(current==root)
    ids=problem.rate_ids;world=worlds[name][ids];parent=parents[root]
    parent_linear=world[:,parent,:3,:3] if parent>=0 else np.repeat(np.eye(3)[None],len(ids),axis=0)
    residual=problem.constraints(value,worlds);offset=0
    for other,edits in problem.edits.actors.items():
        count=len(problem.uniform)*len(problem.scene.actors[other]['rig'].joints)
        tracks=sum(len(e['ids']) for e in edits['tracks'])
        if other==name:offset+=tracks;break
        offset+=tracks+count+sum(c.size for c in problem.caps[other].caps)
    size=(3*len(ids)-3)*len(joints);dynamic=residual[offset:offset+size]
    fixed=np.r_[residual[:offset],residual[offset+size:]];rate=problem.caps[name]
    result=scores(ranked['candidate_key_values'],editor.values(name,value)[root,'translation'][keys],weights,
        parent_linear,world[:,joints][:,:,:3,3],problem.source_world[name][ids][:,joints][:,:,:3,3],np.asarray(affected,dtype=bool),
        rate.caps[0],rate.caps[1],dynamic,fixed,dt=float(rate.dt),
        displacement=float(problem.edits.actors[name]['displacement']),tolerance=float(rate.tolerance))
    # Prefer avoiding new positional failures, then the complete original motion
    # merit. Actual full exports remain authoritative and can reject predictions.
    order=np.lexsort((np.arange(result['population']),np.count_nonzero(ranked['absolute_steps'],axis=1),
        result['squared_positive'],result['maximum_excess'],result['introduced_positional_rows']))
    return order,dict(kind='complete-uniform-positional-interval',positional_rows=result['positional_rows'],
        fixed_rows=result['fixed_rows'],chunk_size=result['chunk_size'],complete_population=result['population'],
        minimum_predicted_maximum_excess=float(result['maximum_excess'].min()),
        minimum_predicted_new_positional_rows=int(result['introduced_positional_rows'].min()),
        proposal_only=True,contacts_and_geometry_not_updated=True)


def search(problem,value,policy,corrections,decode,*,stages=8,probes_per_stage=32):
    value=np.asarray(value).copy();policy=copy.deepcopy(policy)
    corrected,report=checked_search(problem,value,policy,corrections,decode,stages=stages,probes_per_stage=probes_per_stage,
        _adjusted_type=ComponentAdjustedEdits,
        _planner=lambda p,w,c:local_plan(p,w,c,value,policy,allowed_paths=policy['allowed_paths'],_ranker=interval_order),
        _chooser=apply_stencil,_result_schema='strep-native-translation-interval-search-v1')
    report.update(maximum_translation_population=19683,
        scope='Opt-in complete local translation population ranked across all uniform positional displacement/speed/acceleration rows of the affected actor, including all joints and native support edges. Other rows fixed for proposal ranking; contacts and geometry require independent full checks. Prioritize no new predicted positional failures. All original decoded constraints/caps/scales/control/authoring and finite export budgets remain required. No feasibility, quality or release approval.')
    return corrected,report
