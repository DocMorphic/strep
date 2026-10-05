"""Model-free, explicit-profile native GLB clip transfer; retain both originals.

This is rotation/root transfer with a measured LINEAR approximation, not a
contact solver, semantic editor, or proof of animation quality.
"""
import argparse
import copy
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits

from action_worker_lock import worker_lock
from gltf_tools import authored_animation, append_accessor, local_matrix, write_glb
from native_support_clock import NativeSupportSampler
from retarget_rig import resolve_profile, calibration, transfer
from rig_asset import RigAsset
from strep import read, save, sha256, now

METHODS = ('native_rig_transfer.py', 'retarget_rig.py',
           'rig_asset.py', 'gltf_tools.py', 'rig_clip_import.py',
           'native_support_clock.py', 'strep.py', 'action_worker_lock.py')
KEY_MATRIX_LIMIT = 1e-5
POSITION_LIMIT_M = 1e-4
ROTATION_LIMIT_RAD = 1e-4
MAX_KEYS = 8192


def prepare(source, source_profile, target, target_profile, animation_index):
    source_mapping, source_offset = resolve_profile(source, source_profile)
    target_mapping, target_offset = resolve_profile(target, target_profile)
    if np.any(source_offset) or source_profile.get('axis_alignment_xyzw'):
        raise ValueError('Source profile must use unmodified reference axes and zero world offset')
    if set(target_mapping) - set(source_mapping):
        raise ValueError('Every requested target role must exist in the source profile')
    if max(len(source.document['nodes']), len(target.document['nodes'])) > 512:
        raise ValueError('Native transfer currently supports at most 512 nodes per rig')
    if type(animation_index) is not int:
        raise ValueError('Explicit integer source animation index required')
    sampler = NativeSupportSampler(source.document, source.binary, animation_index)
    root = source_mapping['Hips']
    root_ancestors = set()
    node = root
    while node >= 0:
        root_ancestors.add(node); node = source.parents[node]
    relevant = set()
    for node in source_mapping.values():
        while node >= 0:
            relevant.add(node); node = source.parents[node]
    for node, path, _, values, mode in sampler.channels:
        if mode != 'LINEAR':
            raise ValueError('Native rig transfer requires LINEAR source channels; STEP/cubic unsupported')
        if node not in relevant:
            raise ValueError('Animated source accessories or unmapped leaf bones are unsupported')
        if path == 'scale' and np.max(np.abs(values - 1)) > 1e-7:
            raise ValueError('Animated source scale is unsupported')
        if path == 'translation' and node not in root_ancestors:
            reference = local_matrix(source.document['nodes'][node])[:3, 3]
            if np.max(np.abs(values - reference)) > 1e-7:
                raise ValueError('Animated non-root local translations/stretch are unsupported')
    names = list(source_mapping)
    skeleton = SimpleNamespace(bone_order_names=names,
        neutral_joints=np.array([source.reference[source_mapping[n], :3, 3] for n in names]))
    _, scale, diagnostics = calibration(target, target_mapping, skeleton,
                                       target_profile.get('axis_alignment_xyzw'))
    offset = (target.reference[target_mapping['Hips'], :3, 3]
              - scale * source.reference[root, :3, 3] + target_offset)
    diagnostics = {**diagnostics,
        'axis_alignment_space': 'Target reference world axes to source reference world axes; premultiplied onto target reference joint rotation',
        'source_rotation_rebase': 'R_source_world(t) @ R_source_reference_world.T',
        'root_policy': 'Target default pelvis plus scaled source world displacement from source default pelvis plus target profile offset; world trajectory axes retained',
        'neutral_policy': 'Align target reference bone directions to source reference directions; this may change the target default pose',
        'source_roles_unused_by_target': sorted(set(source_mapping) - set(target_mapping)),
        'target_unmapped_joints': [n for n in target.joints if n not in target_mapping.values()],
        'helpers': 'Unmapped target nodes retain reference local transforms; no twist distribution'}
    return sampler, source_mapping, target_mapping, skeleton, offset, scale, diagnostics


