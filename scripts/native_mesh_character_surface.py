"""Rebuilt actor/prop triangle guidance; full decoded meshes decide acceptance."""
import numpy as np
from scipy import sparse
from native_scene_geometry import faces_for
from native_scene_norms import NormRows
from native_surface_lift import lift
from native_triangle_pair_projection import choose_directions


def collect(scene,policy,report,bank,*,floor_bank=None):
    """Retain all observed actor/prop surface identities, including failed trials."""
    scene.check_inputs();times,_,_=scene._clock(dict(policy,mesh_scene_sha256=scene._manifest_sha256))
    if (report['inputs_sha256']!=scene.inputs or report['complete_clock_s']!=times.tolist()
        or report['times_s']!=times.tolist() or report['sample_indices']!=list(range(len(times)))
        or not report['all_policy_samples_evaluated'] or len(report['samples'])!=len(times)
        or report['limits']!=policy['limits']):raise ValueError('Complete bound geometry required for surface guidance')
    actor_faces={name:faces_for(a['rig'])[0] for name,a in scene._scene.actors.items()}
    prop_faces={name:p['asset'].faces for name,p in scene._props.items()}
    if report['actor_faces']!={n:len(f) for n,f in actor_faces.items()} or report['prop_faces']!={n:len(f) for n,f in prop_faces.items()}:
        raise ValueError('Original complete topology required')
    additions={};observed=0;floor_additions={}
    for index,row in enumerate(report['samples']):
        if row['index']!=index or row['time_s']!=float(times[index]):raise ValueError('Ordered original geometry times required')
        seen=set()
        for pair in row['mesh_pairs']:
            if pair['left'][0]!='actor' or pair['right'][0]!='prop':continue
            actor,prop=pair['left'][1],pair['right'][1]
            if (actor,prop) in seen:raise ValueError('Duplicate actor/prop condition')
            seen.add((actor,prop))
            for record in pair['surface']['records']:
                a,b=record['left_triangle'],record['right_triangle'];observed+=1
                if any(type(i) is not int or not 0<=i<len(f) for i,f in [(a,actor_faces[actor]),(b,prop_faces[prop])]):
                    raise ValueError('Original triangle identity required')
                key=(float(times[index]),actor,prop,a,b)
                additions[key]=dict(time_s=key[0],actor=actor,prop=prop,actor_triangle=a,prop_triangle=b)
        if seen!={(a,p) for a in actor_faces for p in prop_faces}:raise ValueError('Complete actor/prop population required')
        if floor_bank is not None:
            seen=set()
            for measured in row['base_scene']['world_planes']:
                actor,plane,vertex=measured['actor'],measured['plane'],measured['peak_vertex']
                if (actor,plane) in seen or actor not in actor_faces or plane not in policy['planes']:
                    raise ValueError('Original distinct floor condition required')
                seen.add((actor,plane))
                if type(vertex) is not int or vertex not in actor_faces[actor]:raise ValueError('Original floor vertex required')
                key=(float(times[index]),actor,plane,vertex)
                floor_additions[key]=dict(time_s=key[0],actor=actor,plane=plane,vertex=vertex)
            if seen!={(a,p) for a in actor_faces for p in policy['planes']}:raise ValueError('Complete floor population required')
    if len(set(bank)|set(additions))*9>500000:raise ValueError('Complete surface guidance exceeds row budget; no records dropped')
    if floor_bank is not None and len(set(floor_bank)|set(floor_additions))>100000:
        raise ValueError('Complete retained floor population exceeds budget; no records dropped')
    scene.check_inputs();before=len(bank);bank.update(additions)
    result=dict(observed_surface_records=observed,new_triangle_time_pairs=len(bank)-before,retained_triangle_time_pairs=len(bank))
    if floor_bank is not None:
        before=len(floor_bank);floor_bank.update(floor_additions)
        result.update(new_floor_vertex_time_pairs=len(floor_bank)-before,retained_floor_vertex_time_pairs=len(floor_bank))
    return result


