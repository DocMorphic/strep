"""Copy a completed bound native comparison into Studio's review namespace."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now
from native_review_publication import NAMESPACE, NAME, SUPPORT, bound_path, validate


def run(source, name):
    source = Path(source).resolve()
    if source.parent != ROOT / 'reports' or not NAME.fullmatch(name):
        raise ValueError('Immediate reports source and simple publication name required')
    target = ROOT / 'reports' / NAMESPACE / name
    if target.exists():
        raise ValueError('Fresh publication required')
    build = read(source / 'build.json')
    if build.get('status') != 'complete' or any(build.get(k) is not False for k in
            ('quality_approved', 'studio_selection_changed', 'human_review_submitted', 'browser_render_verified')):
        raise ValueError('Unapproved completed comparison required')
    inputs = dict(build['inputs'])
    inputs[str(source / 'build.json')] = sha256(source / 'build.json')
    for relative, digest in build['outputs'].items():
        path = bound_path(source, relative)
        if sha256(path) != digest:
            raise ValueError('Changed source output')
        inputs[str(path)] = digest
    def unchanged():
        for path, digest in inputs.items():
            if sha256(path) != digest:
                raise ValueError('Changed native comparison evidence')
    unchanged()
    manifest = read(source / 'viewer-manifest.json')
    paths = []
    for index, version in enumerate(manifest['versions']):
        paths.extend([f'assets/{index}-{i}.glb' for i in range(2)])
        paths.extend([f'audits/{index}-{kind}.json' for kind in ('result', 'decoded')])
    for relative in paths:
        if relative not in build['outputs']:
            raise ValueError('Unbound published asset')
    methods = [Path(__file__), ROOT/'scripts/native_review_publication.py',
               ROOT/'scripts/native-contact-review.html', ROOT/'scripts/native-contact-feedback.mjs']
    method_hashes = {path: sha256(path) for path in methods}
    target.mkdir(parents=True)
    archive = target / 'implementation'; archive.mkdir()
    implementation = {}
    for path, digest in method_hashes.items():
        archived = archive / path.name
        shutil.copyfile(path, archived)
        if sha256(archived) != digest:
            raise ValueError('Implementation copy changed')
        inputs[str(archived)] = digest
        implementation[archived.relative_to(target).as_posix()] = digest
    for relative in paths + ['viewer-manifest.json', 'native-contact-clock.mjs',
                              'soma-preview-skin.js', 'SOMA-preview-LICENSE.txt']:
        destination = target / relative
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(source / relative, destination)
        if sha256(destination) != build['outputs'][relative]:
            raise ValueError('Copy changed')
    html = (ROOT/'scripts/native-contact-review.html').read_text(encoding='utf8')
    if '../../assets/viewer/node_modules/three/' not in html:
        raise ValueError('Unexpected viewer dependencies')
    (target/'viewer.html').write_text(html.replace('../../assets/viewer/node_modules/three/', '/assets/'), encoding='utf8')
    shutil.copyfile(ROOT/'scripts/native-contact-feedback.mjs', target/'native-contact-feedback.mjs')
    unchanged()
    if any(sha256(path) != digest for path, digest in method_hashes.items()):
        raise ValueError('Method changed during publication')
    save(target/'build.json', dict(schema_version=1, kind='native_contact_review', status='complete', at=now(),
        inputs=inputs, source_build_sha256=sha256(source/'build.json'),
        builder_sha256=sha256(__file__), implementation=implementation,
        outputs={p.relative_to(target).as_posix(): sha256(p) for p in target.rglob('*') if p.is_file() and not p.is_relative_to(archive)},
        browser_render_verified=False, studio_selection_changed=False, human_review_submitted=False, quality_approved=False))
    validate(target)
    print(f'/files/{NAMESPACE}/{name}/viewer.html', flush=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('name')
    args = parser.parse_args(); run(args.source, args.name)