def evaluate_transfer(source, target, sampler, source_mapping, target_mapping,
                      skeleton, offset, target_profile, times):
    world = np.array([sampler.sample(float(t)) for t in times])
    nodes = [source_mapping[n] for n in skeleton.bone_order_names]
    deltas = world[:, nodes, :3, :3] @ source.reference[nodes, :3, :3].swapaxes(-1, -2)
    motion = dict(root_positions=world[:, source_mapping['Hips'], :3, 3],
                  global_rot_mats=deltas)
    return transfer(target, motion, skeleton, target_mapping, offset,
                    target_profile.get('axis_alignment_xyzw'))[:3]


def clock(sampler, rate):
    if type(rate) is not int or rate not in (60, 120, 240):
        raise ValueError('Sampling rate must be 60, 120 or 240 Hz')
    # All source times already are Float32. Store the dense ticks in Float32
    # before evaluation, avoiding a separate rounded export clock.
    ticks = np.arange(int(np.ceil(sampler.duration * rate)), dtype=float) / rate
    times = np.unique(np.concatenate([ticks.astype('<f4'), np.array([0., sampler.duration], dtype='<f4')]
                                     + [c[2] for c in sampler.channels])).astype('<f4')
    times = times[times <= sampler.duration]
    if len(times) > MAX_KEYS:
        raise ValueError('Transfer key population exceeds the bounded 8192-key limit')
    if float(times[-1]) != sampler.duration or any(not np.isin(c[2], times).all() for c in sampler.channels):
        raise ValueError('Original source keys or exact duration lost')
    return times


def preserves_target(target, decoded, mapping):
    expected_nodes = copy.deepcopy(target.document['nodes'])
    for node in mapping.values():
        entry = expected_nodes[node]
        if 'matrix' in entry:
            local = local_matrix(entry); entry.pop('matrix')
            entry.update(translation=local[:3,3].tolist(), rotation=Rotation.from_matrix(local[:3,:3]).as_quat().tolist(), scale=[1,1,1])
    old, new = target.document, decoded.document
    excluded = {'buffers','bufferViews','accessors','animations','nodes'}
    return (decoded.binary[:len(target.binary)] == target.binary
        and new.get('animations', [])[:len(old.get('animations', []))] == old.get('animations', [])
        and {k:v for k,v in old.items() if k not in excluded} == {k:v for k,v in new.items() if k not in excluded}
        and [{k:v for k,v in b.items() if k!='byteLength'} for b in old['buffers']] == [{k:v for k,v in b.items() if k!='byteLength'} for b in new['buffers']]
        and new['accessors'][:len(old['accessors'])] == old['accessors']
        and new['bufferViews'][:len(old['bufferViews'])] == old['bufferViews']
        and new['nodes'] == expected_nodes
        and np.allclose(decoded.reference,target.reference,atol=1e-12,rtol=0))


