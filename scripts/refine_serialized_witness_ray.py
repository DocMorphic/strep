"""Bounded local replay around a saved coarse-ray result."""
import numpy as np
from scan_serialized_witness_ray import scan


def refine(exact,original,seed,delta,*,coarse_divisions,witness_start,witness_count,divisions=256,observe=None):
    if type(coarse_divisions) is not int or not 8<=coarse_divisions<=1024:
        raise ValueError('Bounded original ray grid required')
    branches=[]
    for sign in [-1,1]:
        def progress(row):
            if observe:observe(dict(row,direction=sign))
        _,report=scan(exact,original,seed,np.asarray(delta)*sign/coarse_divisions,
            witness_start=witness_start,witness_count=witness_count,divisions=divisions,observe=progress)
        branches.append(dict(direction=sign,report=report))
    chosen=max(branches,key=lambda b:b['report']['final']['minimum_margin'])
    report=chosen['report'];point=np.asarray(report['final_point'])
    return (point.copy() if report['numerically_feasible'] else None),dict(method='refined_serialized_witness_ray_v1',
        original=report['original'],seed=report['seed'],final=report['final'],final_point=point.tolist(),
        coarse_divisions=coarse_divisions,divisions=divisions,selected_direction=chosen['direction'],branches=branches,
        numerically_feasible=report['numerically_feasible'],mesh_validation_required=True,accepted_for_publication=False,quality_approved=False)
