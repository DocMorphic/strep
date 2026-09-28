"""Encode all requested text offline; no action whitelist or substituted prompts."""
import argparse
import os
from pathlib import Path
import torch
from safetensors.torch import load_file,save_file
from strep import ROOT,read,save,sha256,now,source_check,offline_environment
from strep import model_directory
from profile_encoder import revisions,text_hash
from action_requests import conditioning_texts,request_digest


class ActionEncoder(torch.nn.Module):
    def __init__(self,folder,batch):
        super().__init__();folder=Path(folder);meta=read(folder/'manifest.json')
        if meta['status']!='complete' or meta['request_sha256']!=request_digest(batch) or meta['kimodo_commit']!=source_check() or meta['encoder_revisions']!=revisions():
            raise ValueError('Action cache provenance mismatch')
        self.texts=conditioning_texts(batch);self.metadata=meta
        if sorted(meta['entries'])!=self.texts:raise ValueError('Missing requested conditioning')
        features=[]
        for text in self.texts:
            entry=meta['entries'][text];path=folder/entry['file']
            if sha256(path)!=entry['sha256']:raise ValueError('Conditioning checksum mismatch')
            tensor=load_file(str(path))['features']
            if tensor.shape!=(1,1,4096) or not torch.isfinite(tensor).all():raise ValueError('Invalid conditioning')
            features.append(tensor)
        self.features=torch.cat(features)

    def forward(self,texts):
        single=isinstance(texts,str);texts=[texts] if single else texts
        if any(t not in self.texts for t in texts):raise ValueError('Prompt was not encoded')
        result=self.features[[self.texts.index(t) for t in texts]].clone()
        return (result[0],1) if single else (result,[1]*len(texts))


def encode(request_path,folder):
    os.environ.update(offline_environment());batch=read(request_path);folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    expected={'request_sha256':request_digest(batch),'kimodo_commit':source_check(),'encoder_revisions':revisions(),
              'loader_hashes':{name:sha256(ROOT/'scripts'/name) for name in ['action_encoder.py','offload_encoder.py','streamed_encoder.py']}}
    path=folder/'manifest.json'
    meta=read(path) if path.exists() else {**expected,'status':'encoding','started_at':now(),'entries':{},
        'qualification':'Original BF16 base/FP32 adapters with experimental disk offloading; full 8B resident equivalence untested.'}
    if any(meta[k]!=v for k,v in expected.items()):raise ValueError('Cannot reuse different cache configuration')
    for entry in meta['entries'].values():
        if sha256(folder/entry['file'])!=entry['sha256']:raise ValueError('Cached embedding corrupted')
    if meta['status']=='complete':ActionEncoder(folder,batch);return
    for repo,entry in read(ROOT/'models/manifest.json')['models'].items():
        if repo.startswith('nvidia/'):continue
        if entry['revision']!=revisions()[repo]:raise ValueError('Encoder revision mismatch')
        for name,digest in entry['files_sha256'].items():
            if sha256(model_directory(entry)/name)!=digest:raise ValueError('Encoder checksum mismatch')
    save(path,meta)
    from offload_encoder import OffloadedEncoder
    encoder=OffloadedEncoder(ROOT/'.cache/encoder-offload')
    for text in conditioning_texts(batch):
        if text in meta['entries']:continue
        print('Encoding: '+text,flush=True)
        with torch.inference_mode():features,lengths=encoder([text])
        features=features.detach().cpu().contiguous()
        if features.shape!=(1,1,4096) or lengths!=[1] or not torch.isfinite(features).all():raise ValueError('Bad encoder output')
        name=text_hash(text)+'.safetensors';save_file({'features':features},str(folder/name))
        assert torch.equal(load_file(str(folder/name))['features'],features)
        meta['entries'][text]={'file':name,'sha256':sha256(folder/name)};save(path,meta)
    meta.update(status='complete',finished_at=now());save(path,meta);ActionEncoder(folder,batch)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('request',type=Path);p.add_argument('output',type=Path);a=p.parse_args();encode(a.request,a.output)
