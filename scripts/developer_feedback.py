"""Validate a non-blind developer observation against its immutable review package."""
import argparse
from datetime import datetime
from pathlib import Path
from strep import ROOT, read, save, sha256, now


def validate(data, catalog_path):
    catalog_path = Path(catalog_path).resolve()
    base = (ROOT/'reports/rig-jobs').resolve()
    if not catalog_path.is_relative_to(base) or catalog_path.name != 'catalog.json':
        raise ValueError('Use a local rig-jobs review catalog')
    keys = {'schema', 'created_at', 'reviewer_id', 'source', 'frame_range', 'notes',
            'review_type', 'independent_human', 'cleanup_test_performed', 'quality_approved'}
    if not isinstance(data, dict) or set(data) != keys or data['schema'] != 'strep-developer-observation-v1':
        raise ValueError('Invalid developer observation schema')
    if data['review_type'] != 'non_blind_developer' or any(data[k] is not False for k in
            ('independent_human', 'cleanup_test_performed', 'quality_approved')):
        raise ValueError('Developer feedback cannot claim independent review, cleanup timing or approval')
    for field, limit in [('reviewer_id', 120), ('notes', 4000)]:
        if not isinstance(data[field], str) or not 1 <= len(data[field].strip()) <= limit:
            raise ValueError('Invalid '+field)
    try:
        timestamp = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None: raise ValueError('Missing timezone')
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Invalid observation timestamp') from exc
    catalog = read(catalog_path); source = data['source']
    if not isinstance(source, dict): raise ValueError('Missing source binding')
    row = next((r for r in catalog['cases'] if r['id'] == source.get('case_id')), None)
    if row is None: raise ValueError('Unknown review case')
    version = next((v for v in row['variants'] if v['id'] == source.get('variant')), None)
    if version is None: raise ValueError('Unknown motion version')
    expected = dict(study_url='/files/rig-jobs/'+catalog_path.relative_to(base).as_posix(),
        catalog_sha256=sha256(catalog_path), case_id=row['id'], variant=version['id'],
        glb_url=version['glb'], glb_sha256=version['sha256'], frames=row['frames'],
        fps=row['fps'], prompt=row['prompt'], seed=row['seed'])
    if source != expected: raise ValueError('Feedback belongs to a different catalog or motion')
    prefix = '/files/rig-jobs/'
    if not version['glb'].startswith(prefix): raise ValueError('Invalid packaged motion path')
    clip = (base/version['glb'][len(prefix):]).resolve()
    if not clip.is_relative_to(catalog_path.parent) or sha256(clip) != version['sha256']:
        raise ValueError('Packaged motion changed or escaped the review package')
    span = data['frame_range']
    if not isinstance(span, dict) or set(span) != {'start', 'end_inclusive'} or any(type(v) is not int for v in span.values()):
        raise ValueError('Integer frame range required')
    if not 0 <= span['start'] <= span['end_inclusive'] < row['frames']:
        raise ValueError('Frame range outside reviewed clip')
    return dict(valid=True, case_id=row['id'], variant=version['id'], catalog_sha256=sha256(catalog_path),
        glb_sha256=version['sha256'], independent_review=False, quality_approved=False,
        scope='Source-bound developer observation. Content remains a reviewer report, not independently verified fact or release acceptance.')


def import_feedback(catalog, response, output):
    if output.exists(): raise ValueError('Preserve existing feedback import')
    data = read(response); result = validate(data, catalog)
    output.mkdir(parents=True)
    save(output/'observation.json', data)
    save(output/'validation.json', dict(at=now(), response_sha256=sha256(response),
        observation_sha256=sha256(output/'observation.json'), **result))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('catalog', type=Path); p.add_argument('response', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); print(import_feedback(a.catalog.resolve(), a.response.resolve(), a.output.resolve()))
