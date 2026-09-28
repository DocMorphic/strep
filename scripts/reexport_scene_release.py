"""Version an export correction without rerunning or altering saved physics."""
import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path
from strep import read,save,sha256,now,ROOT
from scene_object_export import export_objects


def run(source,output):
    source=Path(source).resolve();output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(source/'scene-animation.zip') as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            if not (output/name).resolve().is_relative_to(output):raise ValueError('Package escapes export directory')
            if name!='README.txt' and hashlib.sha256(archive.read(name)).hexdigest()!=sha256(source/name):raise ValueError('Source package changed')
        archive.extractall(output)
    prior={name:sha256(output/name) for name in ['objects.glb','input-objects.glb']}
    export_objects(read(output/'input.json')['scene'],output/'input-objects.glb')
    export_objects(read(output/'candidate.json')['scene'],output/'objects.glb')
    for name in ['scene_object_export.py','object_geometry_mesh.py','object_geometry.py','reexport_scene_release.py']:
        (output/'export-implementation').mkdir(exist_ok=True);shutil.copyfile(ROOT/'scripts'/name,output/'export-implementation'/name)
    save(output/'export-revision.json',dict(at=now(),source_package_sha256=sha256(source/'scene-animation.zip'),prior_glbs=prior,
        reason='Constant unit-scale object tracks preserve complete TRS and avoid Godot 4.7.2 Euler fallback. Keep immutable tracks when importing.',
        simulation_repeated=False,actor_motion_changed=False,object_trajectory_changed=False,exporter_sha256=sha256(ROOT/'scripts/scene_object_export.py')))
    with (output/'README.txt').open('a',encoding='utf8') as note:
        note.write('Export correction: preserve constant scale tracks (disable remove immutable tracks in Godot import). They preserve complete TRS and avoid a quaternion-to-Euler fallback. Original physics and actor/box trajectories are unchanged.\n')
    with zipfile.ZipFile(output/'scene-animation.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for path in output.rglob('*'):
            if path.is_file() and path.suffix!='.zip':archive.write(path,path.relative_to(output).as_posix())
    print(dict(output=str(output),package_sha256=sha256(output/'scene-animation.zip')),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');parser.add_argument('output');args=parser.parse_args();run(args.source,args.output)
