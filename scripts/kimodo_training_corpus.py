"""Prepare source-bound, human-reviewed native correction targets for development.

Admission records human rights attestations; it does not establish legal rights,
approve release quality or train a model. Unreviewed draft packets cannot enter.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
import shutil
import unicodedata

import torch
from safetensors import safe_open
from safetensors.torch import load_file, save_file

from strep import ROOT, now, read, save, sha256
from kimodo_denoising_target import encode_native_target

SUBMISSION = 'strep-native-correction-submission-v1'
RIGHTS = 'strep-native-correction-rights-attestation-v1'
CONTACT_JOINTS = ['LeftFoot', 'LeftToeBase', 'RightFoot', 'RightToeBase']


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} required')
    return value


def _date(value):
    _text(value, 'Dated human attestation')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('ISO-8601 attestation timestamp required') from exc
    if parsed.tzinfo is None:
        raise ValueError('Attestation timestamp must include timezone')


def _prompt(value):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', _text(value, 'Prompt')).casefold()))


def _bound(reference, relative_to, inputs):
    if not isinstance(reference, dict) or set(reference) != {'path', 'sha256'}:
        raise ValueError('File reference requires path and SHA-256')
    raw = _text(reference['path'], 'Local file path')
    if not isinstance(reference['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', reference['sha256']):
        raise ValueError('Exact lowercase SHA-256 required')
    path = (relative_to / raw).resolve()
    if not path.is_file() or sha256(path) != reference['sha256']:
        raise ValueError(f'Bound file missing or changed: {path.name}')
    key = str(path)
    if key in inputs and inputs[key] != reference['sha256']:
        raise ValueError('Conflicting file bindings')
    inputs[key] = reference['sha256']
    return path


def _reviewer(value):
    if not isinstance(value, dict) or set(value) != {'name', 'role', 'reviewed_at'}:
        raise ValueError('Explicit human reviewer identity/role/time required')
    _text(value['name'], 'Human reviewer')
    if value['role'] not in ('developer', 'animator'):
        raise ValueError('Developer or animator review required')
    _date(value['reviewed_at'])


def _correction(path, frames, names):
    with safe_open(str(path), framework='pt', device='cpu') as archive:
        metadata = archive.metadata()
    expected = {'schema': 'strep-native-correction-v1', 'skeleton': 'somaskel77',
                'joint_names': json.dumps(names, separators=(',', ':')), 'fps': '30',
                'units': 'metres', 'coordinates': 'right-handed-Y-up',
                'contact_joints': json.dumps(CONTACT_JOINTS, separators=(',', ':'))}
    if metadata != expected:
        raise ValueError('Correction must declare exact native joint/contact order and clock/units')
    values = load_file(str(path), device='cpu')
    if set(values) != {'local_rotations', 'root_positions', 'foot_contacts'}:
        raise ValueError('Correction requires rotations, roots and full reviewed contact labels')
    for key, shape in (('local_rotations', (frames, 77, 3, 3)), ('root_positions', (frames, 3))):
        value = values[key]
        if value.dtype != torch.float32 or tuple(value.shape) != shape or not torch.isfinite(value).all():
            raise ValueError('Correction geometry must be finite FP32 on the unchanged segment clock')
    contacts = values['foot_contacts']
    if contacts.dtype != torch.bool or tuple(contacts.shape) != (frames, 4):
        raise ValueError('Every frame and all four foot channels require boolean reviewed labels')
    return values


def _rights(path, source_hash, correction_hash, inputs):
    value = read(path)
    fields = {'schema', 'authorized_by', 'attested_at', 'source_motion_sha256', 'correction_sha256',
              'source_kind', 'use', 'permitted', 'evidence_files', 'obligations', 'notes'}
    if not isinstance(value, dict) or set(value) != fields or value['schema'] != RIGHTS:
        raise ValueError('Explicit correction-specific rights attestation required')
    _text(value['authorized_by'], 'Rights attester')
    _date(value['attested_at'])
    if value['source_motion_sha256'] != source_hash or value['correction_sha256'] != correction_hash:
        raise ValueError('Rights attestation belongs to different source/correction')
    if value['source_kind'] != 'model_output_and_authored_correction' or value['use'] != 'commercial_generative_game_motion_training' or value['permitted'] is not True:
        raise ValueError('Explicit permission attestation for this commercial generative training use required')
    if not isinstance(value['evidence_files'], list) or not value['evidence_files']:
        raise ValueError('Rights attestation requires retained evidence files')
    for reference in value['evidence_files']:
        _bound(reference, path.parent, inputs)
    _text(value['obligations'], 'License/attribution obligations, including explicit none')
    _text(value['notes'], 'Rights rationale and correction ownership')
    return value


def template(draft_path, output):
    draft_path, output = Path(draft_path).resolve(), Path(output)
    draft = read(draft_path)
    if draft.get('schema') != 'strep-native-target-review-draft-v1' or not draft.get('items'):
        raise ValueError('Existing native target review draft required')
    if output.exists():
        raise ValueError('Fresh submission template path required')
    result = {'schema': SUBMISSION, 'draft': {'path': str(draft_path), 'sha256': sha256(draft_path)},
              'reviewer': {'name': None, 'role': 'developer', 'reviewed_at': None},
              'items': [{'id': item['id'], 'decision': 'unreviewed', 'split': None,
                         'semantic_pass': None, 'motion_quality_pass': None, 'contact_schedule_pass': None,
                         'cleanup_seconds': None, 'notes': '', 'correction': None,
                         'rights_attestation': None} for item in draft['items']]}
    save(output, result)
    return result


def validate(submission_path, reservation_path, joint_names):
    """Validate a complete submission and return bound corrections without writing."""
    submission_path, reservation_path = Path(submission_path).resolve(), Path(reservation_path).resolve()
    inputs = {}
    _bound({'path': str(submission_path), 'sha256': sha256(submission_path)}, root := submission_path.parent, inputs)
    _bound({'path': str(reservation_path), 'sha256': sha256(reservation_path)}, root, inputs)
    if not isinstance(joint_names, list) or len(joint_names) != 77 or len(set(joint_names)) != 77:
        raise ValueError('Explicit 77 unique native joint names required')
    data, reservations = read(submission_path), read(reservation_path)
    if not isinstance(data, dict) or set(data) != {'schema', 'draft', 'reviewer', 'items'} or data['schema'] != SUBMISSION:
        raise ValueError('Expected a completed correction submission, not an unapproved review draft')
    _reviewer(data['reviewer'])
    draft_path = _bound(data['draft'], root, inputs)
    draft = read(draft_path)
    if draft.get('schema') != 'strep-native-target-review-draft-v1' or draft.get('training_admitted') is not False or draft.get('quality_approved') is not False:
        raise ValueError('Retain the original unapproved review draft')
    audit_path = _bound({'path': draft['audit_result'], 'sha256': draft['audit_result_sha256']}, draft_path.parent, inputs)
    audit = read(audit_path)
    if audit.get('schema') != 'strep-denoising-target-audit-result-v1' or audit.get('status') != 'complete' or any(audit.get(k) is not True for k in ('base_unchanged', 'input_files_unchanged', 'methods_unchanged')):
        raise ValueError('Completed unchanged-source audit required')
    protocol = _bound({'path': str(audit_path.parent/'protocol.json'), 'sha256': audit['protocol_sha256']}, root, inputs)
    for path, expected in audit['inputs_sha256'].items():
        _bound({'path': path, 'sha256': expected}, audit_path.parent, inputs)
    job = _text(read(protocol)['job'], 'Audited development job')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', job):
        raise ValueError('Invalid audited job identifier')
    if reservations.get('schema_version') != 1 or not isinstance(reservations.get('cases'), list) or not reservations['cases']:
        raise ValueError('Nonempty authoritative release reservations required')
    reserved_ids = {row['id'] for row in reservations['cases']}
    reserved_prompts = {_prompt(row['prompt']) for row in reservations['cases']}
    reserved_seeds = {seed for row in reservations['cases'] for seed in row['seeds']}
    originals = {item['id']: item for item in draft['items']}
    targets = {item['id']: item for item in audit['targets']}
    if len(originals) != len(draft['items']) or len(targets) != len(audit['targets']) or set(originals) != set(targets):
        raise ValueError('Draft and audited segment population must match exactly')
    if not isinstance(data['items'], list) or len(data['items']) != len(originals):
        raise ValueError('Every segment needs an explicit accept or exclude decision')
    seen, accepted, source_splits, correction_hashes = set(), [], {}, set()
    for row in data['items']:
        fields = {'id', 'decision', 'split', 'semantic_pass', 'motion_quality_pass', 'contact_schedule_pass',
                  'cleanup_seconds', 'notes', 'correction', 'rights_attestation'}
        if not isinstance(row, dict) or set(row) != fields or row['id'] not in originals or row['id'] in seen:
            raise ValueError('Unknown, duplicate or incomplete review row')
        seen.add(row['id'])
        item, target = originals[row['id']], targets[row['id']]
        for key in ('prompt', 'source_start_frame', 'source_end_frame_exclusive'):
            if item[key] != target[key]:
                raise ValueError('Draft segment differs from its audited source')
        if item['fps'] != 30 or item['encoded_target_sha256'] != target['target_sha256']:
            raise ValueError('Draft target clock/hash differs from audit')
        if not isinstance(target['case'], str) or not re.fullmatch(r'[A-Za-z0-9_-]+', target['case']) or type(target['source_seed']) is not int:
            raise ValueError('Invalid audited case or seed')
        source = (ROOT/'reports/action-jobs'/job/'takes'/f"{target['case']}-seed-{target['source_seed']}").resolve()
        expected_motion, expected_preview = source/'motion.npz', source/'soma.glb'
        draft_motion = (draft_path.parent/item['source_motion']).resolve()
        draft_preview = (draft_path.parent/item['source_preview']).resolve()
        if draft_motion != expected_motion or draft_preview != expected_preview or audit['inputs_sha256'].get(str(expected_motion)) != item['source_motion_sha256']:
            raise ValueError('Draft source is not the original audited take')
        if (draft_path.parent/item['encoded_target']).resolve() != (ROOT/target['target_file']).resolve():
            raise ValueError('Draft encoded target is not the original audited file')
        for path_key, hash_key in (('source_motion', 'source_motion_sha256'), ('source_preview', 'source_preview_sha256'), ('encoded_target', 'encoded_target_sha256')):
            _bound({'path': item[path_key], 'sha256': item[hash_key]}, draft_path.parent, inputs)
        if row['id'] in reserved_ids or target['case'] in reserved_ids or _prompt(item['prompt']) in reserved_prompts or target['source_seed'] in reserved_seeds:
            raise ValueError('Reserved release ID, prompt or seed cannot enter development supervision')
        _text(row['notes'], 'Review/exclusion rationale')
        if row['decision'] == 'exclude':
            if any(row[key] is not None for key in fields - {'id', 'decision', 'notes'}):
                raise ValueError('Excluded rows must not contain training or approval payloads')
            continue
        if row['decision'] != 'accept_corrected':
            raise ValueError('Unreviewed segments cannot enter training; accept corrected or exclude')
        if row['split'] not in ('train', 'development_validation') or any(row[key] is not True for key in ('semantic_pass', 'motion_quality_pass', 'contact_schedule_pass')):
            raise ValueError('Explicit development split and all three completed human reviews required')
        seconds = row['cleanup_seconds']
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Measured finite nonnegative cleanup seconds required')
        start, end = item['source_start_frame'], item['source_end_frame_exclusive']
        if type(start) is not int or type(end) is not int or start < 0 or not 2 <= end-start <= 300:
            raise ValueError('Native correction requires 2-300 unchanged-clock frames')
        correction = _bound(row['correction'], root, inputs)
        values = _correction(correction, end-start, joint_names)
        rights_path = _bound(row['rights_attestation'], root, inputs)
        rights = _rights(rights_path, item['source_motion_sha256'], row['correction']['sha256'], inputs)
        source_hash = item['source_motion_sha256']
        if source_hash in source_splits and source_splits[source_hash] != row['split']:
            raise ValueError('Segments from the same original motion cannot cross development splits')
        source_splits[source_hash] = row['split']
        if row['correction']['sha256'] in correction_hashes:
            raise ValueError('Duplicate correction payload cannot be counted twice')
        correction_hashes.add(row['correction']['sha256'])
        accepted.append({'row': row, 'original': item, 'target': target, 'correction_path': correction,
                         'values': values, 'rights': rights, 'rights_path': rights_path})
    if not accepted or not any(item['row']['split'] == 'train' for item in accepted):
        raise ValueError('At least one reviewed training correction required')
    return data, accepted, inputs


def encode_correction(motion_rep, values):
    """Encode supplied labels, without asserting that they are human-reviewed."""
    names = motion_rep.skeleton.somaskel77.bone_order_names
    clean, heading, report = encode_native_target(motion_rep, values['local_rotations'], values['root_positions'], names, 30)
    contacts = values['foot_contacts']
    if contacts.dtype != torch.bool or contacts.shape != (clean.shape[1], 4):
        raise ValueError('Full boolean foot labels required')
    raw = motion_rep.unnormalize(clean)
    disagreements = int(((raw[0, :, -4:] > .5) != contacts).sum())
    # Normalize only the four labels: unchanged geometry channels stay exact.
    labels = raw.clone()
    labels[0, :, -4:] = contacts.float()
    normalized_labels = motion_rep.normalize(labels)[..., -4:]
    clean = clean.clone()
    clean[..., -4:] = normalized_labels
    if clean.shape != (1, len(values['root_positions']), 369) or heading.shape != (1,) or not torch.isfinite(clean).all():
        raise ValueError('Invalid corrected normalized target')
    return clean, heading, report, disagreements


def prepare(submission_path, reservation_path, output, motion_rep, codec_binding):
    """Encode admitted geometry and overwrite heuristic contacts with human labels."""
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh corpus directory required; preserve all previous attempts')
    names = motion_rep.skeleton.somaskel77.bone_order_names
    data, accepted, inputs = validate(submission_path, reservation_path, names)
    if not isinstance(codec_binding, dict) or not isinstance(codec_binding.get('inputs_sha256'), dict) or not codec_binding['inputs_sha256']:
        raise ValueError('Explicit representation and codec source file bindings required')
    for path, expected in codec_binding['inputs_sha256'].items():
        _bound({'path': path, 'sha256': expected}, Path(submission_path).resolve().parent, inputs)
    encoded = []
    for item in accepted:
        values = item['values']
        clean, heading, report, disagreements = encode_correction(motion_rep, values)
        encoded.append((item, clean, heading, report, disagreements))
    # Recheck all external bindings before publication, including correction data.
    for path, expected in inputs.items():
        if sha256(path) != expected:
            raise ValueError('Corpus input changed during validation/encoding')
    output.mkdir(parents=True)
    evidence = output/'evidence'; evidence.mkdir()
    archived = {}
    # Only JSON and attested evidence/corrections are copied; raw/model files remain bound.
    selected = {str(Path(submission_path).resolve()), str(Path(reservation_path).resolve()),
                str((Path(submission_path).resolve().parent/data['draft']['path']).resolve())}
    for item in accepted:
        selected.update((str(item['correction_path']), str(item['rights_path'])))
        selected.update(str((item['rights_path'].parent/ref['path']).resolve()) for ref in item['rights']['evidence_files'])
    for path in sorted(selected):
        original = Path(path)
        dest = evidence/f'{inputs[path]}{original.suffix}'
        if not dest.exists():shutil.copyfile(original, dest)
        if sha256(dest) != inputs[path]:raise ValueError('Evidence copy differs from bound input')
        archived[path] = dest.relative_to(output).as_posix()
    manifest = {'schema': 'strep-native-correction-corpus-v1', 'created_at': now(), 'reviewer': data['reviewer'],
                'purpose': 'reviewed development supervision; not formal release evidence',
                'rights_status': 'human attestation with bound evidence; no automatic legal determination',
                'quality_approved': False, 'release_approved': False,
                'codec_binding': codec_binding, 'inputs_sha256': inputs, 'archived_evidence': archived, 'items': []}
    for index, (item, clean, heading, report, differences) in enumerate(encoded):
        path = output/f'target-{index:04d}.safetensors'
        save_file({'clean_features': clean.contiguous(), 'first_heading': heading.contiguous(),
                   'reviewed_foot_contacts': item['values']['foot_contacts']}, str(path))
        manifest['items'].append({'id': item['row']['id'], 'split': item['row']['split'],
                                  'prompt': item['original']['prompt'], 'source_motion_sha256': item['original']['source_motion_sha256'],
                                  'source_start_frame': item['original']['source_start_frame'],
                                  'source_end_frame_exclusive': item['original']['source_end_frame_exclusive'],
                                  'correction_sha256': item['row']['correction']['sha256'],
                                  'cleanup_seconds': item['row']['cleanup_seconds'], 'notes': item['row']['notes'],
                                  'target_file': path.name, 'target_sha256': sha256(path), 'geometry_report': report,
                                  'heuristic_vs_reviewed_contact_difference_count': differences,
                                  'contact_provenance': 'full human-reviewed labels from the bound correction'})
    for path, expected in inputs.items():
        if sha256(path) != expected:
            raise ValueError('Corpus input changed during publication')
    save(output/'manifest.json', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('template'); init.add_argument('draft', type=Path); init.add_argument('output', type=Path)
    build = commands.add_parser('prepare'); build.add_argument('submission', type=Path); build.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'template':
        result = template(args.draft, args.output)
        print(f"Prepared {len(result['items'])} unreviewed decisions; nothing admitted")
        return
    # Instantiate only the pinned representation/statistics, not a denoiser or encoder.
    import sys
    from strep import source_check, model_directory, offline_environment
    from action_worker_lock import worker_lock
    import os
    os.environ.update(offline_environment())
    sys.path.insert(0, str(ROOT/'vendor/kimodo'))
    from omegaconf import OmegaConf
    from kimodo.model.loading import instantiate_from_dict
    with worker_lock():
        revision = source_check()
        entry = read(ROOT/'models/manifest.json')['models']['nvidia/Kimodo-SOMA-RP-v1.1']
        checkpoint = model_directory(entry)
        names = ['config.yaml', *(key for key in entry['files_sha256'] if key.startswith('stats/'))]
        pinned = {}
        for name in names:
            if sha256(checkpoint/name) != entry['files_sha256'][name]:raise ValueError('Pinned representation configuration/statistics changed')
            pinned[name] = entry['files_sha256'][name]
        config = OmegaConf.merge(OmegaConf.load(checkpoint/'config.yaml'), OmegaConf.create({'checkpoint_dir': str(checkpoint)}))
        rep = instantiate_from_dict(OmegaConf.to_container(config, resolve=True)['denoiser']['motion_rep'])
        result = prepare(args.submission, ROOT/'benchmarks/release-prompt-reservations-v1.json', args.output, rep,
                         {'vendor_revision': revision, 'model_revision': entry['revision'], 'representation_files_sha256': pinned,
                          'inputs_sha256': {**{str(checkpoint/key): value for key, value in pinned.items()},
                                            str(ROOT/'scripts/kimodo_denoising_target.py'): sha256(ROOT/'scripts/kimodo_denoising_target.py'),
                                            str(Path(__file__).resolve()): sha256(Path(__file__))}})
        print(f"Prepared {len(result['items'])} reviewed development targets; release approval remains false")


if __name__ == '__main__':
    main()
