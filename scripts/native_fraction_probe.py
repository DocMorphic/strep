"""Bounded neighboring direction fractions and local stored-key rate probes.

This measures a finite set of points, not storage cells or full clip feasibility.
Original cap provenance and complete native/contact/geometry admission belong to
the caller. No probe modifies the source curves or selects a retained clip.
"""
import numpy as np
from native_condition_ledger import NativeConditionLedger, RATE_METRICS
from native_rate_stage_trace import rate_vector
from cumulative_coupled_contacts import backoff_controls, project_direction


def neighbors(centers, radii, *, subdivisions=8, maximum_probes=256):
    """Enumerate distinct positive fractions inside [0, 1], largest first."""
    if (not isinstance(centers, (list, tuple)) or not 1 <= len(centers) <= 32
            or not isinstance(radii, (list, tuple)) or not 1 <= len(radii) <= 8
            or any(type(v) not in (int, float) or not np.isfinite(v) or not 0 < v <= 1 for v in centers)
            or any(type(v) not in (int, float) or not np.isfinite(v) or not 0 < v <= .01 for v in radii)
            or len(set(centers)) != len(centers) or len(set(radii)) != len(radii)
            or type(subdivisions) is not int or not 1 <= subdivisions <= 32
            or type(maximum_probes) is not int or not 1 <= maximum_probes <= 512):
        raise ValueError('Explicit bounded centers, radii, subdivisions and probe budget required')
    result = sorted({float(center + radius * i / subdivisions)
        for center in centers for radius in radii for i in range(-subdivisions, subdivisions + 1)
        if 0 < center + radius * i / subdivisions <= 1}, reverse=True)
    if len(result) > maximum_probes:
        raise ValueError('Complete neighboring fraction population exceeds the probe budget')
    return result


def local_rates(edits, origin, direction, fractions, row_indices, source_caps, source_tolerances, *,
                trust, maximum_probes=256, maximum_rows=32):
    """Measure complete requested local rate rows at every supplied fraction.

    The caller supplies caps from its bound original archive; these are not
    reconstructed or recalibrated here. Passing every requested row remains
    insufficient to retain a clip. All controlled actors share one direction.
    """
    if (type(trust) not in (int, float) or not np.isfinite(trust) or trust <= 0
            or type(maximum_probes) is not int or not 1 <= maximum_probes <= 512
            or type(maximum_rows) is not int or not 1 <= maximum_rows <= 32
            or not isinstance(fractions, (list, tuple)) or not 1 <= len(fractions) <= maximum_probes
            or any(type(v) not in (int, float) or not np.isfinite(v) or not 0 < v <= 1 for v in fractions)
            or len(set(fractions)) != len(fractions)
            or not isinstance(row_indices, (list, tuple)) or not 1 <= len(row_indices) <= maximum_rows
            or any(type(v) is not int for v in row_indices) or len(set(row_indices)) != len(row_indices)
            or not isinstance(source_caps, (list, tuple)) or len(source_caps) != len(row_indices)
            or not isinstance(source_tolerances, (list, tuple)) or len(source_tolerances) != len(row_indices)
            or any(type(v) not in (int, float) or not np.isfinite(v) or v < 0
                   for v in (*source_caps, *source_tolerances))):
        raise ValueError('Complete finite bounded fractions, rate rows, original caps and tolerances required')
    origin = edits.controls(origin).copy(); direction = edits.controls(direction).copy()
    if (np.any(origin < edits.lower) or np.any(origin > edits.upper) or not np.any(direction != 0)
            or np.max(abs(direction)) > trust):
        raise ValueError('Source-box origin and nonzero direction within the exact trust bound required')
    ledger = NativeConditionLedger(edits.scene, edits)
    identities = [ledger.locate(index) for index in row_indices]
    if any(row['kind'] not in {name for name, _, _ in RATE_METRICS} for row in identities):
        raise ValueError('Only edited-actor native joint rate rows can enter this local probe')
    projected, _ = project_direction(origin, direction, edits.lower, edits.upper, trust)
    if not np.array_equal(projected, direction):
        raise ValueError('Supply the existing exact projected direction rather than an outside-box proposal')
    controls = [backoff_controls(origin, direction, edits.lower, edits.upper, trust, fraction) for fraction in fractions]
    if any(np.any(value < edits.lower) or np.any(value > edits.upper)
           or np.max(abs(value - origin)) > fraction * trust for value, fraction in zip(controls, fractions)):
        raise ValueError('Every requested fraction must fit original boxes and the exact trust bound')
    interval = float(ledger.uniform[1] - ledger.uniform[0])
    edits.scene.check_inputs()
    probes = []
    for fraction, value in zip(fractions, controls):
        measured = []; worlds = {}
        for identity, cap, tolerance in zip(identities, source_caps, source_tolerances):
            times = np.array(identity['sample_times_s'])
            key = identity['actor'], tuple(times)
            if key not in worlds:
                worlds[key] = edits.worlds(identity['actor'], value, times, quantized=True)
            vector = rate_vector(worlds[key][:, identity['node']], times, identity['kind'], interval_s=interval)
            norm = float(np.linalg.norm(vector))
            with np.errstate(over='ignore', invalid='ignore'):
                residual = (norm - cap - tolerance) / max(cap, .001)
            if not np.isfinite(residual): raise ValueError('Nonfinite local native rate residual')
            measured.append(dict(row_index=identity['row_index'], vector=vector.tolist(), norm=norm,
                residual=residual, local_row_pass=bool(residual <= 0)))
        probes.append(dict(fraction=float(fraction), controls=value.tolist(), rows=measured,
            all_requested_local_rows_pass=all(row['local_row_pass'] for row in measured)))
    edits.scene.check_inputs()
    return dict(schema='strep-native-fraction-rate-probes-v1', fractions=list(fractions),
        origin_controls=origin.tolist(), direction_controls=direction.tolist(), trust=float(trust),
        rows=identities, source_caps=list(source_caps), source_tolerances=list(source_tolerances),
        source_interval_s=interval, source_actors_sha256=dict(edits.scene.inputs),
        maximum_probes=maximum_probes, maximum_rows=maximum_rows, probes=probes,
        exact_fraction_scaled_trust_box=True, direction_projection_required_unchanged=True,
        rotation_storage_policy=edits.rotation_storage_policy, native_keys_quantized=True,
        source_cap_provenance_checked=False, source_caps_reconstructed=False,
        actual_exports_decoded=False, full_native_conditions_checked=False,
        full_contact_or_geometry_checked=False, quantization_cells_proved=False,
        exhaustive_feasibility_proved=False, retained_clip_selected=False,
        quality_approved=False, release_approved=False)
