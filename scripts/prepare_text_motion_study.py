"""Freeze complete existing development batches for optional offline TMR scoring."""
import argparse
import hashlib
import json
from pathlib import Path
from strep import ROOT, read, sha256
from text_motion_checkpoint import verify_checkpoint


def prepare(catalog, batches, output):
    catalog = Path(catalog).resolve(); output = Path(output).resolve()
    batches = [Path(p).resolve() for p in batches]
    if (any(not p.is_relative_to(ROOT) for p in [catalog,output]+batches)
            or output.exists() or not 1 <= len(batches) <= 32 or len(set(batches)) != len(batches)):
        raise ValueError('Distinct bounded in-project development batches and fresh output required')
    ledger_path = ROOT/'benchmarks/text-motion-evaluator-v1.json'
    ledger = verify_checkpoint(ROOT); model = ROOT/ledger['directory']
    bindings = {}
    def bind(path):
        path = path.resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Existing in-project input required')
        name = path.relative_to(ROOT).as_posix(); checksum = sha256(path)
        if name in bindings and bindings[name] != checksum:
            raise ValueError('Input changed during protocol assembly')
        bindings[name] = checksum
        return name
    bind(catalog); bind(ledger_path)
    cases = read(catalog)['cases']
    family = {c['id']:c['family'] for c in cases}
    if len(family) != len(cases):
        raise ValueError('Distinct catalog cases required')
    for path in sorted(model.rglob('*')):
        if path.is_file(): bind(path)
    descriptions = {}; motions = []; original_records = []
    for batch in batches:
        request = read(batch/'request.json'); cache = read(batch/'conditioning/manifest.json')
        if any('motion_profile' in r for r in request['requests']):
            raise ValueError('Resolved style-profile conditioning requires a separate protocol')
        request_digest = hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if cache['status'] != 'complete' or cache['request_sha256'] != request_digest:
            raise ValueError('Original conditioning provenance mismatch')
        bind(batch/'request.json'); bind(batch/'conditioning/manifest.json')
        ids = set()
        for item in request['requests']:
            tid = item['id']; case_id = tid.rsplit('-',1)[0]
            if tid in ids or case_id not in family or len(item['segments']) != 1:
                raise ValueError('Single-description catalog tracks required')
            ids.add(tid); segment = item['segments'][0]; prompt = segment['prompt']
            if not 0 < segment['duration_s'] <= 10 or not item['seeds'] or len(set(item['seeds'])) != len(item['seeds']):
                raise ValueError('Complete distinct seeds and <=10 s clips required')
            entry = cache['entries'][prompt]; feature = batch/'conditioning'/entry['file']
            if sha256(feature) != entry['sha256']:
                raise ValueError('Original conditioning checksum mismatch')
            feature_name = bind(feature)
            if tid in descriptions:
                prior = descriptions[tid]
                if prior['prompt'] != prompt or bindings[prior['feature_path']] != entry['sha256']:
                    raise ValueError('Duplicate description has different text/features')
            else:
                descriptions[tid] = dict(id=tid,prompt=prompt,family=family[case_id],feature_path=feature_name)
            for seed in item['seeds']:
                if type(seed) is not int:
                    raise ValueError('Integer seeds required')
                folder = batch/'raw'/tid/f'seed-{seed}'/'attempt-001'
                record_path = folder/'record.json'; record = read(record_path)
                motion = folder/'motion.npz'
                if (record['status'] != 'generated' or record['seed'] != seed or record['request'] != item
                        or record['request_sha256'] != request_digest
                        or record['checkpoint_revision'] != '6c9233af1180b8151e3c4703477104af5dce9dd5'
                        or record['checkpoint_sha256'] != 'ef0a0ca45a6089ab4532dde609785771ae3f38755b4ae6cf314b0213e07cd4a3'
                        or sha256(motion) != record['npz_sha256']):
                    raise ValueError('Missing/failed/changed original generation; do not silently discard it')
                timeline = record['timeline']
                if (len(timeline) != 1 or timeline[0]['start_frame'] != 0
                        or timeline[0]['end_frame_exclusive'] != round(segment['duration_s']*30)):
                    raise ValueError('Original complete 30 Hz single-segment clock required')
                bind(record_path); original_records.append(record_path)
                motions.append(dict(id=tid+f'-seed-{seed}', text_id=tid, seed=seed,
                                    family=family[case_id], path=bind(motion),
                                    frames=timeline[0]['end_frame_exclusive']))
    if (not 2 <= len(descriptions) <= 128 or not 1 <= len(motions) <= 512
            or len({m['id'] for m in motions}) != len(motions)):
        raise ValueError('Distinct complete bounded population required')
    for path in sorted((ROOT/'vendor/kimodo/kimodo').rglob('*.py')): bind(path)
    for name in ['prepare_text_motion_study.py','score_text_motion.py','text_motion_retrieval.py',
                 'strep.py','action_worker_lock.py','text_motion_checkpoint.py']:
        bind(ROOT/'scripts'/name)
    plan = dict(schema='strep-tmr-development-study-v1', split='development', fps=30,
                checkpoint_revision=ledger['revision'], model_directory=ledger['directory'],
                texts=list(descriptions.values()), motions=motions, bindings=bindings,
                policy=dict(device='cpu',dtype='float32',sample_mean=True,
                            population='Every requested seed in every declared batch; no outcome-based selection',
                            held_out=False,new_generation=False,new_text_encoding=False,
                            scope='Development retrieval diagnostic, not contact, calibrated correctness, human or release approval.'))
    # Revalidate all original bytes before creating the immutable protocol.
    if any(sha256(ROOT/name) != value for name,value in bindings.items()):
        raise ValueError('Input changed during protocol assembly')
    verify_checkpoint(ROOT, bindings=bindings)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:
        json.dump(plan,stream,indent=2,allow_nan=False)
    return dict(candidate_descriptions=len(descriptions),motion_population=len(motions),
                family_count=len({m['family'] for m in motions}),binding_count=len(bindings),
                protocol_sha256=sha256(output),quality_approved=False,release_approved=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development',action='store_true',required=True,
                        help='Explicitly declare already-exposed development inputs; never use release reservations here')
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--batches',nargs='+',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.catalog,args.batches,args.output)))
