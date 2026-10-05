"""Saved Godot resource proof for a source-bound native rig transfer candidate.

CPU/headless only. This checks editable file/playback fidelity, not contacts,
physics, rendered appearance or animator approval. Original selection stays put.
"""
import argparse
from pathlib import Path
import shutil

import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits

from action_worker_lock import worker_lock
import audit_native_root_runtime as runtime
import native_rig_transfer as bridge
from native_engine_clock import clock_wire
from native_godot_payload import payload
from native_support_clock import NativeSupportSampler
from retarget_rig import resolve_profile
from rig_asset import RigAsset
from scene_prop_bake import engine_run, ENGINE, ENGINE_SHA256
from strep import ROOT, now, read, save, sha256

GDS = ('godot_native_transfer_prepare.gd', 'native_godot_tracks.gd',
       'godot_native_root_audit.gd', 'godot_native_root_adapter.gd',
       'native_godot_preview.gd', 'native_engine_clock.gd')
METHODS = tuple(dict.fromkeys(bridge.METHODS + runtime.METHODS + GDS +
    ('audit_native_rig_transfer.py', 'scene_prop_bake.py', 'process_monitor.py', 'object_release.py')))


def bound_candidate(folder):
    folder = Path(folder).resolve(); report = read(folder / 'report.json')
    if (report.get('schema') != 'strep-native-rig-transfer-v1' or report.get('status') != 'complete'
            or report.get('fidelity', {}).get('passed') is not True
            or report.get('original_selected') is not True
            or sha256(folder / 'character.glb') != report.get('glb_sha256')
            or sha256(folder / 'target-transforms.npz') != report.get('transforms_sha256')):
        raise ValueError('Completed immutable native transfer candidate required')
    names = ('source.glb', 'source-profile.json', 'target.glb', 'target-profile.json')
    if set(report.get('input_snapshots_sha256', {})) != set(names):
        raise ValueError('Complete native transfer input snapshots required')
    for name, digest in report['input_snapshots_sha256'].items():
        if sha256(folder / name) != digest: raise ValueError('Transfer input snapshot changed')
    if set(report.get('implementation_sha256', {})) != set(bridge.METHODS):
        raise ValueError('Complete transfer implementation bindings required')
    for name, digest in report['implementation_sha256'].items():
        if sha256(folder / 'implementation' / name) != digest or sha256(ROOT / 'scripts' / name) != digest:
            raise ValueError('Transfer implementation changed; use a new explicit transfer')
    source, target = RigAsset.load(folder / 'source.glb'), RigAsset.load(folder / 'target.glb')
    sp, tp = read(folder / 'source-profile.json'), read(folder / 'target-profile.json')
    if sp.get('character_sha256') != sha256(folder / 'source.glb') or tp.get('character_sha256') != sha256(folder / 'target.glb'):
        raise ValueError('Snapshot profiles do not bind the original rigs')
    index = report.get('source_animation_index')
    prepared = bridge.prepare(source, sp, target, tp, index)
    times = bridge.clock(prepared[0], report.get('sampling_rate_hz'))
    derived = RigAsset.load(folder / 'character.glb')
    output_index = report.get('output_animation_index')
    if type(output_index) is not int or output_index != len(target.document.get('animations', [])):
        raise ValueError('Appended target animation selection changed')
    mapping, _ = resolve_profile(target, tp)
    if mapping != report.get('target_mapping') or prepared[1] != report.get('source_mapping'):
        raise ValueError('Transfer role mappings changed')
    if len(derived.document.get('animations', [])) != output_index+1 or not bridge.preserves_target(target,derived,mapping):
        raise ValueError('Original target payload changed in the derived candidate')
    metadata=derived.document['animations'][output_index].get('extras',{}).get('strep_native_transfer',{})
    expected=dict(schema='strep-native-rig-transfer-v1',source_sha256=sha256(folder/'source.glb'),target_sha256=sha256(folder/'target.glb'),
        source_profile_sha256=sha256(folder/'source-profile.json'),target_profile_sha256=sha256(folder/'target-profile.json'),
        source_animation_index=index,sampling_rate_hz=report.get('sampling_rate_hz'))
    if metadata!=expected: raise ValueError('Derived transfer recipe changed')
    with np.load(folder / 'target-transforms.npz', allow_pickle=False) as arrays:
        if set(arrays.files) != {'global_matrices','times_s'} or not np.array_equal(arrays['times_s'], times):
            raise ValueError('Transfer stored clock changed')
        saved=arrays['global_matrices']
        if saved.shape!=(len(times),len(target.document['nodes']),4,4) or saved.dtype!=np.dtype('float64') or not np.isfinite(saved).all():
            raise ValueError('Complete finite transfer transform population required')
        sampler=NativeSupportSampler(derived.document,derived.binary,output_index)
        for frame,time in enumerate(times):
            if np.abs(sampler.sample(float(time))-saved[frame]).max()>bridge.KEY_MATRIX_LIMIT:
                raise ValueError('Stored transfer transforms disagree with the exported clip')
    return folder, report, source, target, tp, prepared, times, derived, output_index, mapping['Hips']


