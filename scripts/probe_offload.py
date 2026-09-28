"""Small synthetic-model equivalence check for the dispatch-only LLM2Vec wrapper."""
import copy
import os
import tempfile
from pathlib import Path

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import torch
from accelerate import dispatch_model, disk_offload, init_empty_weights
from peft import LoraConfig, get_peft_model
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from transformers import LlamaConfig, PreTrainedTokenizerFast

from kimodo.model.llm2vec.llm2vec import LLM2Vec
from kimodo.model.llm2vec.models.bidirectional_llama import LlamaBiModel
from offload_encoder import DispatchedLLM2Vec
from safetensors.torch import save_file
from streamed_encoder import build_index
from strep import ROOT, save, now


def main():
    torch.manual_seed(11)
    tokenizer = Tokenizer(WordLevel({'[UNK]': 0, '[PAD]': 1, 'run': 2, 'forward': 3}, unk_token='[UNK]'))
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer = PreTrainedTokenizerFast(tokenizer_object=tokenizer, unk_token='[UNK]', pad_token='[PAD]')
    tokenizer.padding_side = 'left'
    config = LlamaConfig(vocab_size=4, hidden_size=32, intermediate_size=64,
                         num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
                         pad_token_id=1)
    model = LlamaBiModel(config).to(dtype=torch.bfloat16)
    lora = LoraConfig(r=4, lora_alpha=8, target_modules=['q_proj', 'v_proj'])
    model = get_peft_model(model, lora)
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if 'lora_B' in name:
                parameter.normal_(std=0.01)
    model = model.merge_and_unload()
    model = get_peft_model(model, lora).eval()
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if 'lora_B' in name:
                parameter.normal_(std=0.01)
    resident = LLM2Vec(copy.deepcopy(model).cuda(), tokenizer)
    expected = resident.encode(['run forward'], batch_size=1, device='cuda', show_progress_bar=False)
    del resident
    torch.cuda.empty_cache()
    with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
        model = dispatch_model(model, device_map={
            'base_model.model.embed_tokens': 0, 'base_model.model.layers.0': 0,
            'base_model.model.layers.1': 'disk', 'base_model.model.norm': 0,
            'base_model.model.rotary_emb': 0,
        }, offload_dir=folder)
        encoder = DispatchedLLM2Vec(model, tokenizer)
        actual = encoder.encode(['run forward'], batch_size=1, device='cuda', show_progress_bar=False)
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    report = {'checked_at': now(), 'status': 'passed', 'exact_equality': torch.equal(actual, expected),
              'max_absolute_difference': float((actual - expected).abs().max()),
              'scope': 'Synthetic two-layer BF16 LlamaBi with merged and active LoRA; same GPU, resident vs one disk-offloaded layer. Does not establish full 8B equivalence or factory-load compatibility.'}
    save(ROOT / 'reports/offload-wrapper-probe.json', report)
    print(report)

    # Compare streamed CPU MNTP merge + active supervised adapter against resident PEFT.
    with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
        folder = Path(folder)
        base, mntp, supervised = [folder / part for part in ('base', 'mntp', 'supervised')]
        base.mkdir()
        fresh = LlamaBiModel(config).to(dtype=torch.bfloat16)
        state = {'model.' + name: tensor for name, tensor in fresh.state_dict().items()}
        save_file(state, str(base / 'model.safetensors'))
        save(base / 'model.safetensors.index.json', {'weight_map': {name: 'model.safetensors' for name in state}})
        first = get_peft_model(fresh, lora)
        first.peft_config['default'].base_model_name_or_path = str(base)
        with torch.no_grad():
            for name, parameter in first.named_parameters():
                if 'lora_B' in name:
                    parameter.normal_(std=0.01)
        first.save_pretrained(mntp)
        second = get_peft_model(first.merge_and_unload(), lora)
        with torch.no_grad():
            for name, parameter in second.named_parameters():
                if 'lora_B' in name:
                    parameter.normal_(std=0.01)
        second.save_pretrained(supervised)
        resident = LLM2Vec(second.cuda(), tokenizer)
        expected = resident.encode(['run forward'], batch_size=1, device='cuda', show_progress_bar=False)
        with init_empty_weights():
            streamed = get_peft_model(LlamaBiModel(config).to(dtype=torch.bfloat16), lora)
        offload = folder / 'offload'
        build_index(streamed, base, mntp, supervised, offload)
        disk_offload(streamed, offload, execution_device=torch.device('cuda:0'))
        streamed.hf_device_map = {'': 'disk'}
        loaded = DispatchedLLM2Vec(streamed, tokenizer)
        actual = loaded.encode(['run forward'], batch_size=1, device='cuda', show_progress_bar=False)
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    report['streamed_merge_exact_equality'] = True
    report['streamed_merge_max_difference'] = float((actual - expected).abs().max())
    save(ROOT / 'reports/offload-wrapper-probe.json', report)
    print('Synthetic streamed two-adapter loader vs resident PEFT: exact match')


if __name__ == '__main__':
    main()
