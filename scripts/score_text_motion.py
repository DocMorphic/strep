"""Offline pinned TMR evaluation of immutable raw motion and cached text features."""
import argparse
import os
from pathlib import Path
import sys
import time
import shutil
from strep import ROOT, read, save, sha256
from action_worker_lock import worker_lock
from text_motion_retrieval import evaluate


def run(protocol_path, output):
    protocol_path = Path(protocol_path).resolve()
    output = Path(output).resolve()
    if not protocol_path.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        raise ValueError('In-project protocol/output required')
    if output.exists():
        raise FileExistsError(output)
    plan = read(protocol_path)
    if plan['schema'] != 'strep-tmr-development-study-v1':
        raise ValueError('Pinned development study required')
    if (not 2 <= len(plan['texts']) <= 128 or not 1 <= len(plan['motions']) <= 512
            or plan['fps'] != 30 or plan['split'] != 'development'):
        raise ValueError('Bounded 30 Hz development population required')
    bindings = plan['bindings']
    def verify():
        for name, digest in bindings.items():
            path = (ROOT/name).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or sha256(path) != digest:
                raise ValueError('Input/method checksum mismatch: ' + name)
    verify()
    required = [t['feature_path'] for t in plan['texts']] + [m['path'] for m in plan['motions']]
    model_dir = ROOT/plan['model_directory']
    required += [(p.relative_to(ROOT)).as_posix() for p in model_dir.rglob('*') if p.is_file()]
    required += ['scripts/'+name for name in ['score_text_motion.py', 'text_motion_retrieval.py',
                                             'strep.py', 'action_worker_lock.py']]
    if any(p not in bindings for p in required):
        raise ValueError('Every consumed input must be bound')
    if (sha256(model_dir/'config.yaml') != 'e3fb393c1ac2f83f11c86a8dd6dffe2b709756e011ad1709338f07cdca8c03d8'
            or plan['checkpoint_revision'] != 'e427752ae3446dedba49e928c93ddc9f0e413401'
            or read(model_dir/'hub-metadata.json')['sha'] != plan['checkpoint_revision']):
        raise ValueError('Only the verified TMR-SOMA-RP-v1 config/revision is supported')
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', OMP_NUM_THREADS='1',
                      MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    output.mkdir(parents=True)
    # Bind preserved method bytes to the original protocol across later source updates.
    for name in bindings:
        if name.startswith(('scripts/', 'vendor/')) and name.endswith('.py'):
            destination = output/'implementation'/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, destination)
            if sha256(destination) != bindings[name]:
                raise ValueError('Method snapshot mismatch')
    state = dict(status='running', protocol_sha256=sha256(protocol_path),
                 quality_approved=False, release_approved=False, training_admitted=False)
    save(output/'pipeline.json', state)
    started = time.monotonic()
    try:
        with worker_lock():
            import numpy as np
            import torch
            from safetensors.torch import load_file
            sys.path.insert(0, str(ROOT/'vendor/kimodo'))
            from kimodo.model.tmr import TMR, ACTORStyleEncoder
            from kimodo.motion_rep import TMRMotionRep
            from kimodo.skeleton import SOMASkeleton30, build_skeleton
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            # Explicitly reproduce the pinned config; load only tensor checkpoints.
            rep = TMRMotionRep(SOMASkeleton30(), 30, str(model_dir/'stats/motion'))
            common = dict(vae=True, latent_dim=256, ff_size=1024, num_layers=6,
                          num_heads=4, dropout=.1, activation='gelu')
            motion_encoder = ACTORStyleEncoder(motion_rep=rep, llm_shape=None, **common)
            text_encoder = ACTORStyleEncoder(motion_rep=None, llm_shape=(1,4096), **common)
            for encoder, name in [(motion_encoder,'motion_encoder'), (text_encoder,'text_encoder')]:
                weights = torch.load(model_dir/'last_weights'/f'{name}.pt', map_location='cpu', weights_only=True)
                encoder.load_state_dict(weights.get('state_dict', weights), strict=True)
            model = TMR(motion_encoder, text_encoder, vae=True, sample_mean=True,
                        unit_vector=True, compute_grads=False, device='cpu').eval()
            texts = []
            motions = []
            partial = dict(text_ids=[t['id'] for t in plan['texts']], text_vectors=texts,
                           motion_ids=[], motion_vectors=motions, expected_text_ids=[])
            with torch.inference_mode():
                for text in plan['texts']:
                    features = load_file(str(ROOT/text['feature_path']))['features'].float()
                    if features.shape != (1,1,4096) or not torch.isfinite(features).all():
                        raise ValueError('Invalid original text features')
                    latent = model.encode_text(dict(x=features,mask=torch.ones((1,1),dtype=torch.bool)), unit_vector=True)
                    texts.append(latent[0].tolist())
                save(output/'partial-embeddings.json', partial)
                for item in plan['motions']:
                    with np.load(ROOT/item['path'], allow_pickle=False) as data:
                        joints = np.array(data['posed_joints'], copy=True)
                    if (joints.ndim != 3 or not 3 <= len(joints) <= 300 or joints.shape[-1] != 3
                            or not np.isfinite(joints).all() or len(joints) != item['frames']):
                        raise ValueError('Finite complete motion <=10 s required')
                    latent = model.encode_motion(torch.from_numpy(joints).float().unsqueeze(0),
                                                 original_skeleton=build_skeleton(joints.shape[1]), unit_vector=True)
                    if latent.shape != (1,256):
                        raise ValueError('Complete batched motion latent required')
                    motions.append(latent[0].tolist())
                    partial['motion_ids'].append(item['id'])
                    partial['expected_text_ids'].append(item['text_id'])
                    save(output/'partial-embeddings.json', partial)
                    print('Scored ' + item['id'], flush=True)
            vectors = dict(text_ids=[t['id'] for t in plan['texts']], text_vectors=texts,
                           motion_ids=[m['id'] for m in plan['motions']], motion_vectors=motions,
                           expected_text_ids=[m['text_id'] for m in plan['motions']])
            save(output/'embeddings.json', vectors)
            result = evaluate(**vectors)
            verify()
            if sha256(protocol_path) != state['protocol_sha256']:
                raise ValueError('Study protocol changed during evaluation')
            result.update(protocol_sha256=state['protocol_sha256'],
                          embeddings_sha256=sha256(output/'embeddings.json'),
                          checkpoint_revision=plan['checkpoint_revision'],
                          runtime=dict(torch=torch.__version__, device='cpu', sample_mean=True,
                                       dtype='float32', new_text_encoding=False))
            save(output/'result.json', result)
            state.update(status='complete', result_sha256=sha256(output/'result.json'),
                         elapsed_seconds=time.monotonic()-started)
    except Exception as exc:
        state.update(status='failed', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        save(output/'pipeline.json', state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    run(args.protocol, args.output)
