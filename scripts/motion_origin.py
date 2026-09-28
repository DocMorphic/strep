"""Bind original generation intent to the exact motion carried by rig exports."""
import hashlib
import json
from pathlib import Path
import shutil
from strep import read, save, sha256

FILES = ('generation-record.json', 'request.json', 'motion-brief.json')
SCHEMA = 'strep-motion-origin-v1'


def _metadata(folder, name):
    path = folder / name
    if not path.is_file() or path.resolve().parent != folder.resolve():
        raise ValueError('Motion origin metadata is missing or escapes its folder: ' + name)
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Motion origin metadata exceeds 4 MiB')
    data = read(path)
    if not isinstance(data, dict):
        raise ValueError('Motion origin metadata must be an object')
    return data


def describe(motion, metadata_folder=None):
    motion = Path(motion)
    folder = Path(metadata_folder) if metadata_folder is not None else motion.parent
    digest = sha256(motion)
    names = [name for name in FILES if (folder / name).exists()]
    manifest = dict(schema=SCHEMA, motion_sha256=digest, status='unavailable', files={},
        scope='Original source generation intent; not evidence that transferred or edited motion follows it.',
        quality_approved=False)
    if 'generation-record.json' not in names:
        if 'motion-brief.json' in names:
            raise ValueError('Movement profile has no generation record binding it to this motion')
        return manifest
    record = _metadata(folder, 'generation-record.json')
    if record.get('status') != 'generated' or record.get('npz_sha256') != digest:
        raise ValueError('Generation record does not bind this motion')
    request = _metadata(folder, 'request.json')
    if record.get('request') != request or record.get('seed') not in request.get('seeds', []):
        raise ValueError('Generation request or seed differs from retained record')
    brief = record.get('motion_brief')
    if brief is not None:
        if _metadata(folder, 'motion-brief.json') != brief:
            raise ValueError('Movement-profile brief differs from generation record')
        if brief.get('profile') != request.get('motion_profile'):
            raise ValueError('Movement-profile brief differs from original request')
        payload = {k: v for k, v in brief.items() if k != 'resolution_sha256'}
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if brief.get('resolution_sha256') != expected:
            raise ValueError('Movement-profile resolution checksum differs')
        segments = brief.get('segments')
        if not isinstance(segments, list) or len(segments) != len(request.get('segments', [])):
            raise ValueError('Movement-profile segment population differs')
        for actual, original in zip(segments, request['segments']):
            if not isinstance(actual, dict) or not isinstance(original, dict):
                raise ValueError('Movement-profile segments must be objects')
            if actual.get('original_prompt') != original['prompt'] or actual.get('duration_s') != original['duration_s']:
                raise ValueError('Movement-profile original segment differs')
    elif 'motion-brief.json' in names or request.get('motion_profile') is not None:
        raise ValueError('Generation record is missing its movement-profile brief')
    selected = ['generation-record.json', 'request.json'] + (['motion-brief.json'] if brief is not None else [])
    manifest.update(status='recorded', files={name: sha256(folder/name) for name in selected},
        has_movement_profile=brief is not None, seed=record['seed'])
    return manifest


def snapshot(motion, destination, expected):
    """Recheck after validation, copy only fixed names, then verify copied bytes."""
    motion, destination = Path(motion), Path(destination)
    if describe(motion) != expected:
        raise ValueError('Motion origin changed after request validation')
    destination.mkdir(exist_ok=False)
    for name in expected['files']:
        shutil.copyfile(motion.parent/name, destination/name)
    save(destination/'manifest.json', expected)
    verify(motion, destination, expected)


def verify(motion, folder, expected=None):
    folder = Path(folder)
    manifest = _metadata(folder, 'manifest.json')
    if expected is not None and manifest != expected:
        raise ValueError('Motion origin manifest differs from pinned request')
    if manifest != describe(motion, folder):
        raise ValueError('Motion origin snapshot no longer matches its motion or metadata')
    return manifest
