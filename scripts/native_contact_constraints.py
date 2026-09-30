"""Full nonlinear proxy constraints for stationary body-contact restoration.

Max reductions retain every underlying inequality, unlike averaged penalties.
Nonsmooth maxima may limit search; final decoded export remains authoritative.
"""
import torch
from export_motion_sampling import joint_trajectory, motion_rates


def residuals(rotations, positions, point, rates, global_rates, floor, body, support, *, with_labels=False):
    values, labels = [], []
    points = point.points(rotations, positions)
    for row, target in zip(point.rows, point.targets):
        selected = points[row['first_frame']*4:row['last_frame']*4+1, point.index[row['vertex_id']]]
        values.append((torch.linalg.vector_norm(selected-target, dim=-1)-point.tolerance)/point.tolerance)
        labels.extend(f"pin/{row['region']}/{row['vertex_id']}/{i/4:g}" for i in range(row['first_frame']*4, row['last_frame']*4+1))
    point_rates = rates.rates(rotations, positions)
    for row, masks, caps, scales in zip(rates.rows, rates.masks, rates.ceilings, rates.scales):
        for kind, rate, mask, cap, scale in zip(['speed', 'acceleration'], point_rates, masks, caps, scales):
            values.append(((rate[mask, row['point']]-cap)/scale).max().reshape(1))
            labels.append(f"point/{row['region']}/{row['vertex_id']}/{row['phase']}/{kind}")
    for kind, rate, cap, scale in zip(['speed', 'acceleration'], motion_rates(joint_trajectory(rotations, positions, global_rates.parents)),
                                global_rates.ceilings, global_rates.scales):
        values.append(((rate-cap)/scale).max().reshape(1))
        labels.append('global/'+kind)
    values.append(((floor.reference-floor.minimum_heights(rotations, positions))/floor.scale_m).max().reshape(1))
    labels.append('floor')
    for name, reference in body.references.items():
        delta = positions-reference
        for kind, measured, limit in zip(['displacement', 'added_speed'], [torch.linalg.vector_norm(delta, dim=-1),
                                   torch.linalg.vector_norm(torch.diff(delta, dim=0)*30, dim=-1)], body.limits):
            values.append(((measured-limit)/limit).max().reshape(1))
            labels.append('body/'+name+'/'+kind)
    vertices = support.skin(rotations, positions)
    for (name, region), (ids, group) in support.groups.items():
        if group.enabled:
            values.append((group.measure(vertices[:, ids])-group.limits)/torch.tensor(group.allowances, dtype=positions.dtype))
            labels.extend('support/'+name+'/'+region+'/'+kind for kind in ['slide', 'gap'])
    result = torch.cat(values)
    return (result, labels) if with_labels else result
