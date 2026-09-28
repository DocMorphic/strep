"""Experimental original-precision LLM2Vec placement; upstream computation unchanged.

Accelerate owns weight placement. LLM2Vec's two whole-module .to(device) calls
must be suppressed after dispatch; tokenization, pooling and forward remain upstream.
This is a placement experiment, not a demonstrated full-resident equivalence result.
"""
from pathlib import Path

import torch
from kimodo.model.llm2vec.llm2vec import LLM2Vec


class DispatchedLLM2Vec(LLM2Vec):
    def to(self, device=None, *args, **kwargs):
        if args or kwargs or str(device) not in ('cuda', 'cuda:0'):
            raise ValueError('Dispatched encoder only accepts its fixed CUDA execution device')
        if not getattr(self.model, 'hf_device_map', None):
            raise RuntimeError('No Accelerate device map; refusing to suppress model placement')
        return self


class OffloadedEncoder(torch.nn.Module):
    def __init__(self, directory):
        super().__init__()
        from streamed_encoder import load_streamed
        Path(directory).mkdir(parents=True, exist_ok=True)
        print('Loading original BF16 encoder with GPU/CPU/disk dispatch', flush=True)
        self.encoder = load_streamed(directory, DispatchedLLM2Vec)
        self.encoder.eval().requires_grad_(False)
        self.placement = dict(self.encoder.model.hf_device_map)
        print('Encoder dispatch loaded', flush=True)

    def forward(self, texts):
        single = isinstance(texts, str)
        texts = [texts] if single else texts
        features = self.encoder.encode(texts, batch_size=1, show_progress_bar=False,
                                       device='cuda')[:, None]
        return (features[0], 1) if single else (features, [1] * len(texts))
