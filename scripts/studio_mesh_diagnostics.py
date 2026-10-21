"""Summarize saved correction decisions without loading numerical libraries."""

SCHEMA = 'strep-studio-mesh-diagnostics-v1'
CHECKS = (
    ('source_rows_pass', 'Protected motion', False),
    ('strict_edit_caps_pass', 'Allowed edit size', False),
    ('contact_rows_no_worse', 'Preserving existing contacts', False),
    ('contact_merit_improves', 'Improving contact targets', False),
    ('all_declared_point_contacts_pass', 'Meeting all contact targets', False),
    ('geometry_conditions_pass', 'Meeting all sampled geometry checks', True),
    ('geometry_conditions_no_regression', 'Preserving previously passing geometry checks', True),
    ('geometry_metrics_no_worse', 'Avoiding worse overall geometry measurements', True),
    ('geometry_local_depths_pass', 'Avoiding worse local intersections', True),
    ('self_surface_nonregression_pass', 'Avoiding worse body self-intersections', True),
)


def summarize(rows, expected_probes, expected_accepted):
    if type(expected_probes) is not int or expected_probes < 0 or type(expected_accepted) is not int or expected_accepted < 0:
        raise ValueError('Invalid correction attempt counts')
    if not isinstance(rows, list) or len(rows) != expected_probes:
        raise ValueError('Saved correction attempt count differs')
    accepted = 0
    checks = [dict(key=key, label=label, passed=0, failed=0, not_checked=0, not_recorded=0) for key, label, _ in CHECKS]
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or type(row.get('probe')) is not int or row['probe'] != index or type(row.get('accepted')) is not bool:
            raise ValueError('Invalid saved correction decision')
        accepted += row['accepted']
        geometry = row.get('geometry_evaluated')
        if geometry is not None and type(geometry) is not bool:
            raise ValueError('Invalid saved geometry evaluation status')
        for check, (key, _, needs_geometry) in zip(checks, CHECKS):
            if key in row and type(row[key]) is not bool:
                raise ValueError('Invalid saved correction check')
            if needs_geometry and geometry is False:
                if key in row:
                    raise ValueError('Geometry check recorded for an unevaluated attempt')
                state = 'not_checked'
            elif needs_geometry and geometry is None or key not in row:
                state = 'not_recorded'
            else:
                state = 'passed' if row[key] else 'failed'
            check[state] += 1
    if accepted != expected_accepted:
        raise ValueError('Saved accepted edit count differs')
    return dict(schema=SCHEMA, available=True, attempts=len(rows), accepted=accepted, checks=checks,
                quality_approved=False, release_approved=False)
