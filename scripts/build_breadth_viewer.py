"""Build a read-only all-case index without changing the frozen generation study."""
import argparse
import os
from pathlib import Path
from urllib.parse import quote
from strep import ROOT, read, save, sha256


def make_index(study):
    study = Path(study).resolve()
    frozen = read(study / 'freeze.json')
    if sha256(study / 'protocol.json') != frozen['protocol_sha256']:
        raise ValueError('Frozen protocol changed')
    protocol = read(study / 'protocol.json')
    lookup = {}
    for batch in frozen['batches']:
        request = (ROOT / batch['request']).resolve()
        if not request.is_relative_to(ROOT) or sha256(request) != batch['request_sha256']:
            raise ValueError('Frozen request changed or outside project')
        output = (ROOT / batch['output']).resolve()
        if not output.is_relative_to(ROOT / 'reports/action-jobs'):
            raise ValueError('Output outside action jobs')
        for item in read(request)['requests']:
            for seed in item['seeds']:
                key = (item['id'], seed)
                if key in lookup:
                    raise ValueError('Duplicate planned actor/seed')
                take = (output / 'takes' / f'{item["id"]}-seed-{seed}').resolve()
                if not take.is_relative_to(output / 'takes'):
                    raise ValueError('Take outside batch')
                lookup[key] = (batch['id'], quote(Path(os.path.relpath(take, study)).as_posix()) + '/')
    cases = []
    for case in protocol['cases']:
        actors = []
        for actor in case['actors']:
            identifier = case['id'] + '-' + actor['id'].lower()
            takes = []
            for seed in case['seeds']:
                batch, base = lookup.pop((identifier, seed))
                takes.append(dict(seed=seed, batch=batch, base=base))
            actors.append(dict(id=actor['id'], request_id=identifier, prompt=actor['prompt'], takes=takes))
        cases.append(dict(id=case['id'], family=case['family'], context=case['context'],
                          flat_floor_screen_applicable=case['flat_floor_screen_applicable'],
                          scene_validation=case['scene_validation'], duration_s=case['duration_s'], actors=actors))
    if lookup:
        raise ValueError('Unassigned batch outputs')
    return dict(schema='strep-breadth-viewer-v1', protocol_sha256=frozen['protocol_sha256'], cases=cases,
                expected_actor_clips=protocol['expected_actor_clips'])


def build(study):
    study = Path(study).resolve()
    index = make_index(study)
    save(study / 'viewer-index.json', index)
    (study / 'viewer.html').write_bytes((ROOT / 'scripts/breadth-viewer.html').read_bytes())
    return index


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--study', type=Path, default=ROOT / 'reports/breadth-baseline-v2')
    a = p.parse_args()
    print(f'Indexed {len(build(a.study)["cases"])} frozen cases')
