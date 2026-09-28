"""Matched unchanged-checkpoint boundary conditioning study with feature capture."""
import copy
import os
import shutil
import time
from pathlib import Path
import numpy as np
from strep import ROOT,read,save,sha256,offline_environment,source_check,now
from strep import model_directory


def diagnostic(positions,expected):
    delta=positions-expected
    roots=delta[:,0]
    centered=delta-roots[:,None,:]
    return dict(max_joint_error_m=float(np.linalg.norm(delta,axis=-1).max()),max_root_error_m=float(np.linalg.norm(roots,axis=-1).max()),max_root_relative_error_m=float(np.linalg.norm(centered,axis=-1).max()),root_errors_m=roots.tolist(),per_frame_joint_max_m=np.linalg.norm(delta,axis=-1).max(axis=-1).tolist())


def guide_variant(original,mode):
    import torch
    from kimodo.motion_rep.smooth_root import get_smooth_root_pos
    data={k:v.copy() for k,v in original.items()};n=len(data['root_positions']);offset=np.zeros(3,dtype=np.float32)
    if mode not in ('baseline','smooth','dense','smooth_dense') or n<16:
        raise ValueError('Unknown guide mode or insufficient boundary context')
    if mode in ('smooth','smooth_dense'):
        data['smooth_root_pos']=get_smooth_root_pos(torch.from_numpy(data['root_positions'])).numpy().astype(np.float32)
        offset=data['smooth_root_pos'][0].copy();offset[1]=0
        for key in ('root_positions','posed_joints','smooth_root_pos'):data[key]-=offset
    frames=list(range(8))+list(range(n-8,n)) if mode in ('dense','smooth_dense') else [0,1,n-2,n-1]
    return data,frames,offset


