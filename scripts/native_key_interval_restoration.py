"""Bounded repeated native-key correction with complete decoded acceptance."""
import argparse
import copy
from pathlib import Path
import shutil
import time
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_key_interval_model import KeyIntervalModel
from native_scene_conic import direction,solver_identity
from native_key_cached_recourse import validate as validate_recourse,search_model,attempt as repair_attempt
from native_scene_contacts import SceneContacts,fields
from native_scene_geometry import evaluate_to_archive
from audit_native_key_initializer import require
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-key-interval-restoration-v1'


def geometry_face_state(report):
    states={}
    def add(key,faces):
        require(isinstance(faces,list) and all(type(i) is int and i>=0 for i in faces) and len(faces)==len(set(faces)), 'Complete distinct degenerate-face IDs required')
        states[key]=frozenset(faces)
    for sample in report['samples']:
        t=sample['time_s']
        for actor,faces in sample['degenerate_faces'].items():add((t,'actor',actor),faces)
        for pair in sample['actor_pairs']:
            require(len(pair['surface']['degenerate_faces'])==2,'Both partner face populations required')
            for i,faces in enumerate(pair['surface']['degenerate_faces']):add((t,'pair',*pair['actors'],i),faces)
    return states


def geometry_conditions(report):
    """Each existing geometry condition is guarded separately, not averaged."""
    limit=max(report['limits']['penetration_m'],.001);ids=[];values=[]
    def add(identity,value):
        require(type(value) in (int,float,bool) or isinstance(value,np.number),'Finite scalar geometry condition required')
        require(np.isfinite(value),'Unavailable geometry scalar cannot pass');ids.append(identity);values.append(float(value))
    for sample in report['samples']:
        t=sample['time_s'];add((t,'available'),not sample['conditions_available'])
        for actor,faces in sample['degenerate_faces'].items():add((t,'degenerate',actor),len(faces))
        for row in sample['world_planes']:
            key=(t,'plane',row['actor'],row['plane']);add(key+('depth',),(row['maximum_depth_m']-report['limits']['penetration_m'])/limit)
            add(key+('failed',),not row['passed'])
        for row in sample['actor_objects']:
            key=(t,'object',row['actor'],row['object']);state=row['containment']['status']
            require(state in ('outside','near-surface','inside','unavailable'),'Known primitive containment state required')
            add(key+('depth',),(row['maximum_depth_upper_m']-report['limits']['penetration_m'])/limit)
            add(key+('containment',),dict(outside=0,**{'near-surface':1},inside=2,unavailable=3)[state])
            add(key+('center-depth',),abs(row['containment'].get('signed_center_distance_m',0.))/limit if state=='inside' else 0.)
            add(key+('failed',),not row['passed'])
        for row in sample['actor_pairs']:
            key=(t,'pair',*row['actors']);add(key+('crossings',),len(row['surface']['records']))
            add(key+('degenerate',),sum(len(faces) for faces in row['surface']['degenerate_faces']));add(key+('failed',),not row['passed'])
            for measure in row['vertex_containment']:
                part=key+(measure['source'],measure['target'])
                add(part+('unavailable',),not measure['available'])
                add(part+('depth',),(measure.get('max_depth_m',0.)-report['limits']['penetration_m'])/limit)
                add(part+('contained',),measure.get('vertices_over_tolerance',0))
    require(len(ids)==len(set(ids)) and bool(ids),'Distinct complete geometry condition identities required')
    geometry_face_state(report)
    return ids,np.asarray(values,float)