def run(transfer_folder, output):
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Fresh native transfer engine audit output required')
    with worker_lock(), threadpool_limits(limits=1):
        folder, report, source, target, tp, prepared, keys, rig, index, root = bound_candidate(transfer_folder)
        if sha256(ENGINE) != ENGINE_SHA256: raise ValueError('Pinned headless engine checksum mismatch')
        input_files = ('report.json','character.glb','target-transforms.npz') + tuple(report['input_snapshots_sha256'])
        bindings = {name:sha256(folder / name) for name in input_files}
        methods = {name:sha256(ROOT / 'scripts' / name) for name in METHODS}
        output.mkdir(parents=True); archive = output / 'implementation'; archive.mkdir(); project = output / 'project'; project.mkdir()
        save(output / 'pipeline.json',dict(status='running', original_selected=True, quality_approved=False))
        try:
            for name in input_files: shutil.copyfile(folder / name, output / name)
            for name in METHODS: shutil.copyfile(ROOT / 'scripts' / name, archive / name)
            for name in GDS: shutil.copyfile(archive / name, project / name)
            (project / 'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep native rig transfer proof"\n',encoding='utf8')
            fidelity = bridge.verify(source,target,prepared[0],rig,index,prepared,tp,keys)
            if not fidelity['passed']: raise ValueError('Transfer fidelity no longer passes independent readback')
            sampler = NativeSupportSampler(rig.document,rig.binary,index)
            dense = np.unique(np.concatenate([keys.astype(float)] +
                [keys[:-1].astype(float) + f*np.diff(keys.astype(float)) for f in (.25,.5,.75)]))
            placement = np.eye(4);placement[:3,:3] = Rotation.from_euler('yxz',[-37,9,13],degrees=True).as_matrix(); placement[:3,3] = [2.,-.3,1.]
            sampler, dense, placement = runtime.validate(rig,index,root,dense,placement)
            save(output / 'native-payload.json',payload(rig,sampler,bindings['character.glb']))
            resource = output / 'animation.res'
            save(output / 'prepare-request.json',dict(glb=str(output / 'character.glb'),animation_index=index,
                payload=str(output / 'native-payload.json'),animation_resource=str(resource)))
            prep = engine_run(project,'res://godot_native_transfer_prepare.gd',output / 'prepare-request.json',
                              output / 'prepare-engine.json',output / 'prepare.log',300)
            if (prep.get('status') != 'complete' or prep.get('resource_sha256') != sha256(resource)
                    or prep.get('selected_animation_index') != index):
                raise ValueError('Actual saved transfer resource preparation differs')
            resource_hash = sha256(resource)
            save(output / 'runtime-request.json',dict(glb=str(output / 'character.glb'),animation_resource=str(resource),
                animation_index=index,root_bone=rig.document['nodes'][root]['name'],clock=clock_wire(dense),placement=placement.tolist()))
            actual = engine_run(project,'res://godot_native_root_audit.gd',output / 'runtime-request.json',
                                output / 'runtime-engine.json',output / 'runtime.log',300)
            result, arrays = runtime.evaluate(rig,sampler,dense,placement,actual)
            np.savez_compressed(output / 'observations.npz',**arrays)
            with np.load(output / 'observations.npz',allow_pickle=False) as stored:
                if set(stored.files)!=set(arrays) or any(stored[n].dtype!=v.dtype or stored[n].tobytes()!=v.tobytes() for n,v in arrays.items()):
                    raise ValueError('Native transfer observations changed during archive readback')
            for name,digest in bindings.items():
                if sha256(folder / name)!=digest or sha256(output / name)!=digest: raise ValueError('Transfer candidate or audit input changed')
            for name,digest in methods.items():
                if sha256(ROOT / 'scripts' / name)!=digest or sha256(archive / name)!=digest: raise ValueError('Audit implementation changed')
            if sha256(ENGINE)!=ENGINE_SHA256 or sha256(resource)!=resource_hash: raise ValueError('Engine or saved native resource changed')
            for name in GDS:
                if sha256(project / name)!=methods[name]: raise ValueError('Executed engine method differs')
            result.update(schema='strep-native-rig-transfer-engine-v1',created_at=now(),status='complete',engine=actual['engine'],
                input_sha256=bindings,implementation_sha256=methods,engine_sha256=ENGINE_SHA256,
                original_selected=True,quality_approved=False,contact_verified=False,physics_verified=False,release_approved=False,
                source_bytes_unchanged=True,arrays_roundtrip_exact=True,transfer_fidelity=fidelity,
                animation_resource_sha256=resource_hash,raw_engine_sha256=sha256(output / 'runtime-engine.json'),
                observations_sha256=sha256(output / 'observations.npz'),
                scope='Finite native transfer keys plus quarter/midpoint/three-quarter clock; whole imported skeleton and CPU skin; saved editable resource and embedded/extracted root playback. No quality/contact/physics/render/loop/transition approval.')
            save(output / 'result.json',result)
            save(output / 'pipeline.json',dict(status='complete',sampled_runtime_conditions_pass=result['sampled_runtime_conditions_pass'],original_selected=True,quality_approved=False))
            return result
        except Exception as exc:
            save(output / 'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False)); raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('transfer');parser.add_argument('output');args=parser.parse_args()
    print(run(args.transfer,args.output))
