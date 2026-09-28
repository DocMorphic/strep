"""Verify export integrity, prior-source preservation and deterministic replay."""
import numpy as np
from strep import ROOT,read,save,sha256,now
from apply_control_study import FOLDER,STUDY
from motion_controls import edit
from correct_stance import load_motion


def main():
    from kimodo.skeleton import SOMASkeleton77
    skeleton=SOMASkeleton77();study=read(STUDY);profiles={p['id']:p for p in study['profiles']}
    freeze=read(FOLDER/'implementation-freeze.json')
    assert sha256(STUDY)==freeze['study_sha256']
    assert all(sha256(ROOT/'scripts'/k)==v for k,v in freeze['files'].items())
    assert sha256(ROOT/'scripts/analyze_control_study.py')==read(FOLDER/'analysis-freeze.json')['implementation_sha256']
    checks=[];repeats=[]
    for method in ['text','direct']:
        summary=read(FOLDER/method/'summary.json')
        for trial in summary['trials']:
            assert sha256(trial['source_path'])==trial['source_sha256']
            path=FOLDER/method/'stance'/trial['profile']/f"seed-{trial['seed']}/corrected.npz"
            assert sha256(path)==trial['stance_report']['corrected_sha256']
            cp=FOLDER/method/'characters'/trial['id'];cr=read(cp/'report.json')
            assert sha256(cp/'motion.glb')==cr['glb_sha256']
            assert cr['source_summary_sha256']==sha256(FOLDER/method/'summary.json')
            assert max(c['roundtrip_max_vertex_error_m'] for c in cr['conditions'].values())<1e-5
            if method=='direct':
                source=load_motion(trial['control_report']['baseline_path']);profile=profiles[trial['profile']]
                generated,_=edit(source,skeleton,profile['control'],profile['target_degrees']);saved=load_motion(path)
                exact=all(np.array_equal(saved[k],generated[k]) for k in saved)
                assert exact;repeats.append({'id':trial['id'],'arrays_exact':exact})
            checks.append({'method':method,'id':trial['id']})
        assert all(r['errors']==0 for r in read(FOLDER/method/'gltf-validation-summary.json'))
    preserved=[]
    for path in (ROOT/'runs').glob('**/record.json'):
        source=read(path).get('source_motion_file_and_hash')
        if source and source.get('path') and source.get('sha256'):
            assert sha256(source['path'])==source['sha256'];preserved.append(source['path'])
    for trial in read(ROOT/'reports/profile-pilot-v1/summary.json')['trials']:
        assert sha256(trial['source_path'])==trial['source_sha256'];preserved.append(trial['source_path'])
    save(FOLDER/'verification.json',{'checked_at':now(),'frozen_implementation_verified':True,'artifacts':checks,
        'exact_control_repeats':repeats,'prior_raw_files_preserved':len(preserved),
        'scope':'All direct edits repeated; text-conditioned motions are checksum-verified, not independently regenerated here.'})
    print(f'Verified {len(checks)} exports, {len(repeats)} exact edits and {len(preserved)} prior raw files.')


if __name__=='__main__':main()
