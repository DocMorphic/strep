"""Close the complete predeclared reference-objective cohort without filtering failures."""
import argparse
from datetime import datetime
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from compare_reference_temporal_knee import verified_audit,peaks
from rig_asset import RigAsset
from rig_transition import localize
from strep import ROOT,now,read,save,sha256


def run(study,output):
    if output.exists():raise ValueError('Preserve earlier cohort summaries')
    pipeline=read(study/'pipeline.json')
    if pipeline['status'] not in ['complete','complete_with_failures']:
        raise ValueError('Wait for every declared case to reach a terminal state')
    protocol=read(study/'protocol.json');source=read(study/'results.json')['rows']
    if [r['id'] for r in source]!=protocol['cases'] or len(source)!=8:
        raise ValueError('Incomplete or reordered cohort')
    rows=[];inputs=[study/'protocol.json',study/'pipeline.json',study/'results.json']
    frozen_solver=read(ROOT/'reports/knee-contact-reference-v1/protocol.json')
    for row in source:
        if row['status']!='complete':
            failure=study/'failures'/f"{row['id']}.json"
            if not failure.is_file():raise ValueError('Missing retained case failure')
            rows.append(dict(id=row['id'],status='failed',failure=read(failure)));inputs.append(failure)
            continue
        case=Path(row['study']);audit=Path(row['audit']);record=verified_audit(audit)
        if sha256(audit/'verification.json')!=row['verification_sha256']:
            raise ValueError('Audited case changed')
        cp=read(case/'protocol.json');spec=read(case/'spec.json');result=read(case/'result.json')
        if cp['case']!=row['id'] or record['case']!=row['id']:raise ValueError('Case binding differs')
        for field in ['max_sweeps','max_iterations_per_frame','budget_domain','contact_contract']:
            if cp[field]!=frozen_solver[field]:raise ValueError('Per-case solver settings changed')
        for name,digest in frozen_solver['implementation'].items():
            if name.endswith('probe_reference_temporal_knee.py'):continue
            if cp['implementation'].get(name)!=digest:raise ValueError('Per-case objective/solver changed')
        if sha256(case/'reference.npz')!=cp['reference_sha256']:raise ValueError('Reference bytes changed')
        with np.load(case/'fit.npz',allow_pickle=False) as z:fit=dict(z)
        with np.load(case/'reference.npz',allow_pickle=False) as z:reference=z['parameters']
        np.testing.assert_array_equal(reference,fit['reference'])
        rig=RigAsset.load(case/'candidate.glb')
        limb,body=[localize(fit[n],rig.parents) for n in ['limb','body']]
        expected=np.zeros_like(reference);root=spec['root_node']
        expected[:,:3]=fit['body'][:,root,:3,3]-fit['limb'][:,root,:3,3]
        for i,entry in enumerate(spec['edit_joints'].values()):
            n=entry['node'];expected[:,3+3*i:6+3*i]=Rotation.from_matrix(limb[:,n,:3,:3].transpose(0,2,1)@body[:,n,:3,:3]).as_rotvec()
        np.testing.assert_allclose(reference,expected,atol=1e-12,rtol=0)
        speed=peaks(audit)
        for name,pair in speed.items():
            pair['peak_speed_change_m_s']=pair['after']['peak_m_s']-pair['before']['peak_m_s']
            pair['after_peak_near_edit_boundary']=min(abs(pair['after']['arrival_frame']-min(cp['frames'])),
                abs(pair['after']['arrival_frame']-(max(cp['frames'])+1)))<=1
        fields=['floor_worst','dense_floor_passed','center_contact_errors_m','center_contact_passed',
            'candidate_pose_bounds_passed','window_step_bounds_passed','global_step_bounds_passed',
            'outside_matrix_max_error','engine_actor_frames']
        rows.append(dict(id=row['id'],status='complete',reused=row['reused'],**{k:record[k] for k in fields},
            all_editable_key_constraints_passed=result['all_editable_key_constraints_passed'],
            ordered_posture_proxy=record['after_posture']['upright_kneel_upright_proxy_present'],
            before_bounds=record['before_bounds'],after_bounds=record['after_bounds'],peaks=speed,
            reference_max_error=float(abs(reference-expected).max()),
            fitting_and_export_wall_s=(datetime.fromisoformat(read(case/'pipeline.json')['at'])-datetime.fromisoformat(cp['at'])).total_seconds()))
        inputs.extend([audit/'verification.json',case/'reference.npz'])
    complete=[r for r in rows if r['status']=='complete']
    gates=['all_editable_key_constraints_passed','dense_floor_passed','center_contact_passed',
           'candidate_pose_bounds_passed','window_step_bounds_passed','global_step_bounds_passed','ordered_posture_proxy']
    summary=dict(at=now(),inputs={str(p):sha256(p) for p in inputs},rows=rows,planned=8,
        completed=len(complete),failed=8-len(complete),gate_pass_counts={k:sum(r[k] for r in complete) for k in gates},
        engine_actor_frames=sum(r['engine_actor_frames'] for r in complete),
        newly_fitted_engine_actor_frames=sum(r['engine_actor_frames'] for r in complete if not r['reused']),
        cases_with_any_increased_patch_peak=[r['id'] for r in complete if any(v['peak_speed_change_m_s']>1e-6 for v in r['peaks'].values())],
        quality_approved=False,human_review=None,
        scope='Four paired seeds under two ending-guide conditions, not eight independent samples or held-out release data. Prior static-pose comparison contains duplicate reference poses. Speed changes and the one-frame boundary label are descriptive diagnostics, not human realism judgments. Only each declared center-frame contact is fitted.')
    save(output/'verification.json',summary)
    save(output/'decision.json',dict(at=now(),verification_sha256=sha256(output/'verification.json'),
        decision='retain_development_only_no_default_or_release_promotion',quality_approved=False,human_review=None,
        next='Continue the separately prepared explicit held-contact pilot. Keep all failed and successful cohort outputs; do not tune on reserved release prompts. Evaluate full intervals and boundary motion independently.'))
    print({k:summary[k] for k in ['planned','completed','failed','gate_pass_counts','engine_actor_frames','cases_with_any_increased_patch_peak']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('study',type=Path);parser.add_argument('output',type=Path)
    a=parser.parse_args();run(a.study.resolve(),a.output.resolve())
