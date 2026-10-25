"""Bind a personal installation's Strep files to a checked content inventory.

This detects changes across build checks; it is not an atomic filesystem snapshot
or a publisher signature. Models, vendor source and runtime have separate checks.
"""
from pathlib import Path
import shutil
from strep import sha256
from portable_integrity import contained,verify_files


EXCLUDE={'__pycache__','.git','.pytest_cache'}
PROJECT_DIRECTORIES=('scripts','assets','benchmarks','integrations')


def eligible_files(source):
    source=Path(source)
    if not source.is_dir():raise ValueError('Source directory missing: '+str(source))
    for path in sorted(source.rglob('*')):
        relative=path.relative_to(source)
        if not path.is_file() or any(p in EXCLUDE for p in relative.parts):continue
        if path.suffix=='.pth' or path.name.startswith(('__editable__','_virtualenv')):continue
        yield relative,path


def capture_project(root,directories=PROJECT_DIRECTORIES):
    root=Path(root).resolve();files={}
    for directory in directories:
        folder=contained(root,directory)
        for relative,path in eligible_files(folder):
            name=(Path(directory)/relative).as_posix()
            checked=contained(root,name)
            files[name]=sha256(checked)
    return dict(schema='strep-offline-project-source-v1',directories=list(directories),files_sha256=files)


def validate_destination(root, destination, directories=PROJECT_DIRECTORIES):
    """Permit isolated local installs without copying a source subtree into itself."""
    root=Path(root).resolve();requested=Path(destination).absolute();destination=requested.resolve()
    if requested.is_relative_to(root) and not destination.is_relative_to(root):
        raise ValueError('Local installation path escapes the project')
    if root.is_relative_to(destination):
        raise ValueError('Use a separate installation directory')
    if destination.is_relative_to(root):
        local=root/'.local/installations'
        if destination==local or not destination.is_relative_to(local):
            raise ValueError('Use a separate installation under .local/installations/<name>')
    for directory in directories:
        source=contained(root,directory)
        if destination.is_relative_to(source) or source.is_relative_to(destination):
            raise ValueError('Installation must be separate from every copied source directory')
    return destination


def copy_project(root,destination,snapshot):
    root=Path(root).resolve()
    destination=validate_destination(root,destination,snapshot['directories'])
    for relative,digest in snapshot['files_sha256'].items():
        source,target=contained(root,relative),contained(destination,relative)
        if source.is_relative_to(destination):raise ValueError('Source file overlaps installation output')
        if target.exists():raise ValueError('Preserve existing project copy: '+relative)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        if sha256(target)!=digest:raise RuntimeError('Project changed during copy: '+relative)


def verify_project(root,destination,snapshot):
    current=capture_project(root,snapshot['directories'])
    if current!=snapshot:raise RuntimeError('Project source changed during installation build')
    verify_files(destination,snapshot['files_sha256'])
    return len(snapshot['files_sha256'])
