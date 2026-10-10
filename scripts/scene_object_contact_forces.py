"""Sampled supplied-rig/object contact mechanics; never human strength approval.

Bind original scene files, query actual skin, retain every declared contact and
geometry clock, and differentiate an explicit uniform COM clock. Forces alone
cannot pass the coupled sampled condition when actual contact/geometry fails.
"""
import argparse,copy,json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from native_scene_contacts import SceneContacts,fields
from native_surface_contact import evaluate as surface_evaluate,policy_for as surface_policy_for,normals,METHODS as SURFACE_METHODS
from native_scene_geometry import evaluate_to_archive,policy_for as geometry_policy_for,faces_for
from object_dynamics import diagnose
from contact_force_balance import solve,validate as validate_forces

SCHEMA='strep-scene-object-contact-forces-v1'
METHODS=tuple(dict.fromkeys(SURFACE_METHODS+('object_dynamics.py','contact_force_balance.py','scene_object_contact_forces.py')))
FIELDS={'schema','scene','surface_policy','geometry_policy','object','sample_count','body','contact_forces','phases',
    'force_tolerance_N','torque_tolerance_Nm','seconds_per_sample','assumption_notes'}


def finite(value,shape,label):
    a=np.asarray(value,dtype=float)
    if a.shape!=shape or not np.isfinite(a).all():raise ValueError('Complete finite '+label+' required')
    return a


def prepare(scene,surface_policy,geometry_policy,request,digest):
    fields(request,FIELDS,'scene force request')
    if request['schema']!=SCHEMA or request['object'] not in scene.objects:raise ValueError('Named original scene object required')
    surface_policy_for(surface_policy,scene,digest);geometry_policy_for(geometry_policy,scene,digest)
    count=request['sample_count']
    if type(count) is not int or not 3<=count<=900:raise ValueError('Explicit 3–900 sample differentiation clock required')
    times=np.linspace(0,scene.duration,count);fps=(count-1)/scene.duration
    if not 1<=fps<=240:raise ValueError('Differentiation rate must be within 1–240 Hz')
    body=request['body']
    fields(body,('mass_kg','inertia_body_about_com_kg_m2','com_from_object_origin_local_m','gravity_world_m_s2'),'rigid body properties')
    com=finite(body['com_from_object_origin_local_m'],(3,),'explicit object-local COM')
    if np.max(abs(com))>1000:raise ValueError('Bounded declared COM required')
    p,r=scene.object_poses(request['object'],times)
    centers=p+np.einsum('fij,j->fi',r,com)
    demand=diagnose(centers,Rotation.from_matrix(r).as_quat(),fps=fps,mass_kg=body['mass_kg'],
        inertia_body_kg_m2=body['inertia_body_about_com_kg_m2'],gravity_m_s2=body['gravity_world_m_s2'],phases=request['phases'])
    notes=request['assumption_notes']
    if (not isinstance(notes,dict) or set(notes)!={'com','mass','inertia','friction','capacity','contacts'}
            or any(not isinstance(v,str) or not 1<=len(v)<=2000 for v in notes.values())):
        raise ValueError('Explicit body/friction/capacity/contact provenance required')
    entries=[e for e in scene.rows if e['authored']['target'].get('object')==request['object']]
    capacities=request['contact_forces']
    if not entries or not isinstance(capacities,dict) or set(capacities)!={e['authored']['id'] for e in entries}:
        raise ValueError('Force assumptions must cover every contact to the selected object exactly')
    declared=[];total=0
    for entry in entries:
        row=entry['authored'];name=row['id'];item=capacities[name]
        if row['mode']!='hold':raise ValueError('Sticking forces require explicit holds; touch/impact needs a different model')
        fields(item,('friction_coefficient','maximum_point_forces_N'),'contact force assumptions')
        points=np.asarray(entry['target_ids'],float);caps=item['maximum_point_forces_N']
        if not isinstance(caps,list) or len(caps)!=len(points):raise ValueError('One explicit total-force cap per original correspondence required')
        normal=np.asarray(surface_policy['contacts'][name]['target_normal']['normals'],float)
        canonical=np.array([scene.objects[request['object']]['geometry'].local_surface_normal(v) for v in points])
        if not np.allclose(normal,canonical,rtol=0,atol=1e-8):raise ValueError('Declared force normal must match the actual primitive outward normal')
        for i,(point,n,cap) in enumerate(zip(points,canonical,caps)):
            declared.append(dict(id=name+':'+str(i),lever_from_com_world_m=(point-com).tolist(),
                normal_into_body_world=(-n).tolist(),friction_coefficient=item['friction_coefficient'],max_force_N=cap))
        total+=len(points)
    if total>16:raise ValueError('Complete declared force population exceeds sixteen points; no subset is selected')
    validate_forces([0,0,0],[0,0,0],declared,request['force_tolerance_N'],request['torque_tolerance_Nm'])
    budget=request['seconds_per_sample']
    if type(budget) not in (int,float) or not np.isfinite(budget) or not .01<=budget<=2:raise ValueError('Bounded per-sample force solve budget required')
    labels=[None]*count
    for phase in request['phases']:
        for f in range(phase['start_frame'],phase['end_frame_exclusive']):labels[f]=phase['support_assumption']
    for f,time in enumerate(times):
        if labels[f]=='free_flight' and any(e['authored']['interval_s'][0]<=time<=e['authored']['interval_s'][1] for e in entries):
            raise ValueError('Declared free-flight sample cannot have an active sticking hold, including endpoints')
    return dict(times=times,fps=fps,object_positions=p,rotations=r,centers=centers,demand=demand,entries=entries,labels=labels)