def validate(recipe):
    require(isinstance(recipe,dict) and len({'producer','seed'}&set(recipe))==1,'Choose exactly one initializer or explicit seed source')
    source='producer' if 'producer' in recipe else 'seed'
    fields(recipe,('schema',source,'active_keys','iterations','trust','difference_step','backoffs','maximum_seconds')
        +(('active_nodes',) if 'active_nodes' in recipe else ())
        +(('native_recourse',) if 'native_recourse' in recipe else ()),'interval restoration recipe')
    require(recipe['schema']==SCHEMA,'Explicit native-key interval restoration required')
    if source=='producer':
        fields(recipe['producer'],('path','result_sha256','request_sha256'),'original-bound initializer')
        require(type(recipe['producer']['path']) is str and bool(recipe['producer']['path']),'Explicit initializer path required')
        for key in ('result_sha256','request_sha256'):require(type(recipe['producer'][key]) is str and len(recipe['producer'][key])==64,'Trusted initializer digests required')
    else:
        fields(recipe['seed'],('contacts','geometry','request','controls'),'explicit original-bound seed')
        for entry in recipe['seed'].values():
            fields(entry,('path','sha256'),'original seed input')
            require(type(entry['path']) is str and bool(entry['path']),'Explicit seed input path required')
            require(type(entry['sha256']) is str and len(entry['sha256'])==64
                and all(c in '0123456789abcdef' for c in entry['sha256']),'Trusted lowercase seed SHA256 required')
    require(type(recipe['iterations']) is int and 1<=recipe['iterations']<=4,'Choose 1-4 bounded interval iterations')
    require(type(recipe['backoffs']) is int and 1<=recipe['backoffs']<=10,'Choose 1-10 actual decoded backoffs')
    for key,lo,hi in [('trust',1e-6,.02),('difference_step',1e-6,.01),('maximum_seconds',1,750)]:
        require(type(recipe[key]) in (int,float) and np.isfinite(recipe[key]) and lo<=recipe[key]<=hi,'Finite bounded '+key+' required')
    require(isinstance(recipe['active_keys'],list) and bool(recipe['active_keys']) and all(type(v) is int for v in recipe['active_keys']), 'Explicit active native keys required')
    if 'active_nodes' in recipe:
        nodes=recipe['active_nodes']
        require(isinstance(nodes,list) and 1<=len(nodes)<=16 and all(type(n) is int and n>=0 for n in nodes)
            and len(nodes)==len(set(nodes)), 'Distinct explicit active rotation nodes required')
    if 'native_recourse' in recipe:validate_recourse(recipe['native_recourse'],recipe['trust'])
    return recipe


def build_problem(recipe,recipe_path,seed_output):
    """Load either source form without changing the original motion reference."""
    base=Path(recipe_path).resolve().parent
    if 'producer' in recipe:
        producer=recipe['producer']
        return KeyIntervalModel(base/producer['path'],producer['result_sha256'],producer['request_sha256'],recipe['active_keys'],active_nodes=recipe.get('active_nodes'))
    paths={k:(base/v['path']).resolve() for k,v in recipe['seed'].items()}
    return KeyIntervalModel.from_inputs(**paths,active_keys=recipe['active_keys'],output=seed_output,
        expected_sha256={k:v['sha256'] for k,v in recipe['seed'].items()},active_nodes=recipe.get('active_nodes'))


