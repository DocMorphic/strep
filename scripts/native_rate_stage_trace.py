"""Bounded rate-stage diagnostics for existing serialized native curves.

Compare continuous edits, stored-key proxies and actual decoding at one native
rate row. This is neither a solver nor a full-motion/geometry acceptance check.
"""
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from native_condition_ledger import NativeConditionLedger, RATE_METRICS
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from strep import sha256


def rate_vector(poses, times, kind, *, interval_s):
    """Independent two/three-pose rate arithmetic in the native convention."""
    poses = np.asarray(poses, float)
    times = np.asarray(times, float)
    definitions = {name: order for name, order, _ in RATE_METRICS}
    if kind not in definitions:
        raise ValueError('A native joint linear/angular rate metric is required')
    order = definitions[kind]
    if (type(interval_s) not in (int, float) or not np.isfinite(interval_s) or interval_s <= 0
            or poses.shape != (order + 1, 4, 4) or times.shape != (order + 1,)
            or not np.isfinite(poses).all() or not np.isfinite(times).all()
            or times[0] < 0 or np.any(np.diff(times) <= 0)
            or not np.allclose(np.diff(times), interval_s, atol=1e-12, rtol=0)
            or not np.allclose(poses[:, 3], [0, 0, 0, 1], atol=1e-12, rtol=0)):
        raise ValueError('Matching finite homogeneous poses and uniform rate support required')
    rotation = poses[:, :3, :3]
    if (not np.allclose(rotation @ rotation.transpose(0, 2, 1), np.eye(3), atol=1e-6, rtol=0)
            or not np.allclose(np.linalg.det(rotation), 1, atol=1e-6, rtol=0)):
        raise ValueError('Proper native joint rotations required')
    # Match the original source clock's interval, not a newly subtracted local
    # timestamp difference whose last bits can change a tight native decision.
    dt = float(interval_s)
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        if kind == 'joint_linear_velocity':
            result = np.diff(poses[:, :3, 3], axis=0)[0] / dt
        elif kind == 'joint_linear_acceleration':
            result = np.diff(poses[:, :3, 3], n=2, axis=0)[0] / dt**2
        else:
            relative = rotation[1:] @ rotation[:-1].transpose(0, 2, 1)
            angle = Rotation.from_matrix(relative).as_rotvec()
            if np.any(np.linalg.norm(angle, axis=1) >= np.pi - 1e-6):
                raise ValueError('Ambiguous native angular step')
            velocity = angle / dt
            result = velocity[0] if order == 1 else np.diff(velocity, axis=0)[0] / dt
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite native rate arithmetic')
    return result


def trace(edits, controls, row_index, candidate, *, source_cap, source_tolerance):
    """Check candidate/key identity before measuring one explicitly selected row.

    Caps are supplied by the caller's original source-rate archive. This trace
    does not reconstruct/recalibrate that archive or approve its provenance.
    The caller binds the archive; full native audits remain authoritative.
    """
    if (any(type(v) not in (int, float) or not np.isfinite(v) or v < 0
            for v in (source_cap, source_tolerance))):
        raise ValueError('Finite nonnegative original source cap and tolerance required')
    controls = edits.controls(controls)
    ledger = NativeConditionLedger(edits.scene, edits)
    identity = ledger.locate(row_index)
    if identity['kind'] not in {kind for kind, _, _ in RATE_METRICS}:
        raise ValueError('An edited actor native joint rate row is required')
    actor = identity['actor']
    if np.any(controls < edits.lower) or np.any(controls > edits.upper):
        raise ValueError('Trace controls must fit original source-relative boxes')
    edits.scene.check_inputs()
    candidate = Path(candidate).resolve()
    digest = sha256(candidate)
    source = edits.actors[actor]['source']
    audit = edits.audit(actor, candidate, source['animation_index'])
    if not audit['passed']:
        raise ValueError('Serialized candidate must preserve the declared edit contract')
    rig = RigAsset.load(candidate)
    reader = NativeSupportSampler(rig.document, rig.binary, source['animation_index'])
    expected = edits.values(actor, controls, quantized=True)
    matched = set()
    for node, path, clock, values, mode in reader.channels:
        key = node, path
        if key in expected:
            if not np.array_equal(values, expected[key]):
                raise ValueError('Serialized native keys do not match the supplied controls')
            matched.add(key)
    if matched != set(expected):
        raise ValueError('Complete controlled native channels required')
    times = np.asarray(identity['sample_times_s'])
    node = identity['node']
    # Only this row's two or three times are queried. No full-clock crop can pass
    # a clip: the return value explicitly identifies this diagnostic scope.
    worlds = dict(continuous=edits.worlds(actor, controls, times, quantized=False),
        quantized_proxy=edits.worlds(actor, controls, times, quantized=True),
        decoded=np.array([reader.sample(float(t)) for t in times]))
    stages = {}
    for label, world in worlds.items():
        vector = rate_vector(world[:, node], times, identity['kind'],
                             interval_s=float(ledger.uniform[1] - ledger.uniform[0]))
        with np.errstate(over='ignore', invalid='ignore'):
            norm = float(np.linalg.norm(vector))
            excess = norm - source_cap - source_tolerance
            residual = excess / max(source_cap, .001)
        if not np.isfinite([norm, excess, residual]).all():
            raise ValueError('Nonfinite native cap/excess arithmetic')
        stages[label] = dict(vector=vector.tolist(), norm=norm, residual=residual,
            excess_above_cap_and_existing_tolerance=excess, local_row_pass=bool(residual <= 0))
    differences = {}
    for label in ('continuous', 'quantized_proxy'):
        position = np.linalg.norm(worlds[label][:, :, :3, 3] - worlds['decoded'][:, :, :3, 3], axis=2)
        basis = np.abs(worlds[label][:, :, :3, :3] - worlds['decoded'][:, :, :3, :3])
        differences[label + '_vs_decoded'] = dict(
            maximum_joint_position_difference_m=float(position.max()),
            maximum_basis_component_difference=float(basis.max()),
            maximum_rate_vector_component_difference=float(np.max(np.abs(
                np.asarray(stages[label]['vector']) - stages['decoded']['vector']))),
            rate_unit=identity['unit'])
    edits.scene.check_inputs()
    if sha256(candidate) != digest:
        raise ValueError('Serialized candidate changed during the trace')
    return dict(schema='strep-native-rate-stage-trace-v1', row=identity,
        candidate_sha256=digest, controls=controls.tolist(), source_cap=float(source_cap),
        source_tolerance=float(source_tolerance), source_caps_reconstructed=False,
        source_cap_provenance_checked=False, rotation_storage_policy=edits.rotation_storage_policy,
        all_controlled_native_keys_matched=True, static_and_unselected_payloads_preserved=True,
        sample_count=len(times), source_interval_s=float(ledger.uniform[1] - ledger.uniform[0]),
        stages=stages, differences=differences,
        source_actors_sha256=dict(edits.scene.inputs),
        full_motion_audited=False, derivative_columns_recomputed=False,
        contact_checked=False, geometry_checked=False, engine_import_checked=False,
        quality_approved=False, release_approved=False)