def verify(source, target, sampler, decoded, output_index, prepared, target_profile, times):
    _, sm, tm, skeleton, offset, _, _ = prepared
    reader = NativeSupportSampler(decoded.document, decoded.binary, output_index)
    # Quarter, midpoint and three-quarter queries in every stored interval.
    probes = np.sort(np.concatenate([times.astype(float)] +
        [times[:-1].astype(float) + f * np.diff(times.astype(float)) for f in (.25, .5, .75)]))
    key_error = position_error = angle_error = 0.
    for start in range(0, len(probes), 64):
        queries = probes[start:start + 64]
        expected, _, _ = evaluate_transfer(source, target, sampler, sm, tm, skeleton, offset, target_profile, queries)
        actual = np.array([reader.sample(float(t)) for t in queries])
        on_keys = np.isin(queries, times)
        if np.any(on_keys):
            key_error = max(key_error, float(np.abs(actual[on_keys] - expected[on_keys]).max()))
        # Complete target hierarchy, including helpers and ancestors.
        position_error = max(position_error, float(np.linalg.norm(actual[..., :3, 3] - expected[..., :3, 3], axis=-1).max()))
        relative = actual[..., :3, :3] @ expected[..., :3, :3].swapaxes(-1, -2)
        angle_error = max(angle_error, float(Rotation.from_matrix(relative.reshape(-1, 3, 3)).magnitude().max()))
    passed = key_error <= KEY_MATRIX_LIMIT and position_error <= POSITION_LIMIT_M and angle_error <= ROTATION_LIMIT_RAD
    return dict(passed=passed, samples=len(probes), key_samples=len(times), nodes=len(target.document['nodes']),
        maximum_key_matrix_component_error=key_error, key_matrix_limit=KEY_MATRIX_LIMIT,
        maximum_sampled_position_error_m=position_error, position_limit_m=POSITION_LIMIT_M,
        maximum_sampled_rotation_error_rad=angle_error, rotation_limit_rad=ROTATION_LIMIT_RAD,
        continuous_bound_proven=False, query_policy='All stored keys plus quarter/midpoint/three-quarter of every interval')


