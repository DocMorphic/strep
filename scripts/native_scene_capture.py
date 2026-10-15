"""Re-evaluate a sealed actual Godot capture; never manufacture an import.

The original executed scripts remain pinned separately from current Python
measurement methods. A complete scene result is deliberately not required:
the source audit may have stopped after its successful raw engine receipt.
"""
from pathlib import Path
import gc
import numpy as np
from strep import read,sha256
from native_scene_engine import EngineObservations, sample_times, bake_rate


def require(value,message):
    if not value:raise ValueError(message)


def bindings(scene,contacts,policy_path,folder,receipt_sha256):
    folder=Path(folder).resolve();receipt=read(folder/'raw-engine-receipt.json');request=read(folder/'request.json')
    require(sha256(folder/'raw-engine-receipt.json')==receipt_sha256,'Pinned raw engine receipt required')
    require(receipt['returncode']==0,'Successful actual engine capture required')
    require(sha256(folder/'request.json')==receipt['request_sha256'],'Engine request changed')
    require(sha256(folder/'engine-output.json')==receipt['engine_output_sha256'],'Raw engine output changed')
    require(sha256(folder/'engine.log')==receipt['engine_log_sha256'],'Engine log changed')
    require(request['inputs_sha256'].get(str(contacts))==sha256(contacts)
        and request['inputs_sha256'].get(str(policy_path))==sha256(policy_path),'Exact captured contacts and policy required')
    result=dict(request['inputs_sha256'])
    require(all(sha256(p)==h for p,h in result.items()),'Captured input changed')
    require(request['engine_sha256']==receipt['engine_executable_sha256']
        and request['engine_sha256'] in result.values(),'Executed engine binding differs')
    scripts=('godot_native_scene_audit.gd','native_godot_tracks.gd','native_godot_preview.gd','native_engine_clock.gd')
    require(set(receipt['executed_scripts_sha256'])==set(scripts),'Complete executed-script receipt required')
    for name,h in receipt['executed_scripts_sha256'].items():
        executed=folder/'project'/('audit.gd' if name=='godot_native_scene_audit.gd' else name)
        archived=folder/'implementation'/name
        require(sha256(executed)==sha256(archived)==h==request['implementation_sha256'][name],'Executed engine script changed')
        result.update({str(executed):h,str(archived):h})
    require(request['playback_mode']=='native-authoring','Native-authoring capture required')
    require(request['objects']==read(contacts)['objects'],'Captured object request differs')
    require([c['id'] for c in request['cases']]==list(scene.actors),'Complete captured actor population required')
    resources=receipt['animation_resources_sha256'];require(set(resources)==set(scene.actors),'Complete captured resource population required')
    for case in request['cases']:
        actor=scene.actors[case['id']];original=(Path(contacts).parent/read(contacts)['actors'][case['id']]['glb']).resolve()
        require(case['animation_index']==actor['animation_index'] and sha256(case['path'])==sha256(original),'Captured actor selection differs')
        path=Path(case['animation_output']).resolve()
        require(path==folder/(case['id']+'-animation.res') and sha256(path)==resources[case['id']],'Captured animation resource changed')
        result.update({str(path):sha256(path),str(Path(case['path']).resolve()):sha256(case['path'])})
    for name in ('request.json','raw-engine-receipt.json','engine-output.json','engine.log'):result[str(folder/name)]=sha256(folder/name)
    return result


def load(scene,contacts,policy_path,folder,receipt_sha256):
    before=bindings(scene,contacts,policy_path,folder,receipt_sha256);folder=Path(folder)
    request=read(folder/'request.json');_,arrays=scene.evaluate()
    times=sample_times(scene,arrays,read(policy_path),sha256(contacts))
    require(np.array_equal(times,np.asarray(request['sample_times_s'])),'Complete captured clock differs')
    from native_engine_clock import check_clock_wire
    check_clock_wire(request['sample_clock'],times)
    actual=read(folder/'engine-output.json')
    require(bake_rate(actual.get('import_bake_fps',30.),request['playback_mode'])==request['import_bake_fps'],'Captured import bake rate differs')
    observed=EngineObservations(scene,actual,request['cases'],times)
    # Raw frames have been checked and converted to owned numeric observations.
    # Release their Python JSON lists before full-mesh queries begin.
    del actual;gc.collect()
    require(all(sha256(p)==h for p,h in before.items()),'Capture changed during reconstruction')
    return observed
