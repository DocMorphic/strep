"""Copy immutable paired inputs into a fresh review job without copying results."""
import argparse
from pathlib import Path
import shutil
from strep import ROOT, read, save, sha256, now


def copy_request(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    jobs = (ROOT/'reports/paired-edit-jobs').resolve()
    if source.parent != jobs or output.parent != jobs or output.exists():
        raise ValueError('Existing paired input and fresh paired review folder required')
    request_path = source/'request.json'; record = read(request_path)
    if read(source/'state.json').get('status') != 'prepared': raise ValueError('Immutable prepared state required')
    entries = [('request.json', sha256(request_path)), ('state.json', sha256(source/'state.json'))]
    entries += [(record['scene_snapshot']['path'], record['scene_snapshot']['sha256'])]
    entries += [(a['path'], a['sha256']) for a in record['actors'].values()]
    entries += [('implementation/'+name, digest) for name, digest in record['implementation'].items()]
    bound = {}
    for name, digest in entries:
        relative = Path(name); path = (source/relative).resolve()
        if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(source):
            raise ValueError('Prepared artifact escapes source')
        if name in bound and bound[name] != digest: raise ValueError('Conflicting prepared artifacts')
        if sha256(path) != digest: raise ValueError('Prepared artifact changed: '+name)
        bound[name] = digest
    for path, digest in record['inputs'].items():
        if sha256(path) != digest: raise ValueError('Original prepared input changed')
    output.mkdir()
    for name, digest in bound.items():
        target = output/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/name, target)
        if sha256(target) != digest or sha256(source/name) != digest:
            raise ValueError('Prepared artifact changed during copy')
    for path, digest in record['inputs'].items():
        if sha256(path) != digest: raise ValueError('Original input changed during copy')
    save(output/'review-origin.json', dict(at=now(), source=str(source), request_sha256=bound['request.json'],
        copied=bound, quality_approved=False,
        scope='Byte-identical prepared inputs for a separate review job. No solver, export, review result or quality approval copied.'))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); print(copy_request(args.source, args.output))
