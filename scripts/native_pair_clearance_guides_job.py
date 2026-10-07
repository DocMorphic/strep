"""Pinned offline partner-guide proposals; originals stay selected.

This command edits existing native clips under their original Job contract.
It does not generate prompts, approve animation quality or select a library clip.
"""
import argparse,copy,shutil,traceback
from pathlib import Path
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits
from native_scene_contacts import SceneContacts,fields,scalar
from native_stored_pair_job import Job,METHODS as JOB_METHODS
from native_stored_pair_model import centered_problem
from native_pair_clearance_guides import linearize_pair_guides
from native_pair_guide_axis import choose_axis
from native_key_control_support import effective_basis
from native_norm_hinge_guided_step import direction
from native_scene_conic import solver_identity
from native_scene_norms import rows
from native_scene_geometry import faces_for,evaluate_to_archive,METHODS as GEOMETRY_METHODS
from native_surface_model import surface_points,geometry_score
from triangle_crossing import audit
from convex_partner_surface import penetration
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-pair-clearance-guides-job-v1'
METHODS=tuple(sorted(set(JOB_METHODS)|set(GEOMETRY_METHODS)|{
    'native_pair_clearance_guides_job.py','native_pair_clearance_guides.py','native_pair_guide_axis.py',
    'native_key_control_support.py','native_norm_hinge_guided_step.py','native_affine_ray_retreat.py'}))


