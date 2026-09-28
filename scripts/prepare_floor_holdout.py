"""Reuse verified identical prompt features for genuinely new seed-55 inference."""
import copy
import shutil
from strep import ROOT,read,save,sha256,now
from action_encoder import ActionEncoder
from action_requests import request_digest,conditioning_texts

def main():
    source=ROOT/'reports/action-coverage-v1'
    destination=ROOT/'reports/action-jobs/floor-holdout-seed55'
    batch=read(source/'request.json');ActionEncoder(source/'conditioning',batch)
    updated=copy.deepcopy(batch)
    for request in updated['requests']:request['seeds']=[55]
    assert conditioning_texts(updated)==conditioning_texts(batch)
    destination.mkdir(parents=True,exist_ok=False)
    cache=destination/'conditioning';cache.mkdir()
    meta=read(source/'conditioning/manifest.json')
    for entry in meta['entries'].values():
        shutil.copyfile(source/'conditioning'/entry['file'],cache/entry['file'])
        assert sha256(cache/entry['file'])==entry['sha256']
    meta.update(request_sha256=request_digest(updated),reuse_provenance=dict(source=str(source/'conditioning'),
        source_manifest_sha256=sha256(source/'conditioning/manifest.json'),copied_at=now(),reason='Exact identical prompt strings and model/encoder revisions, different random seeds only. No re-encoding.'))
    save(cache/'manifest.json',meta);save(destination/'request.json',updated);ActionEncoder(cache,updated)
    save(ROOT/'benchmarks/floor-contact-v1-freeze.json',dict(created_at=now(),new_seed=55,
        development=['crawl-seed-11','get-up-seed-11','run-roll-stand-seed-11','wave-seed-11'],
        evaluation='Remaining original clips, two existing custom actions, and seven new seed-55 takes. Existing seed22 audits were seen previously; not a blind dataset.',
        hashes={n:sha256(ROOT/'scripts'/n) for n in ['floor_contact.py','evaluate_floor_contact.py','run_floor_contact.py']},
        request_sha256=request_digest(updated)))
    print(destination)

if __name__=='__main__':main()
