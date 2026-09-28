"""Conservative LBS vertex displacement bounds for bounded local joint edits."""
import numpy as np


def skin_displacement_bound(indices,weights,local_points,parents,bone_lengths,rotation_distance_bounds):
    indices=np.asarray(indices);weights=np.asarray(weights);local_points=np.asarray(local_points);parents=np.asarray(parents);lengths=np.asarray(bone_lengths);radii=np.asarray(rotation_distance_bounds)
    if indices.shape!=weights.shape or local_points.shape!=(*indices.shape,3):raise ValueError('Skin array shape mismatch')
    if len(parents)!=len(lengths) or len(parents)!=len(radii) or np.any(indices<0) or np.any(indices>=len(parents)):raise ValueError('Invalid bone indices')
    if not all(np.isfinite(x).all() for x in [weights,local_points,lengths,radii]) or np.any(weights<0) or np.any(lengths<0) or np.any(radii<0) or np.any(radii>np.pi):raise ValueError('Invalid bound data')
    paths=np.full((len(parents),len(parents)),-1.)
    for k in range(len(parents)):
        j=k;distance=0.
        while j>=0:
            paths[j,k]=distance
            parent=parents[j]
            if parent>=j:raise ValueError('Parents must precede children')
            distance+=lengths[j];j=parent
    qnorm=np.linalg.norm(local_points,axis=-1);result=np.zeros(indices.shape[0])
    for j,angle in enumerate(radii):
        if angle==0:continue
        path=paths[j,indices];lever=np.where(path>=0,path+qnorm,0.)
        result+=np.sum(weights*lever,axis=1)*(2*np.sin(angle/2))
    return result
