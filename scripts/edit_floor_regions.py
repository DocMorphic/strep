"""Localize finite-frame floor screens; source defects are not edit defects."""
import numpy as np


def floor_depths(rig, worlds, *, floor_y_m=0.):
    """Measure the complete loaded rig surface at explicitly supplied poses."""
    if type(floor_y_m) not in (int,float) or not np.isfinite(floor_y_m):
        raise ValueError('Explicit finite horizontal floor height required')
    worlds=np.asarray(worlds,float)
    if worlds.ndim!=4 or not len(worlds) or worlds.shape[-2:]!=(4,4) or not np.isfinite(worlds).all():
        raise ValueError('Complete finite pose matrices required')
    depths=[]
    for world in worlds:
        points=np.asarray(rig.vertices(world),float)
        if points.ndim!=2 or points.shape[1]!=3 or not len(points) or not np.isfinite(points).all():
            raise ValueError('Complete finite loaded surface vertices required')
        depths.append(max(0.,float(floor_y_m-points[:,1].min())))
    return np.asarray(depths)


def localize(source_depths, output_depths, edit_weights, times_s, *, limit_m):
    """Use actual edit weights, including protected boundary samples."""
    source,output,weights,times=(np.asarray(v,float) for v in (source_depths,output_depths,edit_weights,times_s))
    if (any(v.ndim!=1 for v in (source,output,weights,times)) or not len(source)
            or any(v.shape!=source.shape for v in (output,weights,times))
            or any(not np.isfinite(v).all() for v in (source,output,weights,times))
            or np.any(source<0) or np.any(output<0) or np.any((weights<0)|(weights>1))
            or times[0]<0 or np.any(np.diff(times)<=0)):
        raise ValueError('Aligned finite depths, weights and increasing times required')
    if type(limit_m) not in (int,float) or not np.isfinite(limit_m) or limit_m<0:
        raise ValueError('Explicit finite nonnegative floor screen limit required')
    protected=weights==0;edited=~protected;source_bad=source>limit_m;output_bad=output>limit_m
    def region(mask):
        ids=np.flatnonzero(mask)
        return dict(frames=ids.tolist(),times_s=times[ids].tolist(),count=len(ids),
                    source_maximum_depth_m=float(source[ids].max()) if len(ids) else None,
                    output_maximum_depth_m=float(output[ids].max()) if len(ids) else None,
                    source_failed_frames=ids[source_bad[ids]].tolist(),
                    output_failed_frames=ids[output_bad[ids]].tolist())
    return dict(schema='strep-edit-floor-regions-v1',limit_m=float(limit_m),protected=region(protected),edited=region(edited),
                preexisting_protected_failures=np.flatnonzero(protected & source_bad).tolist(),
                newly_failed_edited_frames=np.flatnonzero(edited & ~source_bad & output_bad).tolist(),
                recovered_edited_frames=np.flatnonzero(edited & source_bad & ~output_bad).tolist(),
                maximum_protected_depth_change_m=float(abs(output[protected]-source[protected]).max()) if protected.any() else None,
                floor_screen_pass=bool(not output_bad.any()),quality_approved=False,release_approved=False,
                scope='Finite-frame screen at a caller-declared horizontal plane. Zero edit weight includes protected endpoint neighborhoods. Preexisting protected violations cannot be fixed solely by this edit envelope. No support intent, contact, continuous collision, dynamics, causality or human-quality approval.')
