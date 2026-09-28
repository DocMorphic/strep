"""Index retained source generation records without assigning them to edited poses."""
import hashlib
import json
from pathlib import Path
from motion_origin import describe,verify
from strep import read,save,sha256

ROOTS=('source','input','following','generation')


def collect(folder):
    folder=Path(folder).resolve();motions={};origins={}
    def relative(path):
        path=Path(path)
        if not path.resolve().is_relative_to(folder):raise ValueError('Generation history escapes package')
        return path.relative_to(folder).as_posix()
    for name in ROOTS:
        root=folder/name
        if not root.exists():continue
        relative(root)
        for path in root.rglob('motion.npz'):
            relative(path)
            if not path.is_file():raise ValueError('Retained source motion is not a file')
            motions[relative(path)]=path
        for manifest_path in root.rglob('motion-origin/manifest.json'):
            relative(manifest_path)
            if manifest_path.stat().st_size>4*1024*1024:raise ValueError('Motion origin manifest exceeds4MiB')
            manifest=read(manifest_path)
            if not isinstance(manifest,dict):raise ValueError('Motion origin manifest must be an object')
            source=manifest_path.parent.parent
            candidates=[source/n for n in ('motion.npz','character.glb') if (source/n).is_file()]
            for candidate in candidates:relative(candidate)
            matches=[p for p in candidates if sha256(p)==manifest.get('motion_sha256')]
            if len(matches)!=1:raise ValueError('Retained origin has no unique matching local motion')
            motion=matches[0];motions[relative(motion)]=motion;origins[relative(motion)]=manifest_path.parent
    groups={}
    for name,motion in sorted(motions.items()):
        origin=origins.get(name)
        if origin is None and (motion.parent/'motion-origin').exists():
            # A damaged or missing manifest must not downgrade to unavailable.
            relative(motion.parent/'motion-origin');origin=motion.parent/'motion-origin'
        manifest=verify(motion,origin) if origin is not None else describe(motion)
        metadata=origin if origin is not None else motion.parent
        files={}
        for filename,digest in manifest['files'].items():
            path=metadata/filename;files[relative(path)]=digest
        identity=hashlib.sha256(json.dumps(manifest,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        location=dict(motion=name,motion_sha256=manifest['motion_sha256'],metadata_files=files)
        if origin is not None:
            location.update(manifest=relative(origin/'manifest.json'),manifest_sha256=sha256(origin/'manifest.json'))
        if identity not in groups:
            groups[identity]=dict(id=identity,status=manifest['status'],motion_sha256=manifest['motion_sha256'],
                has_movement_profile=bool(manifest.get('has_movement_profile',False)),locations=[],quality_approved=False)
            if 'seed' in manifest:groups[identity]['seed']=manifest['seed']
        groups[identity]['locations'].append(location)
    entries=[groups[k] for k in sorted(groups)]
    return dict(schema='strep-generation-sources-v1',entries=entries,distinct_source_records=len(entries),
        retained_locations=sum(len(e['locations']) for e in entries),recorded_sources=sum(e['status']=='recorded' for e in entries),
        unavailable_sources=sum(e['status']=='unavailable' for e in entries),quality_approved=False,
        applies_to='retained_source_snapshots',
        scope='Bundled source generation history, including transition donors and raw section regenerations. Repeated copies share one record with all locations retained. This is not a contributor timeline, current style assignment, complete external lineage or quality approval.')


def write(folder):
    result=collect(folder);save(Path(folder)/'generation-sources.json',result);return result
