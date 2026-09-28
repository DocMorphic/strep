"""Verify retained artifacts and independently repeat one frozen raw take offline."""
import os
import time
from pathlib import Path
from strep import ROOT,read,save,sha256,now,offline_environment


def main():
    os.environ.update(offline_environment())
    import numpy as np
    from kimodo import load_model
    from kimodo.tools import seed_everything
    from kimodo.constraints import load_constraints_lst
    from kimodo.exports.motion_io import save_kimodo_npz
    from profile_encoder import ProfileEncoder
    from profile_inputs import DEFAULT_STUDY
    folder=ROOT/'reports/profile-pilot-v1';summary=read(folder/'summary.json')
    checks=[]
    for trial in summary['trials']:
        assert sha256(trial['source_path'])==trial['source_sha256']
        out=folder/'stance'/trial['profile']/f"seed-{trial['seed']}"
        assert sha256(out/'corrected.npz')==trial['stance_report']['corrected_sha256']
        char=folder/'characters'/trial['id'];report=read(char/'report.json')
        assert sha256(char/'motion.glb')==report['glb_sha256']
        checks.append(trial['id'])
    # Verify earlier generation artifacts too, without modifying them.
    historical=[]
    for path in (ROOT/'runs').glob('**/record.json'):
        record=read(path)
        source=record.get('source_motion_file_and_hash')
        if source and source.get('path') and source.get('sha256'):
            assert sha256(source['path'])==source['sha256'];historical.append(str(path.relative_to(ROOT)))
    study=read(DEFAULT_STUDY);profile=study['profiles'][0];seed=study['seeds'][0]
    encoder=ProfileEncoder(ROOT/'models/prompt-cache-profile-pilot-v1/manifest.json')
    model=load_model('Kimodo-SOMA-RP-v1.1',device='cuda',text_encoder=encoder)
    constraints=load_constraints_lst(str(folder/'raw/constraints.json'),model.skeleton)
    seed_everything(seed);started=time.perf_counter()
    output=model([profile['prompt']],[round(study['duration_s']*study['fps'])],constraint_lst=constraints,
        num_denoising_steps=study['diffusion_steps'],num_samples=1,multi_prompt=True,num_transition_frames=5,
        post_processing=False,return_numpy=True,cfg_type=study['cfg_type'],cfg_weight=study['cfg_weight'])
    data={key:value[0] for key,value in output.items() if hasattr(value,'shape') and value.shape[0]==1}
    destination=folder/'verification';destination.mkdir(exist_ok=True)
    repeat=destination/'neutral-11-repeat.npz';save_kimodo_npz(str(repeat),data)
    original=folder/'raw/neutral/seed-11/attempt-001/motion.npz'
    with np.load(original,allow_pickle=False) as a,np.load(repeat,allow_pickle=False) as b:
        results={k:{'exact':bool(np.array_equal(a[k],b[k])),
                    'max_abs_difference':float(np.max(np.abs(a[k].astype(float)-b[k].astype(float))))} for k in a.files}
    report={'checked_at':now(),'verified_profile_artifacts':checks,'historical_explicit_pairs':historical,
        'repeat_id':'neutral-11','repeat_generation_time_s':time.perf_counter()-started,
        'repeat_arrays':results,'repeat_all_exact':all(x['exact'] for x in results.values()),
        'original_sha256':sha256(original),'repeat_sha256':sha256(repeat),
        'scope':'One independent raw-generation repeat; not all 15 rerun and not live-vs-cached or full-encoder equivalence.'}
    save(destination/'report.json',report);print(report)
    assert report['repeat_all_exact']


if __name__=='__main__':main()
