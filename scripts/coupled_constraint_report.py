"""Locate preserved-limit failures without changing acceptance thresholds."""
import numpy as np
from hand_norm_proposal import validate


def breakdown(sample, labels, frame_count, guide_rows, witness_rows):
    sample=validate(sample)
    if (type(frame_count) is not int or frame_count<3 or not labels or type(guide_rows) is not int or guide_rows<1
            or type(witness_rows) is not int or witness_rows<1 or len(sample['margins'])!=1+guide_rows+witness_rows):
        raise ValueError('Explicit joint/time and scalar group populations required')
    sizes=[(frame_count-order)*len(labels) for order in [1,2,1,2]]
    if len(sample['vectors'])!=sum(sizes)+5:raise ValueError('Complete rate and five palm rows required')
    vector_groups=[];offset=0
    for kind,unit,size in zip(['position_speed','position_acceleration','angular_speed','angular_acceleration','palm_points','palm_normals'],
                             ['m/s','m/s^2','rad/s','rad/s^2','m','unit_vector'],sizes+[3,2]):
        norm=np.linalg.norm(sample['vectors'][offset:offset+size],axis=1);caps=sample['caps'][offset:offset+size]
        margins=(caps-norm)/sample['scales'][offset:offset+size];worst=int(margins.argmin());failed=np.flatnonzero(margins<0)
        row=dict(kind=kind,unit=unit,rows=size,failed_rows=len(failed),failed_indices=failed.tolist(),
            minimum_margin=float(margins.min()),maximum_excess=float((norm-caps).max()),
            worst=dict(row=worst,norm=float(norm[worst]),cap=float(caps[worst]),excess=float(norm[worst]-caps[worst])))
        if len(vector_groups)<4:
            row['worst'].update(sample=worst//len(labels),joint=labels[worst%len(labels)])
        vector_groups.append(row);offset+=size
    scalar_groups=[];offset=0
    for kind,size in zip(['native_arm_edit','arm_guides','old_surface_witnesses'],[1,guide_rows,witness_rows]):
        values=sample['margins'][offset:offset+size];worst=int(values.argmin());failed=np.flatnonzero(values<0)
        scalar_groups.append(dict(kind=kind,rows=size,failed_rows=len(failed),failed_indices=failed.tolist(),minimum_margin=float(values.min()),worst_row=worst))
        offset+=size
    return dict(vector_groups=vector_groups,scalar_groups=scalar_groups,
        passed=not any(r['failed_rows'] for r in vector_groups+scalar_groups),quality_approved=False)
