"""Resume a verified standard restoration without resetting its original reference."""
import argparse,shutil,time
from pathlib import Path
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_key_interval_restoration import validate as validate_effort,evaluate,retain
from native_key_restoration_continuation import load
from native_scene_conic import direction,solver_identity
from native_scene_contacts import fields
from audit_native_key_initializer import require
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-key-continuation-job-v1'


def validate(recipe):
    fields(recipe,('schema','parent','iterations','trust','difference_step','backoffs','maximum_seconds'),'continuation job recipe')
    require(recipe['schema']==SCHEMA,'Explicit continuation job schema required')
    fields(recipe['parent'],('path','result_sha256','request_sha256','replay','replay_sha256'),'verified standard restoration parent')
    parent=recipe['parent']
    for key in ('path','replay'):require(type(parent[key]) is str and bool(parent[key]),'Explicit parent/replay path required')
    for key in ('result_sha256','request_sha256','replay_sha256'):
        require(type(parent[key]) is str and len(parent[key])==64 and all(c in '0123456789abcdef' for c in parent[key]),'Trusted lowercase SHA256 required')
    validate_effort(dict(schema='strep-native-key-interval-restoration-v1',producer={k:parent[k] for k in ('path','result_sha256','request_sha256')},
        active_keys=[1],**{k:recipe[k] for k in ('iterations','trust','difference_step','backoffs','maximum_seconds')}))
    return recipe


def start(recipe,path,output):
    parent=recipe['parent'];base=Path(path).resolve().parent
    return load(base/parent['path'],parent['result_sha256'],parent['request_sha256'],base/parent['replay'],parent['replay_sha256'],output)


def run(recipe_path,output):
    recipe_path,output=Path(recipe_path).resolve(),Path(output).resolve();require(not output.exists(),'Fresh interval restoration output required')
    recipe=validate(read(recipe_path));producer=(recipe_path.parent/recipe['parent']['path']).resolve();proof=(recipe_path.parent/recipe['parent']['replay']).resolve()
    require(not output.is_relative_to(producer) and not recipe_path.is_relative_to(output) and not proof.is_relative_to(output),'Original inputs must remain outside restoration output')
    with worker_lock(),threadpool_limits(limits=1):
        problem,value,current,receipt=start(recipe,recipe_path,output/'probes/start')
        pins={str(recipe_path):sha256(recipe_path),str(producer/'result.json'):recipe['parent']['result_sha256'],str(producer/'request.json'):recipe['parent']['request_sha256'],str(proof):recipe['parent']['replay_sha256'],**problem.pins};methods={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')};solver=solver_identity()
        archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        save(output/'request.json',dict(schema=SCHEMA,recipe=recipe,source_bindings_sha256=pins,implementation_sha256=methods,solver=solver,controls=problem.size,start_receipt_sha256=sha256(output/'probes/start/continuation.json'),
            original_selected=True,quality_approved=False,release_approved=False))
        records=[current['record']];history=[];started=time.monotonic();reason='iteration_limit';radius=recipe['trust']
        for iteration in range(1,recipe['iterations']+1):
            if current['record']['sampled_conditions_pass']:reason='sampled_conditions_pass';break
            if time.monotonic()-started>=recipe['maximum_seconds']:reason='time_budget';break
            folder=output/'iterations'/str(iteration);folder.mkdir(parents=True)
            system,jac,identity=problem.linearize(value,current['worlds'],radius,step=recipe['difference_step'])
            np.savez_compressed(folder/'affine-system.npz',value=value,vectors=system.vectors,caps=system.caps,scales=system.scales)
            sparse.save_npz(folder/'affine-jacobian.npz',jac);save(folder/'identity.json',identity)
            delta,info=direction(system,jac,value,problem.lower,problem.upper,radius,hard_rows=identity['hard_rows']);save(folder/'solver.json',info)
            step=None;probes=[]
            if delta is not None:
                np.savez_compressed(folder/'direction.npz',delta=delta)
                for backoff in range(recipe['backoffs']):
                    if time.monotonic()-started>=recipe['maximum_seconds']:reason='time_budget';break
                    fraction=.5**backoff;candidate_value=np.clip(value+fraction*delta,problem.lower,problem.upper)
                    candidate=evaluate(problem,candidate_value,output/'probes'/f'{iteration}-{backoff}');records.append(candidate['record'])
                    accepted=retain(current,candidate);probes.append(dict(label=candidate['record']['label'],fraction=fraction,accepted=accepted))
                    print(candidate['record']['label'],candidate['record']['original_rate_failures'],candidate['record']['floor_failures'],accepted,flush=True)
                    if accepted:value=candidate_value;current=candidate;step=fraction;break
            else:reason='no_direction'
            entry=dict(iteration=iteration,accepted_fraction=step,probes=probes,solver_status=info['status']);history.append(entry);save(output/'history.json',history)
            if reason=='time_budget' or delta is None:break
            if step is None:
                radius*=.25
                if radius<1e-6:reason='no_accepted_step';break
        final=evaluate(problem,value,output/'probes/final');records.append(final['record']);problem.check()
        require(all(sha256(p)==h for p,h in pins.items()) and all(sha256(ROOT/'scripts'/n)==h for n,h in methods.items()),'Original inputs or methods changed')
        require(solver_identity()==solver,'Installed solver changed')
        result=dict(schema=SCHEMA,status='complete',at=now(),stop_reason=reason,probes=records,history=history,selected_controls=value.tolist(),
            source_request_sha256=sha256(output/'request.json'),sampled_conditions_pass=final['record']['sampled_conditions_pass'],
            original_rate_failures=final['record']['original_rate_failures'],floor_failures=final['record']['floor_failures'],
            all_original_caps_preserved=True,original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,
            scope='Single-hop verified continuation from a standard restoration, with original reference preserved. Bounded repeated interval proposals with original source limits, complete decoded edit/contact/geometry/rate checks and individual no-worsening guards. Original assets selected. No continuous collision, self-collision, dynamics, engine, semantic or human approval.')
        save(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('recipe',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();run(args.recipe,args.output)
