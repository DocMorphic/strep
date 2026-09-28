"""Generate genuinely conditioned profile takes; preserve every raw attempt."""
import argparse
import os
import time
from pathlib import Path
from strep import ROOT,read,save,sha256,now,source_check,offline_environment
from strep import model_directory
from profile_inputs import DEFAULT_STUDY,validate_study,constraints_for,brief


def main(study_path,cache,folder):
    os.environ.update(offline_environment())
    import torch
    import numpy as np
    from kimodo import load_model
    from kimodo.tools import seed_everything
    from kimodo.constraints import load_constraints_lst
    from kimodo.exports.motion_io import save_kimodo_npz
    from kimodo.exports.bvh import save_motion_bvh
    from kimodo.skeleton import SOMASkeleton77
    from profile_encoder import ProfileEncoder
    from inspect_motion import validate_motion,metrics
    study=validate_study(read(study_path));folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    source_check()
    model_entry=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
    for name,digest in model_entry['files_sha256'].items():
        if sha256(model_directory(model_entry)/name)!=digest:raise RuntimeError('Checkpoint checksum mismatch')
    save(folder/'constraints.json',constraints_for(study))
    encoder=ProfileEncoder(cache,study_path)
    model=load_model('Kimodo-SOMA-RP-v1.1',device='cuda',text_encoder=encoder)
    skeleton=SOMASkeleton77()
    constraints=load_constraints_lst(str(folder/'constraints.json'),model.skeleton)
    for profile in study['profiles']:
        for seed in study['seeds']:
            parent=folder/profile['id']/f'seed-{seed}'
            previous=sorted(parent.glob('attempt-*/record.json')) if parent.exists() else []
            valid=[read(p) for p in previous if read(p).get('status')=='generated']
            if valid:
                record=valid[-1]
                if record['study_sha256']!=sha256(study_path) or record['cache_sha256']!=sha256(cache) or sha256(record['npz'])!=record['npz_sha256']:raise RuntimeError('Resume provenance mismatch')
                print(f'Already verified: {profile["id"]}/{seed}',flush=True);continue
            attempt=parent/f'attempt-{len(previous)+1:03d}';attempt.mkdir(parents=True,exist_ok=False)
            record={'status':'running','started_at':now(),'brief':brief(study,profile,seed),'study_sha256':sha256(study_path),
                'cache_sha256':sha256(cache),'constraint_sha256':sha256(folder/'constraints.json'),
                'checkpoint_revision':model_entry['revision'],'checkpoint_sha256':model_entry['files_sha256']['model.safetensors'],
                'kimodo_commit':source_check(),'generation_script_sha256':sha256(Path(__file__)),
                'diffusion_steps':study['diffusion_steps'],'cfg_type':study['cfg_type'],'cfg_weight':study['cfg_weight'],
                'encoder_qualification':encoder.metadata['execution'],'postprocessing':False}
            save(attempt/'record.json',record);seed_everything(seed);start=time.perf_counter()
            try:
                output=model([profile['prompt']],[round(study['duration_s']*study['fps'])],constraint_lst=constraints,
                    num_denoising_steps=study['diffusion_steps'],num_samples=1,multi_prompt=True,num_transition_frames=5,
                    post_processing=False,return_numpy=True,cfg_type=study['cfg_type'],cfg_weight=study['cfg_weight'])
                data={key:value[0] for key,value in output.items() if hasattr(value,'shape') and value.shape[0]==1}
                target=attempt/'motion.npz';save_kimodo_npz(str(target),data)
                with np.load(target,allow_pickle=False) as archive:data={k:archive[k] for k in archive.files}
                names,_,feet=validate_motion(data,study['fps'])
                save_motion_bvh(attempt/'motion.bvh',torch.from_numpy(data['local_rot_mats']),torch.from_numpy(data['root_positions']),skeleton=skeleton,fps=study['fps'],standard_tpose=True)
                record.update(status='generated',finished_at=now(),generation_time_s=time.perf_counter()-start,npz=str(target.resolve()),npz_sha256=sha256(target),metrics=metrics(data,names,feet,study['fps']))
                save(attempt/'record.json',record)
                print(f'Generated {profile["id"]}/{seed} in {record["generation_time_s"]:.1f}s',flush=True)
            except Exception as error:
                record.update(status='failed',finished_at=now(),error=str(error));save(attempt/'record.json',record);raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,default=DEFAULT_STUDY);p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.study,a.cache,a.output)
