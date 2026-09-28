"""Bounded-memory loader for the pinned Llama + MNTP + supervised LoRA encoder.

MNTP is merged on CPU with PEFT's own merge operation, one matrix at a time.
Supervised LoRA remains active in FP32, matching PEFT's default adapter upcast.
Original downloaded files are never changed. Derived matrices live in the cache.
"""
import gc
from pathlib import Path

import torch
from accelerate import disk_offload, init_empty_weights
from peft import LoraConfig, get_peft_model
from peft.tuners.lora.layer import Linear as LoraLinear
from safetensors import safe_open
from safetensors.torch import save_file
from transformers import AutoConfig, AutoTokenizer

from kimodo.model.llm2vec.models.bidirectional_llama import LlamaBiModel
from strep import ROOT, read, save, sha256, model_paths


def merge_matrix(weight, a, b, config):
    # PEFT's default loader promotes the adapter to float32 before CPU merge.
    base = torch.nn.Linear(weight.shape[1], weight.shape[0], bias=False, device='meta', dtype=torch.bfloat16)
    base.weight = torch.nn.Parameter(weight.to(torch.bfloat16).clone(), requires_grad=False)
    layer = LoraLinear(base, 'default', config=config, r=config.r, lora_alpha=config.lora_alpha)
    layer.lora_A['default'].weight = torch.nn.Parameter(a.float(), requires_grad=False)
    layer.lora_B['default'].weight = torch.nn.Parameter(b.float(), requires_grad=False)
    with torch.no_grad():
        layer.merge()
    return layer.base_layer.weight.detach().contiguous()


def validate_lora(config):
    for field in ('use_dora', 'use_rslora', 'fan_in_fan_out', 'modules_to_save', 'rank_pattern', 'alpha_pattern', 'lora_bias'):
        if getattr(config, field, False):
            raise ValueError(f'Unsupported adapter option: {field}')
    if config.bias != 'none' or str(config.peft_type) not in ('PeftType.LORA', 'LORA'):
        raise ValueError('Only the pinned vanilla bias-free LoRA adapters are supported')


def build_index(model, base_path, mntp_path, supervised_path, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    config = LoraConfig.from_pretrained(mntp_path)
    validate_lora(config)
    base_map = read(Path(base_path) / 'model.safetensors.index.json')['weight_map']
    index = {}
    derived = {}
    mntp_file = Path(mntp_path) / 'adapter_model.safetensors'
    supervised_file = Path(supervised_path) / 'adapter_model.safetensors'
    with safe_open(str(mntp_file), framework='pt') as mntp, safe_open(str(supervised_file), framework='pt') as supervised:
        for number, (name, parameter) in enumerate(model.named_parameters()):
            if '.lora_' in name:
                source = name.replace('.default.weight', '.weight')
                if source not in supervised.keys():
                    source = source.replace('base_model.model.', 'base_model.model.model.', 1)
                if source not in supervised.keys():
                    raise KeyError(f'Missing supervised adapter tensor: {source}')
                index[name] = {'safetensors_file': str(supervised_file.resolve()),
                               'weight_name': source, 'dtype': 'float32'}
                continue
            plain = name.removeprefix('base_model.model.').replace('.base_layer', '')
            source = 'model.' + plain
            shard = Path(base_path) / base_map[source]
            if '.base_layer.' in name:
                adapter_prefix = 'base_model.model.model.' + plain.removesuffix('.weight')
                a_key, b_key = adapter_prefix + '.lora_A.weight', adapter_prefix + '.lora_B.weight'
                # Some encoder-only adapters omit the causal-LM model prefix.
                if a_key not in mntp.keys():
                    adapter_prefix = 'base_model.model.' + plain.removesuffix('.weight')
                    a_key, b_key = adapter_prefix + '.lora_A.weight', adapter_prefix + '.lora_B.weight'
                with safe_open(str(shard), framework='pt') as weights:
                    merged = merge_matrix(weights.get_tensor(source), mntp.get_tensor(a_key), mntp.get_tensor(b_key), config)
                output = directory / (plain + '.safetensors')
                save_file({'weight': merged}, str(output))
                derived[output.name] = sha256(output)
                del merged
                index[name] = {'safetensors_file': str(output.resolve()), 'weight_name': 'weight', 'dtype': 'bfloat16'}
            else:
                index[name] = {'safetensors_file': str(shard.resolve()), 'weight_name': source, 'dtype': 'bfloat16'}
            if number % 40 == 0:
                print(f'Prepared encoder parameter {number}: {plain}', flush=True)
            gc.collect()
    save(directory / 'derived-manifest.json', {'input_manifest_sha256': sha256(ROOT / 'models/manifest.json'),
                                             'matrices_sha256': derived,
                                             'merge': 'PEFT Linear.merge on CPU; BF16 base + FP32 MNTP adapter'})
    save(directory / 'index.json', index)


def load_streamed(directory, container_class):
    paths = model_paths()
    base = next(path for repo, path in paths.items() if repo.startswith('meta-llama/'))
    mntp = next(path for repo, path in paths.items() if repo.endswith('-mntp'))
    supervised = next(path for repo, path in paths.items() if repo.endswith('-supervised'))
    config = AutoConfig.from_pretrained(base, local_files_only=True)
    config._name_or_path = 'meta-llama/Meta-Llama-3-8B-Instruct'
    adapter = LoraConfig.from_pretrained(supervised)
    validate_lora(adapter)
    previous_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.bfloat16)
        with init_empty_weights():
            model = LlamaBiModel(config)
            model = get_peft_model(model, adapter)
    finally:
        torch.set_default_dtype(previous_dtype)
    model.eval().requires_grad_(False)
    build_index(model, base, mntp, supervised, directory)
    disk_offload(model, directory, execution_device=torch.device('cuda:0'))
    model.hf_device_map = {'': 'disk'}
    tokenizer = AutoTokenizer.from_pretrained(mntp, local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = 'left'
    return container_class(model=model, tokenizer=tokenizer)
