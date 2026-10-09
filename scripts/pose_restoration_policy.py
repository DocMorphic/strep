"""Explicit pose tradeoffs and complete row diagnostics; never a quality gate."""
import numpy as np


def tradeoff_policy(labels,rotation_names,*,failure_policy='rowwise',point_policy='preserve'):
    if (not isinstance(labels,list) or not labels or not isinstance(rotation_names,list)
            or any(not isinstance(v,str) or not v for v in labels+rotation_names)
            or len(set(labels))!=len(labels) or len(set(rotation_names))!=len(rotation_names)
            or failure_policy not in ['rowwise','merit'] or point_policy not in ['preserve','tradeoff']):
        raise ValueError('Complete unique row identities and explicit contact policy required')
    complete=labels+['rotation-budget:'+name for name in rotation_names]
    if len(set(complete))!=len(complete):raise ValueError('Complete row identities must remain unique')
    prefixes=('normal:','object:')+(('point:',) if point_policy=='tradeoff' else ())
    mask=np.array([failure_policy=='merit' and label.startswith(prefixes) for label in labels]
        +[False]*len(rotation_names),dtype=bool)
    return complete,mask


def row_diagnostics(labels,initial,final,mask,near=1e-5):
    initial=np.asarray(initial,dtype=float);final=np.asarray(final,dtype=float);mask=np.asarray(mask)
    if (not isinstance(labels,list) or not labels or len(set(labels))!=len(labels)
            or any(not isinstance(v,str) or not v for v in labels)
            or initial.shape!=(len(labels),) or final.shape!=initial.shape or mask.shape!=initial.shape
            or mask.dtype!=bool or not np.isfinite(np.r_[initial,final]).all()
            or type(near) not in [int,float] or not np.isfinite(near) or near<=0):
        raise ValueError('Complete finite labeled inequalities and exact Boolean mask required')
    rows=[dict(label=label,initial_slack=float(a),final_slack=float(b),change=float(b-a),
        passing=bool(b>=0),tradeoff_eligible=bool(m),source_passing_lost=bool(a>=0 and b<0),
        protected_source_regressed=bool(not m and b<min(a,0)))
        for label,a,b,m in zip(labels,initial,final,mask)]
    return dict(rows=rows,failed_rows=[r['label'] for r in rows if not r['passing']],
        tight_passing_rows=[r['label'] for r in rows if 0<=r['final_slack']<=near],
        failed_rows_worsened=[r['label'] for r in rows if r['initial_slack']<0 and r['change']<0],
        source_passing_lost=[r['label'] for r in rows if r['source_passing_lost']],
        protected_source_regressed=[r['label'] for r in rows if r['protected_source_regressed']],
        near_bound_normalized=near,scope='Complete recorded solver rows, not a stationarity or infeasibility proof.',
        quality_approved=False,release_approved=False)
