"""Pack an edited native NPZ and explicit contact intervals without approving it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import numpy as np
import torch
from safetensors.torch import save_file

from strep import ROOT, read, save, sha256, now
from kimodo_training_corpus import CONTACT_JOINTS, RIGHTS, _bound, _correction

SCHEMA = 'strep-native-correction-pack-recipe-v1'


def selected(draft_path, item_id, inputs):
    draft_path = Path(draft_path).resolve()
    draft = read(draft_path)
    if draft.get('schema') != 'strep-native-target-review-draft-v1' or draft.get('training_admitted') is not False:
        raise ValueError('Original unapproved native target draft required')
    items = [item for item in draft['items'] if item['id'] == item_id]
    if len(items) != 1:
        raise ValueError('One known segment required')
    item = items[0]
    start, end = item['source_start_frame'], item['source_end_frame_exclusive']
    if item['fps'] != 30 or type(start) is not int or type(end) is not int or start < 0 or not 2 <= end-start <= 300:
        raise ValueError('Original segment must have 2-300 frames at 30 fps')
    _bound({'path': str(draft_path), 'sha256': sha256(draft_path)}, draft_path.parent, inputs)
    for name in ('motion', 'preview'):
        _bound({'path': item['source_'+name], 'sha256': item['source_'+name+'_sha256']}, draft_path.parent, inputs)
    return item


def contacts_from_intervals(contacts, frames):
    """Require gap-free, nonoverlapping explicit on AND off states on every channel."""
    if not isinstance(contacts, list) or len(contacts) != 4:
        raise ValueError('All four contact channels required')
    labels = torch.empty(frames, 4, dtype=torch.bool)
    for channel, (row, joint) in enumerate(zip(contacts, CONTACT_JOINTS)):
        if not isinstance(row, dict) or set(row) != {'joint', 'intervals'} or row['joint'] != joint or not isinstance(row['intervals'], list) or not row['intervals']:
            raise ValueError('Ordered foot channels with explicit intervals required')
        previous = 0
        for interval in row['intervals']:
            if not isinstance(interval, dict) or set(interval) != {'start_frame', 'end_frame_exclusive', 'contact'}:
                raise ValueError('Each interval requires an explicit on/off contact state')
            start, end, value = interval['start_frame'], interval['end_frame_exclusive'], interval['contact']
            if type(start) is not int or type(end) is not int or start != previous or not start < end <= frames:
                raise ValueError('Contact intervals must exactly partition the segment clock')
            if type(value) is not bool:
                raise ValueError('Unreviewed/null or numeric contact labels cannot be packed')
            labels[start:end, channel] = value
            previous = end
        if previous != frames:
            raise ValueError('Every contact channel must cover every segment frame')
    return labels


def _motion(path, start, frames):
    if type(start) is not int or start < 0:
        raise ValueError('Nonnegative candidate start frame required')
    with np.load(path, allow_pickle=False) as archive:
        local, roots = archive['local_rot_mats'], archive['root_positions']
    if local.dtype != np.float32 or roots.dtype != np.float32 or local.ndim != 4 or local.shape[1:] != (77,3,3) or roots.shape != (len(local),3) or start+frames > len(local):
        raise ValueError('Candidate must be native SOMA77 FP32 with a complete selected window')
    local = torch.from_numpy(local[start:start+frames].copy())
    roots = torch.from_numpy(roots[start:start+frames].copy())
    if not torch.isfinite(local).all() or not torch.isfinite(roots).all():
        raise ValueError('Finite candidate geometry required')
    eye = torch.eye(3)
    if (local@local.mT-eye).abs().max() > 1e-4 or (torch.linalg.det(local)-1).abs().max() > 1e-4:
        raise ValueError('Proper orthonormal candidate rotations required')
    return local, roots


def _intervals(values):
    result, start = [], 0
    for end in range(1, len(values)+1):
        if end == len(values) or values[end] != values[start]:
            result.append({'start_frame': start, 'end_frame_exclusive': end, 'contact': bool(values[start])})
            start = end
    return result


def template(draft_path, item_id, output, joint_names, *, candidate=None, candidate_start=None):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh recipe directory required')
    if len(joint_names) != 77 or len(set(joint_names)) != 77:
        raise ValueError('77 unique native joint names required')
    inputs = {}
    item = selected(draft_path, item_id, inputs)
    source = (Path(draft_path).resolve().parent/item['source_motion']).resolve()
    candidate = source if candidate is None else Path(candidate).resolve()
    if candidate_start is None:
        if candidate != source:
            raise ValueError('An edited candidate requires its explicit matching-window start frame')
        candidate_start = item['source_start_frame']
    frames = item['source_end_frame_exclusive']-item['source_start_frame']
    candidate_ref = {'path': str(candidate), 'sha256': sha256(candidate)}
    _bound(candidate_ref, candidate.parent, inputs)
    _motion(candidate, candidate_start, frames)
    # Historical model predictions are suggestions only, never the filled recipe.
    with np.load(source, allow_pickle=False) as archive:
        predicted = archive['foot_contacts'][item['source_start_frame']:item['source_end_frame_exclusive']]
    if predicted.shape != (frames, 6) or not np.isfinite(predicted).all():
        raise ValueError('Original six-channel predicted contacts required for the suggestion sheet')
    recipe = {'schema': SCHEMA, 'draft': {'path': str(Path(draft_path).resolve()), 'sha256': sha256(draft_path)},
              'item_id': item_id, 'candidate_motion': candidate_ref, 'candidate_start_frame': candidate_start,
              'fps': 30, 'joint_names': joint_names, 'units': 'metres', 'coordinates': 'right-handed-Y-up',
              'contacts': [{'joint': joint, 'intervals': [{'start_frame': 0, 'end_frame_exclusive': frames, 'contact': None}]} for joint in CONTACT_JOINTS]}
    suggestions = {'schema': 'strep-unreviewed-contact-suggestions-v1', 'source_motion_sha256': item['source_motion_sha256'],
                   'scope': 'Original model predictions only; not edited candidate labels or contact truth',
                   'source_start_frame': item['source_start_frame'], 'source_end_frame_exclusive': item['source_end_frame_exclusive'],
                   'contacts': [{'joint': joint, 'intervals': _intervals(predicted[:, index] > .5)} for joint,index in zip(CONTACT_JOINTS,[0,1,3,4])]}
    for path, expected in inputs.items():
        if sha256(path) != expected:raise ValueError('Recipe input changed during preparation')
    output.mkdir(parents=True)
    save(output/'recipe.json', recipe);save(output/'model-suggestions.json', suggestions)
    return recipe


def pack(recipe_path, output, joint_names):
    recipe_path, output = Path(recipe_path).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh correction directory required')
    inputs = {}
    _bound({'path': str(recipe_path), 'sha256': sha256(recipe_path)}, recipe_path.parent, inputs)
    recipe = read(recipe_path)
    fields = {'schema', 'draft', 'item_id', 'candidate_motion', 'candidate_start_frame', 'fps', 'joint_names', 'units', 'coordinates', 'contacts'}
    if not isinstance(recipe, dict) or set(recipe) != fields or recipe['schema'] != SCHEMA:
        raise ValueError('Exact native correction pack recipe required')
    if recipe['fps'] != 30 or recipe['joint_names'] != joint_names or recipe['units'] != 'metres' or recipe['coordinates'] != 'right-handed-Y-up':
        raise ValueError('Pinned native joint order, 30 fps, metres and right-handed Y-up required')
    draft_path = _bound(recipe['draft'], recipe_path.parent, inputs)
    item = selected(draft_path, recipe['item_id'], inputs)
    frames = item['source_end_frame_exclusive']-item['source_start_frame']
    candidate_path = _bound(recipe['candidate_motion'], recipe_path.parent, inputs)
    local, roots = _motion(candidate_path, recipe['candidate_start_frame'], frames)
    contacts = contacts_from_intervals(recipe['contacts'], frames)
    metadata = {'schema':'strep-native-correction-v1', 'skeleton':'somaskel77', 'fps':'30', 'units':'metres',
                'coordinates':'right-handed-Y-up', 'joint_names':json.dumps(joint_names,separators=(',',':')),
                'contact_joints':json.dumps(CONTACT_JOINTS,separators=(',',':'))}
    for path, expected in inputs.items():
        if sha256(path) != expected:raise ValueError('Packing input changed')
    output.mkdir(parents=True)
    target = output/'correction.safetensors'
    save_file({'local_rotations':local,'root_positions':roots,'foot_contacts':contacts},str(target),metadata=metadata)
    checked = _correction(target, frames, joint_names)
    if not torch.equal(checked['local_rotations'],local) or not torch.equal(checked['root_positions'],roots) or not torch.equal(checked['foot_contacts'],contacts):
        raise ValueError('Packed correction differs from input tensors')
    evidence = output/'evidence';evidence.mkdir()
    copies = {}
    for path in (recipe_path, draft_path):
        dest=evidence/(sha256(path)+'.json');shutil.copyfile(path,dest)
        if sha256(dest)!=inputs[str(path)]:raise ValueError('Packing evidence changed')
        copies[str(path)]=dest.relative_to(output).as_posix()
    correction_ref = {'path':str(target),'sha256':sha256(target)}
    rights_path = output/'rights-unreviewed.json'
    save(rights_path, {'schema':RIGHTS,'authorized_by':None,'attested_at':None,
                       'source_motion_sha256':item['source_motion_sha256'],'correction_sha256':correction_ref['sha256'],
                       'source_kind':'model_output_and_authored_correction','use':'commercial_generative_game_motion_training',
                       'permitted':None,'evidence_files':[],'obligations':None,'notes':None})
    save(output/'review-row-unreviewed.json', {'id':item['id'],'decision':'unreviewed','split':None,
                                              'semantic_pass':None,'motion_quality_pass':None,'contact_schedule_pass':None,
                                              'cleanup_seconds':None,'notes':'','correction':correction_ref,
                                              'rights_attestation':{'path':str(rights_path),'sha256':sha256(rights_path)}})
    for path, expected in inputs.items():
        if sha256(path)!=expected:raise ValueError('Input changed during correction publication')
    result = {'schema':'strep-native-correction-pack-result-v1','status':'complete','created_at':now(),
              'item_id':item['id'],'original_motion_sha256':item['source_motion_sha256'],
              'original_start_frame':item['source_start_frame'],'original_end_frame_exclusive':item['source_end_frame_exclusive'],
              'candidate_start_frame':recipe['candidate_start_frame'],'frames':frames,'fps':30,
              'correction':correction_ref,'inputs_sha256':inputs,'archived_evidence':copies,
              'training_admitted':False,'quality_approved':False,'release_approved':False,
              'scope':'Packed authored geometry and declared contacts; human review/rights remain pending'}
    save(output/'result.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    init=commands.add_parser('template');init.add_argument('draft',type=Path);init.add_argument('item_id');init.add_argument('output',type=Path)
    init.add_argument('--candidate',type=Path);init.add_argument('--candidate-start',type=int)
    build=commands.add_parser('pack');build.add_argument('recipe',type=Path);build.add_argument('output',type=Path)
    args=parser.parse_args()
    from strep import source_check
    from inspect_motion import skeleton_metadata
    from action_worker_lock import worker_lock
    with worker_lock():
        source_check();names,_,_=skeleton_metadata(77)
        if args.command=='template':
            template(args.draft,args.item_id,args.output,names,candidate=args.candidate,candidate_start=args.candidate_start)
            print('Recipe has unknown contacts; model suggestions are separate. Nothing approved.')
        else:
            result=pack(args.recipe,args.output,names)
            print(f"Packed {result['frames']} native frames; review, rights and training admission remain pending")


if __name__=='__main__':main()