def add_guards(problem,value,worlds,bank,system,jacobian,hard_rows,trust):
    records=[bank[k] for k in sorted(bank)];count=len(records)
    if not count:return system,jacobian,hard_rows,dict(pairs=0,rows=0)
    if 9*count>500000 or 9*count*problem.size>16_000_000:
        raise ValueError('Complete surface derivative exceeds budget; no records or columns dropped')
    faces={n:faces_for(a['rig'])[0] for n,a in problem.scene.actors.items()}
    groups={};fixed=np.empty((count,3,3));anchored=np.empty_like(fixed)
    for ordinal,row in enumerate(records):
        name=row['actor'];stamp=row['time_s'];clock=int(np.searchsorted(problem.times,stamp))
        if clock==len(problem.times) or problem.times[clock]!=stamp:raise ValueError('Complete geometry clock required before surface guidance')
        ids=faces[name][row['actor_triangle']]
        groups.setdefault(name,[]).append((ordinal,clock,ids))
        prop=problem.mesh._props[row['prop']];p,r=problem.mesh.prop_poses(row['prop'],np.array([stamp]))
        fixed[ordinal]=prop['asset'].vertices_m[prop['asset'].faces[row['prop_triangle']]]@r[0].T+p[0]
    for name,group in groups.items():
        actor=problem.scene.actors[name];p,r=actor['placement'];cache={}
        for ordinal,clock,ids in group:
            if clock not in cache:cache.clear();cache[clock]=actor['rig'].vertices(worlds[name][clock])@r.T+p
            anchored[ordinal]=cache[clock][ids]
    normals=np.empty((count,3))
    for start in range(0,count,256):normals[start:start+256]=choose_directions(anchored[start:start+256],fixed[start:start+256])[0]
    def project(points):
        origin=points[:,:1,:]
        a=np.einsum('pi,pvi->pv',normals,points-origin);b=np.einsum('pi,pvi->pv',normals,fixed-origin)
        return (b[:,None,:]-a[:,:,None]).reshape(-1)
    original=project(anchored);caps=np.minimum(original.reshape(-1,9).min(axis=1),0.)
    gaps=original-np.repeat(caps,9)
    def smooth(matrices):
        points=np.empty_like(anchored)
        for name,group in groups.items():
            actor=problem.scene.actors[name];skin=actor['skin'];p,r=actor['placement']
            for start in range(0,len(group),256):
                block=group[start:start+256];ids=np.array([x[2] for x in block]);clock=np.array([x[1] for x in block])
                selected=matrices[name][clock[:,None,None],skin.nodes[ids],:3,:]
                values=np.einsum('pvkij,pvkj,pvk->pvi',selected,skin.points[ids],skin.weights[ids])@r.T+p
                points[[x[0] for x in block]]=values
        return project(points)
    base=smooth(problem.worlds(value,quantized=False));columns=[];stencils=[]
    for column in range(problem.size):
        if value[column]-.001>=problem.lower[column] and value[column]+.001<=problem.upper[column]:
            plus=value.copy();minus=value.copy();plus[column]+=.001;minus[column]-=.001
            derivative=(smooth(problem.worlds(plus,quantized=False))-smooth(problem.worlds(minus,quantized=False)))/.002
            stencils.append([.001,-.001])
        else:
            room=problem.upper[column]-value[column] if problem.upper[column]-value[column]>=value[column]-problem.lower[column] else problem.lower[column]-value[column]
            h=np.copysign(min(.001,abs(room)),room)
            if h==0:raise ValueError('No surface derivative room')
            other=value.copy();other[column]+=h;derivative=(smooth(problem.worlds(other,quantized=False))-base)/h;stencils.append([float(h)])
        columns.append(sparse.csc_matrix(derivative[:,None]))
    extra,extra_jac,conversion=lift(gaps,sparse.hstack(columns,format='csr'),value,problem.lower,problem.upper,trust,clearance=0.)
    vectors=np.r_[system.vectors[:hard_rows],extra.vectors,system.vectors[hard_rows:]]
    limits=np.r_[system.caps[:hard_rows],extra.caps,system.caps[hard_rows:]]
    scales=np.r_[system.scales[:hard_rows],extra.scales,system.scales[hard_rows:]]
    matrix=sparse.vstack([jacobian[:3*hard_rows],extra_jac,jacobian[3*hard_rows:]],format='csc')
    return NormRows(vectors,limits,scales),matrix,hard_rows+9*count,dict(pairs=count,rows=9*count,
        records=records,directions=normals.tolist(),projected_gap_floors_m=caps.tolist(),stencil_offsets=stencils,
        conversion=conversion,all_nine_vertex_comparisons_retained=True,
        scope='Frozen separating-axis guidance on retained actor/prop triangle pairs. Existing negative directional gaps cannot worsen in the affine proposal; passing directions retain zero separation. Directions rebuild from current decoded geometry. No whole-mesh, partner, containment, continuous collision or motion-quality certificate.')