def assess(scene,request,prepared,surface,geometry,*,maximum_actor_pose_queries):
    """Query actual skin on the differentiation clock; keep force-only scope explicit."""
    times=prepared['times'];fps=prepared['fps'];r=prepared['rotations'];centers=prepared['centers'];entries=prepared['entries']
    geometry_times=np.asarray(geometry['times_s'],float)
    if not np.array_equal(np.unique(geometry_times),geometry_times):raise ValueError('Complete unique geometry clock required')
    lookup=np.searchsorted(geometry_times,times)
    if np.any(lookup>=len(geometry_times)) or not np.array_equal(geometry_times[lookup],times):raise ValueError('Every force-clock time must have actual geometry measurements')
    if len(geometry['samples'])!=len(geometry_times) or any(s['time_s']!=t for s,t in zip(geometry['samples'],geometry_times)):
        raise ValueError('Geometry sample identities must match the complete clock')
    faces={n:faces_for(a['rig'])[0] for n,a in scene.actors.items()};observations={};queries=surface['actor_pose_queries']
    for f,time in enumerate(times):
        cache={}
        for entry in entries:
            row=entry['authored'];name=row['id'];actor=row['actor'];asset=scene.actors[actor]
            if actor not in cache:
                queries+=1
                if queries>maximum_actor_pose_queries:raise ValueError('Complete surface queries exceed the declared budget; no partial result')
                p,rotation=asset['placement'];cache[actor]=asset['rig'].vertices(asset['sampler'].sample(float(time)))@rotation.T+p
            v=cache[actor];ids=entry['ids'];points=v[ids]
            groups=[[int(i)] for i in ids]
            if row['reduction']=='centroid':points=points.mean(0,keepdims=True);groups=[ids]
            targets=np.asarray(entry['target_ids'])@r[f].T+prepared['object_positions'][f]
            error=(points-targets)@r[f]
            thresholds=surface['limits']
            normal=normals(v,faces[actor],groups,minimum_area=thresholds['minimum_normal_area_m2'],minimum_coherence=thresholds['minimum_normal_coherence'])
            outwards=np.array([scene.objects[request['object']]['geometry'].local_surface_normal(p) for p in entry['target_ids']])@r[f].T
            point_rows=[]
            for i,(a,outward) in enumerate(zip(normal,outwards)):
                angle=side_source=side_target=None
                if a['available']:
                    source=np.asarray(a['normal_world']);delta=targets[i]-points[i]
                    angle=float(np.rad2deg(np.arccos(np.clip(-source@outward,-1,1))))
                    side_source=float(source@delta);side_target=float(-outward@delta)
                eligible=bool(a['available'] and angle<=thresholds['maximum_opposition_error_degrees']
                    and min(side_source,side_target)>=-thresholds['backface_allowance_m']
                    and np.linalg.norm(error[i])<=row['limits']['position_m'])
                point_rows.append(dict(source_normal=a,target_outward_normal_world=outward.tolist(),
                    position_error_m=float(np.linalg.norm(error[i])),opposition_error_degrees=angle,
                    source_target_projection_m=side_source,target_source_projection_m=side_target,passed=eligible))
            observations.setdefault(name,[]).append(dict(time_s=float(time),object_local_error_m=error.tolist(),points=point_rows))
    rows=[];unassessed=[];d=prepared['demand']
    for f,same,force,torque in zip(d['sample_frames'],d['same_phase_stencil'],d['required_non_gravity_force_world_N'],d['required_torque_about_com_world_Nm']):
        if not same or prepared['labels'][f]=='unknown':
            unassessed.append(dict(frame=f,reason='cross_phase_stencil' if not same else 'unknown_support'));continue
        contacts=[];checks=[]
        for entry in entries:
            row=entry['authored'];name=row['id'];a,b=row['interval_s']
            if not a<=times[f]<=b:continue
            cap=request['contact_forces'][name];observed=observations[name]
            span=observed[f-1:f+2];errors=np.array([s['object_local_error_m'] for s in span])
            speeds=np.linalg.norm(np.diff(errors,axis=0),axis=2)*fps
            active_stencil=bool(a<=times[f-1] and times[f+1]<=b)
            passed=bool(active_stencil and all(p['passed'] for s in span for p in s['points']) and speeds.max()<=row['limits']['relative_speed_m_s'])
            checks.append(dict(contact=name,active_stencil=active_stencil,maximum_relative_speed_m_s=float(speeds.max()),passed=passed))
            targets=np.asarray(entry['target_ids'])@r[f].T+prepared['object_positions'][f]
            for i,(point,limit) in enumerate(zip(targets,cap['maximum_point_forces_N'])):
                contacts.append(dict(id=name+':'+str(i),lever_from_com_world_m=(point-centers[f]).tolist(),
                    normal_into_body_world=(-np.array(observed[f]['points'][i]['target_outward_normal_world'])).tolist(),
                    friction_coefficient=cap['friction_coefficient'],max_force_N=limit))
        report=solve(force,torque,contacts,force_tolerance_N=request['force_tolerance_N'],torque_tolerance_Nm=request['torque_tolerance_Nm'],seconds=request['seconds_per_sample'])
        geometry_ok=bool(geometry['samples'][lookup[f]]['passed'])
        contact_ok=bool(all(c['passed'] for c in checks) and (bool(checks) or prepared['labels'][f]=='free_flight'))
        rows.append(dict(frame=f,time_s=float(times[f]),assessment=report,actual_contact_stencil_checks=checks,
            sampled_geometry_passed=geometry_ok,actual_sticking_contact_samples_passed=contact_ok,
            coupled_sampled_scene_force_consistent=bool(report['conditional_force_balance_passed'] and contact_ok and geometry_ok
                and surface['point_contacts_pass'] and surface['surface_contacts_pass'] and geometry['sampled_conditions_pass'])))
    return dict(schema=SCHEMA,object=request['object'],uniform_times_s=times.tolist(),differentiation_fps=fps,
        body=request['body'],world_com_positions_m=centers.tolist(),demand=d,assessed_samples=rows,unassessed_samples=unassessed,
        unestimated_endpoint_frames=[0,len(times)-1],actual_contact_observations=observations,actor_pose_queries=queries,
        conditional_force_feasible=sum(s['assessment']['conditional_force_balance_passed'] for s in rows),
        coupled_sampled_scene_force_consistent=sum(s['coupled_sampled_scene_force_consistent'] for s in rows),
        assumption_notes=request['assumption_notes'],quality_approved=False,release_approved=False,training_admitted=False,
        scope='Actual supplied-rig skin, original primitive targets, complete declared sampled scene geometry and explicit object COM/inertia/caps on one added uniform clock. Conditional forces remain separate from failed contact/geometry. No anatomy, measured human capacity, actor reaction/joint dynamics, impacts, self-collision, continuous-time, engine or quality certificate.')


