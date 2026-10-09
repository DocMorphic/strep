"""CPU source fixtures; no Kimodo/vendor/model payload needed."""
import sys
from pathlib import Path
import threading
import numpy as np
import pytest
import torch
from safetensors.torch import save_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from motion_checkpoint_transport import parameter_allocations,stream_checkpoint
from strep import sha256
from motion_checkpoint_transport import load_cuda_motion_model


class Tiny(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear=torch.nn.Linear(4,4)
        self.attention=torch.nn.MultiheadAttention(4,2,batch_first=True)
        self.norm=torch.nn.LayerNorm(4)
        self.register_buffer('position',torch.sin(torch.arange(12,dtype=torch.float32)).reshape(3,4),persistent=False)
        self.register_buffer('count',torch.tensor(2))
    def forward(self,x):
        x=self.linear(x)+self.position
        return self.norm(self.attention(x,x,x,need_weights=False)[0])


def checkpoint(tmp_path,module,changed=None):
    values={'denoiser.backbone.'+k:v.detach().contiguous().clone() for k,v in module.state_dict().items()}
    if changed:changed(values)
    path=tmp_path/'model.safetensors';save_file(values,str(path))
    return path,sha256(path)


def test_selective_allocation_preserves_cpu_buffers_defaults_types_and_restores_constructors():
    previous=(torch.nn.Linear.__init__,torch.nn.MultiheadAttention.__init__)
    dtype,device=torch.get_default_dtype(),torch.get_default_device()
    with parameter_allocations('meta') as counts:
        model=Tiny()
        assert model.linear.weight.is_meta and model.attention.in_proj_weight.is_meta
        assert model.norm.weight.device.type=='cpu' and model.position.device.type=='cpu'
        explicit=torch.nn.Linear(4,4,True,'cpu',torch.float64)
        assert explicit.weight.device.type=='cpu' and explicit.weight.dtype==torch.float64
        assert type(model.linear) is torch.nn.Linear and type(model.attention) is torch.nn.MultiheadAttention
        assert counts['Linear']>=3 and counts['MultiheadAttention']==1
    assert (torch.nn.Linear.__init__,torch.nn.MultiheadAttention.__init__)==previous
    assert torch.get_default_dtype()==dtype and torch.get_default_device()==device


def test_scope_rejects_nested_threads_and_restores_after_constructor_failure():
    previous=(torch.nn.Linear.__init__,torch.nn.MultiheadAttention.__init__)
    with pytest.raises(RuntimeError,match='deliberate'):
        with parameter_allocations('cpu'):
            with pytest.raises(ValueError,match='active'):
                with parameter_allocations('cpu'):pass
            raise RuntimeError('deliberate')
    errors=[]
    def background():
        try:
            with parameter_allocations('cpu'):pass
        except ValueError as exc:errors.append(str(exc))
    worker=threading.Thread(target=background);worker.start();worker.join()
    assert len(errors)==1 and 'main-thread' in errors[0]
    assert (torch.nn.Linear.__init__,torch.nn.MultiheadAttention.__init__)==previous


def test_complete_stream_matches_standard_load_weights_buffers_and_forward_bits(tmp_path):
    torch.manual_seed(7);source=Tiny().eval();path,digest=checkpoint(tmp_path,source)
    torch.manual_seed(99)
    with parameter_allocations('cpu'):target=Tiny().eval()
    position=target.position.clone();report=stream_checkpoint(target,path,digest,device='cpu')
    for name,value in source.state_dict().items():assert torch.equal(value,target.state_dict()[name])
    assert torch.equal(position,target.position) and torch.equal(source.position,target.position)
    x=torch.arange(24,dtype=torch.float32).reshape(2,3,4)/10
    assert torch.equal(source(x),target(x))
    assert report['tensors']==len(source.state_dict()) and report['checkpoint_sha256']==sha256(path)==digest
    assert report['backend']=='pread' and not report['dtype_conversion'] and not report['quality_approved']


@pytest.mark.parametrize('fault',['missing','extra','shape','dtype','collision','budget','digest'])
def test_complete_preflight_rejects_without_partial_copy(tmp_path,fault):
    target=Tiny();before={k:v.clone() for k,v in target.state_dict().items()}
    def change(values):
        name='denoiser.backbone.linear.weight'
        if fault=='missing':del values[name]
        elif fault=='extra':values['unexpected']=torch.zeros(1)
        elif fault=='shape':values[name]=torch.zeros(5,4)
        elif fault=='dtype':values[name]=values[name].double()
        elif fault=='collision':values['linear.weight']=values[name].clone()
    path,digest=checkpoint(tmp_path,target,change)
    with pytest.raises(ValueError):stream_checkpoint(target,path,'0'*64 if fault=='digest' else digest,device='cpu',
        maximum_tensor_bytes=1 if fault=='budget' else 64*1024**2)
    for name,value in before.items():assert torch.equal(value,target.state_dict()[name])


@pytest.mark.parametrize('budget',[True,0,-1,257*1024**2,1.5])
def test_invalid_budget_rejected_before_file_access(tmp_path,budget):
    with pytest.raises(ValueError):stream_checkpoint(Tiny(),tmp_path/'absent.safetensors','a'*64,device='cpu',maximum_tensor_bytes=budget)


def test_signed_zero_and_non_default_exact_dtype_preserved(tmp_path):
    source=torch.nn.Linear(2,2,dtype=torch.float64)
    with torch.no_grad():source.weight.copy_(torch.tensor([[-0.,0.],[np.nextafter(0.,1.),np.nextafter(1.,2.)]],dtype=torch.float64))
    path,digest=checkpoint(tmp_path,source);target=torch.nn.Linear(2,2,dtype=torch.float64)
    stream_checkpoint(target,path,digest,device='cpu')
    assert target.weight.detach().numpy().tobytes()==source.weight.detach().numpy().tobytes()


def test_change_after_preflight_rejected(tmp_path,monkeypatch):
    import motion_checkpoint_transport as module
    target=Tiny();path,digest=checkpoint(tmp_path,target);original=module.sha256;calls=0
    def changing(p):
        nonlocal calls
        calls+=1
        if calls==2:path.write_bytes(path.read_bytes()+b'changed')
        return original(p)
    monkeypatch.setattr(module,'sha256',changing)
    with pytest.raises(ValueError,match='header'):stream_checkpoint(target,path,digest,device='cpu')


def test_aliased_targets_rejected_before_mutation(tmp_path):
    target=torch.nn.Module();target.first=torch.nn.Linear(2,2);target.second=target.first
    before=target.first.weight.detach().clone();path,digest=checkpoint(tmp_path,target)
    with pytest.raises(ValueError,match='Aliased'):stream_checkpoint(target,path,digest,device='cpu')
    assert torch.equal(before,target.first.weight)


@pytest.mark.skipif(not torch.cuda.is_available(),reason='CUDA smoke is optional; CPU source coverage stays complete')
def test_cuda_transport_matches_cpu_loaded_reference_forward_and_nonpersistent_buffers(tmp_path):
    source=Tiny().eval();path,digest=checkpoint(tmp_path,source)
    reference=source.to('cuda:0');reference_position=reference.position.clone()
    with parameter_allocations('cuda:0'):target=Tiny().eval()
    assert target.linear.weight.device.type=='cuda' and target.position.device.type=='cpu'
    stream_checkpoint(target,path,digest,device='cuda:0');target=target.to('cuda:0')
    assert torch.equal(target.position,reference_position)
    x=torch.arange(24,dtype=torch.float32,device='cuda:0').reshape(2,3,4)/10
    assert torch.equal(reference(x),target(x))


def test_upstream_failure_restores_loader_and_allocation_methods(tmp_path,monkeypatch):
    import types
    import strep
    from strep import save
    checkpoint_path=tmp_path/'model.safetensors';checkpoint_path.write_bytes(b'bound fixture')
    save(tmp_path/'models/manifest.json',{'models':{'nvidia/Kimodo-SOMA-RP-v1.1':
        {'files_sha256':{'model.safetensors':sha256(checkpoint_path)}}}})
    monkeypatch.setattr(strep,'ROOT',tmp_path);monkeypatch.setattr(strep,'source_check',lambda:None)
    monkeypatch.setattr(strep,'model_directory',lambda entry:tmp_path)
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    package=types.ModuleType('kimodo');package.__path__=[]
    model_package=types.ModuleType('kimodo.model');model_package.__path__=[];package.model=model_package
    upstream=types.ModuleType('kimodo.model.twostage_denoiser');model_package.twostage_denoiser=upstream
    class Denoiser:
        def load_ckpt(self,path):raise AssertionError('Original loader must not run')
    upstream.TwostageDenoiser=Denoiser
    previous=(torch.nn.Linear.__init__,torch.nn.MultiheadAttention.__init__,Denoiser.load_ckpt)
    def broken(*args,**kwargs):raise RuntimeError('deliberate upstream failure')
    package.load_model=broken
    for name,value in [('kimodo',package),('kimodo.model',model_package),('kimodo.model.twostage_denoiser',upstream)]:
        monkeypatch.setitem(sys.modules,name,value)
    with pytest.raises(RuntimeError,match='deliberate upstream'):load_cuda_motion_model(object())
    assert (torch.nn.Linear.__init__,torch.nn.MultiheadAttention.__init__,Denoiser.load_ckpt)==previous
    with parameter_allocations('cpu'):torch.nn.Linear(2,2)


def test_generation_backend_defaults_and_explicit_transport_forward_exact_encoder(monkeypatch):
    import types
    import generate_actions
    import motion_checkpoint_transport
    encoder=object();model=object();receipt={'bound':'fixture'};calls=[]
    upstream=types.ModuleType('kimodo')
    def original(name,**kwargs):calls.append((name,kwargs));return model
    upstream.load_model=original;monkeypatch.setitem(sys.modules,'kimodo',upstream)
    def streamed(value):
        assert value is encoder
        calls.append('streamed');return model,receipt
    monkeypatch.setattr(motion_checkpoint_transport,'load_cuda_motion_model',streamed)
    assert generate_actions.load_motion_backend(encoder,'upstream')==(model,None)
    assert calls==[('Kimodo-SOMA-RP-v1.1',{'device':'cuda','text_encoder':encoder})]
    assert generate_actions.load_motion_backend(encoder,'cuda-streamed')==(model,receipt)
    assert calls[-1]=='streamed'
    with pytest.raises(ValueError,match='transport'):generate_actions.load_motion_backend(encoder,'unknown')
    assert len(calls)==2


def test_generation_invalid_transport_rejected_before_loading_or_file_access(tmp_path):
    import generate_actions
    with pytest.raises(ValueError,match='transport'):
        generate_actions.main(tmp_path/'absent.json',tmp_path/'output',checkpoint_transport='unknown')
    assert not (tmp_path/'output').exists()