def evaluate(problem,value,folder):
    folder=Path(folder).resolve();require(not folder.exists(),'Fresh candidate archive required');folder.mkdir(parents=True)
    path=folder/'character.glb';index=problem.export(value,path)
    spec=copy.deepcopy(read(problem.producer/'contacts.json'));spec['actors'][problem.name].update(glb=str(path),sha256=sha256(path),animation_index=index)
    save(folder/'contacts.json',spec);digest=sha256(folder/'contacts.json');policy=copy.deepcopy(problem.policy);policy['contacts_sha256']=digest;save(folder/'geometry.json',policy)
    scene=SceneContacts(spec,folder);worlds=np.asarray([scene.actors[problem.name]['sampler'].sample(float(t)) for t in problem.times])
    norms=problem.rows(value,worlds);contact,contact_arrays=scene.evaluate();save(folder/'contact-result.json',contact);np.savez_compressed(folder/'contact-observations.npz',**contact_arrays)
    geometry,transport=evaluate_to_archive(scene,policy,digest,folder/'geometry-observations.npz');geometry.update(**transport);save(folder/'geometry-result.json',geometry)
    gaps,witnesses=problem.floor(worlds);residual=norms.residual();rates=residual[problem.edit_count:];floor_residual=-gaps/max(problem.policy['limits']['penetration_m'],.001)
    identities,geometry_residual=geometry_conditions(geometry);face_state=geometry_face_state(geometry);full=np.r_[rates,floor_residual,geometry_residual]
    positive=np.maximum(full,0);score=[float(positive.max()),float(positive@positive),int((full>0).sum())]
    root_error=float(abs(worlds[:,problem.request['root_node']]-problem.source_world[:,problem.request['root_node']]).max())
    prefix_pass=bool(np.all(residual[:problem.edit_count]<=0) and contact['passed'] and root_error==0)
    passed=bool(prefix_pass and np.all(rates<=0) and geometry['sampled_conditions_pass'])
    arrays=dict(controls=value,times_s=problem.times,uniform_times_s=problem.uniform,source_world=problem.source_world,candidate_world=worlds,
        vectors=norms.vectors,caps=norms.caps,scales=norms.scales,residual=residual,floor_gaps_m=gaps,floor_witnesses=witnesses,geometry_residual=geometry_residual,
        **{f'rate_cap_{i}':c for i,c in enumerate(problem.original_caps)})
    np.savez_compressed(folder/'observations.npz',**arrays)
    record=dict(label=folder.name,controls=value.tolist(),original_rate_failures=int((rates>0).sum()),edit_failures=int((residual[:problem.edit_count]>0).sum()),
        floor_failures=int((floor_residual>0).sum()),geometry_condition_failures=int((geometry_residual>0).sum()),geometry_conditions=len(geometry_residual),
        geometry_identity=[list(i) for i in identities],contact_pass=contact['passed'],geometry_pass=geometry['sampled_conditions_pass'],
        geometry_degenerate_faces=[dict(identity=list(i),faces=sorted(v)) for i,v in face_state.items()],
        decoded_prefix_pass=prefix_pass,sampled_conditions_pass=passed,root_error=root_error,score=score,glb_sha256=sha256(path),output_animation_index=index,
        observations_sha256=sha256(folder/'observations.npz'),geometry_result_sha256=sha256(folder/'geometry-result.json'),contact_result_sha256=sha256(folder/'contact-result.json'),
        original_selected=True,quality_approved=False,release_approved=False)
    save(folder/'probe.json',record)
    return dict(record=record,worlds=worlds,norms=norms,residual=residual,full=full,geometry=geometry,geometry_identity=identities,geometry_face_state=face_state,gaps=gaps)


def retain(before,after):
    require(before['full'].shape==after['full'].shape and before['geometry_identity']==after['geometry_identity'],'Complete unchanged condition population required')
    require(before['geometry_face_state'].keys()==after['geometry_face_state'].keys(),'Complete unchanged face populations required')
    safe=bool(after['record']['decoded_prefix_pass'] and np.all(after['full']<=np.maximum(0,before['full']))
        and all(after['geometry_face_state'][k]<=faces for k,faces in before['geometry_face_state'].items()))
    improved=bool(after['record']['score'][:2]<before['record']['score'][:2])
    return safe and improved


