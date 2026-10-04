"""Developer ratings of existing neutral packets, separate from independent evidence."""
import argparse
import copy
from pathlib import Path
import shutil
import uuid

from strep import ROOT, read, save, sha256, now
from review_session import _validate_rows
from portable_review_packet import package


def validate(data, manifest, digest):
    fields = {'schema', 'packet_id', 'manifest_sha256', 'reviewer_id', 'human_review',
              'independent_human', 'review_type', 'quality_approved', 'release_approved', 'reviews'}
    if not isinstance(data, dict) or set(data) != fields or data['schema'] != 'strep-developer-packet-review-v1':
        raise ValueError('Developer packet review schema required')
    if manifest.get('review_type') != 'developer' or data['review_type'] != 'developer':
        raise ValueError('Developer review requires a developer packet')
    if data['human_review'] is not True or any(data[k] is not False for k in
            ('independent_human', 'quality_approved', 'release_approved')):
        raise ValueError('Developer human attestation required; independence and approval must remain false')
    if data['packet_id'] != manifest['packet_id'] or data['manifest_sha256'] != digest:
        raise ValueError('Review belongs to another packet')
    result = _validate_rows(data, manifest, digest)
    result.update(review_type='developer', independent_review=False, release_approved=False,
        scope='User-entered developer ratings and cleanup attestations. Not independent animator review, verified editing, or release acceptance.')
    return result


def _inventory(packet):
    manifest = read(packet/'manifest.json')
    if manifest.get('schema') != 'strep-review-packet-v1' or manifest.get('review_type', 'independent') != 'independent':
        raise ValueError('Existing independent neutral packet required')
    cases = manifest['cases']
    if not cases or len({c['id'] for c in cases}) != len(cases) or len({c['path'] for c in cases}) != len(cases):
        raise ValueError('Distinct complete packet cases required')
    files = read(packet/'package-integrity.json')['files']
    actual = {p.relative_to(packet).as_posix() for p in packet.rglob('*') if p.is_file()}
    allowed = {'manifest.json', 'viewer.html', 'LICENSE.txt', 'serve.py', 'README.txt'} | {c['path'] for c in cases}
    if actual != set(files) | {'package-integrity.json'} or any(n not in allowed and not n.startswith('runtime/') for n in files):
        raise ValueError('Unexpected packet files; exclude organizer data')
    for name, digest in files.items():
        path = (packet/name).resolve()
        if not path.is_relative_to(packet) or sha256(path) != digest:
            raise ValueError('Changed or escaping packet file')
    for case in cases:
        if not case['path'].startswith('clips/') or files.get(case['path']) != case['sha256']:
            raise ValueError('Changed or invalid clip binding')
    return manifest, {name: sha256(packet/name) for name in actual}


def prepare(source, output, archive):
    source, output, archive = [Path(p).resolve() for p in (source, output, archive)]
    if output.exists() or archive.exists() or output.is_relative_to(source) or source.is_relative_to(output) or archive.is_relative_to(source) or archive.is_relative_to(output):
        raise ValueError('Use fresh, separate developer packet and archive paths')
    original, hashes = _inventory(source)
    manifest = copy.deepcopy(original)
    manifest.update(packet_id=uuid.uuid4().hex, created_at=now(), review_type='developer',
        instructions='Developer review of the complete supplied raw population. Watch at normal speed and record your own judgments. Ratings and actual cleanup records do not count as independent review or release approval. No ratings are generated automatically.')
    output.mkdir(parents=True)
    for case in manifest['cases']:
        dest = output/case['path']; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/case['path'], dest)
        if sha256(dest) != case['sha256']: raise ValueError('Copied clip changed')
    shutil.copyfile(source/'LICENSE.txt', output/'LICENSE.txt')
    shutil.copyfile(ROOT/'scripts/human-review.html', output/'viewer.html')
    save(output/'manifest.json', manifest)
    result = package(output, archive)
    if any(sha256(source/name) != digest for name, digest in hashes.items()):
        raise ValueError('Source packet changed during developer packaging')
    if read(output/'manifest.json')['cases'] != original['cases']:
        raise ValueError('Developer packet changed case population or context')
    result.update(source_packet_id=original['packet_id'], source_manifest_sha256=hashes['manifest.json'],
        source_files_sha256=hashes, manifest_sha256=sha256(output/'manifest.json'),
        human_reviews_collected=0, independent_review=False, quality_approved=False, release_approved=False)
    return result


def import_reviews(packet, response, output):
    packet, response, output = [Path(p).resolve() for p in (packet, response, output)]
    if output.exists() or output.is_relative_to(packet): raise ValueError('Preserve existing packet and imported evidence')
    manifest = read(packet/'manifest.json'); digest = sha256(packet/'manifest.json'); response_hash = sha256(response)
    data = read(response); result = validate(data, manifest, digest)
    for case in manifest['cases']:
        path = (packet/case['path']).resolve()
        if not path.is_relative_to(packet) or sha256(path) != case['sha256']: raise ValueError('Review clip changed or escaped packet')
    if sha256(response) != response_hash or sha256(packet/'manifest.json') != digest:
        raise ValueError('Review source changed during validation')
    output.mkdir(parents=True); shutil.copyfile(response, output/'response.json')
    if sha256(output/'response.json') != response_hash: raise ValueError('Copied review changed')
    save(output/'validation.json', dict(created_at=now(), response_sha256=response_hash, **result))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('prepare'); b.add_argument('source', type=Path); b.add_argument('output', type=Path); b.add_argument('archive', type=Path)
    i = sub.add_parser('import'); i.add_argument('packet', type=Path); i.add_argument('response', type=Path); i.add_argument('output', type=Path)
    a = p.parse_args()
    print(prepare(a.source, a.output, a.archive) if a.command == 'prepare' else import_reviews(a.packet, a.response, a.output))
