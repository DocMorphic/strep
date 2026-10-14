"""Opt-in local translation rankings followed by complete decoded motion checks."""
import copy
import numpy as np
from native_translation_stencil import rank
from native_support_clock import NativeSupportSampler
from native_component_storage_search import apply_choice,plan as single_plan
from native_component_pair_search import option_identity
from native_component_storage_repair import ComponentAdjustedEdits
from native_rotation_storage_search import search as checked_search


def apply_stencil(corrections,bundle):
    if (not isinstance(bundle,dict) or set(bundle)!={'choices'}
            or not isinstance(bundle['choices'],list) or len(bundle['choices']) not in (3,6,9)):
        raise ValueError('One to three complete three-axis translation keys required')
    identities=[option_identity(row) for row in bundle['choices']]
    keys=sorted({i[3] for i in identities})
    if (len({i[:3] for i in identities})!=1 or identities[0][2]!='translation'
            or len(set(identities))!=len(identities)
            or keys!=list(range(keys[0],keys[0]+len(keys)))
            or any({i[4] for i in identities if i[3]==key}!={0,1,2} for key in keys)):
        raise ValueError('Distinct complete axes on consecutive keys of one translation track required')
    output=copy.deepcopy(corrections)
    for row in bundle['choices']:output=apply_choice(output,row)
    return output


def plan(problem,worlds,corrections,value,policy,*,allowed_paths=('rotation','translation'),_ranker=None,_metrics=(1,)):
    """Complete stencil for the worst supported positional acceleration failure.

    All rate failures remain in diagnostics. The proposal family explicitly
    covers translation/acceleration only, rather than silently treating other
    failure types as solved. Unsupported support falls through to the next
    eligible row; an empty plan means this family has no available proposal.
    """
    if (not isinstance(_metrics,tuple) or not _metrics or any(type(m) is not int or m not in (0,1) for m in _metrics)
            or len(set(_metrics))!=len(_metrics)):
        raise ValueError('Explicit distinct positional speed/acceleration metrics required')
    _,failures=single_plan(problem,worlds,corrections,allowed_paths=allowed_paths)
    if 'translation' not in allowed_paths:return [],failures
    eligible=[]
    for failure in failures:
        if failure['metric'] not in _metrics or failure['actor'] not in problem.edits.actors:continue
        name=failure['actor'];actor=problem.scene.actors[name];node=failure['node'];ancestors=[];current=node
        while current>=0:ancestors.append(current);current=actor['rig'].parents[current]
        joint=actor['rig'].joints.index(node);rate=problem.caps[name];frame=failure['frame']
        metric=failure['metric'];width=metric+2
        cap=float(rate.caps[metric][frame,joint]);severity=failure['excess']/max(cap,.001)
        for track in problem.edits.actors[name]['tracks']:
            if track['path']!='translation' or track['node'] not in ancestors:continue
            times=problem.uniform[frame:frame+width];clock=track['clock'];keys=set()
            for time in times:
                k=int(np.searchsorted(clock,time))
                keys.update([k] if k<len(clock) and clock[k]==time else [max(0,k-1),min(len(clock)-1,k)])
            keys=sorted(keys)
            if (len(times)!=width or not 1<=len(keys)<=3 or keys!=list(range(keys[0],keys[0]+len(keys)))
                    or any(k not in track['ids'] for k in keys)):continue
            eligible.append((severity,-ancestors.index(track['node']),name,node,frame,track,keys,times,cap,metric))
    if not eligible:return [],failures
    chosen=max(eligible,key=lambda row:row[:5]);severity,_,name,node,frame,track,keys,times,cap,metric=chosen
    rate=problem.caps[name];root=track['node'];clock=track['clock'];value=problem.edits.controls(value)
    editor=ComponentAdjustedEdits(problem.edits,policy,corrections)
    current=editor.values(name,value)[root,'translation']
    nearest=problem.edits.values(name,value)[root,'translation'][keys]
    weights=np.zeros((len(times),len(keys)))
    for i,key in enumerate(keys):
        basis=np.zeros((len(clock),3));basis[key,0]=1
        weights[:,i]=[NativeSupportSampler.value('translation',clock,basis,'LINEAR',float(t))[0] for t in times]
    current_samples=np.array([NativeSupportSampler.value('translation',clock,current,'LINEAR',float(t)) for t in times])
    ids=np.searchsorted(problem.times,times);parent=problem.scene.actors[name]['rig'].parents[root]
    parent_linear=worlds[name][ids,parent,:3,:3] if parent>=0 else np.repeat(np.eye(3)[None],len(times),axis=0)
    ranked=rank(nearest,current_samples,weights,parent_linear,worlds[name][ids,node,:3,3],
                cap=cap,dt=float(rate.dt),tolerance=float(rate.tolerance),metric='speed' if metric==0 else 'acceleration')
    result=[]
    # Equal local predictions can include gratuitous whole-support offsets.
    # Prefer fewer absolute corrections on ties, so a nearest-value restoration
    # is tried before equally ranked jitter that can fail elsewhere in the clip.
    order=np.lexsort((np.arange(ranked['population']),
                      np.count_nonzero(ranked['absolute_steps'],axis=1),ranked['predicted_excess']))
    ranking=None
    if _ranker is not None:
        order,ranking=_ranker(problem,worlds,corrections,value,policy,name,root,keys,ranked)
        order=np.asarray(order)
        if (order.shape!=(ranked['population'],) or not np.issubdtype(order.dtype,np.integer)
                or not np.array_equal(np.sort(order),np.arange(ranked['population']))):
            raise ValueError('Complete proposal population permutation required')
    for index in order:
        choices=[dict(actor=name,node=root,path='translation',key_index=key,component=component,step=int(step))
            for key,steps in zip(keys,ranked['absolute_steps'][index].reshape(len(keys),3))
            for component,step in enumerate(steps)]
        result.append(dict(choices=choices))
    # Retain the exact target and population in the existing stage diagnostics.
    failures=copy.deepcopy(failures)
    for failure in failures:
        if (failure['actor'],failure['node'],failure['frame'],failure['metric'])==(name,node,frame,metric):
            failure['translation_stencil']=dict(track_node=root,keys=keys,complete_population=ranked['population'],
                minimum_predicted_excess=float(ranked['predicted_excess'].min()),proposal_only=True)
            if ranking is not None:failure['translation_stencil']['interval_ranking']=copy.deepcopy(ranking)
    return result,failures


def search(problem,value,policy,corrections,decode,*,stages=8,probes_per_stage=32):
    corrected,report=checked_search(problem,value,policy,corrections,decode,stages=stages,probes_per_stage=probes_per_stage,
        _adjusted_type=ComponentAdjustedEdits,_planner=lambda p,w,c:plan(p,w,c,value,policy,allowed_paths=policy['allowed_paths']),
        _chooser=apply_stencil,_result_schema='strep-native-translation-stencil-search-v1')
    report.update(maximum_translation_population=19683,
        scope='Explicit finite first-improvement translation-stencil search on the worst supported sampled positional acceleration row. Complete local three-axis/one-to-three-key ranking; exported prefix is bounded separately. Every export independently checks all original motion rows/caps/scales/controls/authoring. Other rate failures remain unresolved diagnostics. No exhaustive whole-clip feasibility, geometry, engine, semantic, quality or release approval.')
    return corrected,report
