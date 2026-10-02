"""Offline development training; only a verified reviewed native corpus is used."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys

from strep import ROOT,read,save,sha256,now,offline_environment


def run(plan_path,output,*,until_step=None,resume=None,resume_manifest_sha256=None):
    import torch
    from omegaconf import OmegaConf
    from strep import source_check,model_directory
    from kimodo.model.loading import instantiate_from_dict
    from kimodo.model.diffusion import Diffusion
    from kimodo.sanitize import sanitize_texts
    from kimodo_training_corpus import _bound
    from kimodo_corpus_reader import verify_corpus
    from kimodo_adapter_probe import fingerprint,feedforward_adapters,unfused_transformer
    from kimodo_denoising_target import capture_full_noise_schedule
    from kimodo_corpus_trainer import train,configuration_hash,validate_plan,OBJECTIVE
    from action_encoder import ActionEncoder

    plan_path=Path(plan_path).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh training run directory required')
    output.mkdir();shutil.copyfile(plan_path,output/'input-plan.json')
    record={'schema':'strep-kimodo-reviewed-training-run-v1','status':'checking_inputs','started_at':now(),
            'quality_approved':False,'release_approved':False,'inputs_sha256':{str(plan_path):sha256(plan_path)},'methods_sha256':{}}
    save(output/'result.json',record)
    inputs=record['inputs_sha256']
    def archive():
        for module in tuple(sys.modules.values()):
            raw=getattr(module,'__file__',None)
            if not raw:continue
            path=Path(raw).resolve()
            if path.suffix=='.py' and (path.is_relative_to(ROOT/'scripts') or path.is_relative_to(ROOT/'vendor/kimodo/kimodo')):
                digest=sha256(path)
                if str(path) in inputs and inputs[str(path)]!=digest:raise ValueError('Imported training source changed')
                relative=path.relative_to(ROOT);dest=output/'methods'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,dest);assert sha256(dest)==digest
                inputs[str(path)]=digest;record['methods_sha256'][relative.as_posix()]=digest
    try:
        archive();plan=read(plan_path)
        if not isinstance(plan,dict) or set(plan)!={'schema','training','rank','alpha','corpus','conditioning'} or plan['schema']!='strep-kimodo-reviewed-training-plan-v1':
            raise ValueError('Explicit reviewed training plan required')
        if type(plan['rank']) is not int or not 1<=plan['rank']<=32 or isinstance(plan['alpha'],bool) or not isinstance(plan['alpha'],(int,float)) or not 0<plan['alpha']<=128:
            raise ValueError('Finite bounded adapter rank/alpha required')
        if not isinstance(plan['conditioning'],list) or not plan['conditioning']:raise ValueError('Pinned existing conditioning caches required')
        revision=source_check();manifest_path=ROOT/'models/manifest.json';inputs[str(manifest_path)]=sha256(manifest_path)
        entry=read(manifest_path)['models']['nvidia/Kimodo-SOMA-RP-v1.1'];checkpoint=model_directory(entry)
        for name,digest in entry['files_sha256'].items():
            if sha256(checkpoint/name)!=digest:raise ValueError('Pinned acquired model changed')
            inputs[str(checkpoint/name)]=digest
        config=OmegaConf.merge(OmegaConf.load(checkpoint/'config.yaml'),OmegaConf.create({'checkpoint_dir':str(checkpoint)}))
        conf=OmegaConf.to_container(config,resolve=True)
        schedule=capture_full_noise_schedule(Diffusion(num_base_steps=conf['num_base_steps']))
        validate_plan(plan['training'],schedule)
        pinned={name:digest for name,digest in entry['files_sha256'].items() if name=='config.yaml' or name.startswith('stats/')}
        codec={'vendor_revision':revision,'model_revision':entry['revision'],'representation_files_sha256':pinned,
               'inputs_sha256':{**{str(checkpoint/name):digest for name,digest in pinned.items()},
                               str(ROOT/'scripts/kimodo_denoising_target.py'):sha256(ROOT/'scripts/kimodo_denoising_target.py'),
                               str(ROOT/'scripts/kimodo_training_corpus.py'):sha256(ROOT/'scripts/kimodo_training_corpus.py')}}
        corpus_path=_bound(plan['corpus'],plan_path.parent,inputs)
        if corpus_path.name!='manifest.json':raise ValueError('Prepared corpus manifest required')
        rep=instantiate_from_dict(conf['denoiser']['motion_rep'])
        corpus=verify_corpus(corpus_path.parent,rep,expected_manifest_sha256=plan['corpus']['sha256'],expected_codec_binding=codec)
        text_by_prompt={}
        for source in plan['conditioning']:
            if not isinstance(source,dict) or set(source)!={'request','manifest'}:raise ValueError('Pinned conditioning request and manifest required')
            request_path=_bound(source['request'],plan_path.parent,inputs)
            cache_manifest=_bound(source['manifest'],plan_path.parent,inputs)
            meta=read(cache_manifest)
            for row in meta['entries'].values():
                path=(cache_manifest.parent/row['file']).resolve()
                if not path.is_relative_to(cache_manifest.parent):raise ValueError('Conditioning path escapes its cache')
                _bound({'path':str(path),'sha256':row['sha256']},plan_path.parent,inputs)
            encoder=ActionEncoder(cache_manifest.parent,read(request_path))
            for prompt in encoder.texts:
                feature=encoder([prompt])[0].detach().cpu().to(torch.float32)
                if prompt in text_by_prompt and not torch.equal(feature,text_by_prompt[prompt]):raise ValueError('Conflicting prompt features in caches')
                text_by_prompt[prompt]=feature
        texts={}
        for example in corpus.examples:
            prompt=sanitize_texts([example.prompt])[0]
            if prompt not in text_by_prompt:raise ValueError('Reviewed prompt absent from conditioning caches')
            texts[example.id]=text_by_prompt[prompt].clone()
        if not torch.cuda.is_available():raise RuntimeError('This native FP32 training entry point currently requires CUDA')
        torch.set_num_threads(2);torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False
        torch.manual_seed(plan['training']['seed'])
        model=instantiate_from_dict(conf['denoiser']);original=fingerprint(model);model=model.cuda()
        schedule=capture_full_noise_schedule(Diffusion(num_base_steps=conf['num_base_steps']).cuda())
        archive();record.update(status='training',model_revision=entry['revision'],vendor_revision=revision,base_fingerprint=original)
        save(output/'result.json',record)
        with unfused_transformer(),feedforward_adapters(model,plan['rank'],plan['alpha']) as adapters:
            binding={'model_id':entry['repo_id'],'model_revision':entry['revision'],'vendor_revision':revision,
                     'checkpoint_sha256':entry['files_sha256']['model.safetensors'],
                     'configuration_sha256':configuration_hash(plan['training'],corpus,texts,schedule,inputs),
                     'base_state_fingerprint':original,'objective':OBJECTIVE,
                     'data_manifest_sha256':corpus.manifest_sha256,'purpose':'development_training'}
            result=train(corpus,model,adapters,texts,schedule,plan['training'],binding,output/'training',until_step=until_step,
                         resume=resume,resume_manifest_sha256=resume_manifest_sha256,extra_bindings=inputs)
        if fingerprint(model)!=original:raise ValueError('Frozen base changed during training')
        if any(sha256(path)!=digest for path,digest in inputs.items()):raise ValueError('Training inputs changed')
        corpus.assert_unchanged()
        record.update(status=result['status'],finished_at=now(),completed_steps=result['completed_steps'],
                      result_path=str(output/'training/result.json'),base_unchanged=True,inputs_unchanged=True)
        save(output/'result.json',record);return record
    except Exception as exc:
        try:archive()
        except Exception as archive_error:record['archive_error']=str(archive_error)
        record.update(status='failed',finished_at=now(),error=str(exc));save(output/'result.json',record);raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--until-step',type=int);parser.add_argument('--resume',type=Path);parser.add_argument('--resume-manifest-sha256')
    args=parser.parse_args();os.environ.update(offline_environment());os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
    sys.path.insert(0,str(ROOT/'vendor/kimodo'))
    from action_worker_lock import worker_lock
    with worker_lock():print(run(args.plan,args.output,until_step=args.until_step,resume=args.resume,resume_manifest_sha256=args.resume_manifest_sha256))


if __name__=='__main__':main()
