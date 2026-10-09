"""Generate open-vocabulary clips/sequences and preserve every attempt."""
import argparse
import os
import time
from pathlib import Path
from strep import ROOT,read,save,sha256,now,source_check,offline_environment
from strep import model_directory
from action_requests import validate_batch,timeline,request_digest
from generation_constraints import compile_guides,load_guides
from motion_profile import brief,resolved_segments


def load_motion_backend(encoder,checkpoint_transport):
    """Explicit worker choice; the established upstream path stays the default."""
    if checkpoint_transport=='upstream':
        from kimodo import load_model
        return load_model('Kimodo-SOMA-RP-v1.1',device='cuda',text_encoder=encoder),None
    if checkpoint_transport=='cuda-streamed':
        from motion_checkpoint_transport import load_cuda_motion_model
        return load_cuda_motion_model(encoder)
    raise ValueError('Unknown checkpoint transport')


def main(request_path,folder,*,checkpoint_transport='upstream'):
    if checkpoint_transport not in ('upstream','cuda-streamed'):raise ValueError('Unknown checkpoint transport')
    os.environ.update(offline_environment())
    import numpy as np
    import torch
    from kimodo.tools import seed_everything
    from kimodo.exports.motion_io import save_kimodo_npz
    from kimodo.exports.bvh import save_motion_bvh
    from kimodo.skeleton import SOMASkeleton77
    from action_encoder import ActionEncoder
    from inspect_motion import validate_motion,metrics
    from audit_generation_guides import audit
    batch=validate_batch(read(request_path));folder=Path(folder)
    # Fail before GPU loading, including when resuming an existing generation.
    guides={r['id']:compile_guides(r) for r in batch['requests']}
    entry=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
    for name,digest in entry['files_sha256'].items():
        if sha256(model_directory(entry)/name)!=digest:raise ValueError('Checkpoint checksum mismatch')
    encoder=ActionEncoder(folder/'conditioning',batch)
    model,transport_receipt=load_motion_backend(encoder,checkpoint_transport);skeleton=SOMASkeleton77()
    for request in batch['requests']:
        compiled,provenance=guides[request['id']]
        constraints=load_guides(compiled,model.skeleton,device=model.device)
        for seed in request['seeds']:
            parent=folder/'raw'/request['id']/f'seed-{seed}';parent.mkdir(parents=True,exist_ok=True)
            previous=sorted(parent.glob('attempt-*/record.json'))
            valid=[read(p) for p in previous if read(p)['status']=='generated']
            if valid:
                last=valid[-1]
                if last['request_sha256']!=request_digest(batch) or sha256(last['npz'])!=last['npz_sha256']:raise ValueError('Resume mismatch')
                continue
            attempt=parent/f'attempt-{len(previous)+1:03d}';attempt.mkdir()
            record={'status':'running','started_at':now(),'request':request,'seed':seed,'request_sha256':request_digest(batch),
                'kimodo_commit':source_check(),'checkpoint_revision':entry['revision'],'checkpoint_sha256':entry['files_sha256']['model.safetensors'],
                'encoder':encoder.metadata,'fps':30,'diffusion_steps':100,'cfg_type':'separated','cfg_weight':[2,2],
                'postprocessing':False,'constraints':compiled,'constraint_sources':provenance,
                'constraint_adapter_sha256':sha256(ROOT/'scripts/generation_constraints.py'),
                'num_transition_frames':5,'timeline':timeline(request),
                'scene_status':'Single humanoid only; no objects, partner tracks or scene-aware contact solving.',
                'generation_script_sha256':sha256(Path(__file__))}
            record['first_heading_angle']=request.get('first_heading_angle',0.)
            if transport_receipt is not None:
                record['checkpoint_transport']=transport_receipt
                record['checkpoint_transport_script_sha256']=sha256(ROOT/'scripts/motion_checkpoint_transport.py')
            if 'motion_profile' in request:record['motion_brief']=brief(request)
            save(attempt/'record.json',record);seed_everything(seed);started=time.perf_counter()
            try:
                frames=[s['end_frame_exclusive']-s['start_frame'] for s in record['timeline']]
                output=model([s['prompt'] for s in resolved_segments(request)],frames,constraint_lst=constraints,
                    num_denoising_steps=100,num_samples=1,multi_prompt=True,num_transition_frames=5,
                    post_processing=False,return_numpy=True,cfg_type='separated',cfg_weight=[2,2],first_heading_angle=request.get('first_heading_angle'))
                data={k:v[0] for k,v in output.items() if hasattr(v,'shape') and v.shape[0]==1}
                target=attempt/'motion.npz';save_kimodo_npz(str(target),data);data=dict(np.load(target,allow_pickle=False))
                names,_,feet=validate_motion(data,30)
                if len(data['posed_joints'])!=sum(frames):raise ValueError('Unexpected sequence frame count')
                save_motion_bvh(attempt/'motion.bvh',torch.from_numpy(data['local_rot_mats']),torch.from_numpy(data['root_positions']),skeleton=skeleton,fps=30,standard_tpose=True)
                if compiled:save(attempt/'constraint-audit.json',audit(data,compiled))
                record.update(status='generated',npz=str(target.resolve()),npz_sha256=sha256(target),
                              generation_time_s=time.perf_counter()-started,metrics=metrics(data,names,feet,30),finished_at=now())
                print(f"Generated {request['id']}/{seed}: {len(data['posed_joints'])} frames",flush=True)
            except Exception as exc:
                record.update(status='failed',error=str(exc),finished_at=now());save(attempt/'record.json',record);raise
            save(attempt/'record.json',record)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('request',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--checkpoint-transport',choices=['upstream','cuda-streamed'],default='upstream')
    a=p.parse_args();main(a.request,a.output,checkpoint_transport=a.checkpoint_transport)
