"""Load only the unchanged motion checkpoint on CUDA; no text or motion generation."""
import json
import os
import time

import psutil
import torch

from strep import ROOT, offline_environment, read, save, sha256, source_check


class UnavailableEncoder(torch.nn.Module):
    def forward(self, *args, **kwargs):
        raise RuntimeError('This diagnostic has no text encoder and cannot generate motion')


def main():
    source_check()
    os.environ.update(offline_environment())
    manifest = read(ROOT / 'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
    for name, digest in manifest['files_sha256'].items():
        if sha256(ROOT / 'models/checkpoints/Kimodo-SOMA-RP-v1.1' / name) != digest:
            raise ValueError(f'Checkpoint hash mismatch: {name}')
    from kimodo import load_model
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    model = load_model('Kimodo-SOMA-RP-v1.1', device='cuda:0', text_encoder=UnavailableEncoder())
    torch.cuda.synchronize()
    report = {'kind': 'checkpoint_load_only_no_inference', 'seconds': time.perf_counter() - start,
              'model': 'Kimodo-SOMA-RP-v1.1', 'checkpoint_revision': manifest['revision'],
              'parameters': sum(p.numel() for p in model.parameters()),
              'internal_joints': model.skeleton.nbjoints, 'output_joints': model.output_skeleton.nbjoints,
              'fps': model.fps, 'cuda_allocated_bytes': torch.cuda.memory_allocated(),
              'cuda_peak_allocated_bytes': torch.cuda.max_memory_allocated(),
              'process_rss_bytes': psutil.Process().memory_info().rss,
              'text_encoder_loaded': False, 'motion_generated': False}
    save(ROOT / 'reports/checkpoint-probe.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
