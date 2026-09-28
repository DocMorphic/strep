"""Locate dynamics tradeoffs across a frozen whole-support population snapshot."""
import argparse
from pathlib import Path
import numpy as np
from strep import read,save,sha256,now


def curve(before,after,frames,mask=None):
    a,b,f=np.asarray(before,float),np.asarray(after,float),np.asarray(frames,int)
    if a.ndim!=1 or a.shape!=b.shape or a.shape!=f.shape or not np.isfinite(np.r_[a,b]).all() or np.any(a<0) or np.any(b<0):
        raise ValueError('Matching finite nonnegative ordered traces required')
    if np.any(np.diff(f)<=0):raise ValueError('Trace clock is not ordered')
    active=np.ones(len(a),bool) if mask is None else np.asarray(mask,bool)
    if active.shape!=a.shape:raise ValueError('Support mask does not match trace')
    boundaries=np.flatnonzero(np.diff(np.r_[False,active,False])!=0)
    if not active.any():return dict(samples=0,comparison=None)
    a,b,f=a[active],b[active],f[active]
    delta=b-a;i=int(delta.argmax());peak=int(b.argmax())
    boundary_frames=np.asarray(frames)[np.minimum(boundaries,len(frames)-1)] if mask is not None else np.array([],int)
    return dict(samples=len(a),before_max=float(a.max()),after_max=float(b.max()),peak_change=float(b.max()-a.max()),
        before_p95=float(np.percentile(a,95)),after_p95=float(np.percentile(b,95)),
        before_squared_sum=float(a@a),after_squared_sum=float(b@b),
        maximum_pointwise_increase=float(delta[i]),maximum_increase_frame=int(f[i]),candidate_peak_frame=int(f[peak]),
        candidate_peak_distance_to_predicted_boundary_frames=int(np.min(np.abs(boundary_frames-f[peak]))) if len(boundary_frames) else None,
        frames=f.tolist(),before=a.tolist(),after=b.tolist())


def run(snapshot,output):
    output.mkdir(parents=True,exist_ok=False)
    summary=read(snapshot/'summary.json');study=Path(summary['study']);protocol=read(study/'protocol.json')
    if sha256(study/'protocol.json')!=summary['protocol_sha256'] or sha256(snapshot/'captured-results.json')!=summary['captured_results_sha256']:
        raise ValueError('Snapshot or protocol changed')
    if [r['id'] for r in summary['rows']]!=[r['id'] for r in protocol['cases']]:raise ValueError('Population changed')
    records=[]
    for row in summary['rows']:
        result={k:row[k] for k in ['id','status','family','action','rig']}
        if row['status']!='complete':records.append(result);continue
        folder=study/'takes'/row['id'];trace=read(folder/'traces.json')
        if sha256(folder/'traces.json')!=row['traces_sha256'] or sha256(folder/'verification.json')!=row['verification_sha256']:raise ValueError('Completed evidence changed')
        a,b=[next(t for t in trace['variants'] if t['variant']==v) for v in ['input','candidate']]
        for t in (a,b):
            if sha256(folder/t['variant']/'character.glb')!=t['source_sha256']:raise ValueError('Trace/export mismatch')
        if a['root_acceleration_frames']!=b['root_acceleration_frames']:raise ValueError('Root clocks differ')
        result['root']=curve(a['root_acceleration_m_s2'],b['root_acceleration_m_s2'],a['root_acceleration_frames'])
        result['feet']={}
        for side in ['Left','Right']:
            first,second=a['feet'][side],b['feet'][side]
            if first['step_end_frames']!=second['step_end_frames'] or first['predicted_support_steps']!=second['predicted_support_steps']:raise ValueError('Support clock/labels changed')
            result['feet'][side]=curve(first['horizontal_speed_m_s'],second['horizontal_speed_m_s'],first['step_end_frames'],first['predicted_support_steps'])
        result['floor']={v:row['metrics'][v]['floor_max_m'] for v in ['input','candidate']}
        result['input_sha256'],result['candidate_sha256']=a['source_sha256'],b['source_sha256']
        records.append(result)
    finished=[r for r in records if r['status']=='complete']
    # These thresholds summarize the size of observed changes, not release gates.
    root=[r['id'] for r in finished if r['root']['peak_change']>.0036]
    foot=[r['id'] for r in finished if any(f.get('peak_change',0)>.001 for f in r['feet'].values())]
    boundary=[dict(id=r['id'],side=side,frame=f['candidate_peak_frame'],increase_m_s=f['peak_change']) for r in finished for side,f in r['feet'].items()
              if f.get('peak_change',0)>.001 and f['candidate_peak_distance_to_predicted_boundary_frames']<=2]
    save(output/'traces.json',dict(rows=records,quality_approved=False))
    save(output/'summary.json',dict(at=now(),snapshot=str(snapshot),snapshot_sha256=sha256(snapshot/'summary.json'),
        planned=len(records),complete=len(finished),unfinished=len(records)-len(finished),
        root_peak_increase_above_0036_m_s2=root,foot_peak_increase_above_001_m_s=foot,
        increased_foot_peaks_within_two_frames_of_predicted_boundary=boundary,
        trace_sha256=sha256(output/'traces.json'),implementation_sha256=sha256(__file__),quality_approved=False,
        scope='Descriptive comparison on the frozen completed subset; pending rows retained. Predicted contacts are unconfirmed. Boundary proximity is correlation, not causal or semantic proof. Thresholds are reporting bins, not quality acceptance.'))
    lines=['# Whole-support dynamics tradeoffs','',f'{len(finished)}/{len(records)} completed in this frozen snapshot. No quality promotion.',
        '',f'{len(root)} root peaks increase by more than0.0036m/s²; {len(foot)} cases have a predicted-support foot peak increase above0.001m/s.',
        '',f'{len(boundary)} increased foot peaks lie within two frames of a predicted support boundary. This is a diagnostic association, not proof of bad motion or incorrect labels.',
        '', '| Case | Floor mm, input → candidate | Root peak, input → candidate | Foot peak change L/R, m/s |','|---|---:|---:|---:|']
    for r in records:
        if r['status']!='complete':lines.append(f"| {r['id']} | {r['status']} | — | — |");continue
        feet=' / '.join(f"{r['feet'][s].get('peak_change',0):+.4f}" if r['feet'][s]['samples'] else 'no support' for s in ['Left','Right'])
        lines.append(f"| {r['id']} | {r['floor']['input']*1000:.3f} → {r['floor']['candidate']*1000:.3f} | {r['root']['before_max']:.3f} → {r['root']['after_max']:.3f} | {feet} |")
    (output/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(dict(complete=len(finished),planned=len(records),root_regressions=len(root),foot_regressions=len(foot),near_boundary_peaks=len(boundary)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.snapshot.resolve(),a.output.resolve())
