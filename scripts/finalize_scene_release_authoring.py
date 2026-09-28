"""Retain original failures and publish the independently checked export revision."""
import hashlib
import shutil
import urllib.request
import zipfile
import numpy as np
from strep import ROOT,read,save,sha256,now
from gltf_tools import read_glb
from rig_clip_import import AnimationSampler


def main():
    report=ROOT/'reports/scene-release-authoring-v1'
    job=ROOT/'reports/scene-release-jobs/20260927-052950-518417bb';revised=job/'exports/trs-v1'
    initial=read(ROOT/'reports/godot-scene-release-authoring-v1/verification.json')
    final=read(ROOT/'reports/godot-scene-release-trs-v1/verification.json')
    assert not initial['all_precision_screens_passed'] and final['all_precision_screens_passed']
    differences=[]
    for file in ['input-objects.glb','objects.glb']:
        a,b=read_glb(job/file),read_glb(revised/file);before=AnimationSampler(*a,0);after=AnimationSampler(*b,0)
        error=max(float(np.abs(before.sample(float(np.float32(f/30)))-after.sample(float(np.float32(f/30)))).max()) for f in np.arange(0,179.5,.5))
        assert error==0
        differences.append(dict(file=file,samples=359,max_decoded_matrix_difference=error))
    unchanged=[]
    with zipfile.ZipFile(revised/'scene-animation.zip') as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            assert hashlib.sha256(archive.read(name)).hexdigest()==sha256(revised/name)
            if name not in ['README.txt','objects.glb','input-objects.glb','export-revision.json'] and not name.startswith('export-implementation/'):
                assert sha256(revised/name)==sha256(job/name);unchanged.append(name)
    served=[]
    for file in ['objects.glb','scene-animation.zip']:
        url='http://127.0.0.1:8768/files/'+(revised/file).relative_to(ROOT/'reports').as_posix()
        with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
        assert hashlib.sha256(data).hexdigest()==sha256(revised/file)
        served.append(dict(file=file,sha256=sha256(revised/file),bytes=len(data)))
    result=dict(at=now(),original_engine=initial,revised_engine=final,decoded_comparison=differences,unchanged_files=unchanged,served_revised=served,
        root_cause='Godot 4.7.2 AnimationMixer converts rigid rotations through Euler angles when a full TRS track is absent. Constant unit-scale animation selects the full-transform path; preserve immutable tracks on import.',
        source='https://github.com/godotengine/godot/blob/4.7.2-stable/scene/animation/animation_mixer.cpp#L1833-L1844',
        physics_repeated=False,whole_interaction_approved=False)
    save(report/'export-revision-verification.json',result);save(job/'engine-export-verification.json',result)
    manifest=read(job/'manifest.json')
    for item in manifest['scenes']:
        if item['id']=='candidate':
            item['downloads']=[dict(label='Scene package · ZIP',path='exports/trs-v1/scene-animation.zip'),dict(label='Object GLB',path='exports/trs-v1/objects.glb'),dict(label='Events',path='events.json'),dict(label='Engine audit',path='engine-export-verification.json'),dict(label='Original export · precision failure',path='scene-animation.zip')]
            item['review_note']='Release at frame 121: 3 kg, friction 0.4, bounce 0.2. Revised export passes Godot transform checks with constant scale tracks retained. Floor-only simulation; actors and other boxes are not colliders. Contact/body failures remain; no animator approval.'
    save(job/'manifest.json',manifest)
    save(report/'decision.json',dict(at=now(),status='development_only',studio_release_authoring_implemented=True,
        saved_job=job.relative_to(ROOT).as_posix(),immutable_original_package_sha256=initial['package_sha256'],revised_package_sha256=final['package_sha256'],
        original_engine_precision_passed=False,revised_engine_precision_passed=True,
        release_audit=read(job/'release-audit.json'),independent_animator_reviews=0,cleanup_time_observations=0,release_gates_promoted=[],
        limitations=['Native 77-joint actors and box geometry only in this release tool','Floor collider only; no actor/environment/object collision response','Saved contact windows restrict release timing','Existing grip, body penetration and orientation failures remain','Godot import must retain constant scale tracks','No training, held-out release evaluation or human approval']))
    snapshot=report/'final-implementation';snapshot.mkdir(exist_ok=True)
    names=['scene_release_job.py','scene_object_export.py','object_geometry_mesh.py','object_geometry.py','scene-release-editor.js','scene-viewer.js','scene-object-geometry.js','action_studio_server.py','action-studio.html','run_portable_scene_import.py','godot_scene_import_audit.gd','verify_scene_release_job.py','reexport_scene_release.py','godot_rotation_playback_diagnostic.gd','export_attached_scene.py','finalize_scene_release_authoring.py']
    for name in names:shutil.copyfile(ROOT/'scripts'/name,snapshot/name)
    save(report/'final-implementation.json',dict(at=now(),files={name:sha256(snapshot/name) for name in names}))
    print(dict(published=True,original_retained=True,revised_engine_passed=True))


if __name__=='__main__':main()