def run(out,resume=False,guidance=False):
    os.environ.update(offline_environment())
    import torch
    from kimodo import load_model
    from kimodo.tools import seed_everything
    from kimodo.skeleton import SOMASkeleton77
    from kimodo.exports.motion_io import save_kimodo_npz
    from kimodo.exports.bvh import save_motion_bvh
    from action_encoder import ActionEncoder
    from generation_constraints import compile_guides,load_guides
    from audit_generation_guides import audit
    from inspect_motion import validate_motion
    from build_soma_preview import make_preview,ASSET
    from gltf_tools import write_glb
    from audit_body_ground import measure
    from action_worker_lock import worker_lock
    out=Path(out).resolve()
    if resume:
        if not out.is_dir() or read(out/'pipeline.json')['status']!='failed':raise ValueError('Resume requires a retained failed study')
        save(out/'previous-failure.json',read(out/'pipeline.json'))
    else:out.mkdir(parents=True,exist_ok=False)
    sources={'jump-205':'20260926-231829-75e87cd5','dance-203':'20260926-231039-29827f32'}
    if guidance:sources.update({'jump-204':'20260926-231304-7a8565eb','dance-204':'20260926-231129-6dfb83a6'})
    modes=['baseline','constraint3','constraint4','constraint6'] if guidance else ['baseline','smooth','dense','smooth_dense']
    design=dict(sources=sources,modes=modes,checkpoint_unchanged=True,seeds='Original saved seeds; paired comparisons only',scope='Retained failure cases, no held-out semantic claim. Constraint-weight sweep with text weight fixed at two.' if guidance else 'Two retained failure cases, no held-out semantic claim. Smoothing and eight-frame context tested individually and together. Baseline replay must reproduce saved raw motion. Features captured without altering model output.')
    if resume and read(out/'design.json')!=design:raise ValueError('Resume design differs')
    save(out/'design.json',design)
    snapshot=out/('implementation-resume' if resume else 'implementation');snapshot.mkdir()
    for name in ['study_boundary_guides.py','generation_constraints.py','audit_generation_guides.py']:
        shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    entry=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
    for name,digest in entry['files_sha256'].items():
        if sha256(model_directory(entry)/name)!=digest:raise ValueError('Checkpoint checksum mismatch')
    save(out/'pipeline.json',dict(status='starting'))
    results=[];skin=dict(np.load(ASSET,allow_pickle=False))
    with worker_lock():
        first=ROOT/'reports/rig-jobs'/sources['jump-205']/'generation'
        model=load_model('Kimodo-SOMA-RP-v1.1',device='cuda',text_encoder=ActionEncoder(first/'conditioning',read(first/'request.json')))
        original_generate=model._generate;captured={}
        def capture(*args,**kwargs):
            value=original_generate(*args,**kwargs)
            captured.update(features=value.detach().cpu(),observed=kwargs['observed_motion'].detach().cpu(),mask=kwargs['motion_mask'].detach().cpu())
            return value
        model._generate=capture
        for case,job in sources.items():
            source=ROOT/'reports/rig-jobs'/job;batch=read(source/'generation/request.json');request=batch['requests'][0];seed=request['seeds'][0]
            model.text_encoder=ActionEncoder(source/'generation/conditioning',batch)
            original=dict(np.load(source/'source/guide-motion.npz',allow_pickle=False));n=len(original['root_positions'])
            raw=dict(np.load(source/'generation/takes'/f'replacement-seed-{seed}'/'motion.npz',allow_pickle=False))
            for mode in modes:
                label=case+'-'+mode;folder=out/label;folder.mkdir(exist_ok=resume)
                save(out/'pipeline.json',dict(status='generating',case=case,mode=mode,completed=len(results)))
                guide,anchors,offset=guide_variant(original,'baseline' if mode.startswith('constraint') else mode);path=folder/'guide.npz'
                if (folder/'record.json').exists():
                    saved=read(folder/'request.json')
                    if sha256(path)!=saved['generation_constraints'][0]['sha256']:raise ValueError('Resume guide changed')
                else:np.savez_compressed(path,**guide)
                req=copy.deepcopy(request);req['generation_constraints'][0].update(motion=path.relative_to(ROOT).as_posix(),sha256=sha256(path),source_frames=anchors,frame_indices=anchors)
                if (folder/'record.json').exists() and read(folder/'request.json')!=req:raise ValueError('Resume request changed')
                compiled,provenance=compile_guides(req);constraints=load_guides(compiled,model.skeleton,device=model.device)
                save(folder/'request.json',req);save(folder/'constraints.json',compiled)
                cfg=[2.,float(mode[-1]) if mode.startswith('constraint') else 2.]
                if (folder/'record.json').exists():
                    old=read(folder/'record.json')
                    if old['raw_sha256']!=sha256(folder/'motion.npz') or old['raw_feature_sha256']!=sha256(folder/'feature-capture.npz') or old['checkpoint_sha256']!=entry['files_sha256']['model.safetensors'] or old['seed']!=seed or old['mode']!=mode or old.get('cfg_weight',[2,2])!=cfg:raise ValueError('Resume provenance mismatch')
                    cap=dict(np.load(folder/'feature-capture.npz',allow_pickle=False));captured.update({k:torch.from_numpy(cap[k]) for k in ('features','observed','mask')});seconds=old['generation_seconds']
                else:
                    seed_everything(seed);started=time.perf_counter()
                    output=model([s['prompt'] for s in req['segments']],[n],constraint_lst=constraints,num_denoising_steps=100,num_samples=1,multi_prompt=True,num_transition_frames=5,post_processing=False,return_numpy=True,cfg_type='separated',cfg_weight=cfg,first_heading_angle=req['first_heading_angle'])
                    seconds=time.perf_counter()-started;data={k:v[0] for k,v in output.items() if hasattr(v,'shape') and v.shape[0]==1}
                    save_kimodo_npz(str(folder/'motion.npz'),data)
                data=dict(np.load(folder/'motion.npz',allow_pickle=False));validate_motion(data,30)
                replay=None
                if mode=='baseline':
                    replay={k:float(np.abs(data[k].astype(float)-raw[k].astype(float)).max()) for k in ('root_positions','local_rot_mats','global_rot_mats','posed_joints','foot_contacts')}
                    if max(replay.values())>1e-5:raise ValueError('Baseline replay differs from frozen motion')
                features=captured['features'].to(model.device)
                pos=model.motion_rep.inverse(features,is_normalized=True,posed_joints_from='positions')['posed_joints'][0].detach().cpu().numpy()
                fk=model.motion_rep.inverse(features,is_normalized=True,posed_joints_from='rotations')['posed_joints'][0].detach().cpu().numpy()
                conditions=model.motion_rep.unnormalize(captured['observed'].to(model.device))
                expected_features=model.motion_rep.inverse(captured['observed'].to(model.device),is_normalized=True,posed_joints_from='positions')['posed_joints'][0].detach().cpu().numpy()
                expected=constraints[0].global_joints_positions.detach().cpu().numpy()
                condition_error=float(np.abs(expected_features[anchors]-expected).max())
                if condition_error>1e-5:raise ValueError('Compiled positions differ from guide conditioning')
                np.savez_compressed(folder/'feature-capture.npz',features=captured['features'].numpy(),observed=captured['observed'].numpy(),mask=captured['mask'].numpy(),position_head=pos,rotation_fk=fk)
                mask=captured['mask'][0].numpy();rotation_mask=mask[:,model.motion_rep.slice_dict['global_rot_data']]
                common=[0,1,n-2,n-1];index=[anchors.index(f) for f in common]
                guide_audit=audit(data,compiled);save(folder/'constraint-audit.json',guide_audit)
                ground=measure(data,skin);save(folder/'ground-audit.json',ground)
                record=dict(case=case,source_job=job,mode=mode,seed=seed,frames=n,generation_seconds=seconds,checkpoint_revision=entry['revision'],checkpoint_sha256=entry['files_sha256']['model.safetensors'],kimodo_commit=source_check(),encoder=model.text_encoder.metadata,guide_provenance=provenance,canonical_offset_from_original_m=offset.tolist(),anchors=anchors,condition_encoding_max_error=condition_error,position_head=diagnostic(pos[anchors],expected),rotation_fk=diagnostic(fk[anchors],expected),common_anchors_position_head=diagnostic(pos[common],expected[index]),common_anchors_rotation_fk=diagnostic(fk[common],expected[index]),position_vs_rotation_fk_max_m=float(np.linalg.norm(pos[anchors]-fk[anchors],axis=-1).max()),rotation_channels_masked=int(rotation_mask.sum()),baseline_replay_max_errors=replay,raw_sha256=sha256(folder/'motion.npz'),raw_feature_sha256=sha256(folder/'feature-capture.npz'),guides_passed=guide_audit['numerical_screen_passed'],native_mesh_floor_m=ground['mesh_max_depth_m'],human_approved=False)
                record.update(cfg_type='separated',cfg_weight=cfg,diffusion_steps=100,postprocessing=False)
                save(folder/'record.json',record)
                save_motion_bvh(folder/'motion.bvh',torch.from_numpy(data['local_rot_mats']),torch.from_numpy(data['root_positions']),skeleton=SOMASkeleton77(),fps=30,standard_tpose=True)
                document,binary,_,_=make_preview(skin,data,np.zeros(3),repeat=False);write_glb(folder/'soma.glb',document,binary)
                results.append({k:record[k] for k in ['case','mode','generation_seconds','guides_passed','common_anchors_position_head','common_anchors_rotation_fk','position_vs_rotation_fk_max_m','condition_encoding_max_error','rotation_channels_masked','baseline_replay_max_errors','native_mesh_floor_m']})
                save(out/'comparison.json',dict(cases=results,production_changed=False,quality_approved=False))
                print(label,results[-1],flush=True)
        model._generate=original_generate
    save(out/'pipeline.json',dict(status='complete',cases=len(results),finished_at=now()))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--resume',action='store_true');p.add_argument('--guidance',action='store_true');args=p.parse_args()
    existed=args.output.exists();previous=read(args.output/'pipeline.json')['status'] if (args.output/'pipeline.json').exists() else None
    try:run(args.output,args.resume,args.guidance)
    except Exception as exc:
        if (not existed or (args.resume and previous=='failed')) and (args.output/'pipeline.json').exists():save(args.output/'pipeline.json',dict(status='failed',error=str(exc),finished_at=now()))
        raise
