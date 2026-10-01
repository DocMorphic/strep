"""Bound native comparison packages; read-only Studio access, no selection."""
from pathlib import Path
import math
import re
from strep import ROOT, read, sha256

NAMESPACE = 'native-contact-reviews'
NAME = re.compile(r'[a-zA-Z0-9_-]{1,80}')
DIGEST = re.compile(r'[0-9a-f]{64}')
SUPPORT = {'viewer.html', 'viewer-manifest.json', 'native-contact-clock.mjs',
           'native-contact-feedback.mjs', 'soma-preview-skin.js', 'SOMA-preview-LICENSE.txt'}


def bound_path(folder, relative):
    if not isinstance(relative, str) or '\\' in relative:
        raise ValueError('Invalid comparison path')
    path = (folder / relative).resolve()
    if not path.is_relative_to(folder) or path == folder or Path(relative).as_posix() != relative:
        raise ValueError('Escaping comparison path')
    return path


def validate(folder):
    """Verify all served bytes, not just presence of a completion marker."""
    folder = Path(folder).resolve()
    build = read(folder / 'build.json')
    if build.get('schema_version') != 1 or build.get('status') != 'complete' or build.get('kind') != 'native_contact_review':
        raise ValueError('Completed native comparison publication required')
    for key in ('quality_approved', 'studio_selection_changed', 'human_review_submitted', 'browser_render_verified'):
        if build.get(key) is not False:
            raise ValueError('Publication must preserve unapproved scope')
    outputs = build['outputs']
    if not isinstance(outputs, dict) or not SUPPORT <= outputs.keys():
        raise ValueError('Missing comparison support files')
    for relative, digest in outputs.items():
        if relative not in SUPPORT and not re.fullmatch(r'(assets/[0-7]-[01]\.glb|audits/[0-7]-(result|decoded)\.json)', relative):
            raise ValueError('Unsupported publication output')
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest) or sha256(bound_path(folder, relative)) != digest:
            raise ValueError('Changed publication output')
    for relative, digest in build.get('implementation', {}).items():
        if not re.fullmatch(r'implementation/[a-zA-Z0-9_.-]+', relative) or sha256(bound_path(folder, relative)) != digest:
            raise ValueError('Changed publication implementation archive')
    manifest = read(folder / 'viewer-manifest.json')
    versions = manifest['versions']
    if not isinstance(versions, list) or not 2 <= len(versions) <= 8:
        raise ValueError('Two to eight alternatives required')
    expected = set(SUPPORT)
    for index, version in enumerate(versions):
        if version['id'] != str(index) or not isinstance(version['label'], str) or not version['label'].strip() or version.get('quality_approved') is not False:
            raise ValueError('Invalid comparison version')
        duration, event = version['duration_s'], version['event_time_s']
        if any(type(t) not in (int, float) or not math.isfinite(t) for t in (duration, event)) or not 0 <= event <= duration or duration <= 0:
            raise ValueError('Invalid native clock')
        actors = version['actors']
        if len(actors) != 2 or not DIGEST.fullmatch(version['source_result_sha256']):
            raise ValueError('Paired actors and source binding required')
        for actor_index, actor in enumerate(actors):
            relative = f'assets/{index}-{actor_index}.glb'
            if actor['url'] != relative or outputs.get(relative) != actor['sha256']:
                raise ValueError('Actor binding differs')
            placement = actor['placement']
            translation, rotation = placement['translation_m'], placement['rotation_xyzw']
            if not isinstance(translation, list) or len(translation) != 3 or not isinstance(rotation, list) or len(rotation) != 4:
                raise ValueError('Invalid actor placement')
            if any(type(v) not in (int, float) or not math.isfinite(v) for v in translation + rotation) or abs(math.sqrt(sum(v*v for v in rotation))-1) > 1e-6:
                raise ValueError('Invalid actor placement')
            expected.add(relative)
        audit = f'audits/{index}-result.json'
        if version['audit'] != audit or outputs.get(audit) != version['source_result_sha256']:
            raise ValueError('Result binding differs')
        expected.update((audit, f'audits/{index}-decoded.json'))
    if set(outputs) != expected:
        raise ValueError('Missing or extraneous version output')
    return manifest, build


def listing():
    parent = ROOT / 'reports' / NAMESPACE
    reviews, rejected = [], []
    for candidate in sorted(parent.glob('*'), reverse=True):
        if not candidate.is_dir() or not NAME.fullmatch(candidate.name):
            continue
        try:
            if candidate.resolve().parent != parent.resolve():
                raise ValueError('Escaping publication folder')
            manifest, build = validate(candidate)
            reviews.append(dict(id=candidate.name, label=candidate.name.replace('-', ' '),
                viewer_url=f'/files/{NAMESPACE}/{candidate.name}/viewer.html',
                build_sha256=sha256(candidate / 'build.json'), versions=len(manifest['versions']),
                quality_approved=False))
        except (OSError, ValueError, KeyError, TypeError) as error:
            rejected.append(dict(id=candidate.name, error=str(error)))
    return dict(reviews=reviews, rejected=rejected)


def served_file(relative):
    """Only immutable, hash-checked published outputs are served."""
    parts = relative.split('/')
    if len(parts) < 3 or parts[0] != NAMESPACE or not NAME.fullmatch(parts[1]):
        return None
    parent = (ROOT / 'reports' / NAMESPACE).resolve()
    folder = (parent / parts[1]).resolve()
    if folder.parent != parent:
        return None
    try:
        _, build = validate(folder)
        tail = '/'.join(parts[2:])
        if tail != 'build.json' and tail not in build['outputs']:
            return None
        return bound_path(folder, tail)
    except (OSError, ValueError, KeyError, TypeError):
        return None