def run(request_path,output):
    request_path=Path(request_path).resolve();output=Path(output).resolve();request_hash=sha256(request_path);request=read(request_path)
    if sha256(request_path)!=request_hash:raise ValueError('Request changed while reading')
    fields(request,FIELDS,'scene force request')
    if output.exists():raise FileExistsError(output)
    if not output.is_relative_to(ROOT/'reports') or output==ROOT/'reports':raise ValueError('Fresh ignored scene-force output required')
    inputs={str(request_path):request_hash};paths={}
    for name in ('scene','surface_policy','geometry_policy'):
        entry=request[name];fields(entry,('path','sha256'),'bound scene force input')
        p=(request_path.parent/entry['path']).resolve()
        if sha256(p)!=entry['sha256']:raise ValueError('Bound input changed')
        inputs[str(p)]=entry['sha256'];paths[name]=p
    original=SceneContacts(read(paths['scene']),paths['scene'].parent);inputs.update(original.inputs)
    prepare(original,read(paths['surface_policy']),read(paths['geometry_policy']),request,inputs[str(paths['scene'])])
    if any(output.is_relative_to(Path(p)) or Path(p).is_relative_to(output) for p in inputs):raise ValueError('Output must be separate from every immutable input')
    output.mkdir(parents=True);copies={};methods={};source_folder=Path(__file__).resolve().parent
    try:
        save(output/'pipeline.json',dict(status='processing',stage='freeze-inputs',quality_approved=False,release_approved=False))
        for i,(p,h) in enumerate(inputs.items()):
            dest=output/'inputs'/f'{i}{Path(p).suffix}';dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
            if sha256(dest)!=h:raise ValueError('Source changed while freezing')
            copies[p]=dest.relative_to(output).as_posix()
        for name in METHODS:
            source=source_folder/name;h=sha256(source);dest=output/'implementation'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(source,dest)
            if sha256(dest)!=h:raise ValueError('Bound method changed while freezing')
            methods[name]=h
        save(output/'protocol.json',dict(schema=SCHEMA,at=now(),inputs_sha256=inputs,methods_sha256=methods,input_snapshots=copies,
            sample_count=request['sample_count'],uniform_clock_preserves_exact_clip_endpoints=True,quality_approved=False,release_approved=False))
        spec=read(output/copies[str(paths['scene'])])
        for name,actor in spec['actors'].items():actor['glb']=copies[str((paths['scene'].parent/actor['glb']).resolve())]
        save(output/'effective-scene.json',spec);digest=sha256(output/'effective-scene.json');scene=SceneContacts(spec,output)
        sp=read(output/copies[str(paths['surface_policy'])]);gp=read(output/copies[str(paths['geometry_policy'])])
        sp['contacts_sha256']=gp['contacts_sha256']=digest
        frozen=read(output/copies[str(request_path)]);prepared=prepare(scene,sp,gp,frozen,digest)
        save(output/'pipeline.json',dict(status='processing',stage='actual-surface-contacts',quality_approved=False,release_approved=False))
        surface,arrays=surface_evaluate(scene,sp,digest);np.savez(output/'surface-observations.npz',**arrays);save(output/'surface-result.json',surface)
        clocks=[np.asarray(gp['clock']['times_s'],float),prepared['times']]
        clocks.extend(np.asarray(a,float) for k,a in arrays.items() if k.endswith('_times_s'))
        gp['clock']['times_s']=np.unique(np.concatenate(clocks)).tolist()
        save(output/'effective-geometry-policy.json',gp);save(output/'effective-surface-policy.json',sp)
        save(output/'pipeline.json',dict(status='processing',stage='complete-scene-geometry',quality_approved=False,release_approved=False))
        geometry,_=evaluate_to_archive(scene,gp,digest,output/'geometry-observations');save(output/'geometry-result.json',geometry)
        save(output/'pipeline.json',dict(status='processing',stage='coupled-contact-forces',quality_approved=False,release_approved=False))
        report=assess(scene,frozen,prepared,surface,geometry,maximum_actor_pose_queries=sp['maximum_actor_pose_queries']);save(output/'assessment.json',report)
        if any(sha256(Path(p))!=h or sha256(output/copies[p])!=h for p,h in inputs.items()):raise ValueError('Original or frozen source changed')
        if any(sha256(source_folder/n)!=h or sha256(output/'implementation'/n)!=h for n,h in methods.items()):raise ValueError('Bound method changed')
        scene.check_inputs()
        files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file() and p!=output/'pipeline.json'}
        result=dict(status='complete',at=now(),inputs_sha256=inputs,methods_sha256=methods,files_sha256=files,
            assessed_samples=len(report['assessed_samples']),conditional_force_feasible=report['conditional_force_feasible'],
            coupled_sampled_scene_force_consistent=report['coupled_sampled_scene_force_consistent'],quality_approved=False,release_approved=False,training_admitted=False)
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',result_sha256=sha256(output/'result.json'),quality_approved=False,release_approved=False));return result
    except BaseException as exc:
        save(output/'pipeline.json',dict(status='failed',error_type=type(exc).__name__,error=str(exc),quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('request',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    with worker_lock(),threadpool_limits(limits=1):print(json.dumps(run(args.request,args.output)))
