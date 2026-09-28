"""Create a separate personal Windows installation from locally licensed files.

No downloads, credentials, inference cache, or research outputs are copied.
Does not authorize redistribution of gated weights or third-party dependencies.
"""
import argparse
import importlib.metadata
from pathlib import Path
import shutil
import subprocess
import sys
from strep import ROOT, read, save, sha256, source_check, model_directory, now


EXCLUDE = {'__pycache__', '.git', '.pytest_cache'}


def copy_tree(source, destination):
    for path in source.rglob('*'):
        relative = path.relative_to(source)
        if not path.is_file() or any(p in EXCLUDE for p in relative.parts):
            continue
        if path.suffix == '.pth' or path.name.startswith(('__editable__', '_virtualenv')):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def build(destination):
    destination = destination.resolve()
    if destination.exists() or destination.is_relative_to(ROOT) or ROOT.is_relative_to(destination):
        raise ValueError('Choose a new installation folder outside the development project')
    commit = source_check()
    # 23 GiB copied files plus regenerated encoder matrices and working outputs.
    if shutil.disk_usage(destination.parent).free < 40 * 1024**3:
        raise RuntimeError('At least 40 GiB free space required')
    destination.mkdir()
    save(destination / 'build-status.json', {'status': 'building', 'started_at': now()})
    for directory in ['scripts', 'assets', 'benchmarks', 'integrations']:
        print('Copying ' + directory, flush=True)
        copy_tree(ROOT / directory, destination / directory)
    vendor = ROOT / 'vendor/kimodo'
    names = subprocess.check_output(['git', '-c', f'safe.directory={vendor.as_posix()}', '-C', str(vendor),
                                     'ls-files', '-z'], text=True).split('\0')
    hashes = {}
    for relative in filter(None, names):
        source = vendor / relative
        target = destination / 'vendor/kimodo' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        hashes[relative] = sha256(target)
    save(destination / 'benchmarks/vendor-export.json', {'schema': 1, 'commit': commit, 'files_sha256': hashes})
    print('Copying standalone Python and installed dependencies', flush=True)
    runtime = destination / 'runtime/python'
    copy_tree(Path(sys.base_prefix), runtime)
    copy_tree(Path(sys.prefix) / 'Lib/site-packages', runtime / 'Lib/site-packages')
    # This standalone 3.10 build reports isolated=1 under _pth but still enables
    # the user site when 'import site' is present. Disable it before addusersitepackages.
    site_path = runtime / 'Lib/site.py'
    site_source = site_path.read_text(encoding='utf-8')
    if site_source.count('ENABLE_USER_SITE = None') != 1:
        raise RuntimeError('Unexpected Python site.py; isolation patch requires review')
    original_site_hash = sha256(site_path)
    site_path.write_text(site_source.replace('ENABLE_USER_SITE = None', 'ENABLE_USER_SITE = False'), encoding='utf-8')
    save(destination / 'runtime/isolation-patch.json', {'file': 'runtime/python/Lib/site.py',
        'original_sha256': original_site_hash, 'patched_sha256': sha256(site_path),
        'change': 'Initialize ENABLE_USER_SITE=False before site processes any user directory'})
    (runtime / 'python310._pth').write_text('.\nDLLs\nLib\nLib/site-packages\n../../scripts\n../../vendor/kimodo\nimport site\n', encoding='utf-8')
    shutil.copyfile(ROOT / 'scripts/portable_site.py', runtime / 'Lib/site-packages/sitecustomize.py')
    distributions = sorted([{'name': d.metadata['Name'], 'version': d.version,
                             'license': d.metadata.get('License'),
                             'license_expression': d.metadata.get('License-Expression')}
                            for d in importlib.metadata.distributions()], key=lambda x: x['name'].lower())
    save(destination / 'dependency-inventory.json', {'distributions': distributions,
                                                  'notice': 'Installed metadata and licenses retained; not a redistribution clearance.'})
    acquisition = read(ROOT / 'models/manifest.json')
    save(destination / 'models/manifest.json', acquisition)
    for entry in acquisition['models'].values():
        print('Copying pinned model ' + entry['repo_id'], flush=True)
        source = model_directory(entry)
        target = destination / source.relative_to(ROOT)
        for relative, digest in entry['files_sha256'].items():
            out = target / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, out)
            if sha256(out) != digest:
                raise RuntimeError('Model hash mismatch: ' + entry['repo_id'] + '/' + relative)
        if not entry['repo_id'].startswith('nvidia/'):
            refs = target.parent.parent / 'refs'
            refs.mkdir(exist_ok=True)
            (refs / 'main').write_text(entry['revision'], encoding='utf-8')
    copy_tree(ROOT / '.cache/godot/4.7.2-stable', destination / '.cache/godot/4.7.2-stable')
    (destination / 'Strep.cmd').write_text('@echo off\r\n"%~dp0runtime\\python\\python.exe" "%~dp0scripts\\portable_launch.py" %*\r\n', encoding='utf-8')
    (destination / 'README.txt').write_text(
        'Strep personal offline installation (Windows x64, NVIDIA CUDA GPU).\n'
        'Run Strep.cmd, then open http://127.0.0.1:8768/studio.\n'
        'Strep.cmd --port 8770 selects another local port.\n'
        'Strep.cmd verify hashes all bundled files; Strep.cmd probe checks Python/CUDA/source isolation.\n'
        'First new prompt rebuilds encoder matrices locally and may take several minutes.\n'
        'No training or quality approval is implied. Human review remains necessary.\n'
        'Python external sockets are denied; this is not OS-level network isolation.\n'
        'Models and dependencies retain their own licenses. Personal local copy, not a redistributable release.\n', encoding='utf-8')
    if source_check() != commit:
        raise RuntimeError('Vendor source changed during build')
    print('Hashing complete installation', flush=True)
    files = {p.relative_to(destination).as_posix(): sha256(p) for p in destination.rglob('*')
             if p.is_file() and p.name != 'build-status.json'}
    save(destination / 'installation.json', {'schema': 1, 'built_at': now(), 'vendor_commit': commit,
                                           'purpose': 'personal offline relocation experiment', 'files_sha256': files})
    save(destination / 'build-status.json', {'status': 'complete', 'finished_at': now(), 'files': len(files)})
    print(str(destination), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    build(parser.parse_args().destination)
