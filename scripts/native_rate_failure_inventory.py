"""Complete sampled source-rate failure diagnostics, never a motion approval.

Limits describe the supplied source-preservation policy, not human capacities.
The caller binds original populations and obtains saved rates from the actual
decoder. All four metrics for every declared actor and every failed row remain
present. Exceeding an output budget rejects the whole inventory.
"""
import numpy as np

METRICS = ('linear_speed', 'linear_acceleration', 'angular_speed', 'angular_acceleration')
UNITS = ('m/s', 'm/s^2', 'rad/s', 'rad/s^2')
MAXIMUM_ROWS = 2000000
MAXIMUM_RECORDS = 65536
MAXIMUM_BYTES = 64 * 1024**2


def _real(value):
    raw = np.asarray(value)
    if raw.dtype.kind not in 'fiu' or raw.dtype.itemsize > 8 or not np.isfinite(raw).all():
        raise ValueError('Complete finite real arrays required')
    return raw.astype(float, copy=False)


def rate_failure_inventory(groups, actor_names, *, maximum_rows=MAXIMUM_ROWS,
                           maximum_records=MAXIMUM_RECORDS,
                           maximum_array_bytes=MAXIMUM_BYTES):
    for value, limit in [(maximum_rows, MAXIMUM_ROWS), (maximum_records, MAXIMUM_RECORDS),
                         (maximum_array_bytes, MAXIMUM_BYTES)]:
        if type(value) is not int or not 1 <= value <= limit:
            raise ValueError('Explicit bounded complete inventory budgets required')
    if (not isinstance(actor_names, (list, tuple)) or not 1 <= len(actor_names) <= 64
            or any(type(n) is not str or not 1 <= len(n) <= 128 for n in actor_names)
            or len(set(actor_names)) != len(actor_names)):
        raise ValueError('Explicit distinct declared actor names required')
    if not isinstance(groups, (list, tuple)) or len(groups) != 4 * len(actor_names):
        raise ValueError('All four source metrics for every declared actor required')
    prepared = []; identities = set(); actor_layout = {}; previous_end = 0
    total_rows = 0; input_bytes = 0; records = 0; joint_groups = 0
    for group in groups:
        fields = {'actor', 'metric', 'first_row', 'times_s', 'joint_nodes', 'joint_names',
                  'caps', 'tolerance', 'raw_margins', 'saved_margins', 'saved_rates'}
        if type(group) is not dict or set(group) != fields:
            raise ValueError('Explicit complete source group fields required')
        actor = group['actor']; metric = group['metric']; first = group['first_row']
        if (type(actor) is not str or type(metric) is not str or actor not in actor_names
                or metric not in METRICS or (actor, metric) in identities):
            raise ValueError('Every distinct declared actor/metric required')
        identities.add((actor, metric)); index = METRICS.index(metric)
        order = 2 if index in (1, 3) else 1
        caps = np.asarray(group['caps']); raw = np.asarray(group['raw_margins'])
        saved = np.asarray(group['saved_margins']); rates = np.asarray(group['saved_rates'])
        times = np.asarray(group['times_s']); nodes = np.asarray(group['joint_nodes'])
        names = group['joint_names']; tolerance = group['tolerance']
        if (caps.ndim != 2 or not 1 <= caps.shape[0] <= 20000 or not 1 <= caps.shape[1] <= 512
                or any(a.shape != caps.shape for a in (raw, saved, rates))
                or raw.dtype != np.dtype(float) or saved.dtype != np.dtype(float)
                or times.shape != (caps.shape[0] + order,) or nodes.shape != (caps.shape[1],)
                or nodes.dtype.kind not in 'iu' or nodes.dtype.itemsize > 8
                or np.any(nodes < 0) or len(np.unique(nodes)) != len(nodes)
                or not isinstance(names, (list, tuple)) or len(names) != len(nodes)
                or any(type(n) is not str or not 1 <= len(n) <= 256 for n in names)):
            raise ValueError('Complete aligned rate/time/joint populations required')
        count = caps.size
        if (type(first) is not int or first < previous_end or first + count > MAXIMUM_ROWS
                or type(tolerance) not in (int, float) or not np.isfinite(tolerance)
                or not 0 <= tolerance <= 1):
            raise ValueError('Ordered nonoverlapping source rows and original tolerance required')
        previous_end = first + count; total_rows += count; joint_groups += len(nodes)
        input_bytes += 8 * (caps.size + raw.size + saved.size + rates.size + times.size + nodes.size)
        if total_rows > maximum_rows or 3 * input_bytes + 5 * total_rows > maximum_array_bytes:
            raise ValueError('Complete input/workspace exceeds budget; no rows truncated')
        caps, raw, saved, rates, times = [_real(a) for a in (caps, raw, saved, rates, times)]
        if (np.any(caps < 0) or np.any(caps > 1e9) or np.any(rates < 0)
                or np.any(np.diff(times) <= 0) or times[0] < 0
                or not np.allclose(np.diff(times), times[1] - times[0], atol=1e-12, rtol=0)):
            raise ValueError('Original nonnegative caps/rates and increasing clock required')
        # Retain the exact arithmetic used by the existing world evaluator.
        canonical = -((rates - caps - tolerance) / np.maximum(caps, .001))
        if canonical.tobytes() != saved.tobytes():
            raise ValueError('Saved rates must reproduce every original canonical margin byte')
        layout = (times.tobytes(), nodes.tobytes(), tuple(names))
        if actor in actor_layout and actor_layout[actor] != layout:
            raise ValueError('All actor metrics must retain identical clocks and joint identities')
        actor_layout[actor] = layout
        failed = (raw < 0) | (saved < 0); records += int(np.count_nonzero(failed))
        prepared.append((group, caps, raw, saved, rates, times, nodes, failed))
    if identities != {(a, m) for a in actor_names for m in METRICS}:
        raise ValueError('No declared actor/metric may be omitted')
    estimated = 3 * input_bytes + 5 * total_rows + 4096 * records + 1024 * joint_groups
    if records > maximum_records or estimated > maximum_array_bytes:
        raise ValueError('Complete failure records exceed budget; no failure selection allowed')
    failures = []; summaries = []; joint_summaries = []
    for group, caps, raw, saved, rates, times, nodes, failed in prepared:
        actor = group['actor']; metric = group['metric']; index = METRICS.index(metric)
        order = 2 if index in (1, 3) else 1; zero = caps == 0
        raw_bad = raw < 0; saved_bad = saved < 0
        summary = dict(actor=actor, metric=metric, units=UNITS[index], first_row=group['first_row'],
            rows=caps.size, joints=len(nodes), stencils=len(caps), raw_failed=int(raw_bad.sum()),
            saved_failed=int(saved_bad.sum()), union_failed=int(failed.sum()), both_failed=int((raw_bad & saved_bad).sum()),
            zero_cap_rows=int(zero.sum()), zero_cap_failed=int((zero & failed).sum()),
            positive_cap_failed=int((~zero & failed).sum()),
            maximum_saved_excess=float(max(0., np.max(rates - caps - group['tolerance']))),
            maximum_raw_normalized_violation=float(max(0., -raw.min())),
            maximum_saved_normalized_violation=float(max(0., -saved.min())))
        summaries.append(summary)
        for j, node in enumerate(nodes):
            joint_summaries.append(dict(actor=actor, metric=metric, units=UNITS[index], joint_node=int(node),
                joint_name=group['joint_names'][j], rows=len(caps), raw_failed=int(raw_bad[:, j].sum()),
                saved_failed=int(saved_bad[:, j].sum()), union_failed=int(failed[:, j].sum()),
                zero_cap_failed=int((zero[:, j] & failed[:, j]).sum()),
                maximum_saved_excess=float(max(0., np.max(rates[:, j] - caps[:, j] - group['tolerance'])))))
        for i, j in np.argwhere(failed):
            failures.append(dict(row=group['first_row'] + int(i) * len(nodes) + int(j), actor=actor,
                metric=metric, units=UNITS[index], joint_node=int(nodes[j]), joint_name=group['joint_names'][j],
                stencil_start=int(i), times_s=times[i:i + order + 1].tolist(),
                original_cap=float(caps[i, j]), source_tolerance=float(group['tolerance']),
                saved_measured_rate=float(rates[i, j]), saved_signed_excess=float(rates[i, j] - caps[i, j] - group['tolerance']),
                raw_margin=float(raw[i, j]), saved_margin=float(saved[i, j]),
                fails_raw=bool(raw_bad[i, j]), fails_saved=bool(saved_bad[i, j]),
                original_cap_exactly_zero=bool(zero[i, j])))
    assert len(failures) == records and len({f['row'] for f in failures}) == records
    return dict(failures=failures, groups=summaries, joint_groups=joint_summaries,
        report=dict(schema='strep-native-rate-failure-inventory-v1', declared_actors=list(actor_names),
            complete_groups=len(groups), complete_rows=total_rows, failure_records=records,
            raw_failed=sum(g['raw_failed'] for g in summaries), saved_failed=sum(g['saved_failed'] for g in summaries),
            both_failed=sum(g['both_failed'] for g in summaries),
            zero_cap_failed=sum(g['zero_cap_failed'] for g in summaries),
            positive_cap_failed=sum(g['positive_cap_failed'] for g in summaries),
            all_declared_populations_retained=True, all_failure_records_retained=True,
            saved_canonical_margins_byte_identical=True, estimated_working_and_record_bytes=estimated,
            maximum_array_bytes=maximum_array_bytes, maximum_failure_records=maximum_records,
            physical_margin_tolerance_added=0., optimizer_called=False, quality_approved=False, release_approved=False,
            scope='All four supplied source-rate populations per declared actor. Saved physical rates reproduce original margins exactly; raw margins are reported, not claimed as fresh raw-rate measurements. Exact-zero caps are distinguished without a near-zero cutoff. Source preservation limits are not anatomy/style/strength calibration. No infeasibility, repaired motion, continuous-time, geometry, engine or human certificate.'))
