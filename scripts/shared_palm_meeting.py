"""Explicit paired surface-anchor target; contact scoring is not collision approval."""
import numpy as np


def geometry(centers, normals):
    centers=np.asarray(centers,float);normals=np.asarray(normals,float)
    if (centers.shape!=(2,3) or normals.shape!=(2,3) or not np.isfinite(centers).all()
            or not np.isfinite(normals).all() or not np.allclose(np.linalg.norm(normals,axis=1),1.,rtol=0,atol=1e-8)):
        raise ValueError('Two finite surface anchors and unit outward normals required')
    return centers,normals


def target(centers, normals, separation_m=.001):
    centers,normals=geometry(centers,normals)
    if not np.isfinite(separation_m) or not 0<=separation_m<=.002:
        raise ValueError('Explicit separation from zero to two millimetres required')
    normal=normals[0]-normals[1];length=np.linalg.norm(normal)
    if length<1e-8:raise ValueError('Opposing palm orientation is ambiguous')
    normal/=length;midpoint=centers.mean(axis=0)
    return dict(midpoint_m=midpoint.tolist(),separation_m=float(separation_m),
        centers_m=np.stack([midpoint-normal*separation_m/2,midpoint+normal*separation_m/2]).tolist(),
        normals=np.stack([normal,-normal]).tolist(),anchor_tolerance_m=.0005,
        maximum_gap_m=.002,normal_tolerance_degrees=20.,new_authored_condition=True)


def measure(centers, normals, specification):
    centers,normals=geometry(centers,normals)
    desired,desired_normals=geometry(specification['centers_m'],specification['normals'])
    error=np.linalg.norm(centers-desired,axis=1);gap=float(np.linalg.norm(centers[0]-centers[1]))
    angles=np.rad2deg(np.arccos(np.clip(np.sum(normals*desired_normals,axis=1),-1,1)))
    return dict(anchor_errors_m=error.tolist(),gap_m=gap,normal_errors_degrees=angles.tolist(),
        contact_target_pass=bool(np.all(error<=specification['anchor_tolerance_m']) and gap<=specification['maximum_gap_m']
            and np.all(angles<=specification['normal_tolerance_degrees'])),
        collision_validation_required=True,quality_approved=False)
