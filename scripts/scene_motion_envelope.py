"""Explicit scene-bound motion budgets, separate from physical scene metrics.

Game-author limits and source peaks are not physiological calibration. The
historical exact per-sample source comparison remains a separate observation.
"""
import copy
import re
import numpy as np
from scene_metric_retention import snapshot_metrics,compare_metrics

TRACKS={'skin_speed_m_s':('m/s',1),'skin_acceleration_m_s2':('m/s^2',2),
        'joint_speed_m_s':('m/s',1),'joint_acceleration_m_s2':('m/s^2',2)}
SCHEMA='strep-scene-motion-envelope-v1'


class MotionEnvelope:
    def __init__(self,policy,reference,*,context_sha256,reference_metrics_sha256):
        reference=snapshot_metrics(reference)
        required={'schema','name','limit_provenance','context_sha256','reference_metrics_sha256','fps','frames','limits'}
        if (not isinstance(policy,dict) or set(policy)!=required or policy['schema']!=SCHEMA
                or any(not isinstance(policy[k],str) or not policy[k].strip() or len(policy[k])>300 for k in ['name','limit_provenance'])
                or any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in [context_sha256,reference_metrics_sha256])
                or policy['context_sha256']!=context_sha256 or policy['reference_metrics_sha256']!=reference_metrics_sha256
                or type(policy['fps']) is not int or policy['fps']!=30 or type(policy['frames']) is not int or not 3<=policy['frames']<=300):
            raise ValueError('Complete explicit motion envelope bound to the original scene and metrics required')
        self.policy=copy.deepcopy(policy);self.frames=policy['frames'];self.caps={};self.layout={k:v.shape for k,v in reference.items()}
        if any(k.startswith('motion_excess.') for k in reference):raise ValueError('Motion excess names are reserved; no original metric may be overwritten')
        if not isinstance(policy['limits'],list) or len(policy['limits'])!=len(TRACKS):raise ValueError('Every original motion track needs an explicit budget')
        for limit in policy['limits']:
            if not isinstance(limit,dict) or set(limit)!={'metric','unit','upper'}:raise ValueError('Exact metric/unit/upper fields required')
            name=limit['metric']
            if name not in TRACKS or name in self.caps or name not in reference or limit['unit']!=TRACKS[name][0] or reference[name].shape!=(self.frames-TRACKS[name][1],):raise ValueError('Distinct complete motion track, original clock and correct units required')
            upper=limit['upper']
            if not (type(upper) in (int,float) or isinstance(upper,list) and all(type(v) in (int,float) for v in upper)):raise ValueError('Numeric scalar or complete authored limit track required')
            values=np.asarray(upper,dtype=float)
            if values.ndim==0:values=np.full(reference[name].shape,float(values))
            if values.shape!=reference[name].shape or not np.isfinite(values).all() or np.any(values<0) or np.any(values>1e6):raise ValueError('Finite nonnegative complete motion budgets required')
            self.caps[name]=values.copy()
        if set(self.caps)!=set(TRACKS):raise ValueError('No original motion track may be omitted')

    def observe(self,metrics):
        values=snapshot_metrics(metrics)
        if set(values)!=set(self.layout) or any(values[k].shape!=s for k,s in self.layout.items()):raise ValueError('Every original physical/motion metric and row must remain present')
        result={}
        for name,value in values.items():
            if name in self.caps:result['motion_excess.'+name]=np.maximum(value-self.caps[name],0.)
            else:result[name]=value
        return result

    def assess(self,metrics):
        original=snapshot_metrics(metrics);self.observe(original);tracks={}
        for name,cap in self.caps.items():
            excess=original[name]-cap;tracks[name]=dict(rows=len(cap),unit=TRACKS[name][0],maximum_value=float(original[name].max()),
                minimum_cap=float(cap.min()),maximum_cap=float(cap.max()),maximum_signed_excess=float(excess.max()),failed_rows=int(np.count_nonzero(excess>0)))
        return dict(schema='strep-scene-motion-envelope-assessment-v1',all_motion_bounds_pass=all(v['failed_rows']==0 for v in tracks.values()),tracks=tracks,
            context_sha256=self.policy['context_sha256'],reference_metrics_sha256=self.policy['reference_metrics_sha256'],tolerance_added=0.,quality_approved=False,release_approved=False,
            scope='Complete declared speed/acceleration budgets only. Author/source limits are not anatomical capacity, realism, contact, collision or whole-asset approval. Every physical metric passes through unchanged; all original raw observations remain separate.')

    def compare(self,before,after):
        return dict(strict_source_comparison=compare_metrics(before,after),envelope_comparison=compare_metrics(self.observe(before),self.observe(after)),
            before_bounds=self.assess(before),after_bounds=self.assess(after),physical_metric_population_unchanged=True,quality_approved=False,release_approved=False)


def source_peak_policy(reference,frames,context_sha256,reference_metrics_sha256):
    """Explicit template: redistribute time while retaining original global peaks.

    No multiplier or extra headroom. This is a separate authoring policy, never
    a reinterpretation of a historical per-sample failure or a release gate.
    """
    values=snapshot_metrics(reference)
    if not set(TRACKS)<=set(values):raise ValueError('Every original complete motion track is required')
    policy=dict(schema=SCHEMA,name='Original whole-clip peaks',limit_provenance='Unchanged recorded reference maxima; temporal redistribution allowed within these explicit motion budgets. No physiological or quality calibration.',
        context_sha256=context_sha256,reference_metrics_sha256=reference_metrics_sha256,fps=30,frames=frames,
        limits=[dict(metric=name,unit=unit,upper=float(values[name].max())) for name,(unit,_) in TRACKS.items()])
    MotionEnvelope(policy,values,context_sha256=context_sha256,reference_metrics_sha256=reference_metrics_sha256)
    return policy


if __name__=='__main__':
    import argparse
    from pathlib import Path
    from strep import read,save,sha256
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('context',type=Path);p.add_argument('reference_metrics',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    if a.output.exists():p.error('Choose a fresh policy file; existing author input is preserved')
    pins={str(f):sha256(f) for f in [a.context,a.reference_metrics]};context=read(a.context)
    if context.get('schema')!='strep-authored-scene-guidance-v1':p.error('Compiled authored scene context required')
    with np.load(a.reference_metrics,allow_pickle=False) as z:reference={k:z[k] for k in z.files}
    policy=source_peak_policy(reference,context['frames'],pins[str(a.context)],pins[str(a.reference_metrics)])
    if any(sha256(f)!=h for f,h in pins.items()):p.error('Original inputs changed while preparing policy')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    import json
    with a.output.open('x',encoding='utf-8') as stream:json.dump(policy,stream,indent=2);stream.write('\n')
    print(str(a.output.resolve()))
