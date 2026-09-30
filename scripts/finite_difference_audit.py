"""Measure local finite-difference stability without choosing or accepting a step."""
import numpy as np


def _stats(values):
    values = np.asarray(values, float)
    index = np.unravel_index(np.argmax(np.abs(values)), values.shape)
    return dict(maximum_absolute=float(np.abs(values[index])),
                rms=float(np.sqrt(np.mean(values * values))),
                worst_index=[int(i) for i in index])


def audit(evaluate, point, steps, directions, radii, groups, observe=None):
    """Audit forward/central derivatives in normalized [-1, 1] coordinates.

    Every probe is evaluated, never clipped. Groups partition all output rows;
    their `is_margin` flag enables sign-prediction counts, not acceptance.
    Directional probes are separate from coordinate derivative construction.
    Differences can reflect curvature, nonsmoothness or numerical error; this
    diagnostic cannot distinguish those causes or certify feasibility.
    """
    point = np.asarray(point, float); steps = np.asarray(steps, float)
    directions = np.asarray(directions, float); radii = np.asarray(radii, float)
    if point.ndim != 1 or not point.size or not np.isfinite(point).all():
        raise ValueError('Finite nonempty point required')
    for values in [steps, radii]:
        if values.ndim != 1 or not values.size or not np.isfinite(values).all() or np.any(values <= 0) or np.any(np.diff(values) <= 0):
            raise ValueError('Positive increasing steps and radii required')
    if directions.ndim != 2 or not len(directions) or directions.shape[1] != len(point) or not np.isfinite(directions).all() or np.any(np.max(np.abs(directions), axis=1) == 0):
        raise ValueError('Matching finite nonzero probe directions required')
    if np.any(np.abs(point) + steps[-1] > 1) or np.any(np.abs(point + radii[-1] * directions) > 1):
        raise ValueError('All unmodified probes must lie inside normalized bounds')
    calls = 0; shape = None
    def checked(x):
        nonlocal calls, shape
        value = np.asarray(evaluate(x.copy()), float)
        if value.ndim != 1 or not value.size or not np.isfinite(value).all() or shape is not None and value.shape != shape:
            raise ValueError('Matching nonempty finite output vectors required')
        shape = value.shape; calls += 1
        if observe: observe(calls)
        return value.copy()
    base = checked(point)
    cursor = 0; names = set()
    for group in groups:
        if (not isinstance(group['name'], str) or not group['name'] or group['name'] in names
                or type(group['start']) is not int or type(group['stop']) is not int
                or group['start'] != cursor or group['stop'] <= cursor
                or type(group['is_margin']) is not bool):
            raise ValueError('Unique contiguous output groups required')
        cursor = group['stop']; names.add(group['name'])
    if cursor != len(base): raise ValueError('Groups must partition every output row')
    probes = [(float(radius), i, direction * radius, checked(point + direction * radius))
              for radius in radii for i, direction in enumerate(directions)]
    reports = []; previous = None
    for step in steps:
        forward = np.empty((len(base), len(point))); central = np.empty_like(forward)
        for column in range(len(point)):
            delta = np.zeros_like(point); delta[column] = step
            plus, minus = checked(point + delta), checked(point - delta)
            forward[:, column] = (plus - base) / step
            central[:, column] = (plus - minus) / (2 * step)
        report = dict(step=float(step), groups=[])
        for group in groups:
            region = slice(group['start'], group['stop']); b = base[region]
            entry = dict(**group, minimum_value=float(b.min()),
                         forward_central_difference=_stats(forward[region] - central[region]), predictions=[])
            if previous is not None:
                entry['central_difference_from_previous_step'] = _stats(central[region] - previous[region])
            for radius, index, delta, actual in probes:
                observed = actual[region]; change = observed - b
                for method, jacobian in [('forward', forward), ('central', central)]:
                    predicted = b + jacobian[region] @ delta
                    record = dict(radius=radius, direction=index, method=method,
                                  actual_change=_stats(change), residual=_stats(observed - predicted))
                    if group['is_margin']:
                        record.update(actual_negative_rows=int(np.count_nonzero(observed < 0)),
                                      predicted_negative_rows=int(np.count_nonzero(predicted < 0)),
                                      missed_negative_rows=int(np.count_nonzero((observed < 0) & (predicted >= 0))))
                    entry['predictions'].append(record)
            report['groups'].append(entry)
        reports.append(report); previous = central
    return dict(evaluations=calls, dimensions=len(point), rows=len(base), steps=reports,
                accepted_for_publication=False, quality_approved=False)
