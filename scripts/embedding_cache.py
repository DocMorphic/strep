"""Export/replay unchanged encoder outputs for the fixed v0 study, not arbitrary prompts."""
import argparse
import os
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

from strep import ROOT, LOCK, read, save, sha256, now, source_check, offline_environment
from strep import model_directory


def required_texts():
    from kimodo.sanitize import sanitize_texts
    benchmark = read(ROOT / 'benchmarks/v0.json')
    texts = [sentence.strip() + '.' for case in benchmark['cases'] for track in case['tracks']
             for sentence in track['prompt'].split('.') if sentence.strip()]
    return sorted(set(sanitize_texts(texts)))


class CachedEncoder(torch.nn.Module):
    def __init__(self, manifest_path):
        super().__init__()
        path = Path(manifest_path).resolve()
        meta = read(path)
        if meta['kimodo_git_commit'] != source_check():
            raise ValueError('Embedding source revision mismatch')
        if meta['benchmark_sha256'] != sha256(ROOT / 'benchmarks/v0.json'):
            raise ValueError('Embedding benchmark hash mismatch')
        expected = {m['repo_id']: m['revision'] for m in read(LOCK)['models'] if not m['repo_id'].startswith('nvidia/')}
        if meta['encoder_revisions'] != expected:
            raise ValueError('Embedding encoder revisions mismatch')
        tensor_path = path.parent / 'embeddings.safetensors'
        if sha256(tensor_path) != meta['tensor_sha256']:
            raise ValueError('Embedding tensor checksum mismatch')
        tensors = load_file(str(tensor_path), device='cpu')
        self.texts = meta['texts']
        if set(self.texts) != set(required_texts()) or len(self.texts) != len(set(self.texts)):
            raise ValueError('Embedding prompt coverage mismatch')
        self.features = tensors['features']
        if self.features.shape != (len(self.texts), 1, 4096) or not torch.isfinite(self.features).all():
            raise ValueError('Invalid embedding tensor shape or values')
        self.metadata = meta

    def forward(self, texts):
        single = isinstance(texts, str)
        texts = [texts] if single else texts
        unknown = set(texts) - set(self.texts)
        if unknown:
            raise ValueError('Uncached prompt; this fixed-study cache cannot encode new actions')
        # Clone because the upstream sampler modifies conditioning in place.
        features = self.features[[self.texts.index(t) for t in texts]].clone()
        return (features[0], 1) if single else (features, [1] * len(texts))


def export(destination, device, offload=False):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Use a new cache directory to preserve previous provenance')
    os.environ.update(offline_environment())
    os.environ['TEXT_ENCODER_DEVICE'] = device
    from kimodo.model.llm2vec.llm2vec_wrapper import LLM2VecEncoder
    from kimodo.model.load_model import TEXT_ENCODER_PRESETS
    manifest = read(ROOT / 'models/manifest.json')
    revisions = {}
    for model in read(LOCK)['models']:
        if model['repo_id'].startswith('nvidia/'):
            continue
        entry = manifest['models'][model['repo_id']]
        if entry['revision'] != model['revision']:
            raise ValueError('Encoder model manifest revision mismatch')
        for name, digest in entry['files_sha256'].items():
            if sha256(model_directory(entry) / name) != digest:
                raise ValueError('Encoder file checksum mismatch')
        revisions[model['repo_id']] = model['revision']
    if offload:
        from offload_encoder import OffloadedEncoder
        encoder = OffloadedEncoder(ROOT / '.cache/encoder-offload')
    else:
        encoder = LLM2VecEncoder(**TEXT_ENCODER_PRESETS['llm2vec']['kwargs'])
    texts = required_texts()
    rows = []
    for text in texts:
        print(f'Encoding prompt {len(rows) + 1}/{len(texts)}: {text}', flush=True)
        features, lengths = encoder([text])
        if lengths != [1]:
            raise ValueError('Unexpected text lengths')
        rows.append(features.detach().cpu())
    features = torch.cat(rows).contiguous()
    destination.mkdir(parents=True)
    save_file({'features': features}, str(destination / 'embeddings.safetensors'))
    save(destination / 'manifest.json', {
        'kind': 'offloaded_original_precision_fixed_prompt_cache' if offload else 'unchanged_encoder_fixed_prompt_cache', 'created_at': now(),
        'kimodo_git_commit': source_check(), 'benchmark_sha256': sha256(ROOT / 'benchmarks/v0.json'),
        'encoder_revisions': revisions, 'encoder_model_files': manifest,
        'texts': texts, 'device': device, 'encoder_dtype': 'bfloat16',
        'output_dtype': str(features.dtype), 'batch_size': 1,
        'placement': getattr(encoder, 'placement', device),
        'full_resident_equivalence': 'not_tested' if offload else 'not_applicable',
        'loader_source_sha256': {name: sha256(ROOT / 'scripts' / name) for name in
                                ('embedding_cache.py', 'offload_encoder.py', 'streamed_encoder.py')} if offload else None,
        'small_model_validation': read(ROOT / 'reports/offload-wrapper-probe.json') if offload else None,
        'torch_version': torch.__version__, 'tensor_sha256': sha256(destination / 'embeddings.safetensors'),
        'scope': 'Only these fixed prompts; no new-prompt offline capability demonstrated'
    })
    cached = CachedEncoder(destination / 'manifest.json')
    replay, _ = cached(texts)
    if not torch.equal(replay, features):
        raise RuntimeError('Embedding serialization round-trip mismatch')
    print(f'Exported {len(texts)} prompts with exact tensor round-trip: {destination}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destination', type=Path)
    p.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    p.add_argument('--offload', action='store_true', help='Experimental original BF16 GPU/CPU/disk dispatch')
    args = p.parse_args()
    if args.offload and args.device != 'cuda':
        p.error('--offload requires --device cuda')
    export(args.destination, args.device, args.offload)