def run(request_path,output):
    request_path=Path(request_path).resolve();output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        if output.exists():raise ValueError('Fresh immutable clearance output required')
        request=read(request_path);fields(request,('schema','job','guides','families','event_times_s','axis_mode'),'pair clearance job')
        if request['schema']!=SCHEMA:raise ValueError('Explicit pair clearance job schema required')
        inputs={str(request_path):sha256(request_path)};paths={}
        for role in ('job','guides'):
            pin=request[role];fields(pin,('path','sha256'),'pinned '+role)
            if not isinstance(pin['path'],str) or not pin['path']:raise ValueError('Explicit pinned file path required')
            path=(request_path.parent/pin['path']).resolve()
            if not path.is_file() or sha256(path)!=pin['sha256']:raise ValueError('Pinned '+role+' bytes differ')
            paths[role]=path;inputs[str(path)]=pin['sha256']
        families=request['families'];events=request['event_times_s']
        if (not isinstance(families,list) or not families or len(families)>2
                or any(not isinstance(f,str) or f not in ('original-norms','event-key-preserved') for f in families)
                or len(set(families))!=len(families)):
            raise ValueError('Choose unique explicit original-norm/event-key guide variants')
        if not isinstance(events,list) or len(events)>16:raise ValueError('Explicit bounded event-time list required')
        if ('event-key-preserved' in families)!=bool(events):raise ValueError('Event-key variant requires explicit preservation times')
        axis_mode=request['axis_mode']
        if type(axis_mode) is not str or axis_mode not in ('explicit','rank-patch'):raise ValueError('Explicit axis mode required')
        job=Job(paths['job']);inputs.update(job.inputs);guides=read(paths['guides']);settings=job.request['settings'];x=job.value.copy()
        if not isinstance(guides,list) or not 1<=len(guides)<=64:raise ValueError('One to 64 explicit guide descriptors required')
        for time in events:
            scalar(time,0.,job.scene.duration,'event time')
            if np.count_nonzero(job.problem.times==time)!=1:raise ValueError('Event time must already occur in the original complete native clock')
        if len(set(events))!=len(events):raise ValueError('Unique event preservation times required')
        # Adding files below an existing immutable result would change its
        # archived population even if no original bytes were overwritten.
        for path in inputs:
            parent=Path(path).parent
            if (parent/'result.json').is_file() and output.is_relative_to(parent):
                raise ValueError('Output must stay outside immutable input studies')
        parameter=[];support=[]
        for time in events:
            for name,actor in job.edits.actors.items():
                for entry in actor['tracks']:
                    basis=effective_basis(entry['clock'],entry['ids'],entry['weights'],time)
                    support.append(dict(actor=name,node=entry['node'],path=entry['path'],time_s=time,basis=basis.tolist()))
                    for component in range(entry['controls'].shape[1]):
                        row=np.zeros(len(x));row[entry['controls'][:,component]]=basis;parameter.append(row)
        if len(parameter)>96:raise ValueError('Event preservation exceeds the complete 96-row parameter budget')
        eq=np.asarray(parameter).reshape(len(parameter),len(x))
        output.mkdir(parents=True);(output/'implementation').mkdir();(output/'stencils').mkdir()
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
        save(output/'request.json',request);save(output/'job.json',job.request);save(output/'input-guides.json',guides)
        save(output/'event-support.json',support)
        def phase(name,**kw):
            status=name if name in ('complete','failed') else 'processing'
            data=dict(status=status,phase=name,at=now());data.update(kw);save(output/'pipeline.json',data)
        try:
            spec=copy.deepcopy(job.spec)
            for n,entry in spec['actors'].items():
                path=job.files[n] if n in job.files else job.roles['source_'+n];entry.update(glb=str(path),sha256=sha256(path))
            save(output/'guide-scene.json',spec);digest=sha256(output/'guide-scene.json')
            scene=SceneContacts(spec,output);policy=copy.deepcopy(job.policy);policy['contacts_sha256']=digest;save(output/'guide-policy.json',policy)
            centered,decoded,centering=centered_problem(job.problem,x,job.files,scene,policy,digest,source_policy=job.policy)
            residual=job.problem.constraints(x,decoded);native=rows(job.problem,x,decoded)
            if not (np.all(residual<=0) and np.all(native.residual()<=0) and job.reference_bounds(job.files,decoded)['passed']):
                raise ValueError('Original decoded motion/vector/reference feasible seed required; geometry remains unapproved')
            if len(native.caps)>settings['maximum_rows']:raise ValueError('Complete native norm population exceeds original row budget')
            choices=[]
            if axis_mode=='rank-patch':
                for guide in guides:
                    fields(guide,('actor_a','vertices_a','actor_b','vertices_b','time_s','axis_world','clearance_m','scale_m'),'pair guide')
                    names=[guide['actor_a'],guide['actor_b']]
                    if any(type(n) is not str or n not in job.scene.actors for n in names) or names[0]==names[1]:raise ValueError('Distinct existing guide actors required')
                    t=scalar(guide['time_s'],0.,job.scene.duration,'guide time');frames=np.flatnonzero(job.problem.times==t)
                    if len(frames)!=1:raise ValueError('Guide time must occur once in the complete original native clock')
                    points=[];triangles=[]
                    for name,key in zip(names,('vertices_a','vertices_b')):
                        a=job.scene.actors[name];ids=guide[key]
                        if (not isinstance(ids,list) or not ids or any(type(i) is not int or not 0<=i<len(a['skin'].vertex_references) for i in ids)
                                or len(set(ids))!=len(ids)):raise ValueError('Explicit unique valid patch vertices required')
                        p,r=a['placement'];points.append(a['rig'].vertices(decoded[name][int(frames[0])])[ids]@r.T+p)
                        lookup={v:i for i,v in enumerate(ids)}
                        triangles.append(np.array([[lookup[int(v)] for v in f] for f in faces_for(a['rig'])[0] if all(int(v) in lookup for v in f)],int).reshape(-1,3))
                    axis,choice=choose_axis(points[0],triangles[0],points[1],triangles[1],guide['axis_world'],clearance_m=guide['clearance_m'],scale_m=guide['scale_m'])
                    if any(not np.isfinite(q['axis_world']).all() or abs(np.linalg.norm(q['axis_world'])-1.)>1e-12 for q in choice['tests']):raise ValueError('Every ranked candidate axis must be finite and unit length')
                    choices.append(dict(time_s=t,original_axis_world=guide['axis_world'],left_faces=triangles[0].tolist(),right_faces=triangles[1].tolist(),**choice))
                    guide['axis_world']=axis.tolist()
            save(output/'axis-choices.json',choices);save(output/'guides.json',guides)
            def sink(c,s,sample):
                np.savez_compressed(output/'stencils'/f"column-{c:03d}-{'positive' if s>0 else 'negative'}.npz",**sample)
                phase('native-differences',completed_stencils=len(list((output/'stencils').glob('*.npz'))))
            model=linearize_pair_guides(centered,x,decoded,guides,step=settings['difference_step'],
                maximum_elements=settings['maximum_nonzeros'],stencil_sink=sink)
            for key in ('vectors','caps','scales'):np.testing.assert_array_equal(getattr(native,key),getattr(model.native,key))
            save(output/'model.json',dict(model.identity,stored_pair_centering=centering))
            np.savez_compressed(output/'system.npz',controls=x,lower=job.problem.lower,upper=job.problem.upper,
                vectors=native.vectors,caps=native.caps,scales=native.scales,guide_residual=model.guide_residual,
                guide_points=model.points,gaps_m=model.gaps_m,continuous_origin_points=model.continuous_origin_points,parameter_rows=eq)
            sparse.save_npz(output/'native-jacobian.npz',model.native_jacobian);sparse.save_npz(output/'guide-jacobian.npz',model.guide_jacobian)
            records=[];faces={n:faces_for(a['rig'])[0] for n,a in job.scene.actors.items()}
            row_scales=np.concatenate([np.full(len(g['vertices_a'])*len(g['vertices_b']),g['scale_m']) for g in guides])
            row_clearances=np.concatenate([np.full(len(g['vertices_a'])*len(g['vertices_b']),g['clearance_m']) for g in guides])
            def observe(worlds):
                gaps=[];points=[];queries=[]
                for g in guides:
                    frame=int(np.flatnonzero(job.problem.times==g['time_s'])[0]);vertices={};actors=(g['actor_a'],g['actor_b']);axis=np.array(g['axis_world'])
                    for name in actors:
                        a=job.scene.actors[name];p,r=a['placement'];vertices[name]=a['rig'].vertices(worlds[name][frame])@r.T+p
                    left,right=vertices[actors[0]][g['vertices_a']],vertices[actors[1]][g['vertices_b']]
                    gaps.append(((right@axis)[None,:]-(left@axis)[:,None]).ravel());points.append(np.concatenate([left,right]).ravel())
                    crossing=audit(vertices[actors[0]],faces[actors[0]],vertices[actors[1]],faces[actors[1]],tolerance_m=job.policy['limits']['surface_tolerance_m'])
                    depths=[dict(source=a,target=b,**penetration(vertices[a],vertices[b],faces[b],tolerance_m=job.policy['limits']['penetration_m'])) for a,b in (actors,actors[::-1])]
                    queries.append(dict(time_s=g['time_s'],surface=crossing,vertex_containment=depths,maximum_partner_depth_m=max(d['max_depth_m'] for d in depths)))
                return np.concatenate(points),np.concatenate(gaps),queries
            for family in families:
                phase('guide-solve',family=family)
                delta,info=direction(native,model.native_jacobian,model.guide_residual,model.guide_jacobian,
                    x,job.problem.lower,job.problem.upper,settings['trust'],parameter_rows=eq if family=='event-key-preserved' else None)
                save(output/(family+'-solver.json'),dict(identity=solver_identity(),result=info,delta=None if delta is None else delta.tolist()))
                if delta is None:continue
                for i,fraction in enumerate(settings['fractions']):
                    label=family+f'-fraction-{i:02d}';folder=output/label;folder.mkdir();value=x+fraction*delta;step=value-x;files={}
                    for n in job.edits.actors:
                        q=folder/(n+'.glb');job.edits.export(n,value,q)
                        if not job.edits.audit(n,q,job.scene.actors[n]['animation_index'],value=value)['passed']:raise ValueError('Actual stored export authoring audit failed')
                        files[n]=q
                    actual,worlds=job.problem.decoded(files,value);actual_norms=rows(job.problem,value,worlds);bounds=job.reference_bounds(files,worlds)
                    smooth=centered.constraints(value,centered.worlds(value,quantized=False));points,gaps,queries=observe(worlds)
                    deficit=np.minimum((gaps-row_clearances)/row_scales,0.)
                    inside=bool(np.all(value>=job.problem.lower) and np.all(value<=job.problem.upper) and np.max(abs(step))<=settings['trust'])
                    record=dict(label=label,family=family,fraction=fraction,original_step_box_pass=inside,
                        maximum_actual_control_step=float(abs(step).max()),failed_native_rows=int((actual>0).sum()),
                        failed_contact_rows=int((actual[job.problem.protected_rows:]>0).sum()),centered_failed_native_rows=int((smooth>0).sum()),
                        original_vector_norm_failures=int((actual_norms.residual()>0).sum()),
                        native_conditions_pass=bool(np.all(actual<=0) and np.all(actual_norms.residual()<=0)),reference_bounds=bounds,
                        actual_guide_squared_negative_part=float(deficit@deficit),actual_minimum_guide_gap_m=float(gaps.min()),
                        guide_frame_queries=queries,guide_frame_maximum_partner_depth_m=max(q['maximum_partner_depth_m'] for q in queries),
                        guide_frame_triangle_records=sum(len(q['surface']['records']) for q in queries),
                        full_geometry_assessed=False,retained=False,quality_approved=False,release_approved=False)
                    np.savez_compressed(folder/'observations.npz',controls=value,residual=actual,centered_residual=smooth,
                        actual_gaps_m=gaps,guide_points=points,vectors=actual_norms.vectors,caps=actual_norms.caps,scales=actual_norms.scales,**{n+'_worlds':w for n,w in worlds.items()})
                    save(folder/'result.json',record);records.append(record);phase('actual-export',label=label,native_failures=record['failed_native_rows'])
            eligible=[v for v in records if v['original_step_box_pass'] and v['native_conditions_pass'] and v['reference_bounds']['passed']]
            selected=min(eligible,key=lambda v:(v['guide_frame_maximum_partner_depth_m'],v['guide_frame_triangle_records'])) if eligible else None
            if selected is not None:
                folder=output/selected['label']
                with np.load(folder/'observations.npz',allow_pickle=False) as z:worlds={n:z[n+'_worlds'].copy() for n in job.scene.actors}
                phase('selected-complete-geometry',label=selected['label'])
                geometry,_=evaluate_to_archive(job.scene,job.policy,sha256(job.roles['source_scene']),folder/'geometry-observations.npz',
                    actor_vertices=surface_points(job.problem,worlds))
                np.testing.assert_array_equal(geometry['times_s'],job.geometry_times);save(folder/'geometry.json',geometry)
                selected.update(full_geometry_assessed=True,geometry_score=list(geometry_score(geometry)),geometry_conditions_pass=geometry['sampled_conditions_pass'])
                save(folder/'result.json',selected)
            job.check()
            if any(sha256(q)!=h for q,h in inputs.items()):raise ValueError('Pinned clearance input bytes changed')
            if any(not sha256(ROOT/'scripts'/n)==sha256(output/'implementation'/n)==h for n,h in methods.items()):raise ValueError('Worker implementation bytes changed')
            result=dict(schema=SCHEMA,status='complete',at=now(),request_sha256=sha256(request_path),inputs_sha256=inputs,methods_sha256=methods,
                original_native_norm_rows=len(native.caps),controls=len(x),guide_rows=model.identity['guide_scalar_rows'],guide_count=len(guides),axis_mode=axis_mode,complete_native_samples=len(job.problem.times),geometry_samples=len(job.geometry_times),
                records=records,full_geometry_selection=None if selected is None else selected['label'],
                full_geometry_selection_rule='Lowest maximum partner depth across every declared guide time, then total guide-time triangle records, stable variant/fraction order among strict original motion/vector/reference/box passing exports.',
                files_sha256={str(q.relative_to(output)):sha256(q) for q in output.rglob('*') if q.is_file() and q.name!='pipeline.json'},
                original_selected=True,quality_approved=False,release_approved=False,
                scope='Fresh pinned existing-clip multi-time partner guide job with all complete original native constraints. All requested solver variants and fractions retained, exports freshly decoded and fully motion/reference audited. '
                      'Only declared motion-feasible guide-frame-ranked selection receives full original scene geometry. No automatic storage repair, clip/library selection, engine, prompt generation or human-quality approval.')
            save(output/'result.json',result);phase('complete');return result
        except BaseException as exc:
            save(output/'failure.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc()));phase('failed');raise


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--request',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();result=run(args.request,args.output)
    print('Complete:',len(result['records']),'proposals; original selected; quality unapproved')


if __name__=='__main__':main()
