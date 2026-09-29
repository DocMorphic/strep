"""Necessary vertical root-acceleration bounds from exported floor/support geometry.

This does not use the optimizer, its matrices, or its infeasibility certificate.
It relaxes every omitted constraint, including horizontal motion and edit steps.
"""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now
from verify_authored_root_correction import samples
from authored_root_correction import root_weights
from study_breadth_root_cleanup import active_frames
from audit_authoring_intent import check_files


def vertical_offset_bounds(points,weights,patches,active,root_edit,vertical_budget,radius,eps):
    frames=len(points)
    lo=np.maximum(np.full(frames,-radius-eps),-vertical_budget-eps-root_edit)
    hi=np.minimum(np.full(frames,radius+eps),vertical_budget+eps-root_edit)
    positive=weights>1e-12
    if np.any(weights < 0) or not positive.any():raise ValueError('Positive root influence required')
    for f in range(frames):
        height=points[f,:,1]
        # Each currently penetrating vertex may retain its depth plus audit eps.
        floor=(-np.maximum(0.,-height[positive])-eps-height[positive])/weights[positive]
        lo[f]=max(lo[f],float(floor.max()))
        for side,patch in patches.items():
            if not active[side][f]:continue
            ids=np.asarray(patch['vertices']);w=weights[ids];y=height[ids]
            cap=max(0.,float(y.min()))+eps
            # Use any low vertex, not the optimizer's fixed hover witness. This
            # is a necessary bound even if the active lowest vertex switches.
            if np.any((w<=1e-12)&(y<=cap)):continue
            movable=w>1e-12
            if not movable.any():raise ValueError('No hover witness')
            hi[f]=min(hi[f],float(((cap-y[movable])/w[movable]).max()))
    for f in [0,1,frames-2,frames-1]:lo[f]=max(lo[f],-eps);hi[f]=min(hi[f],eps)
    if np.any(lo>hi+1e-10):raise ValueError('Inconsistent source bounds')
    return lo,hi


def acceleration_lower_bound(root_y,lo,hi,fps=30):
    a=np.diff(root_y,n=2)*fps**2
    lower=a+(lo[:-2]-2*hi[1:-1]+lo[2:])*fps**2
    upper=a+(hi[:-2]-2*lo[1:-1]+hi[2:])*fps**2
    distance=np.maximum(np.maximum(lower,-upper),0.)
    return lower,upper,distance


def run(study,output):
    if output.exists():raise ValueError('Preserve earlier diagnosis')
    request=read(study/'request.json');done=read(study/'completion.json');results=read(study/'results.json')
    if done['request_sha256']!=sha256(study/'request.json') or done['results_sha256']!=sha256(study/'results.json'):raise ValueError('Completed experiment binding changed')
    if [c['id'] for c in request['cases']]!=[r['id'] for r in results['rows']]:raise ValueError('Population changed')
    output.mkdir(parents=True);rows=[]
    for case,result in zip(request['cases'],results['rows']):
        folder=study/'takes'/case['id'];check_files(folder,case['files']);spec=read(folder/'contact-spec.json');policy=request['policy'];frames=spec['frames'];root=spec['root_node']
        rig,source=samples(folder/'candidate/character.glb',frames);_,raw=samples(folder/'input/character.glb',frames)
        points=np.asarray([rig.vertices(w) for w in source[::2]]);weights=root_weights(rig,root)
        active={side:active_frames(read(folder/'contacts.json'),side,frames) for side in spec['patches']}
        root_y=source[::2,root,1,3];root_edit=root_y-raw[::2,root,1,3]
        lo,hi=vertical_offset_bounds(points,weights,spec['patches'],active,root_edit,spec['limits']['root_vertical_m'],policy['root_correction_radius_m'],policy['position_tolerance_m'])
        lower,upper,bound=acceleration_lower_bound(root_y,lo,hi)
        raw_peak=float(np.linalg.norm(np.diff(raw[::2,root,:3,3],n=2,axis=0)*900,axis=1).max())
        threshold=raw_peak+policy['acceleration_tolerance_m_s2'];witnesses=np.flatnonzero(bound>threshold+1e-8)
        selected=Path(result['selected'])
        if sha256(selected)!=result['selected_sha256']:raise ValueError('Selected output changed')
        row=dict(id=case['id'],action=case['action'],rig=case['rig'],solver_status=result['solver']['status'],outcome=result['status'],
            original_peak_m_s2=raw_peak,acceptance_peak_m_s2=threshold,necessary_vertical_bound_max_m_s2=float(bound.max()),
            excluded_by_vertical_bound=bool(len(witnesses)),witnesses=[dict(center_frame=int(i+1),minimum_absolute_vertical_acceleration_m_s2=float(bound[i]),interval_m_s2=[float(lower[i]),float(upper[i])],offset_lower_m=lo[i:i+3].tolist(),offset_upper_m=hi[i:i+3].tolist()) for i in witnesses],
            source_sha256=sha256(folder/'candidate/character.glb'),selected_sha256=sha256(selected))
        if row['excluded_by_vertical_bound'] and result['status']=='restored':raise ValueError('Bound contradicts verified candidate')
        rows.append(row);save(output/(case['id']+'.json'),row)
    save(output/'summary.json',dict(at=now(),completion_sha256=sha256(study/'completion.json'),implementation_sha256=sha256(__file__),rows=rows,
        excluded=sum(r['excluded_by_vertical_bound'] for r in rows),quality_approved=False,
        scope='Necessary vertical-component lower bound under preserved full-skin floor depths, active foot hover, original vertical edit budget, 1cm correction radius and endpoint constraints. Includes export tolerances and allows low-vertex switching. Nonexclusion does not establish feasibility; excludes only this root-only correction family.'))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print([(r['id'],r['excluded_by_vertical_bound']) for r in run(a.study.resolve(),a.output.resolve())])
