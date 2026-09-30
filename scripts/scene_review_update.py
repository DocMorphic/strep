"""Append a bound display correction without rewriting historical scene artifacts."""
import argparse
import copy
from pathlib import Path
import shutil
from strep import read, save, sha256, now


def displayed_manifest(path):
    path = Path(path); manifest = read(path); update_path = path.parent/'review-update.json'
    if not update_path.exists(): return manifest
    update = read(update_path)
    if update['original_manifest_sha256'] != sha256(path): raise ValueError('Review update belongs to another manifest')
    for name,digest in update['evidence'].items():
        evidence = (path.parent/name).resolve()
        if not evidence.is_relative_to(path.parent.resolve()) or sha256(evidence) != digest:
            raise ValueError('Supplemental review evidence changed')
    scenes = {s['id']:s for s in manifest['scenes']}
    if not update['scene_notes'] or not set(update['scene_notes']) <= set(scenes): raise ValueError('Review update scene differs')
    result = copy.deepcopy(manifest)
    for scene in result['scenes']:
        if scene['id'] in update['scene_notes']:
            note = update['scene_notes'][scene['id']]
            if not isinstance(note,str) or not 1 <= len(note) <= 2000: raise ValueError('Bounded review note required')
            scene['review_note'] = note
    return result


def annotate_failed_angular(collection, replay):
    collection, replay = Path(collection).resolve(), Path(replay).resolve()
    if (collection/'review-update.json').exists() or (collection/'angular-review').exists(): raise ValueError('Preserve previous supplemental review')
    provenance = read(collection/'provenance.json'); protocol = read(replay/'request.json'); proof = read(replay/'verification.json')
    if proof['status'] != 'complete' or proof['request_sha256'] != sha256(replay/'request.json') or proof['passed'] is not False:
        raise ValueError('Completed failed angular evidence required')
    if protocol['study_result_sha256'] != provenance['fit_result_sha256']: raise ValueError('Angular review belongs to another publication')
    for name,digest in provenance['files'].items():
        path = (collection/name).resolve()
        if not path.is_relative_to(collection) or sha256(path) != digest: raise ValueError('Published artifact changed')
    for actor in proof['actors']:
        for version,key in [('source','source_sha256'),('candidate','candidate_sha256')]:
            matches = [r for r in provenance['records'] if r['version']==version and r['actor']==actor['actor']]
            if len(matches)!=1 or matches[0]['copied_glb_sha256'] != actor[key]: raise ValueError('Supplemental review actor differs')
    expected = {r['actor'] for r in provenance['records'] if r['version']=='candidate'}
    if len(proof['actors']) != len(expected) or {a['actor'] for a in proof['actors']} != expected: raise ValueError('Complete angular participants required')
    failures = sum(v['exceeding_observations'] for a in proof['actors'] for v in a['rates'].values())
    if failures <= 0: raise ValueError('Measured angular failures required')
    manifest = read(collection/'manifest.json'); candidate = next(s for s in manifest['scenes'] if s['id']=='candidate')
    evidence = collection/'angular-review'; evidence.mkdir()
    for name in ['request.json','verification.json']: shutil.copyfile(replay/name, evidence/name)
    note = f'Historical candidate: failed independent angular replay ({failures} limit exceedances). Not accepted under current motion checks. Earlier review: '+candidate.get('review_note','')
    save(collection/'review-update.json', dict(at=now(), original_manifest_sha256=sha256(collection/'manifest.json'),
        evidence={p.relative_to(collection).as_posix():sha256(p) for p in evidence.iterdir()}, scene_notes=dict(candidate=note), quality_approved=False))
    displayed_manifest(collection/'manifest.json')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('collection',type=Path);p.add_argument('replay',type=Path);a=p.parse_args()
    annotate_failed_angular(a.collection,a.replay)
