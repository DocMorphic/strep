"""Resumable per-prompt original-precision offload encoding for a frozen study."""
import argparse
import hashlib
import os
from pathlib import Path
import torch
from safetensors.torch import load_file,save_file
from strep import ROOT,LOCK,read,save,sha256,now,source_check,offline_environment
from strep import model_directory
from profile_inputs import DEFAULT_STUDY,texts_for


def text_hash(text):return hashlib.sha256(text.encode()).hexdigest()


def revisions():return {m['repo_id']:m['revision'] for m in read(LOCK)['models'] if not m['repo_id'].startswith('nvidia/')}


class ProfileEncoder(torch.nn.Module):
    def __init__(self,manifest,study_path=DEFAULT_STUDY):
        super().__init__()
        path=Path(manifest);meta=read(path)
        if meta['status']!='complete' or meta['study_sha256']!=sha256(study_path) or meta['kimodo_commit']!=source_check() or meta['encoder_revisions']!=revisions():
            raise ValueError('Profile cache provenance mismatch or incomplete cache')
        self.texts=texts_for(read(study_path));self.metadata=meta
        if sorted(meta['entries'])!=self.texts:raise ValueError('Prompt coverage mismatch')
        features=[]
        for text in self.texts:
            entry=meta['entries'][text];file=path.parent/entry['file']
            if entry['text_sha256']!=text_hash(text) or sha256(file)!=entry['sha256']:raise ValueError('Cache checksum mismatch')
            value=load_file(str(file))['features']
            if value.shape!=(1,1,4096) or not torch.isfinite(value).all():raise ValueError('Invalid conditioning')
            features.append(value)
        self.features=torch.cat(features)
    def forward(self,texts):
        single=isinstance(texts,str);texts=[texts] if single else texts
        if any(t not in self.texts for t in texts):raise ValueError('New prompt requires real encoding')
        value=self.features[[self.texts.index(t) for t in texts]].clone()
        return (value[0],1) if single else (value,[1]*len(texts))


def encode(study_path,destination):
    os.environ.update(offline_environment())
    path=Path(destination);path.mkdir(parents=True,exist_ok=True)
    manifest=path/'manifest.json'
    metadata={'started_at':now(),'status':'running','study_sha256':sha256(study_path),'kimodo_commit':source_check(),
        'encoder_revisions':revisions(),'entries':{},'execution':'Original BF16 base with FP32 adapters; experimental disk-offload loader; full 8B resident equivalence untested.',
        'loader_hashes':{name:sha256(ROOT/'scripts'/name) for name in ('profile_encoder.py','offload_encoder.py','streamed_encoder.py')},
        'offline_environment':True}
    if manifest.exists():
        old=read(manifest)
        for key in ('study_sha256','kimodo_commit','encoder_revisions','loader_hashes'):
            if old[key]!=metadata[key]:raise ValueError('Cannot resume a different encoding configuration')
        metadata=old
        for text,entry in old['entries'].items():
            if entry['text_sha256']!=text_hash(text) or sha256(path/entry['file'])!=entry['sha256']:raise ValueError('Existing cache corrupted')
        if old['status']=='complete':
            ProfileEncoder(manifest,study_path);print('Complete cache verified');return
    # Verify pinned encoder files before using the offline loader.
    for repo,entry in read(ROOT/'models/manifest.json')['models'].items():
        if repo.startswith('nvidia/'):continue
        if entry['revision']!=revisions()[repo]:raise ValueError('Encoder revision mismatch')
        for name,digest in entry['files_sha256'].items():
            if sha256(model_directory(entry)/name)!=digest:raise ValueError('Encoder file checksum mismatch')
    save(manifest,metadata)
    from offload_encoder import OffloadedEncoder
    encoder=OffloadedEncoder(ROOT/'.cache/encoder-offload')
    for text in texts_for(read(study_path)):
        if text in metadata['entries']:continue
        print('Encoding new profile: '+text,flush=True)
        with torch.inference_mode():features,lengths=encoder([text])
        features=features.detach().cpu().contiguous()
        if lengths!=[1] or features.shape!=(1,1,4096) or not torch.isfinite(features).all():raise RuntimeError('Invalid encoder output')
        name=text_hash(text)+'.safetensors'
        save_file({'features':features},str(path/name))
        if not torch.equal(load_file(str(path/name))['features'],features):raise RuntimeError('Embedding round trip failed')
        metadata['entries'][text]={'file':name,'text_sha256':text_hash(text),'sha256':sha256(path/name)}
        save(manifest,metadata)
    metadata.update(status='complete',finished_at=now(),prompt_count=len(metadata['entries']))
    save(manifest,metadata);ProfileEncoder(manifest,study_path)
    print('All new profile prompts encoded and verified offline.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,default=DEFAULT_STUDY);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();encode(a.study,a.output)
