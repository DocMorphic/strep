"""Source-matched original/revised support comparison, retaining all statuses."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from strep import ROOT, read, save, sha256, now
from summarize_breadth_contact import metrics


def comparable(old_spec,new_spec,old_request,new_request):
    before,after=copy.deepcopy(old_spec),copy.deepcopy(new_spec)
    before.pop('provenance',None);after.pop('provenance',None)
    if before!=after:raise ValueError('Solver bounds, clock, patches or objective settings differ')
    if old_request['method']!='support' or new_request['method']!='support_reference':
        raise ValueError('Unexpected comparison methods')
    keys=['input_glb_sha256','native_motion_sha256','native_skin_sha256','targets_m','raw_native_heights_m',
          'support','support_weight','max_sweeps']
    if any(old_request[k]!=new_request[k] for k in keys):
        raise ValueError('Inputs, targets, support guides or sweep budgets differ')


def run(study,output):
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists():raise ValueError('Preserve earlier comparison')
    protocol=read(study/'protocol.json');baseline=Path(protocol['baseline']);original=read(baseline/'protocol.json')
    files={}
    def verify(path,digest):
        path=Path(path)
        if sha256(path)!=digest:raise ValueError('Changed evidence: '+str(path))
        files[str(path)]=digest
    verify(study/'protocol.json',read(study/'freeze.json')['protocol_sha256'])
    verify(baseline/'protocol.json',protocol['baseline_protocol_sha256'])
    if protocol['cases']!=original['cases'] or len(protocol['cases'])!=10:
        raise ValueError('Comparison populations differ')
    for folder,spec in [(study,protocol),(baseline,original)]:
        for name,digest in spec['implementation'].items():verify(folder/'implementation'/name,digest)
    new_bytes=(study/'results.json').read_bytes();old_bytes=(baseline/'results.json').read_bytes()
    new,old=json.loads(new_bytes),json.loads(old_bytes)
    expected={c['id'] for c in protocol['cases']}
    if len(new['rows'])!=10 or {r['case'] for r in new['rows']}!=expected:
        raise ValueError('Incomplete revised status population')
    if len(old['rows'])!=20 or {(r['case'],r['method']) for r in old['rows']}!={(c,m) for c in expected for m in ['clearance','support']}:
        raise ValueError('Incomplete original status population')
    paired=[];population=[]
    for case in protocol['cases']:
        base=next(r for r in old['rows'] if (r['case'],r['method'])==(case['id'],'support'))
        revised=next(r for r in new['rows'] if r['case']==case['id'])
        group=next((g for g in old['engine_groups'] if g['case']==case['id'] and g['status']=='complete'),None)
        population.append(dict(case=case['id'],baseline_status=base['status'],revised_status=revised['status'],baseline_engine_complete=group is not None))
        if base['status']!='complete' or revised['status']!='complete' or group is None:continue
        for relative,digest in case['files'].items():verify(Path(case['source'])/relative,digest)
        old_folder=baseline/'takes'/base['id'];new_folder=study/'takes'/case['id']
        old_proof,new_proof=read(old_folder/'verification.json'),read(new_folder/'verification.json')
        if old_proof!=base['verification'] or new_proof!=revised['verification']:
            raise ValueError('Candidate verification changed')
        if not all(p['bounds_and_preservation_passed'] for p in [old_proof,new_proof]):
            raise ValueError('Candidate bounds/preservation did not pass')
        comparable(read(old_folder/'spec.json'),read(new_folder/'spec.json'),read(old_folder/'request.json'),read(new_folder/'request.json'))
        for folder,proof in [(old_folder,old_proof),(new_folder,new_proof)]:
            if proof['source_sha256']!=case['files']['character.glb']:raise ValueError('Different source rig clip')
            verify(folder/'input/character.glb',proof['source_sha256']);verify(folder/'candidate/character.glb',proof['candidate_sha256'])
            for relative in ['verification.json','spec.json','request.json','input/contacts.json']:
                files[str(folder/relative)]=sha256(folder/relative)
        if (old_folder/'input/contacts.json').read_bytes()!=(new_folder/'input/contacts.json').read_bytes():
            raise ValueError('Different predicted contact annotations')
        if old_proof['metrics']['input']!=new_proof['metrics']['input']:
            raise ValueError('Independently decoded input metrics differ')
        old_engine=baseline/'engine-groups'/case['id']/'audit/verification.json'
        new_engine=study/'engine-groups'/case['id']/'audit/verification.json'
        if read(old_engine)!=group['proof']:raise ValueError('Original engine proof changed')
        verify(new_engine,revised['engine_sha256']);files[str(old_engine)]=sha256(old_engine)
        before_checks=read(old_engine)['checks'];after_checks=read(new_engine)['checks']
        clearance=next(r for r in old['rows'] if (r['case'],r['method'])==(case['id'],'clearance'))
        expected_before=[case['files']['character.glb'],old_proof['candidate_sha256'],clearance['verification']['candidate_sha256']]
        expected_after=[case['files']['character.glb'],new_proof['candidate_sha256']]
        for checks,digests in [(before_checks,expected_before),(after_checks,expected_after)]:
            if sorted(c['source_sha256'] for c in checks)!=sorted(digests) or any(c['frames']!=case['motion']['frames'] for c in checks):
                raise ValueError('Engine population or source hashes differ')
        if revised['engine_actor_frames']!=sum(c['frames'] for c in after_checks):raise ValueError('Incorrect revised engine frame count')
        a,b=metrics(old_proof['metrics']['candidate']),metrics(new_proof['metrics']['candidate'])
        deltas={key:b[key]-a[key] if a[key] is not None and b[key] is not None else None for key in ['floor_m','support_speed_p95_max_m_s','hover_max_m','root_acceleration_max_m_s2','local_rotation_step_max_degrees']}
        paired.append(dict(case=case['id'],rig=case['rig'],seed=case['motion']['seed'],input=metrics(old_proof['metrics']['input']),
            original_support=a,revised_support=b,revised_minus_original=deltas,
            original_engine_actor_frames=sum(c['frames'] for c in before_checks),revised_engine_actor_frames=sum(c['frames'] for c in after_checks)))
    if not paired:raise ValueError('No completed matched engine-verified pairs yet; no comparison written')
    all_complete=len(paired)==10
    output.mkdir();(output/'original-results-snapshot.json').write_bytes(old_bytes);(output/'revised-results-snapshot.json').write_bytes(new_bytes)
    status='complete_population' if all_complete else 'interim_population'
    save(output/'summary.json',dict(at=now(),status=status,study=str(study),baseline=str(baseline),verifier_sha256=sha256(__file__),
        source_results_sha256=dict(original=hashlib.sha256(old_bytes).hexdigest(),revised=hashlib.sha256(new_bytes).hexdigest()),
        verified_files=files,population=population,paired=paired,completed_pairs=len(paired),planned_pairs=10,quality_approved=False,
        scope='Same inputs, guides, solver bounds and sweep budgets verified before comparison. Only completed source-matched candidates with full engine groups scored; every status retained. Predicted support is unconfirmed. No held-out, anatomical, semantic, balance or human approval.'))
    lines=['# Support/reference comparison','',f'{len(paired)} of 10 matched inputs complete. '+('All declared inputs included.' if all_complete else 'Remaining inputs are unscored; these are interim results.'),'',
        '| Input | Method | Support p95 speed (m/s) | Floor depth (mm) | Hover (mm) | Root acceleration (m/s²) | Proxy screens |',
        '|---|---|---:|---:|---:|---:|---|']
    def number(v,scale=1):return 'missing' if v is None else f'{v*scale:.4f}'
    for pair in paired:
        for method in ['input','original_support','revised_support']:
            m=pair[method]
            lines.append('| '+' | '.join([pair['case'],method,number(m['support_speed_p95_max_m_s']),number(m['floor_m'],1000),number(m['hover_max_m'],1000),number(m['root_acceleration_max_m_s2']),'pass' if m['proposed_proxy_screens_passed'] else 'fail'])+' |')
    lines+=['','Proxy thresholds are unchanged: floor10mm, support p95 speed0.05m/s, hover30mm. Root acceleration and local rotation step are reported for regression inspection; no physical-balance threshold is inferred. All failed and incomplete attempts remain in the population.']
    (output/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(dict(status=status,completed_pairs=len(paired),planned_pairs=10),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.study,a.output)
