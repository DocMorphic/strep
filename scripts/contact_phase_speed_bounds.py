"""Necessary travel bounds between constant targets for one mesh's vertices.

These bounds use target geometry and contact tolerances only. They do not set
a realism threshold, measure actual speed, or prove a motion is achievable.
Call separately for each actor; vertex identities must refer to the same mesh.
"""
import math


def transition_bounds(phases, *, contact_error_m):
    if (type(contact_error_m) not in (int, float) or not math.isfinite(contact_error_m)
            or contact_error_m <= 0 or not isinstance(phases, list)):
        raise ValueError('Explicit phase list and finite positive contact tolerance required')
    parsed = []
    for index, phase in enumerate(phases):
        if not isinstance(phase, dict):
            raise ValueError('Complete contact phase records required')
        vertex = phase.get('vertex'); start = phase.get('start_time_s'); end = phase.get('end_time_s')
        target = phase.get('target_m')
        if (type(vertex) is not int or vertex < 0
                or type(start) not in (int, float) or type(end) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(end) or not 0 <= start <= end
                or not isinstance(target, (list, tuple)) or len(target) != 3
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in target)):
            raise ValueError('Finite ordered phase times, vertex identity and three target coordinates required')
        parsed.append((start, end, index, vertex, tuple(target)))
    rows = []
    ordered = sorted(parsed)
    for position, first in enumerate(ordered):
        for second in ordered[position+1:]:
            if first[3] != second[3]:
                continue
            gap = max(0., second[0]-first[1])
            separation = math.dist(first[4], second[4])
            travel = max(0., separation-2*contact_error_m)
            speed = travel/gap if gap else (0. if travel == 0 else None)
            if not math.isfinite(separation) or speed is not None and not math.isfinite(speed):
                raise ValueError('Contact target difference exceeds finite arithmetic range')
            rows.append(dict(first_phase_index=first[2], second_phase_index=second[2], vertex=first[3],
                first_end_time_s=first[1], second_start_time_s=second[0], time_gap_s=gap,
                target_separation_m=separation, minimum_travel_m=travel,
                minimum_average_speed_m_s=speed, simultaneous_target_conflict=bool(gap == 0 and travel > 0)))
    return dict(pairs=rows,contact_error_m=contact_error_m,
        simultaneous_target_conflicts=sum(row['simultaneous_target_conflict'] for row in rows),
        maximum_finite_minimum_average_speed_m_s=max((r['minimum_average_speed_m_s'] for r in rows
            if r['minimum_average_speed_m_s'] is not None),default=0.),
        actual_motion_assessed=False,quality_approved=False,release_approved=False)
