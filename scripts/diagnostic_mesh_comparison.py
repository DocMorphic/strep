"""Full sampled geometry comparison of a rejected clip, never promotion."""
import numpy as np
from sampled_surface_guard import topology, snapshot, compare
from triangle_crossing import audit
from convex_partner_surface import penetration


def run(faces,counts,times,vertices,save,observe=None):
    meshes=topology(faces,counts);times=np.asarray(times,float)
    if times.ndim!=1 or not len(times) or not np.isfinite(times).all() or times[0]<0 or np.any(np.diff(times)<=0):
        raise ValueError('Complete increasing diagnostic clock required')
    snapshots={}
    for label in ['baseline','rejected']:
        rows=[]
        for index,stamp in enumerate(times):
            pair=vertices(label,index)
            if len(pair)!=2 or any(np.asarray(p).shape!=(m['vertices'],3) or not np.isfinite(p).all() for p,m in zip(pair,meshes)):
                raise ValueError('Complete finite posed meshes required')
            row=dict(time_s=float(stamp),surface=audit(pair[0],faces[0],pair[1],faces[1]),
                depths=[penetration(pair[a],pair[b],faces[b]) for a,b in [(0,1),(1,0)]])
            save(f'{label}-geometry-{index:02d}.json',row);rows.append(row)
            if observe:observe(dict(phase='rejected_mesh_diagnostic',subject=label,completed=index+1,total=len(times)))
        snapshots[label]=snapshot(meshes,rows);save(f'{label}-snapshot.json',snapshots[label])
    decision=compare(snapshots['baseline'],snapshots['rejected'])
    result=dict(diagnostic_only=True,mesh_regression=decision,
        pair_time_crossings={label:sum(len(r['proper']) for r in data['samples']) for label,data in snapshots.items()},
        accepted_for_publication=False,quality_approved=False,collision_free_certified=False,selected_for_studio=False)
    save('mesh-comparison.json',result)
    return result