def export(source_path, source_profile_path, target_path, target_profile_path,
           animation_index, output, rate=120):
    paths = [Path(p).resolve() for p in (source_path, source_profile_path, target_path, target_profile_path)]
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Fresh native rig transfer output required')
    with worker_lock(), threadpool_limits(limits=1):
        hashes = {str(p): sha256(p) for p in paths}
        source, target = RigAsset.load(paths[0]), RigAsset.load(paths[2])
        sp, tp = read(paths[1]), read(paths[3])
        if sp.get('character_sha256') != hashes[str(paths[0])] or tp.get('character_sha256') != hashes[str(paths[2])]:
            raise ValueError('Rig profile character checksum mismatch')
        prepared = prepare(source, sp, target, tp, animation_index)
        sampler, sm, tm, skeleton, offset, scale, diagnostics = prepared
        times = clock(sampler, rate)
        methods = {n: sha256(Path(__file__).parent / n) for n in METHODS}
        output.mkdir(parents=True)
        save(output / 'pipeline.json', dict(status='running', original_selected=True, quality_approved=False))
        try:
            snapshots = ('source.glb', 'source-profile.json', 'target.glb', 'target-profile.json')
            for path, name in zip(paths, snapshots): shutil.copyfile(path, output / name)
            archive = output / 'implementation'; archive.mkdir()
            for name in METHODS: shutil.copyfile(Path(__file__).parent / name, archive / name)
            matrices, translations, rotations = evaluate_transfer(source, target, sampler, sm, tm, skeleton, offset, tp, times)
            document, binary = copy.deepcopy(target.document), bytearray(target.binary)
            animation = authored_animation('Transferred ' + sampler.name)
            time_accessor = append_accessor(document, binary, times, 'SCALAR')
            for node in translations:
                entry = document['nodes'][node]
                if 'matrix' in entry:
                    local = local_matrix(entry); entry.pop('matrix')
                    entry.update(translation=local[:3, 3].tolist(), rotation=Rotation.from_matrix(local[:3, :3]).as_quat().tolist(), scale=[1, 1, 1])
                for path, values, kind in (('translation', translations[node], 'VEC3'), ('rotation', rotations[node], 'VEC4')):
                    acc = append_accessor(document, binary, values, kind)
                    animation['channels'].append(dict(sampler=len(animation['samplers']), target=dict(node=node, path=path)))
                    animation['samplers'].append(dict(input=time_accessor, output=acc, interpolation='LINEAR'))
            output_index = len(document.get('animations', []))
            animation['extras']['strep_native_transfer'] = dict(schema='strep-native-rig-transfer-v1',
                source_sha256=hashes[str(paths[0])], target_sha256=hashes[str(paths[2])],
                source_profile_sha256=hashes[str(paths[1])], target_profile_sha256=hashes[str(paths[3])],
                source_animation_index=animation_index, sampling_rate_hz=rate)
            document.setdefault('animations', []).append(animation)
            write_glb(output / 'character.glb', document, binary)
            decoded = RigAsset.load(output / 'character.glb')
            # Every old accessor/bufferView/animation and payload byte survives.
            preserved = preserves_target(target, decoded, tm)
            if not preserved: raise ValueError('Original target payload/default transforms changed')
            fidelity = verify(source, target, sampler, decoded, output_index, prepared, tp, times)
            root = tm['Hips']
            save(output / 'root-motion.json', dict(space='Target pelvis world transform, Y-up metres; extraction not applied',
                node=root, times_s=times.tolist(), positions_m=matrices[:, root, :3, 3].tolist(),
                rotations_xyzw=Rotation.from_matrix(matrices[:, root, :3, :3]).as_quat().tolist()))
            save(output / 'contacts.json', dict(provenance='No contact annotations inferred or solved during rig transfer', intervals=[]))
            np.savez_compressed(output / 'target-transforms.npz', global_matrices=matrices, times_s=times)
            with np.load(output / 'target-transforms.npz', allow_pickle=False) as stored:
                if not np.array_equal(stored['global_matrices'], matrices) or not np.array_equal(stored['times_s'], times):
                    raise ValueError('Stored transfer transforms changed')
            for path, name in zip(paths, snapshots):
                if sha256(path) != hashes[str(path)] or sha256(output / name) != hashes[str(path)]:
                    raise ValueError('Input or input snapshot changed during transfer')
            for name, digest in methods.items():
                if sha256(Path(__file__).parent / name) != digest or sha256(archive / name) != digest:
                    raise ValueError('Transfer implementation changed during execution')
            report = dict(schema='strep-native-rig-transfer-v1', created_at=now(), status='complete' if fidelity['passed'] else 'failed',
                input_sha256=hashes, input_snapshots_sha256={n:hashes[str(p)] for p,n in zip(paths,snapshots)},
                implementation_sha256=methods, source_animation_index=animation_index,
                output_animation_index=output_index, source_duration_s=sampler.duration, last_key_time_s=float(times[-1]),
                source_mapping=sm, target_mapping=tm, source_skin_joints=len(source.joints), target_skin_joints=len(target.joints),
                sampling_rate_hz=rate, samples=len(times), all_source_keys_retained=True, duration_extension_s=0.,
                scale_from_mean_leg_lengths=scale, combined_root_offset_m=offset.tolist(), calibration=diagnostics,
                fidelity=fidelity, original_target_payload_preserved=preserved, source_bytes_unchanged=True,
                glb_sha256=sha256(output / 'character.glb'), transforms_sha256=sha256(output / 'target-transforms.npz'),
                original_selected=True, quality_approved=False, contact_verified=False, engine_import_verified=False, release_approved=False,
                limitations=['Explicit reviewed mappings and default-node references; reference direction alignment does not solve anatomical twist.',
                    'Target unmapped helpers/fingers stay at reference locals; no helper twist distribution.',
                    'Source non-root translation/stretch, animated accessories, STEP/cubic, scale, morph and compressed data unsupported.',
                    'Finite interpolation probes are not continuous-time bounds or motion-quality/contact/physics evidence.'])
            save(output / 'report.json', report)
            save(output / 'pipeline.json', dict(status=report['status'], fidelity_pass=fidelity['passed'], original_selected=True, quality_approved=False))
            if not fidelity['passed']: raise ValueError('Native transfer interpolation fidelity failed; retain candidate and measured report')
            return report
        except Exception as exc:
            save(output / 'pipeline.json', dict(status='failed', error=str(exc), original_selected=True, quality_approved=False))
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'source-profile', 'target', 'target-profile', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--animation-index', type=int, required=True)
    parser.add_argument('--rate', type=int, choices=(60, 120, 240), default=120)
    args = parser.parse_args()
    print(export(args.source, args.source_profile, args.target, args.target_profile,
                 args.animation_index, args.output, args.rate))
