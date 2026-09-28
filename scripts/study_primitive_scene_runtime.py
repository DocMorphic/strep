"""Actual shared-clock actor/primitive playback using an existing development actor."""
import argparse
import shutil
from pathlib import Path
from strep import ROOT,read,save,sha256,now
from scene_runtime import package
from study_scene_runtime import verify
from probe_godot_render import run_engine


def run(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    source=ROOT/'reports/scene-runtime-v2/release';authored=output/'authored';authored.mkdir()
    scene=read(source/'portable-scene.json');scene['id']='primitive-shared-clock-development'
    shutil.copytree(source/'actors',authored/'actors')
    # Reuse only the recorded rigid track; it is no longer a simulation result.
    for name,obj in scene['objects'].items():
        obj.pop('shape',None);obj.pop('size_m',None)
        obj['geometry']=dict(schema='strep-object-geometry-v1',shape='sphere',radius_m=.25)
        obj['trajectory_provenance']='Authored playback fixture reusing a box trajectory; not spherical dynamics or generated contact.'
    scene.pop('objects_glb',None);scene['contacts']=[]
    save(authored/'portable-scene.json',scene)
    save(authored/'events.json',dict(fps=30,events=[dict(type='authored_preview_marker',object=next(iter(scene['objects'])),frame=30,time_s=1.)]))
    folder=output/'package';metadata=package(authored/'portable-scene.json',folder)
    project=output/'project';project.mkdir();(project/'project.godot').write_text('config_version=5\n')
    implementation=output/'implementation';implementation.mkdir()
    names=['godot_scene_clock.gd','godot_scene_clock_audit.gd','scene_runtime.py','scene_object_export.py','scene_constraints.py','object_geometry.py','object_geometry_mesh.py','study_primitive_scene_runtime.py','study_scene_runtime.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,implementation/name)
    for name in ['godot_scene_clock.gd','godot_scene_clock_audit.gd']:shutil.copyfile(ROOT/'scripts'/name,project/name)
    request=dict(cases=[dict(id='primitive',folder=str(folder),frames=metadata['frames'],metadata_sha256=sha256(folder/'scene-runtime.json'),package_sha256=sha256(folder/'scene-runtime.zip'))],controls=[],
        implementation={n:sha256(implementation/n) for n in names},source_scene_sha256=sha256(source/'portable-scene.json'),
        limits=dict(actor_matrix=1e-4,object_matrix=1e-5),scope='Existing actor and newly authored sphere fixture. Playback/packaging test only; no sphere interaction or physics success claimed.')
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    command=[str(engine),'--headless','--path',str(project),'--fixed-fps','60','--script','godot_scene_clock_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')]
    save(output/'request.json',request);save(output/'pipeline.json',dict(status='engine_running',at=now()))
    run_engine(command,output/'engine.log',timeout=120)
    passed,checks=verify(request,read(output/'engine-output.json'),output)
    save(output/'pipeline.json',dict(status='complete' if passed else 'failed_comparison',passed=passed,quality_approved=False))
    print(dict(passed=passed,checks=checks))
    if not passed:raise ValueError('Primitive scene runtime check failed; outputs retained')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.output)