def run(recipe_path,output):
    recipe_path,output=Path(recipe_path).resolve(),Path(output).resolve();require(not output.exists(),'Fresh interval restoration output required')
    recipe=validate(read(recipe_path))
    require(not recipe_path.is_relative_to(output),'Original inputs must remain outside restoration output')
    if 'producer' in recipe:
        require(not output.is_relative_to((recipe_path.parent/recipe['producer']['path']).resolve()),'Original inputs must remain outside restoration output')
    else:
        require(all(not (recipe_path.parent/v['path']).resolve().is_relative_to(output) for v in recipe['seed'].values()),'Original inputs must remain outside restoration output')
    with worker_lock(),threadpool_limits(limits=1):
        problem=build_problem(recipe,recipe_path,output/'seed')
        pins={str(recipe_path):sha256(recipe_path),**problem.pins};methods={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')};solver=solver_identity()
        output.mkdir(parents=True,exist_ok='seed' in recipe);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        save(output/'request.json',dict(schema=SCHEMA,recipe=recipe,source_bindings_sha256=pins,implementation_sha256=methods,solver=solver,controls=problem.size,
            original_selected=True,quality_approved=False,release_approved=False))
        value=problem.initial.copy();current=evaluate(problem,value,output/'probes/start');records=[current['record']];history=[];started=time.monotonic();reason='iteration_limit';radius=recipe['trust']
        for iteration in range(1,recipe['iterations']+1):
            if current['record']['sampled_conditions_pass']:reason='sampled_conditions_pass';break
            if time.monotonic()-started>=recipe['maximum_seconds']:reason='time_budget';break
            folder=output/'iterations'/str(iteration);folder.mkdir(parents=True)
            system,jac,identity=problem.linearize(value,current['worlds'],radius,step=recipe['difference_step'])
            np.savez_compressed(folder/'affine-system.npz',value=value,vectors=system.vectors,caps=system.caps,scales=system.scales)
            sparse.save_npz(folder/'affine-jacobian.npz',jac);save(folder/'identity.json',identity)
            delta,info=direction(system,jac,value,problem.lower,problem.upper,radius,hard_rows=identity['hard_rows']);save(folder/'solver.json',info)
            del system,jac
            step=None;probes=[];repair_count=0;selected_label=None
            if delta is not None:
                np.savez_compressed(folder/'direction.npz',delta=delta)
                for backoff in range(recipe['backoffs']):
                    if time.monotonic()-started>=recipe['maximum_seconds']:reason='time_budget';break
                    fraction=.5**backoff;candidate_value=np.clip(value+fraction*delta,problem.lower,problem.upper)
                    candidate=evaluate(problem,candidate_value,output/'probes'/f'{iteration}-{backoff}');records.append(candidate['record'])
                    accepted=retain(current,candidate);choice=dict(label=candidate['record']['label'],fraction=fraction,accepted=accepted);probes.append(choice)
                    print(candidate['record']['label'],candidate['record']['original_rate_failures'],candidate['record']['floor_failures'],accepted,flush=True)
                    if 'native_recourse' in recipe:
                        choice['recourse']=[];config=recipe['native_recourse']
                        if not accepted and repair_count<config['attempts_per_iteration'] and time.monotonic()-started<recipe['maximum_seconds']:
                            _,eligibility=search_model(current,candidate,problem.edit_count,config)
                            if eligibility['eligible']:
                                repair_count+=1
                                repair,repaired=repair_attempt(problem,current,candidate,folder,folder/('repair-'+str(backoff)),config)
                                choice['recourse'].append(repair)
                                if repaired is not None:records.append(repaired['record'])
                                if repair['accepted']:
                                    value=np.asarray(repaired['record']['controls'],float);current=repaired;step=fraction;selected_label=repair['label'];break
                    if accepted:value=candidate_value;current=candidate;step=fraction;selected_label=candidate['record']['label'];break
            else:reason='no_direction'
            entry=dict(iteration=iteration,accepted_fraction=step,probes=probes,solver_status=info['status']);history.append(entry);save(output/'history.json',history)
            if 'native_recourse' in recipe:entry['selected_label']=selected_label;save(output/'history.json',history)
            if reason=='time_budget' or delta is None:break
            if step is None:
                radius*=.25
                if radius<1e-6:reason='no_accepted_step';break
        final=evaluate(problem,value,output/'probes/final');records.append(final['record']);problem.check()
        if 'seed' in recipe:np.savez_compressed(output/'key-controls.npz',times_s=problem.clock,controls=problem.controls(value))
        require(all(sha256(p)==h for p,h in pins.items()) and all(sha256(ROOT/'scripts'/n)==h for n,h in methods.items()),'Original inputs or methods changed')
        require(solver_identity()==solver,'Installed solver changed')
        result=dict(schema=SCHEMA,status='complete',at=now(),stop_reason=reason,probes=records,history=history,selected_controls=value.tolist(),
            source_request_sha256=sha256(output/'request.json'),sampled_conditions_pass=final['record']['sampled_conditions_pass'],
            original_rate_failures=final['record']['original_rate_failures'],floor_failures=final['record']['floor_failures'],
            all_original_caps_preserved=True,original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,
            scope='Bounded repeated interval proposals with original source limits, complete decoded edit/contact/geometry/rate checks and individual no-worsening guards. Original assets selected. No continuous collision, self-collision, dynamics, engine, semantic or human approval.')
        save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.recipe,args.output)
