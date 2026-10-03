"""Source-bound surface orientation/side diagnostics for authored point contacts.

Oriented normals follow mesh winding, not inferred anatomical palms. This
read-only audit adds explicit authored conditions; it never edits or approves a
clip and never replaces complete geometry or engine checks.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now
from native_scene_contacts import SceneContacts,fields,scalar,vector
from native_scene_geometry import faces_for,METHODS as GEOMETRY_METHODS

METHODS=tuple(dict.fromkeys(GEOMETRY_METHODS+('native_surface_contact.py',)))


def normals(points,faces,groups,*,minimum_area,minimum_coherence):
    """Area-weight all incident faces once per point/centroid vertex group."""
    points=np.asarray(points,float);faces=np.asarray(faces)
    if (points.ndim!=2 or points.shape[1:]!=(3,) or not len(points) or not np.isfinite(points).all()
            or faces.ndim!=2 or faces.shape[1:]!=(3,) or not len(faces)
            or not np.issubdtype(faces.dtype,np.integer) or faces.min()<0 or faces.max()>=len(points)
            or type(minimum_area) not in (int,float) or not np.isfinite(minimum_area) or minimum_area<=0
            or type(minimum_coherence) not in (int,float) or not np.isfinite(minimum_coherence) or not 0<minimum_coherence<=1):
        raise ValueError('Complete finite surface, indexed faces and explicit normal reliability thresholds required')
    triangle=points[faces];cross=np.cross(triangle[:,1]-triangle[:,0],triangle[:,2]-triangle[:,0])
    area=np.linalg.norm(cross,axis=1);result=[]
    for ids in groups:
        ids=np.asarray(ids)
        if (ids.ndim!=1 or not len(ids) or not np.issubdtype(ids.dtype,np.integer)
                or ids.min()<0 or ids.max()>=len(points) or len(np.unique(ids))!=len(ids)):
            raise ValueError('Distinct existing surface vertex group required')
        incident=np.flatnonzero(np.isin(faces,ids).any(1));total=float(area[incident].sum())
        summed=cross[incident].sum(0);length=float(np.linalg.norm(summed));coherence=length/total if total>0 else 0.
        degenerate=incident[area[incident]<=minimum_area]
        available=bool(len(incident) and not len(degenerate) and length>minimum_area and coherence>=minimum_coherence)
        result.append(dict(available=available,normal_world=(summed/length).tolist() if available else None,
            incident_faces=incident.tolist(),degenerate_faces=degenerate.tolist(),
            summed_twice_area_m2=total,normal_coherence=coherence,
            scope='Winding-derived area-weighted incident-face normal; no anatomical or outward-volume inference.'))
    return result


def policy_for(policy,scene,digest):
    fields(policy,('schema','contacts_sha256','limits','maximum_actor_pose_queries','contacts'),'surface contact policy')
    if policy['schema']!='strep-native-surface-contact-v1' or policy['contacts_sha256']!=digest:
        raise ValueError('Surface policy must bind the exact contact JSON')
    limits=policy['limits'];fields(limits,('maximum_opposition_error_degrees','backface_allowance_m','minimum_normal_area_m2','minimum_normal_coherence'),'surface contact limits')
    scalar(limits['maximum_opposition_error_degrees'],0,90,'normal opposition angle')
    scalar(limits['backface_allowance_m'],0,.005,'backface allowance')
    scalar(limits['minimum_normal_area_m2'],1e-16,1e-4,'normal area reliability floor')
    scalar(limits['minimum_normal_coherence'],.000001,1,'normal coherence')
    budget=policy['maximum_actor_pose_queries']
    if type(budget) is not int or not 1<=budget<=20000:raise ValueError('Choose 1-20000 explicit actor pose queries')
    contacts=policy['contacts'];expected={r['authored']['id'] for r in scene.rows}
    if not isinstance(contacts,dict) or set(contacts)!=expected:raise ValueError('Surface policy must cover every authored contact exactly')
    for entry in scene.rows:
        row=entry['authored'];target=row['target'];item=contacts[row['id']]
        fields(item,('target_normal',),'surface contact target');declaration=item['target_normal']
        if target['space']=='actor':
            fields(declaration,('space',),'partner surface normal')
            if declaration['space']!='partner-surface':raise ValueError('Partner normals derive from the exact target vertex references')
        else:
            fields(declaration,('space','normals'),'explicit target normals')
            if declaration['space']!=target['space']:raise ValueError('Explicit normal must use its target world/object coordinates')
            count=1 if row['reduction']=='centroid' else len(entry['ids'])
            if not isinstance(declaration['normals'],list) or len(declaration['normals'])!=count:raise ValueError('One target normal per contact point required')
            for normal in declaration['normals']:
                if abs(np.linalg.norm(vector(normal,3,'target normal'))-1)>1e-8:raise ValueError('Unit explicit target normal required')
    return limits,budget


def evaluate(scene,policy,digest,*,actor_vertices=None,object_poses=None):
    limits,budget=policy_for(policy,scene,digest);base,point_arrays=scene.evaluate()
    faces={n:faces_for(a['rig'])[0] for n,a in scene.actors.items()};queries=0;results=[];arrays={}
    for i,entry in enumerate(scene.rows):
        row=entry['authored'];target=row['target'];clock=point_arrays[f'contact_{i}_times_s']
        effector=point_arrays[f'contact_{i}_effector_world_m'];goal=point_arrays[f'contact_{i}_target_world_m']
        object_rotation=None
        if target['space']=='object':
            _,object_rotation=(scene.object_poses if object_poses is None else object_poses)(target['object'],clock)
            object_rotation=np.asarray(object_rotation,float)
            if (object_rotation.shape!=(len(clock),3,3) or not np.isfinite(object_rotation).all()
                    or not np.allclose(object_rotation@object_rotation.transpose(0,2,1),np.eye(3),atol=1e-8,rtol=0)
                    or not np.allclose(np.linalg.det(object_rotation),1,atol=1e-8,rtol=0)):
                raise ValueError('Complete proper object normal transforms required')
        observations=[];normal_rows=[];target_rows=[];valid_rows=[]
        for j,time in enumerate(clock):
            cache={}
            def vertex_population(name):
                nonlocal queries
                if name not in cache:
                    queries+=1
                    if queries>budget:raise ValueError('Complete surface audit exceeds explicit pose budget; no partial result')
                    actor=scene.actors[name]
                    if actor_vertices is None:
                        p,r=actor['placement'];v=actor['rig'].vertices(actor['sampler'].sample(float(time)))@r.T+p
                    else:v=np.asarray(actor_vertices(name,float(time)),float)
                    if v.shape!=(len(actor['skin'].nodes),3) or not np.isfinite(v).all():raise ValueError('Complete finite posed surface population required')
                    cache[name]=v
                return cache[name]
            def oriented(name,ids,reduction,expected_points):
                v=vertex_population(name)
                actual=v[ids].mean(0,keepdims=True) if reduction=='centroid' else v[ids]
                if not np.allclose(actual,expected_points,atol=2e-12,rtol=0):raise ValueError('Surface and contact point observations differ')
                groups=[ids] if reduction=='centroid' else [[int(v)] for v in ids]
                return normals(v,faces[name],groups,minimum_area=limits['minimum_normal_area_m2'],minimum_coherence=limits['minimum_normal_coherence'])
            left=oriented(row['actor'],entry['ids'],row['reduction'],effector[j])
            if target['space']=='actor':right=oriented(target['actor'],entry['target_ids'],target['reduction'],goal[j])
            else:
                normals_target=np.asarray(policy['contacts'][row['id']]['target_normal']['normals'],float)
                if target['space']=='object':normals_target=normals_target@object_rotation[j].T
                right=[dict(available=True,normal_world=n.tolist(),scope='Explicit authored target normal; anatomical/surface outwardness not inferred.') for n in normals_target]
            stamp=[];ln=[];rn=[];valid=[]
            for k,(a,b) in enumerate(zip(left,right)):
                available=a['available'] and b['available'];angle=side_left=side_right=None
                if available:
                    na,nb=np.asarray(a['normal_world']),np.asarray(b['normal_world']);delta=goal[j,k]-effector[j,k]
                    angle=float(np.rad2deg(np.arccos(np.clip(-na@nb,-1,1))))
                    side_left=float(na@delta);side_right=float(-nb@delta)
                passed=bool(available and angle<=limits['maximum_opposition_error_degrees']
                    and min(side_left,side_right)>=-limits['backface_allowance_m'])
                stamp.append(dict(point=k,source_normal=a,target_normal=b,opposition_error_degrees=angle,
                    source_target_projection_m=side_left,target_source_projection_m=side_right,passed=passed))
                ln.append(a['normal_world'] if a['available'] else [0.,0,0]);rn.append(b['normal_world'] if b['available'] else [0.,0,0]);valid.append(available)
            observations.append(dict(time_s=float(time),points=stamp));normal_rows.append(ln);target_rows.append(rn);valid_rows.append(valid)
        point_pass=bool(base['contacts'][i]['passed']);surface_pass=all(p['passed'] for s in observations for p in s['points'])
        results.append(dict(id=row['id'],contact_points_pass=point_pass,surface_orientation_and_side_pass=surface_pass,
            passed=bool(point_pass and surface_pass),samples=observations))
        arrays[f'contact_{i}_times_s']=clock;arrays[f'contact_{i}_source_normals_world']=np.asarray(normal_rows)
        arrays[f'contact_{i}_target_normals_world']=np.asarray(target_rows);arrays[f'contact_{i}_normal_available']=np.asarray(valid_rows,bool)
    scene.check_inputs()
    return dict(schema='strep-native-surface-contact-result-v1',status='complete',contacts=results,actor_pose_queries=queries,
        limits=limits,point_contacts_pass=base['passed'],surface_contacts_pass=all(r['passed'] for r in results),
        new_authored_conditions=True,original_selected=True,anatomical_review_pending=True,
        collision_verified=False,engine_playback_verified=False,quality_approved=False,training_admitted=False,release_approved=False,
        scope='Winding-derived normals at every existing contact clock with explicit opposition/side limits. '
            'World/object target normals are authored, not inferred. Full incident triangle populations retained. '
            'No anatomical palm identification, contact force, penetration, continuous collision, renderer or quality proof.'),arrays


def run(contacts_path,policy_path,output):
    contacts_path,policy_path,output=map(lambda p:Path(p).resolve(),(contacts_path,policy_path,output))
    if output.exists():raise ValueError('Fresh surface contact audit directory required')
    with worker_lock(),threadpool_limits(limits=1):
        bindings={str(p):sha256(p) for p in (contacts_path,policy_path)}
        scene=SceneContacts(read(contacts_path),contacts_path.parent);policy=read(policy_path)
        policy_for(policy,scene,bindings[str(contacts_path)]);bindings.update(scene.inputs)
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True)
        archive=output/'implementation';archive.mkdir();save(output/'pipeline.json',dict(status='processing',original_selected=True))
        try:
            for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
            snapshots={}
            for i,(p,h) in enumerate(bindings.items()):
                dest=output/'input'/f'{i}{Path(p).suffix}';dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
                if sha256(dest)!=h:raise ValueError('Surface contact input snapshot changed')
                snapshots[p]=dict(path=dest.relative_to(output).as_posix(),sha256=h)
            save(output/'request.json',dict(at=now(),inputs_sha256=bindings,implementation_sha256=methods,source_snapshots=snapshots))
            result,arrays=evaluate(scene,policy,bindings[str(contacts_path)])
            if any(sha256(p)!=h or sha256(output/snapshots[p]['path'])!=h for p,h in bindings.items()):raise ValueError('Surface contact input changed')
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(archive/n)!=h for n,h in methods.items()):raise ValueError('Surface contact method changed')
            np.savez_compressed(output/'observations.npz',**arrays)
            result.update(observations_sha256=sha256(output/'observations.npz'),implementation_sha256=methods,source_snapshots=snapshots)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for n in ('contacts','policy','output'):parser.add_argument(n,type=Path)
    args=parser.parse_args();run(args.contacts,args.policy,args.output)
