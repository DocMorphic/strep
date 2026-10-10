"""Independently replay saved retrieval arithmetic, populations and source hashes.

Does not independently certify TMR feature extraction or the learned encoders.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib,'file_digest') else hashlib.sha256(stream.read()).hexdigest()


def audit(protocol_path, study, output):
    protocol_path, study, output = map(lambda p: Path(p).resolve(), (protocol_path, study, output))
    if any(not p.is_relative_to(ROOT) for p in (protocol_path, study, output)):
        raise ValueError('In-project audit paths required')
    if output.exists():
        raise FileExistsError(output)
    def read(path):
        if path.stat().st_size > 8*1024**2:
            raise ValueError('Bounded complete audit inputs required')
        return json.loads(path.read_text(encoding='utf-8-sig'))
    plan = read(protocol_path)
    vectors = read(study/'embeddings.json')
    result = read(study/'result.json')
    pipeline = read(study/'pipeline.json')
    if (plan['schema'] != 'strep-tmr-development-study-v1' or plan['split'] != 'development'
            or pipeline['status'] != 'complete'
            or pipeline['result_sha256'] != digest(study/'result.json')
            or result['protocol_sha256'] != digest(protocol_path)
            or result['embeddings_sha256'] != digest(study/'embeddings.json')):
        raise ValueError('Complete source-bound study required')
    for name, expected in plan['bindings'].items():
        path = (ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or digest(path) != expected:
            raise ValueError('Study input/method changed: '+name)
    tids = [t['id'] for t in plan['texts']]
    mids = [m['id'] for m in plan['motions']]
    expected_ids = [m['text_id'] for m in plan['motions']]
    if (vectors['text_ids'] != tids or vectors['motion_ids'] != mids
            or vectors['expected_text_ids'] != expected_ids
            or result['text_ids'] != tids or result['motion_ids'] != mids
            or len(set(tids)) != len(tids) or len(set(mids)) != len(mids)):
        raise ValueError('Complete ordered population mismatch')
    tv, mv = vectors['text_vectors'], vectors['motion_vectors']
    if len(tv) != len(tids) or len(mv) != len(mids):
        raise ValueError('Missing embeddings')
    for row in tv+mv:
        if (len(row) != 256 or any(type(v) not in (int,float) or not math.isfinite(v) for v in row)
                or abs(sum(v*v for v in row)-1) > 1e-4):
            raise ValueError('Finite complete unit vectors required')
    if len(result['scores']) != len(mids) or len(result['rows']) != len(mids):
        raise ValueError('Missing result rows')
    max_error = 0.
    top1 = top3 = 0
    by_text = {t:dict(population=0, top1=0, top3=0) for t in tids}
    for i, (mid, target_id) in enumerate(zip(mids, expected_ids)):
        actual = result['scores'][i]
        if len(actual) != len(tids):
            raise ValueError('Incomplete score matrix')
        for j, score in enumerate(actual):
            expected = (.5 + .5*sum(mv[i][k]*tv[j][k] for k in range(256)))
            if type(score) not in (int,float) or not math.isfinite(score):
                raise ValueError('Finite scores required')
            error = abs(score-expected); max_error = max(error,max_error)
            if error > 1e-12:
                raise ValueError('Scalar dot-product replay mismatch')
        target = actual[tids.index(target_id)]
        best = 1+sum(score > target for score in actual)
        worst = sum(score >= target for score in actual)
        maxima = [tids[j] for j in range(len(tids)) if actual[j] == max(actual)]
        row = result['rows'][i]
        margin = target-max(score for t,score in zip(tids,actual) if t != target_id)
        if (row['motion_id'] != mid or row['expected_text_id'] != target_id
                or row['rank_best'] != best or row['rank_worst'] != worst
                or row['top_text_ids'] != maxima or row['expected_score'] != target
                or row['margin_to_best_alternative'] != margin):
            raise ValueError('Rank/tie/margin replay mismatch')
        top1 += worst <= 1; top3 += worst <= 3
        by_text[target_id]['population'] += 1
        by_text[target_id]['top1'] += worst <= 1
        by_text[target_id]['top3'] += worst <= 3
    if (result['population'] != len(mids) or result['candidate_descriptions'] != len(tids)
            or result['conservative_top1_count'] != top1 or result['conservative_top3_count'] != top3
            or any(result[k] is not False for k in ['quality_approved','release_approved','training_admitted'])):
        raise ValueError('Summary or approval mismatch')
    receipt = dict(schema='strep-tmr-score-audit-v1', status='complete',
                   protocol_sha256=digest(protocol_path), result_sha256=digest(study/'result.json'),
                   embeddings_sha256=digest(study/'embeddings.json'),
                   auditor_sha256=digest(Path(__file__).resolve()), binding_count=len(plan['bindings']),
                   score_population=len(mids)*len(tids), max_dot_replay_error=max_error,
                   population=len(mids), candidate_descriptions=len(tids), by_text=by_text,
                   conservative_top1_count=top1, conservative_top3_count=top3,
                   quality_approved=False, release_approved=False, training_admitted=False,
                   scope='Independent scalar dot products and saved rank/tie/margin/count arithmetic, ordered full population and unchanged input/method hashes. TMR representation, learned encoders, original text-encoder fidelity, real action correctness and physical/human quality are not independently certified.')
    with output.open('x',encoding='utf-8') as stream:
        json.dump(receipt,stream,indent=2,allow_nan=False)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol',type=Path)
    parser.add_argument('study',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    print(json.dumps(audit(args.protocol,args.study,args.output)))
