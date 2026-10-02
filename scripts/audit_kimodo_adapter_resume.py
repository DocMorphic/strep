"""Real-checkpoint numerical AdamW resume canary; no motion training data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time


def run(output):
    from strep import ROOT, read, save, sha256, now, source_check, model_directory
    import torch
    from safetensors.torch import save_file
    from omegaconf import OmegaConf
    from kimodo.model.loading import instantiate_from_dict
    from kimodo_adapter_probe import feedforward_adapters, unfused_transformer, fingerprint
    from kimodo_adapter_state import save_state, load_state
    from kimodo_denoising_target import clean_motion_loss
    if output.exists():
        raise ValueError('Fresh output required; preserve previous checkpoints/failures')
    output.mkdir(parents=True)
    protocol = {'schema':'strep-adapter-resume-canary-v1','seed':1236,'dtype':'float32','batch':1,'frames':30,
                'input':'Torch Gaussian plus .01 times a CPU Gaussian scalar', 'target':'zero feature tensor, not a valid motion',
                'text':'zero tensor, no encoded prompt','timestep':500,'heading':0,'rank':8,'alpha':8,
                'save_after_step':3,'reference_end_step':5,'replayed_updates':2,
                'optimizer':{'type':'AdamW','lr':.0001,'foreach':False,'fused':False},
                'purpose':'numerical lifecycle only; no corpus admission or quality claim'}
    save(output/'protocol.json',protocol)
    result = {'schema':'strep-adapter-resume-canary-result-v1','started_at':now(),'status':'running',
              'quality_approved':False,'release_approved':False,'trained_motion_model':False,
              'logical_optimizer_steps':0,'physical_optimizer_updates':0,'prefix':[],'reference':[],'replay':[],
              'inputs_sha256':{},'methods_sha256':{}}
    def archive_methods():
        for module in tuple(sys.modules.values()):
            raw = getattr(module,'__file__',None)
            if raw:
                path = Path(raw).resolve()
                if path.suffix == '.py' and (path.is_relative_to(ROOT/'scripts') or path.is_relative_to(ROOT/'vendor/kimodo/kimodo')):
                    relative = str(path.relative_to(ROOT))
                    if relative in result['methods_sha256'] and sha256(path) != result['methods_sha256'][relative]:
                        raise RuntimeError('Imported source changed')
                    dest = output/'methods'/relative
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(path,dest)
                    result['methods_sha256'][relative] = sha256(path)
    archive_methods()
    save(output/'result.json',result)
    try:
        revision = source_check()
        entry = read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
        checkpoint = model_directory(entry)
        for name,expected in entry['files_sha256'].items():
            path = checkpoint/name
            if sha256(path) != expected:
                raise ValueError('Pinned checkpoint changed')
            result['inputs_sha256'][str(path)] = expected
        if not torch.cuda.is_available():
            raise RuntimeError('This real-checkpoint canary requires CUDA')
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.manual_seed(protocol['seed'])
        config = OmegaConf.merge(OmegaConf.load(checkpoint/'config.yaml'),OmegaConf.create({'checkpoint_dir':str(checkpoint)}))
        model = instantiate_from_dict(OmegaConf.to_container(config,resolve=True)['denoiser'])
        original = fingerprint(model)
        model = model.cuda().train()
        result.update(gpu=torch.cuda.get_device_name(),torch=torch.__version__,cuda_runtime=torch.version.cuda,
                      base_fingerprint_before=original,base_parameter_count=sum(p.numel() for p in model.parameters()))
        config_binding = {'checkpoint_files_sha256':entry['files_sha256'],
                          'state_method_sha256':sha256(ROOT/'scripts/kimodo_adapter_state.py'),
                          'adapter_method_sha256':sha256(ROOT/'scripts/kimodo_adapter_probe.py'),
                          'objective_method_sha256':sha256(ROOT/'scripts/kimodo_denoising_target.py')}
        binding = {'model_id':entry['repo_id'],'model_revision':entry['revision'],'vendor_revision':revision,
                   'checkpoint_sha256':entry['files_sha256']['model.safetensors'],
                   'configuration_sha256':hashlib.sha256(json.dumps(config_binding,sort_keys=True).encode()).hexdigest(),
                   'base_state_fingerprint':original,'objective':'experimental-stage-balanced-x0/numerical-zero-target',
                   'data_manifest_sha256':sha256(output/'protocol.json'),'purpose':'numerical_lifecycle'}
        dim = model.motion_rep.motion_rep_dim
        valid = torch.ones(1,30,dtype=torch.bool,device='cuda')
        clean = torch.zeros(1,30,dim,device='cuda')
        def optimizer(adapters,lr=.0001):
            return torch.optim.AdamW([p for _,layer in adapters for p in (layer.a,layer.b)],lr=lr,foreach=False,fused=False)
        def update(optim,branch,step):
            optim.zero_grad(set_to_none=True)
            cpu_noise = torch.randn(3)
            noisy = torch.randn_like(clean) + .01 * float(cpu_noise[0])
            start = time.perf_counter()
            prediction = model(x=noisy,x_pad_mask=valid,text_feat=torch.zeros(1,1,4096,device='cuda'),
                               text_feat_pad_mask=torch.ones(1,1,dtype=torch.bool,device='cuda'),
                               timesteps=torch.tensor([500],device='cuda'),first_heading_angle=torch.zeros(1,device='cuda'))
            loss = clean_motion_loss(prediction,clean,valid)
            loss['loss'].backward()
            optim.step()
            torch.cuda.synchronize()
            row = {'logical_step':step,'loss':float(loss['loss'].detach()),
                   'root_loss':float(loss['root_loss'].detach()),'body_loss':float(loss['body_loss'].detach()),
                   'elapsed_seconds':time.perf_counter()-start,
                   'input_sha256':hashlib.sha256(noisy.detach().cpu().numpy().tobytes()).hexdigest(),
                   'cpu_draw':cpu_noise.tolist(),'base_gradients_present':any(p.grad is not None for p in model.parameters() if not p.requires_grad)}
            if row['base_gradients_present'] or not torch.isfinite(loss['loss']):
                raise RuntimeError('Invalid canary update')
            result[branch].append(row)
            result['physical_optimizer_updates'] += 1
            save(output/'result.json',result)
            return row
        archive_methods()
        torch.cuda.reset_peak_memory_stats()
        with unfused_transformer(),feedforward_adapters(model,8,8) as adapters:
            optim = optimizer(adapters)
            for step in range(1,4):
                update(optim,'prefix',step)
            saved = save_state(output/'checkpoint-step-3',adapters,binding,model=model,completed_steps=3,optimizer=optim,
                               cursor={'epoch':0,'next_example':3})
            print('Saved numerical checkpoint at logical step 3',flush=True)
            for step in (4,5):
                update(optim,'reference',step)
            expected = {name+suffix:p.detach().cpu().clone() for name,layer in adapters for suffix,p in (('.a',layer.a),('.b',layer.b))}
            expected_states = {name+suffix+'.'+key:value.detach().cpu().clone() for name,layer in adapters
                               for suffix,p in (('.a',layer.a),('.b',layer.b)) for key,value in optim.state[p].items()}
            save_file({**expected,**expected_states},str(output/'reference-step-5.safetensors'))
        torch.manual_seed(999999)
        with unfused_transformer(),feedforward_adapters(model,8,8) as adapters:
            resumed = optimizer(adapters,lr=.01)
            restored = load_state(output/'checkpoint-step-3',adapters,binding,model=model,optimizer=resumed,restore_rng=True)
            if restored['completed_steps'] != 3 or resumed.param_groups[0]['lr'] != .0001:
                raise RuntimeError('Counter/hyperparameter restoration failed')
            for step in (4,5):
                update(resumed,'replay',step)
            actual = {name+suffix:p.detach().cpu().clone() for name,layer in adapters for suffix,p in (('.a',layer.a),('.b',layer.b))}
            actual_states = {name+suffix+'.'+key:value.detach().cpu().clone() for name,layer in adapters
                             for suffix,p in (('.a',layer.a),('.b',layer.b)) for key,value in resumed.state[p].items()}
            result['adapter_max_delta'] = max(float((actual[key]-value).abs().max()) for key,value in expected.items())
            result['optimizer_max_delta'] = max(float((actual_states[key]-value).abs().max()) for key,value in expected_states.items())
            result['replay_inputs_identical'] = all(a['input_sha256'] == b['input_sha256'] and a['cpu_draw'] == b['cpu_draw'] for a,b in zip(result['reference'],result['replay']))
            result['replay_losses_identical'] = all(a['loss'] == b['loss'] for a,b in zip(result['reference'],result['replay']))
            save_state(output/'resumed-step-5',adapters,binding,model=model,completed_steps=5,optimizer=resumed,
                       cursor={'epoch':0,'next_example':5})
        result.update(base_fingerprint_after=fingerprint(model),peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                      peak_reserved_bytes=torch.cuda.max_memory_reserved(),logical_optimizer_steps=5)
        if result['base_fingerprint_after'] != original or result['adapter_max_delta'] != 0 or result['optimizer_max_delta'] != 0 or not result['replay_inputs_identical'] or not result['replay_losses_identical']:
            raise RuntimeError('Numerical resume diverged or base changed')
        for name,expected_hash in result['inputs_sha256'].items():
            if sha256(name) != expected_hash:
                raise RuntimeError('Pinned input changed during canary')
        for name,expected_hash in result['methods_sha256'].items():
            if sha256(ROOT/name) != expected_hash:
                raise RuntimeError('Archived method changed during canary')
        result.update(status='complete',base_unchanged=True,input_files_unchanged=True,methods_unchanged=True)
        print(json.dumps({key:result[key] for key in ('status','adapter_max_delta','optimizer_max_delta','replay_inputs_identical','replay_losses_identical','peak_allocated_bytes')}),flush=True)
    except Exception as exc:
        result.update(status='failed',error_type=type(exc).__name__,error=str(exc))
        raise
    finally:
        result['finished_at'] = now()
        save(output/'result.json',result)


def main():
    from strep import ROOT,offline_environment
    from action_worker_lock import worker_lock
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args = parser.parse_args()
    os.environ.update(offline_environment())
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    sys.path.insert(0,str(ROOT/'vendor/kimodo'))
    with worker_lock():
        run(args.output)


if __name__ == '__main__':
    main()
