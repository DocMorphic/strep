"""Opt-in checkpoint transport; preserve upstream architecture and arithmetic.

Use only in an isolated, sequential model worker. Large learned layers may be
allocated on CUDA while deterministic positional/statistics buffers keep their
upstream CPU construction. No default dtype/device, checkpoint or vendor edits.
"""
from contextlib import contextmanager
import functools
import inspect
import math
from pathlib import Path
import threading
import torch
from safetensors import safe_open
from strep import sha256

LOCK=threading.Lock()
DTYPES={'BOOL':torch.bool,'U8':torch.uint8,'I8':torch.int8,'I16':torch.int16,
        'I32':torch.int32,'I64':torch.int64,'F16':torch.float16,'BF16':torch.bfloat16,
        'F32':torch.float32,'F64':torch.float64}


@contextmanager
def parameter_allocations(device):
    """Temporary worker-local placement of large learned layers, not buffers."""
    device=torch.device(device)
    if threading.current_thread() is not threading.main_thread() or threading.active_count()!=1:
        raise ValueError('Isolated sequential main-thread model worker required')
    if not LOCK.acquire(blocking=False):raise ValueError('Model allocation transport is already active')
    previous={cls:cls.__init__ for cls in (torch.nn.Linear,torch.nn.MultiheadAttention)}
    owner=threading.get_ident();counts={cls.__name__:0 for cls in previous}
    try:
        for cls,original in previous.items():
            signature=inspect.signature(original)
            def wrapper(original,signature,name):
                @functools.wraps(original)
                def initialize(*args,**kwargs):
                    if threading.get_ident()!=owner:raise ValueError('Allocation transport crossed worker threads')
                    bound=signature.bind(*args,**kwargs)
                    if bound.arguments.get('device') is None:bound.arguments['device']=device
                    counts[name]+=1
                    return original(*bound.args,**bound.kwargs)
                return initialize
            cls.__init__=wrapper(original,signature,cls.__name__)
        yield counts
    finally:
        for cls,original in previous.items():cls.__init__=original
        LOCK.release()


def stream_checkpoint(module,path,expected_sha256,*,device,prefix='denoiser.backbone.',maximum_tensor_bytes=64*1024**2):
    """Validate the complete population, then copy one exact tensor at a time."""
    path=Path(path).resolve();device=torch.device(device)
    if (path.suffix!='.safetensors' or type(expected_sha256) is not str or len(expected_sha256)!=64
            or any(c not in '0123456789abcdef' for c in expected_sha256)
            or type(maximum_tensor_bytes) is not int or not 1<=maximum_tensor_bytes<=256*1024**2
            or not isinstance(prefix,str) or not prefix):
        raise ValueError('Bound safetensors input and explicit complete tensor budget required')
    if sha256(path)!=expected_sha256:raise ValueError('Checkpoint binding differs')
    target=module.state_dict();logical=0;maximum=0;mapping={};storages=set()
    # pread avoids retaining all read file pages in a mapped checkpoint. The
    # installed transport must support it; never silently fall back to mmap.
    with safe_open(str(path),framework='pt',device='cpu',backend='pread') as saved:
        for key in saved.keys():
            name=key.replace(prefix,'')  # Exactly the pinned upstream key rule.
            if name in mapping or name not in target:raise ValueError('Checkpoint key population differs')
            mapping[name]=key;slice_=saved.get_slice(key);value=target[name]
            if (not isinstance(value,torch.Tensor) or value.is_meta or list(value.shape)!=slice_.get_shape()
                    or DTYPES.get(slice_.get_dtype())!=value.dtype):
                raise ValueError('Exact checkpoint shape/dtype and materialized target required')
            storage=(str(value.device),value.untyped_storage().data_ptr())
            if value.numel() and storage in storages:raise ValueError('Aliased checkpoint targets need a separate explicit policy')
            if value.numel():storages.add(storage)
            size=math.prod(value.shape)*value.element_size()
            if size>maximum_tensor_bytes:raise ValueError('Complete checkpoint tensor exceeds transport budget')
            logical+=size;maximum=max(maximum,size)
        if set(mapping)!=set(target):raise ValueError('Complete checkpoint key population required')
    if sha256(path)!=expected_sha256:raise ValueError('Checkpoint changed during header validation')
    with torch.no_grad(),safe_open(str(path),framework='pt',device=str(device),backend='pread') as saved:
        for name,key in mapping.items():
            value=saved.get_tensor(key);destination=target[name]
            if value.shape!=destination.shape or value.dtype!=destination.dtype:
                raise ValueError('Checkpoint tensor differs from checked header')
            destination.copy_(value)
            # Compare bits, including signed zero; no dtype conversion or NaN
            # equivalence can turn a changed value into an accepted transport.
            observed=destination.to(value.device)
            if not torch.equal(observed.contiguous().reshape(-1).view(torch.uint8),value.contiguous().reshape(-1).view(torch.uint8)):
                raise ValueError('Copied checkpoint bits differ')
            del value,observed
    if sha256(path)!=expected_sha256:raise ValueError('Checkpoint changed during transport')
    return dict(schema='strep-motion-checkpoint-transport-v1',checkpoint_sha256=expected_sha256,
        tensors=len(mapping),logical_bytes=logical,maximum_tensor_bytes=maximum,
        backend='pread',device=str(device),dtype_conversion=False,checkpoint_modified=False,
        quality_approved=False,release_approved=False)


def load_cuda_motion_model(text_encoder,*,device='cuda:0'):
    """Load the pinned SOMA model through upstream code with opt-in transport."""
    from strep import ROOT,read,source_check,model_directory
    device=torch.device(device)
    if (device.type!='cuda' or not torch.cuda.is_available() or text_encoder is None
            or torch.get_default_dtype()!=torch.float32 or torch.get_default_device().type!='cpu'):
        raise ValueError('CUDA, supplied conditioning and unchanged float32/CPU defaults required')
    source_check();entry=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
    folder=model_directory(entry);checkpoint=folder/'model.safetensors'
    if any(sha256(folder/name)!=digest for name,digest in entry['files_sha256'].items()):
        raise ValueError('Pinned model files differ')
    import kimodo.model.twostage_denoiser as upstream
    from kimodo import load_model
    original=upstream.TwostageDenoiser.load_ckpt;receipts=[]
    def streamed(module,path):
        if Path(path).resolve()!=checkpoint.resolve():raise ValueError('Unexpected motion checkpoint path')
        # Large trainable allocations must be on the requested GPU; the small
        # upstream CPU LayerNorm parameters retain their original construction.
        if any(p.device!=device and p.numel()*p.element_size()>4096 for p in module.parameters()):
            raise ValueError('Large learned layer escaped CUDA allocation')
        receipts.append(stream_checkpoint(module,checkpoint,entry['files_sha256']['model.safetensors'],device=device))
    with parameter_allocations(device) as counts:
        try:
            upstream.TwostageDenoiser.load_ckpt=streamed
            model=load_model('Kimodo-SOMA-RP-v1.1',device=str(device),text_encoder=text_encoder)
        finally:upstream.TwostageDenoiser.load_ckpt=original
    if len(receipts)!=1:raise ValueError('Exactly one complete motion checkpoint load required')
    source_check()
    if any(sha256(folder/name)!=digest for name,digest in entry['files_sha256'].items()):
        raise ValueError('Pinned model files changed during loading')
    return model,dict(receipts[0],allocation_calls=counts,upstream_constructor=True,
        positional_buffer_construction='Unchanged upstream CPU operations',default_policy_changed=False)
