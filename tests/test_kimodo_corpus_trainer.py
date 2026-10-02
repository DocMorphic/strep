"""Numerical trainer fixtures only; no real human review or learned motion claim."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest
import torch
from torch import nn
from safetensors.torch import load_file

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_kimodo_corpus_reader import prepared,verify
from test_kimodo_training_corpus import fixture,Rep
import kimodo_training_corpus as producer
from kimodo_corpus_reader import verify_corpus
from kimodo_corpus_trainer import train,configuration_hash,validate_plan,OBJECTIVE
from kimodo_denoising_target import FullNoiseSchedule
from kimodo_adapter_probe import feedforward_adapters,unfused_transformer,fingerprint
from strep import read,save,sha256


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__();self.input=nn.Linear(369,8);self.output=nn.Linear(8,369)
        for name in ('root_model','body_model'):
            block=nn.Module();block.seqTransEncoder=nn.TransformerEncoder(
                nn.TransformerEncoderLayer(8,2,16,dropout=.1,batch_first=True),1,enable_nested_tensor=False)
            setattr(self,name,block)
    def forward(self,**args):
        x=self.input(args['x'])
        x=x+args['text_feat'][...,:8]+args['timesteps'][:,None,None]/1000
        return self.output(self.body_model.seqTransEncoder(self.root_model.seqTransEncoder(x)))


PLAN=dict(schema='strep-native-adapter-training-v1',seed=91,epochs=4,learning_rate=.003,weight_decay=.01,
          gradient_clip=1.,checkpoint_every=2,condition='unconstrained',validation_seed=77,validation_timesteps=[0,3])


def schedule():return FullNoiseSchedule(4,torch.tensor([.99,.8,.6,.1]),torch.tensor([.1,.6,.8,.99]))


def conditioning(corpus):return {row.id:torch.full((1,1,4096),index/10) for index,row in enumerate(corpus.examples)}


def identity(model,corpus,texts,plan=PLAN):
    return dict(model_id='numerical_fixture',model_revision='0'*40,vendor_revision='1'*40,checkpoint_sha256='a'*64,
                configuration_sha256=configuration_hash(plan,corpus,texts,schedule()),base_state_fingerprint=fingerprint(model),
                objective=OBJECTIVE,data_manifest_sha256=corpus.manifest_sha256,purpose='numerical_lifecycle')


@pytest.fixture(autouse=True)
def threads():
    previous=torch.get_num_threads();torch.set_num_threads(2)
    yield
    torch.set_num_threads(previous)


def execution(f,output,*,plan=PLAN,stop=None,resume=None,seed=25,model=None):
    corpus=verify(f);texts=conditioning(corpus)
    if model is None:torch.manual_seed(100);model=TinyModel()
    bound=identity(model,corpus,texts,plan);before=fingerprint(model)
    torch.manual_seed(seed)
    with unfused_transformer(),feedforward_adapters(model,2,2) as adapters:
        result=train(corpus,model,adapters,texts,schedule(),plan,bound,output,until_step=stop,resume=resume,
                     resume_manifest_sha256=sha256(Path(resume)/'manifest.json') if resume else None)
    assert fingerprint(model)==before
    return result


def test_actual_verified_targets_update_only_train_and_keep_fixed_validation(prepared):
    f=prepared;model=TinyModel().eval();result=execution(f,f.root/'attempt',model=model)
    assert result['status']=='complete' and result['completed_steps']==4
    assert [row['id'] for row in result['updates']]==['segment0']*4
    assert all(row['id']=='segment1' for report in result['validation'] for row in report['rows'])
    assert len({tuple(row['noise_sha256'] for row in report['rows']) for report in result['validation']})==1
    assert model.training is False and result['quality_approved'] is result['release_approved'] is False
    final=load_file(f.root/'attempt/checkpoint-step-4/adapter.safetensors')
    initial=load_file(f.root/'attempt/checkpoint-step-0/adapter.safetensors')
    assert any(not torch.equal(final[key],initial[key]) for key in final)


def test_interrupted_stream_replays_inputs_losses_and_all_checkpoint_tensors(prepared):
    f=prepared;full=execution(f,f.root/'full');prefix=execution(f,f.root/'prefix',stop=2)
    assert prefix['status']=='stopped_at_requested_step'
    resumed=execution(f,f.root/'resumed',resume=f.root/'prefix/checkpoint-step-2',seed=999)
    for expected,actual in zip(full['updates'][2:],resumed['updates']):
        assert {k:v for k,v in expected.items() if k!='elapsed_seconds'}=={k:v for k,v in actual.items() if k!='elapsed_seconds'}
    for name in ('adapter.safetensors','training.safetensors'):
        a=load_file(f.root/'full/checkpoint-step-4'/name);b=load_file(f.root/'resumed/checkpoint-step-4'/name)
        assert a.keys()==b.keys() and all(torch.equal(a[key],b[key]) for key in a)


@pytest.mark.parametrize('field,value',[('seed',True),('epochs',0),('learning_rate',float('nan')),('weight_decay',-1),
                                       ('gradient_clip',0),('condition','invented'),('validation_timesteps',[4]),('validation_timesteps',[0,0])])
def test_invalid_plans_rejected_before_updates(field,value):
    plan=copy.deepcopy(PLAN);plan[field]=value
    with pytest.raises(ValueError):validate_plan(plan,schedule())


def test_configuration_binds_prompt_features_schedule_and_plan(prepared):
    corpus=verify(prepared);text=conditioning(corpus);original=configuration_hash(PLAN,corpus,text,schedule())
    changed=copy.deepcopy(PLAN);changed['condition']='first_last_pose'
    assert configuration_hash(changed,corpus,text,schedule())!=original
    text['segment0'].add_(1);assert configuration_hash(PLAN,corpus,text,schedule())!=original
    with pytest.raises(ValueError,match='verified'):configuration_hash(PLAN,object(),text,schedule())


def test_empty_validation_or_unobserved_interior_rejected(prepared):
    f=prepared;corpus=verify(f);corpus.examples=tuple(replace(row,split='train') for row in corpus.examples)
    model=TinyModel();texts=conditioning(corpus);bound=identity(model,corpus,texts)
    with unfused_transformer(),feedforward_adapters(model,2,2) as adapters:
        with pytest.raises(ValueError,match='validation'):train(corpus,model,adapters,texts,schedule(),PLAN,bound,f.root/'bad')
    corpus=verify(f);corpus.examples=tuple(replace(row,frames=2) for row in corpus.examples)
    plan={**PLAN,'condition':'first_last_pose'};texts=conditioning(corpus);bound=identity(model,corpus,texts,plan)
    with unfused_transformer(),feedforward_adapters(model,2,2) as adapters:
        with pytest.raises(ValueError,match='interior'):train(corpus,model,adapters,texts,schedule(),plan,bound,f.root/'bad')


def test_source_changed_during_update_prevents_checkpoint_publication(prepared):
    f=prepared;model=TinyModel()
    def changed(module,args,result):
        if module.training:f.evidence.write_text('Changed numerical fixture')
    model.register_forward_hook(changed)
    with pytest.raises(ValueError,match='changed'):execution(f,f.root/'failed',model=model)
    result=read(f.root/'failed/result.json')
    assert result['status']=='failed' and result['completed_steps']==1 and not (f.root/'failed/checkpoint-step-1').exists()


def test_nonfinite_gradients_fail_before_optimizer_update(prepared):
    f=prepared;corpus=verify(f);text=conditioning(corpus);model=TinyModel();bound=identity(model,corpus,text)
    with unfused_transformer(),feedforward_adapters(model,2,2) as adapters:
        adapters[0][1].b.register_hook(lambda value:torch.full_like(value,float('nan')))
        with pytest.raises(ValueError,match='Finite gradients'):train(corpus,model,adapters,text,schedule(),PLAN,bound,f.root/'failed')
    result=read(f.root/'failed/result.json');assert result['attempted_optimizer_updates']==result['completed_steps']==0


def test_resume_requires_pinned_manifest_and_matching_cursor(prepared):
    f=prepared;execution(f,f.root/'prefix',stop=2);path=f.root/'prefix/checkpoint-step-2'
    metadata=read(path/'manifest.json');metadata['cursor']['next_example']=1;save(path/'manifest.json',metadata)
    with pytest.raises(ValueError,match='cursor'):execution(f,f.root/'failed',resume=path)
    assert read(f.root/'failed/result.json')['attempted_optimizer_updates']==0


def fresh_process_fixture(arguments):
    """Use an explicit mock codec and human declarations only for a CPU canary."""
    torch.set_num_threads(2)
    root,output,resume=map(Path,arguments)
    producer.ROOT=root
    def encode(rep,local,roots,*args):
        clean=torch.full((1,len(roots),369),-2/3);clean[0,:,:3]=roots
        return clean,torch.tensor([.25]),{'quality_approved':False,'training_rights_verified':False}
    producer.encode_native_target=encode
    corpus=verify_corpus(root/'corpus',Rep(),expected_manifest_sha256=sha256(root/'corpus/manifest.json'),
                         expected_codec_binding={'inputs_sha256':{str(root/'ownership.txt'):sha256(root/'ownership.txt')}},reservation_path=root/'reserved.json')
    text=conditioning(corpus);torch.manual_seed(100);model=TinyModel();bound=identity(model,corpus,text)
    torch.manual_seed(987654)
    with unfused_transformer(),feedforward_adapters(model,2,2) as adapters:
        train(corpus,model,adapters,text,schedule(),PLAN,bound,output,resume=resume,resume_manifest_sha256=sha256(resume/'manifest.json'))


def test_resume_in_new_python_process_matches_uninterrupted_run(prepared):
    f=prepared;execution(f,f.root/'full');execution(f,f.root/'prefix',stop=2)
    code="import sys;sys.path.insert(0,sys.argv[1]);from test_kimodo_corpus_trainer import fresh_process_fixture;fresh_process_fixture(sys.argv[2:])"
    process=subprocess.run([sys.executable,'-c',code,str(Path(__file__).parent),str(f.root),str(f.root/'fresh'),str(f.root/'prefix/checkpoint-step-2')],capture_output=True,text=True,timeout=120)
    assert process.returncode==0,process.stdout+process.stderr
    for name in ('adapter.safetensors','training.safetensors'):
        expected=load_file(f.root/'full/checkpoint-step-4'/name);actual=load_file(f.root/'fresh/checkpoint-step-4'/name)
        assert all(torch.equal(value,actual[key]) for key,value in expected.items())
