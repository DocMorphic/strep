"""Explicit local smooth-root SOMA checkpoint loading without changing defaults.

Receipts and every file are pinned before construction. Reuses the unchanged
upstream constructor and bounded CUDA transport. Supplies a caller-owned text
encoder; never resolves a registry alias or starts a text/API download.
"""
from pathlib import Path
import re
from strep import ROOT,read,sha256,source_check

FILES={'LICENSE','README.md','config.yaml','model.safetensors',*
    ('stats/motion/'+part+'/'+name+'.npy' for part in ('body','global_root','local_root') for name in ('mean','std'))}


def binding(receipt_path,receipt_sha256):
    path=Path(receipt_path).resolve()
    if sha256(path)!=receipt_sha256:raise ValueError('Pinned checkpoint acquisition receipt changed')
    value=read(path)
    if (value['status']!='complete' or value['weights_acquired'] is not True
            or value['inference_executed'] is not False or value['default_changed'] is not False
            or value['quality_approved'] is not False or value['release_approved'] is not False
            or not re.fullmatch(r'nvidia/Kimodo-SOMA-RP-v\d+(?:\.\d+)*',value['repo'])
            or not re.fullmatch('[0-9a-f]{40}',value['revision']) or set(value['files'])!=FILES):
        raise ValueError('Complete explicit smooth-root SOMA checkpoint acquisition required')
    folder=Path(value['target']).resolve()
    if folder.parent!=(ROOT/'models/checkpoints').resolve():raise ValueError('Explicit local checkpoint folder required')
    pins={str(path):receipt_sha256}
    for name,entry in value['files'].items():
        file=folder/name
        if (not re.fullmatch('[0-9a-f]{64}',entry['sha256']) or type(entry['bytes']) is not int
                or entry['bytes']<=0 or file.stat().st_size!=entry['bytes'] or sha256(file)!=entry['sha256']):
            raise ValueError('Pinned complete checkpoint file changed')
        pins[str(file)]=entry['sha256']
    if (folder/'model.safetensors').stat().st_size>1200*1024**2:raise ValueError('Complete checkpoint exceeds qualified file budget')
    return value,folder,pins


def check_configuration(plain,baseline):
    """Check unresolved data before any interpolation or Hydra construction."""
    if plain!=baseline:raise ValueError('New architecture requires separate qualification')
    if (plain['_target_']!='kimodo.model.Kimodo' or plain['denoiser']['_target_']!='kimodo.model.twostage_denoiser.TwostageDenoiser'
            or plain['denoiser']['motion_rep']['_target_']!='kimodo.motion_rep.KimodoMotionRep'
            or plain['denoiser']['motion_rep']['skeleton']['_target_']!='kimodo.skeleton.SOMASkeleton30'
            or plain['denoiser']['ckpt_path']!='${oc.select:checkpoint_dir}/model.safetensors'
            or plain['denoiser']['motion_rep']['stats_path']!='${oc.select:checkpoint_dir}/stats/motion/'):
        raise ValueError('Qualified local SOMA constructor configuration required')
    targets={};interpolations={}
    def visit(value,path=()):
        if isinstance(value,dict):
            for k,v in value.items():
                if k.startswith('_'):
                    if k!='_target_':raise ValueError('Unexpected constructor directive')
                    targets[path]=v
                visit(v,path+(k,))
        elif isinstance(value,list):
            for i,v in enumerate(value):visit(v,path+(i,))
        elif isinstance(value,str) and '${' in value:interpolations[path]=value
    visit(plain)
    if set(targets)!={() ,('denoiser',),('denoiser','motion_rep'),('denoiser','motion_rep','skeleton')}:
        raise ValueError('Unexpected nested constructor')
    if set(interpolations)!={('denoiser','ckpt_path'),('denoiser','motion_rep','stats_path')}:
        raise ValueError('Unexpected checkpoint interpolation')


def model_configuration(folder,baseline):
    """Resolve only the already-qualified architecture; no remote config target."""
    from omegaconf import OmegaConf
    current=OmegaConf.load(folder/'config.yaml');original=OmegaConf.load(baseline/'config.yaml')
    check_configuration(OmegaConf.to_container(current,resolve=False),OmegaConf.to_container(original,resolve=False))
    config=OmegaConf.to_container(OmegaConf.merge(current,OmegaConf.create({'checkpoint_dir':str(folder)})),resolve=True)
    config.pop('checkpoint_dir',None);config['text_encoder']=None
    return config


def load(receipt_path,receipt_sha256,text_encoder,*,device='cuda:0'):
    import os
    if any(os.environ.get(k)!='1' for k in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE')):
        raise ValueError('Isolated offline model worker required')
    source=source_check();entry,folder,pins=binding(receipt_path,receipt_sha256)
    manifest=ROOT/'models/manifest.json';manifest_pin=sha256(manifest)
    old=read(manifest)['models']['nvidia/Kimodo-SOMA-RP-v1.1'];baseline=ROOT/'models/checkpoints/Kimodo-SOMA-RP-v1.1'
    for name in ('config.yaml','LICENSE'):
        if sha256(baseline/name)!=old['files_sha256'][name]:raise ValueError('Qualified baseline configuration changed')
    if (folder/'LICENSE').read_bytes()!=(baseline/'LICENSE').read_bytes():raise ValueError('Different checkpoint license requires review')
    config=model_configuration(folder,baseline)
    import torch
    if (not isinstance(text_encoder,torch.nn.Module) or not torch.cuda.is_available()
            or torch.device(device).type!='cuda' or torch.get_default_dtype()!=torch.float32
            or torch.get_default_device().type!='cpu'):
        raise ValueError('Supplied encoder, CUDA and unchanged float32/CPU defaults required')
    device=torch.device(device)
    if torch.cuda.mem_get_info(device)[0]<3*1024**3:raise ValueError('At least 3 GiB free VRAM required for qualified load')
    from kimodo.model.loading import instantiate_from_dict
    import kimodo.model.twostage_denoiser as upstream
    from motion_checkpoint_transport import parameter_allocations,stream_checkpoint
    checkpoint=folder/'model.safetensors';original=upstream.TwostageDenoiser.load_ckpt;copies=[]
    def transfer(module,path):
        if Path(path).resolve()!=checkpoint:raise ValueError('Constructor requested another checkpoint')
        if any(p.device!=device and p.numel()*p.element_size()>4096 for p in module.parameters()):
            raise ValueError('Large learned layer escaped CUDA allocation')
        copies.append(stream_checkpoint(module,checkpoint,entry['files']['model.safetensors']['sha256'],device=device))
    with parameter_allocations(device) as counts:
        try:
            upstream.TwostageDenoiser.load_ckpt=transfer
            model=instantiate_from_dict(config,overrides={'device':str(device)})
        finally:upstream.TwostageDenoiser.load_ckpt=original
    if len(copies)!=1:raise ValueError('Exactly one complete checkpoint transfer required')
    model.text_encoder=text_encoder;model=model.eval()
    if source_check()!=source or sha256(manifest)!=manifest_pin or any(sha256(p)!=h for p,h in pins.items()):
        raise ValueError('Checkpoint/source/default manifest changed during loading')
    return model,dict(schema='strep-versioned-kimodo-load-v1',repo=entry['repo'],revision=entry['revision'],
        checkpoint_sha256=entry['files']['model.safetensors']['sha256'],acquisition_receipt_sha256=receipt_sha256,
        transport=copies[0],allocation_calls=counts,kimodo_commit=source,default_changed=False,registry_changed=False,
        text_encoder_supplied=True,upstream_constructor=True,quality_approved=False,release_approved=False)
