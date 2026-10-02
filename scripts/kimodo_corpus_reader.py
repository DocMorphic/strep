"""Verify reviewed-corpus provenance and exact target derivation before training."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re

import torch
from safetensors.torch import load_file

from strep import ROOT, read, sha256
from kimodo_training_corpus import validate, encode_correction, _bound


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('A pinned lowercase manifest SHA-256 is required')


def _inside(folder, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('Corpus artifact must be a relative local path')
    path = (folder/relative).resolve()
    if not path.is_relative_to(folder) or not path.is_file():
        raise ValueError('Corpus artifact is missing or escapes its directory')
    return path


def _tensors(path, expected_hash, frames):
    if sha256(path) != expected_hash:
        raise ValueError('Prepared target checksum mismatch')
    values = load_file(str(path), device='cpu')
    if sha256(path) != expected_hash:
        raise ValueError('Prepared target changed during read')
    if set(values) != {'clean_features', 'first_heading', 'reviewed_foot_contacts'}:
        raise ValueError('Prepared target requires clean features, heading and reviewed contacts')
    for name, shape in (('clean_features', (1,frames,369)), ('first_heading', (1,))):
        value = values[name]
        if value.dtype != torch.float32 or tuple(value.shape) != shape or not torch.isfinite(value).all():
            raise ValueError('Prepared target must have finite FP32 native features/heading')
    contacts = values['reviewed_foot_contacts']
    if contacts.dtype != torch.bool or tuple(contacts.shape) != (frames,4):
        raise ValueError('Prepared target requires a complete Boolean contact clock')
    return values


@dataclass(frozen=True)
class Example:
    id: str
    prompt: str
    split: str
    frames: int
    target_path: Path
    target_sha256: str


class VerifiedCorpus:
    """Immutable example table; rehash target files per read and sources on demand."""
    def __init__(self, folder, manifest_hash, examples, bindings):
        self.folder = folder
        self.manifest_sha256 = manifest_hash
        self.examples = tuple(examples)
        self._bindings = dict(bindings)

    def read(self, example_id):
        selected = [item for item in self.examples if item.id == example_id]
        if len(selected) != 1:
            raise ValueError('One verified example ID required')
        if sha256(self.folder/'manifest.json') != self.manifest_sha256:
            raise ValueError('Corpus manifest changed after verification')
        item = selected[0]
        return {key: value.clone() for key,value in _tensors(item.target_path,item.target_sha256,item.frames).items()}

    def assert_unchanged(self):
        """Recheck the full snapshot before checkpointing or resuming a trainer."""
        for path, expected in self._bindings.items():
            if sha256(path) != expected:
                raise ValueError('Verified corpus source, evidence or target changed')


def verify_corpus(folder, motion_rep, *, expected_manifest_sha256, expected_codec_binding,
                  reservation_path=ROOT/'benchmarks/release-prompt-reservations-v1.json'):
    """Revalidate reviews and independently derive each saved target on CPU.

    The caller pins the manifest and expected codec; computing a hash from an
    untrusted manifest is not authentication. This cannot prove human identities
    or legal rights, and never changes release or quality approvals.
    """
    folder = Path(folder).resolve()
    manifest_path = folder/'manifest.json'
    _digest(expected_manifest_sha256)
    if sha256(manifest_path) != expected_manifest_sha256:
        raise ValueError('Corpus manifest differs from the pinned training snapshot')
    manifest = read(manifest_path)
    fields = {'schema','created_at','reviewer','submission','release_reservations','purpose','rights_status',
              'quality_approved','release_approved','codec_binding','inputs_sha256','archived_evidence','items'}
    if not isinstance(manifest, dict) or set(manifest) != fields or manifest['schema'] != 'strep-native-correction-corpus-v2':
        raise ValueError('Explicit v2 corpus submission/reservation references required')
    if manifest['quality_approved'] is not False or manifest['release_approved'] is not False:
        raise ValueError('A development corpus cannot assert quality or release approval')
    if manifest['purpose'] != 'reviewed development supervision; not formal release evidence' or manifest['rights_status'] != 'human attestation with bound evidence; no automatic legal determination':
        raise ValueError('Development scope and attested rights provenance required')
    if not isinstance(expected_codec_binding, dict) or not expected_codec_binding or manifest['codec_binding'] != expected_codec_binding:
        raise ValueError('Prepared corpus differs from the expected codec binding')
    if hasattr(motion_rep, 'buffers') and any(value.device.type != 'cpu' for value in motion_rep.buffers()):
        raise ValueError('Use a separate CPU representation for corpus verification')
    reservations = Path(reservation_path).resolve()
    inputs = {}
    supplied = _bound(manifest['release_reservations'], folder, inputs)
    if supplied != reservations:
        raise ValueError('Corpus used a different release reservation catalog')
    submission = _bound(manifest['submission'], folder, inputs)
    data, accepted, original_inputs = validate(submission, reservations, motion_rep.skeleton.somaskel77.bone_order_names)
    if data['reviewer'] != manifest['reviewer']:
        raise ValueError('Corpus reviewer differs from the bound submission')
    inputs.update(original_inputs)
    codec_inputs = expected_codec_binding.get('inputs_sha256')
    if not isinstance(codec_inputs, dict) or not codec_inputs:
        raise ValueError('Explicit representation/codec file bindings required')
    for path, expected in codec_inputs.items():
        _bound({'path':path,'sha256':expected}, submission.parent, inputs)
    if manifest['inputs_sha256'] != inputs:
        raise ValueError('Corpus input inventory differs from the verified submission/codec')
    if not isinstance(manifest['archived_evidence'], dict):
        raise ValueError('Archived review/correction evidence required')
    required = {str(submission),str(reservations),str((submission.parent/data['draft']['path']).resolve())}
    for item in accepted:
        required.update((str(item['correction_path']),str(item['rights_path'])))
        required.update(str((item['rights_path'].parent/ref['path']).resolve()) for ref in item['rights']['evidence_files'])
    if set(manifest['archived_evidence']) != required:
        raise ValueError('Corpus must retain every submitted review and accepted correction/right evidence')
    bindings = {str(manifest_path):expected_manifest_sha256,**inputs}
    for original, relative in manifest['archived_evidence'].items():
        path = _inside(folder, relative)
        if sha256(path) != inputs[original]:
            raise ValueError('Archived corpus evidence checksum mismatch')
        bindings[str(path)] = inputs[original]
    if not isinstance(manifest['items'], list) or len(manifest['items']) != len(accepted):
        raise ValueError('Prepared targets must cover every accepted correction exactly once')
    by_id = {item['row']['id']:item for item in accepted}
    seen, paths, examples = set(), set(), []
    for row in manifest['items']:
        row_fields = {'id','split','prompt','source_motion_sha256','source_start_frame','source_end_frame_exclusive',
                      'correction_sha256','cleanup_seconds','notes','target_file','target_sha256','geometry_report',
                      'heuristic_vs_reviewed_contact_difference_count','contact_provenance'}
        if not isinstance(row, dict) or set(row) != row_fields or row['id'] not in by_id or row['id'] in seen:
            raise ValueError('Unknown, duplicate or incomplete prepared example')
        seen.add(row['id']);item = by_id[row['id']]
        for name in ('split','cleanup_seconds','notes'):
            if row[name] != item['row'][name]:raise ValueError('Prepared example differs from its reviewed decision')
        for name in ('prompt','source_motion_sha256','source_start_frame','source_end_frame_exclusive'):
            if row[name] != item['original'][name]:raise ValueError('Prepared example differs from the audited original segment')
        if row['correction_sha256'] != item['row']['correction']['sha256'] or row['contact_provenance'] != 'full human-reviewed labels from the bound correction':
            raise ValueError('Prepared correction/contact provenance mismatch')
        path = _inside(folder, row['target_file'])
        if path in paths:raise ValueError('Different examples cannot share one target file')
        paths.add(path);_digest(row['target_sha256'])
        count = row['source_end_frame_exclusive']-row['source_start_frame']
        values = _tensors(path,row['target_sha256'],count)
        clean, heading, report, differences = encode_correction(motion_rep,item['values'])
        if not torch.equal(values['clean_features'],clean) or not torch.equal(values['first_heading'],heading) or not torch.equal(values['reviewed_foot_contacts'],item['values']['foot_contacts']):
            raise ValueError('Prepared target differs from its independently re-encoded correction/labels')
        if row['geometry_report'] != report or row['heuristic_vs_reviewed_contact_difference_count'] != differences:
            raise ValueError('Prepared geometry/contact report differs from its correction')
        examples.append(Example(row['id'],row['prompt'],row['split'],count,path,row['target_sha256']))
        bindings[str(path)] = row['target_sha256']
    verified = VerifiedCorpus(folder,expected_manifest_sha256,examples,bindings)
    verified.assert_unchanged()
    return verified


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus',type=Path);parser.add_argument('--manifest-sha256',required=True)
    args=parser.parse_args()
    import sys,os
    from strep import source_check,model_directory,offline_environment
    from action_worker_lock import worker_lock
    os.environ.update(offline_environment());sys.path.insert(0,str(ROOT/'vendor/kimodo'))
    from omegaconf import OmegaConf
    from kimodo.model.loading import instantiate_from_dict
    with worker_lock():
        revision=source_check()
        entry=read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1'];checkpoint=model_directory(entry)
        pinned={name:value for name,value in entry['files_sha256'].items() if name=='config.yaml' or name.startswith('stats/')}
        for name,expected in pinned.items():
            if sha256(checkpoint/name)!=expected:raise ValueError('Pinned representation file changed')
        config=OmegaConf.merge(OmegaConf.load(checkpoint/'config.yaml'),OmegaConf.create({'checkpoint_dir':str(checkpoint)}))
        rep=instantiate_from_dict(OmegaConf.to_container(config,resolve=True)['denoiser']['motion_rep'])
        binding={'vendor_revision':revision,'model_revision':entry['revision'],'representation_files_sha256':pinned,
                 'inputs_sha256':{**{str(checkpoint/name):value for name,value in pinned.items()},
                                 str(ROOT/'scripts/kimodo_denoising_target.py'):sha256(ROOT/'scripts/kimodo_denoising_target.py'),
                                 str(ROOT/'scripts/kimodo_training_corpus.py'):sha256(ROOT/'scripts/kimodo_training_corpus.py')}}
        corpus=verify_corpus(args.corpus,rep,expected_manifest_sha256=args.manifest_sha256,expected_codec_binding=binding)
        print({'verified_examples':len(corpus.examples),'train_examples':sum(row.split=='train' for row in corpus.examples),
               'development_validation_examples':sum(row.split=='development_validation' for row in corpus.examples),
               'data_manifest_sha256':corpus.manifest_sha256,'release_approved':False})


if __name__=='__main__':main()
