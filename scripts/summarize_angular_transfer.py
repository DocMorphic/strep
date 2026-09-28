"""Bind the complete two-clip development replication, including its failed preflight."""
from pathlib import Path
from strep import ROOT,read,save,sha256,now


def main():
    output=ROOT/'reports/angular-transfer-summary-v1.json'
    if output.exists():raise ValueError('Preserve previous summary')
    population=[('dance',1),('dance',2),('backpedal',1),('backpedal',2),('backpedal',3),('backpedal',4)]
    rows=[]
    for action,version in population:
        study=ROOT/f'reports/angular-{action}-rig01-v{version}'
        proof=read(study/'derivative-proof.json');pipeline=read(study/'pipeline.json')
        row=dict(study=str(study),status=pipeline['status'],proof_sha256=sha256(study/'derivative-proof.json'),preflight_passed=proof['passed'])
        if pipeline['status']=='complete':
            completion=read(study/'completion.json');audit_path=ROOT/f'reports/angular-{action}-rig01-audit-v{version}/completion.json';audit=read(audit_path)
            if audit['completion_sha256']!=sha256(study/'completion.json'):raise ValueError('Audit binding changed')
            for name,digest in completion['files'].items():
                if sha256(study/name)!=digest:raise ValueError('Completed file changed')
            for name,digest in audit['files'].items():
                if sha256(name)!=digest:raise ValueError('Audited motion changed')
            row.update(completion_sha256=sha256(study/'completion.json'),audit=str(audit_path),audit_sha256=sha256(audit_path),target=audit['target'],target_degrees=audit['target_degrees'],target_passed=audit['target_passed'],all_preservation_checks_passed=audit['all_preservation_checks_passed'],remaining_joint_failures=[j for j in audit['joints'] if not j['original_joint_peak_passed']],engine_actor_frames=audit['engine_actor_frames'],candidate_sha256=sha256(study/'take/candidate/character.glb'))
        elif pipeline['status']!='preparation_failed':raise ValueError('Unexpected unfinished study')
        rows.append(row)
    dynamics=read(ROOT/'reports/angular-transfer-joint-dynamics-v1.json');final=[]
    for case in dynamics['cases']:
        study=Path(case['study']);request=read(study/'request.json');metrics={}
        for label,path in [('original_source',Path('reports/block-release-dance-v3') if 'dance' in study.name else Path('reports/release-restore-v1')),('final',study)]:
            metrics[label]=read(ROOT/path/'take/verification.json')['metrics']['candidate']
        comparison=read(study/'take/comparison.json')
        final.append(dict(study=str(study),aggregate_checks=comparison['checks'],metrics=metrics,p95_increases=[d for d in case['differences'] if d['p95_increase_over_raw_prior_degrees']>1e-9]))
    save(output,dict(at=now(),implementation_sha256=sha256(__file__),population=rows,final=final,dynamics_sha256=sha256(ROOT/'reports/angular-transfer-joint-dynamics-v1.json'),quality_approved=False,scope='Two selected development clips, six preparations including one failed preflight, five completed correction trials. Repeated trials are not independent clips or held-out evaluation. No human, physics or release approval.'))
    print(dict(completed=sum(r['status']=='complete' for r in rows),preflight_failures=sum(not r['preflight_passed'] for r in rows),final=[dict(study=f['study'],p95_increases=f['p95_increases'],floor={k:[v['floor_depth_max_m'],v['half_frame_floor_depth_max_m']] for k,v in f['metrics'].items()}) for f in final]))


if __name__=='__main__':main()
