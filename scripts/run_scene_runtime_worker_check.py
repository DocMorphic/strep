"""Retained real Studio release worker + engine playback on a 2-actor/2-object fixture."""
from pathlib import Path
import shutil
import sys
from strep import ROOT,read,save,sha256,now
from probe_godot_render import run_engine
from study_scene_runtime import verify


def run():
    output=ROOT/'reports/scene-release-jobs/scene-runtime-worker-v1';output.mkdir(exist_ok=False)
    implementation=output/'implementation';implementation.mkdir()
    test=ROOT/'tests/test_scene_release_job.py';shutil.copyfile(test,implementation/test.name)
    for name in ('run_scene_runtime_worker_check.py','study_scene_runtime.py','godot_scene_clock.gd','godot_scene_clock_audit.gd'):
        shutil.copyfile(ROOT/'scripts'/name,implementation/name)
    save(output/'pipeline.json',dict(at=now(),status='worker_running'))
    sys.path.insert(0,str(ROOT/'tests'))
    from test_scene_release_job import test_real_worker_generic_objects_multiple_actors_portable_tracks_and_events
    # Call the test body directly, outside its temporary-directory cleanup fixture.
    # The production worker, simulation and package run unchanged; all inputs remain.
    test_real_worker_generic_objects_multiple_actors_portable_tracks_and_events(output,'moving_scene')
    folder=output/'job';data=read(folder/'scene-runtime.json')
    assert len(data['actors'])==2 and len(data['objects'])==2
    project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep scene worker playback"\n',encoding='utf-8')
    for name in ('godot_scene_clock.gd','godot_scene_clock_audit.gd'):shutil.copyfile(ROOT/'scripts'/name,project/name)
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    assert sha256(engine)==read(engine.parent/'acquisition.json')['executables'][engine.name]
    command=[str(engine),'--headless','--path',str(project),'--fixed-fps','60','--script','godot_scene_clock_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')]
    request=dict(at=now(),cases=[dict(id='two-actors-two-objects',folder=str(folder),frames=data['frames'],metadata_sha256=sha256(folder/'scene-runtime.json'),package_sha256=sha256(folder/'scene-animation.zip'))],controls=[],command=command,engine_sha256=sha256(engine),implementation={p.name:sha256(p) for p in implementation.iterdir()},limits=dict(actor_matrix=1e-4,object_matrix=1e-5),scope='Authored integration fixture: existing actor duplicated at a second placement, crate plus prescribed moving shelf. Real Studio release simulation/export and shared playback; no new generated interaction or quality approval.')
    save(output/'request.json',request);save(output/'pipeline.json',dict(at=now(),status='engine_running'))
    run_engine(command,output/'engine.log',timeout=120)
    passed,checks=verify(request,read(output/'engine-output.json'),output)
    save(output/'pipeline.json',dict(at=now(),status='complete' if passed else 'failed_comparison',passed=passed));print(dict(passed=passed,checks=checks))
    if not passed:raise ValueError('Worker export did not pass playback checks')


if __name__=='__main__':run()
