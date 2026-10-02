"""Sequential experimental x0 adapter training over a verified native corpus."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import time

import torch

from strep import read,save,sha256,now
from kimodo_corpus_reader import VerifiedCorpus
from kimodo_adapter_state import save_state,load_state
from kimodo_denoising_target import denoising_inputs,clean_motion_loss,FullNoiseSchedule

OBJECTIVE='experimental-stage-balanced-x0/v1'


def validate_plan(plan,schedule):
    if not isinstance(schedule,FullNoiseSchedule):raise ValueError('Captured full original noise schedule required')
    fields={'schema','seed','epochs','learning_rate','weight_decay','gradient_clip',
            'checkpoint_every','condition','validation_seed','validation_timesteps'}
    if not isinstance(plan,dict) or set(plan)!=fields or plan['schema']!='strep-native-adapter-training-v1':
        raise ValueError('Explicit native training plan required')
    for key in ('seed','validation_seed'):
        if type(plan[key]) is not int or not 0<=plan[key]<2**32:raise ValueError('Integer seed required')
    for key in ('epochs','checkpoint_every'):
        if type(plan[key]) is not int or not 1<=plan[key]<=10000:raise ValueError('Positive bounded epoch/checkpoint interval required')
    for key in ('learning_rate','weight_decay','gradient_clip'):
        value=plan[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or (key!='weight_decay' and value==0):
            raise ValueError('Finite learning rate, decay and clipping values required')
    if plan['condition'] not in ('unconstrained','first_last_pose'):raise ValueError('Explicit supported condition required')
    steps=plan['validation_timesteps']
    if not isinstance(steps,list) or not steps or any(type(t) is not int or not 0<=t<schedule.num_base_steps for t in steps) or len(set(steps))!=len(steps):
        raise ValueError('Distinct original-schedule validation timesteps required')


def tensor_digest(value):
    value=value.detach().cpu().contiguous()
    return hashlib.sha256(str((value.dtype,tuple(value.shape))).encode()+value.numpy().tobytes()).hexdigest()


def configuration_hash(plan,corpus,texts,schedule,extra_bindings=None):
    """Bind the objective, stream, embeddings, schedule and imported methods."""
    validate_plan(plan,schedule)
    if type(corpus) is not VerifiedCorpus:raise ValueError('Use the fully verified corpus reader')
    if set(texts)!={row.id for row in corpus.examples}:raise ValueError('Every example needs exact prompt conditioning')
    for text in texts.values():
        if not isinstance(text,torch.Tensor) or text.dtype!=torch.float32 or tuple(text.shape)!=(1,1,4096) or not torch.isfinite(text).all() or text.requires_grad:
            raise ValueError('Detached finite FP32 prompt features required')
    methods=['kimodo_corpus_trainer.py','kimodo_corpus_reader.py','kimodo_adapter_state.py','kimodo_adapter_probe.py','kimodo_denoising_target.py']
    value={'objective':OBJECTIVE,'plan':plan,'manifest':corpus.manifest_sha256,
           'stream':[{k:getattr(row,k) for k in ('id','prompt','split','frames','target_sha256')} for row in corpus.examples],
           'text':{key:tensor_digest(value) for key,value in texts.items()},
           'schedule':{'steps':schedule.num_base_steps,'clean':tensor_digest(schedule.sqrt_alpha),'noise':tensor_digest(schedule.sqrt_one_minus_alpha)},
           'methods':{name:sha256(Path(__file__).parent/name) for name in methods},'extra_bindings':extra_bindings or {}}
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def train(corpus,model,adapters,texts,schedule,plan,binding,output,*,until_step=None,
          resume=None,resume_manifest_sha256=None,extra_bindings=None):
    """Batch-one sequential updates; validation uses isolated fixed RNG draws.

    Caller verifies the base/codec/text caches, installs adapters inside
    unfused_transformer(), and supplies independent model/data bindings.
    No automatic promotion, data admission, shuffled loader or mixed precision.
    """
    validate_plan(plan,schedule)
    expected=configuration_hash(plan,corpus,texts,schedule,extra_bindings)
    if binding['configuration_sha256']!=expected or binding['data_manifest_sha256']!=corpus.manifest_sha256 or binding['objective']!=OBJECTIVE:
        raise ValueError('Training configuration, objective or corpus differs from binding')
    training=[row for row in corpus.examples if row.split=='train']
    validation=[row for row in corpus.examples if row.split=='development_validation']
    if not training or not validation or len(training)+len(validation)!=len(corpus.examples):
        raise ValueError('Separate nonempty training and development validation populations required')
    if plan['condition']=='first_last_pose' and any(row.frames<3 for row in corpus.examples):
        raise ValueError('Endpoint observations require an unobserved interior frame')
    total=plan['epochs']*len(training)
    stop=total if until_step is None else until_step
    if type(stop) is not int or not 0<=stop<=total:raise ValueError('Stop must be an absolute planned update count')
    output=Path(output).resolve()
    if output.exists():raise ValueError('Fresh training attempt directory required')
    factors=[p for _,layer in adapters for p in (layer.a,layer.b)]
    if not factors:raise ValueError('Installed adapters required')
    device=factors[0].device
    if schedule.sqrt_alpha.device!=device or any(p.device!=device or p.dtype!=torch.float32 for p in model.parameters()):
        raise ValueError('FP32 model/factors and full schedule must share a device')
    optimizer=torch.optim.AdamW(factors,lr=plan['learning_rate'],weight_decay=plan['weight_decay'],foreach=False,fused=False)
    inputs=dict(extra_bindings or {})
    def unchanged():
        corpus.assert_unchanged()
        for path,digest in inputs.items():
            if sha256(path)!=digest:raise ValueError('Training source/model/conditioning file changed')
        if configuration_hash(plan,corpus,texts,schedule,extra_bindings)!=expected:
            raise ValueError('Training method, plan, schedule or prompt features changed')
    unchanged();output.mkdir();save(output/'plan.json',plan)
    record={'schema':'strep-native-adapter-training-result-v1','status':'running','started_at':now(),
            'binding':binding,'train_ids':[row.id for row in training],'validation_ids':[row.id for row in validation],
            'completed_steps':0,'attempted_optimizer_updates':0,'updates':[],'validation':[],
            'quality_approved':False,'release_approved':False,'scope':'Experimental denoising supervision; losses do not establish animation quality'}
    steps=0;previous_training=model.training
    def args(row,noise,timesteps):
        values=corpus.read(row.id);clean=values['clean_features'].to(device)
        valid=torch.ones((1,row.frames),dtype=torch.bool,device=device)
        observed=torch.zeros_like(clean,dtype=torch.bool)
        if plan['condition']=='first_last_pose':observed[:,[0,-1]]=True
        result=denoising_inputs(clean,noise,timesteps,schedule,texts[row.id].to(device),values['first_heading'].to(device),valid=valid,observed=observed)
        return result,clean,valid,observed
    def evaluate():
        was_training=model.training;model.eval();rows=[]
        devices=[device.index if device.index is not None else torch.cuda.current_device()] if device.type=='cuda' else []
        try:
            with torch.random.fork_rng(devices=devices),torch.no_grad():
                for index,row in enumerate(validation):
                    for offset,t in enumerate(plan['validation_timesteps']):
                        generator=torch.Generator(device=device).manual_seed(plan['validation_seed']+index*len(plan['validation_timesteps'])+offset)
                        noise=torch.randn((1,row.frames,369),device=device,generator=generator)
                        call,clean,valid,observed=args(row,noise,torch.tensor([t],device=device))
                        loss=clean_motion_loss(model(**call),clean,valid,observed)
                        rows.append({'id':row.id,'timestep':t,'loss':float(loss['loss']),
                                     'root_loss':float(loss['root_loss']),'body_loss':float(loss['body_loss']),
                                     'noise_sha256':tensor_digest(noise)})
        finally:model.train(was_training)
        record['validation'].append({'after_step':steps,'rows':rows})
    def checkpoint():
        unchanged()
        path=output/f'checkpoint-step-{steps}'
        save_state(path,adapters,binding,model=model,completed_steps=steps,optimizer=optimizer,
                   cursor={'epoch':steps//len(training),'next_example':steps%len(training)})
        record['last_checkpoint']={'path':str(path),'manifest_sha256':sha256(path/'manifest.json')}
    try:
        if resume is not None:
            path=Path(resume)/'manifest.json'
            if not isinstance(resume_manifest_sha256,str) or sha256(path)!=resume_manifest_sha256:
                raise ValueError('Pinned resume manifest required')
            metadata=read(path);steps=metadata['completed_steps']
            if type(steps) is not int or not 0<=steps<=stop or metadata['cursor']!={'epoch':steps//len(training),'next_example':steps%len(training)}:
                raise ValueError('Resume cursor differs from the sequential training stream')
            load_state(resume,adapters,binding,model=model,optimizer=optimizer,restore_rng=True)
            record['resume']={'path':str(resume),'manifest_sha256':resume_manifest_sha256,'completed_steps':steps}
        else:
            if resume_manifest_sha256 is not None:raise ValueError('Resume hash without a checkpoint')
            torch.manual_seed(plan['seed'])
        record['completed_steps']=steps
        # Establish a fully checked zero/resume-step checkpoint before any update.
        checkpoint();evaluate();save(output/'result.json',record)
        model.train()
        while steps<stop:
            row=training[steps%len(training)]
            optimizer.zero_grad(set_to_none=True)
            noise=torch.randn((1,row.frames,369),device=device)
            timesteps=torch.randint(schedule.num_base_steps,(1,),device=device)
            call,clean,valid,observed=args(row,noise,timesteps)
            started=time.perf_counter();loss=clean_motion_loss(model(**call),clean,valid,observed)
            if loss['root_channel_count']==0 or loss['body_channel_count']==0:raise ValueError('No supervised channels')
            loss['loss'].backward()
            if any(p.grad is None or not torch.isfinite(p.grad).all() for p in factors):raise ValueError('Finite gradients for every factor required')
            if any(p.grad is not None for p in model.parameters() if not p.requires_grad):raise ValueError('Frozen base received gradients')
            norm=torch.nn.utils.clip_grad_norm_(factors,plan['gradient_clip'],error_if_nonfinite=True)
            record['attempted_optimizer_updates']+=1;optimizer.step()
            if any(not torch.isfinite(p).all() for p in factors):raise ValueError('Nonfinite updated factors')
            steps+=1;record['completed_steps']=steps
            record['updates'].append({'step':steps,'id':row.id,'timestep':int(timesteps[0]),'noise_sha256':tensor_digest(noise),
                                      'loss':float(loss['loss'].detach()),'root_loss':float(loss['root_loss'].detach()),
                                      'body_loss':float(loss['body_loss'].detach()),'gradient_norm_before_clip':float(norm),
                                      'elapsed_seconds':time.perf_counter()-started})
            if steps%plan['checkpoint_every']==0 or steps%len(training)==0 or steps==stop:
                checkpoint();evaluate()
            save(output/'result.json',record)
        unchanged();record.update(status='complete' if steps==total else 'stopped_at_requested_step',finished_at=now(),inputs_unchanged=True)
        save(output/'result.json',record);return record
    except Exception as exc:
        record.update(status='failed',finished_at=now(),error=str(exc));save(output/'result.json',record);raise
    finally:model.train(previous_training)
