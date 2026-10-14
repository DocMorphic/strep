"""Original-reference fidelity for explicit weight-conditioned game exports."""
from pathlib import Path
import copy,shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now
from rig_asset import RigAsset
from native_support_clock import NativeSupportSampler
from native_scene_engine import SKIN_POSITION_TOLERANCE
from native_skin_export import unchanged
from verify_native_scene_engine import load


def compare(original,conditioned,animation_index,placement,times,imported_vertices):
    """Preserve non-weight data and check all original vertices at every time."""
    unchanged(original,conditioned)
    before=NativeSupportSampler(original.document,original.binary,animation_index)
    after=NativeSupportSampler(conditioned.document,conditioned.binary,animation_index)
    times=np.asarray(times,float);p,r=placement
    if (times.ndim!=1 or len(times)<2 or not np.isfinite(times).all() or times[0]<0
            or np.any(np.diff(times)<=0) or times[-1]>before.duration or before.duration!=after.duration):
        raise ValueError('Complete unchanged increasing clip clock required')
    native_errors=[];engine_errors=[]
    for time in times:
        raw=original.vertices(before.sample(float(time)))@r.T+p
        native=conditioned.vertices(after.sample(float(time)))@r.T+p
        observed=np.asarray(imported_vertices(float(time)),float)
        if observed.shape!=raw.shape or not np.isfinite(observed).all():
            raise ValueError('Complete finite original-ordered imported vertex population required')
        native_errors.append(float(np.linalg.norm(native-raw,axis=1).max()))
        engine_errors.append(float(np.linalg.norm(observed-raw,axis=1).max()))
    native_errors=np.asarray(native_errors);engine_errors=np.asarray(engine_errors)
    report=dict(samples=len(times),vertices=len(raw),native_derivative_error_m=float(native_errors.max()),
        imported_original_error_m=float(engine_errors.max()),tolerance_m=SKIN_POSITION_TOLERANCE,
        source_animation_and_non_weight_data_preserved=True,mesh_weights_changed=True,
        original_reference_fidelity_pass=bool(np.all(native_errors<=SKIN_POSITION_TOLERANCE) and np.all(engine_errors<=SKIN_POSITION_TOLERANCE)),
        quality_approved=False,release_approved=False)
    return report,dict(native_errors_m=native_errors,imported_original_errors_m=engine_errors)


def run(contacts,geometry_policy,engine_dir,originals,output):
    output=Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    if not isinstance(originals,dict) or not originals:raise ValueError('Explicit complete original actor bindings required')
    with worker_lock(),threadpool_limits(limits=1):
        scene,policy,observed,times,bindings=load(contacts,geometry_policy,engine_dir)
        if set(originals)!=set(scene.actors):raise ValueError('Every imported actor needs an original reference')
        roots={}
        for name,value in originals.items():
            if not isinstance(value,dict) or set(value)!={'path','sha256'}:raise ValueError('Exact original path/hash required')
            path=Path(value['path']).resolve()
            if path.is_relative_to(output) or not path.is_file() or sha256(path)!=value['sha256']:
                raise ValueError('Unchanged original asset outside audit output required')
            roots[name]=path;bindings[str(path)]=sha256(path)
        methods={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}
        output.mkdir();shutil.copyfile(__file__,output/'auditor.py');rows={};arrays={'times_s':times}
        for name,actor in scene.actors.items():
            report,data=compare(RigAsset.load(roots[name]),actor['rig'],actor['animation_index'],actor['placement'],times,
                lambda time:observed.actor_vertices(name,time))
            rows[name]=report;arrays.update({name+'_'+k:v for k,v in data.items()})
        np.savez_compressed(output/'observations.npz',**arrays)
        load(contacts,geometry_policy,engine_dir);scene.check_inputs()
        if (any(sha256(p)!=h for p,h in bindings.items()) or methods!={p.name:sha256(p) for p in (ROOT/'scripts').glob('*.py')}):
            raise ValueError('Original/producer/audit source changed')
        result=dict(schema='strep-conditioned-skin-fidelity-v1',at=now(),status='complete',actors=rows,
            all_original_reference_fidelity_pass=all(r['original_reference_fidelity_pass'] for r in rows.values()),
            original_actor_bindings=copy.deepcopy(originals),source_bindings_sha256=bindings,implementation_sha256=methods,
            observations_sha256=sha256(output/'observations.npz'),additional_engine_executions=0,
            original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,
            scope='Completed actual engine observations compared against immutable original assets before weight conditioning. Full original-order vertices and declared clock; unchanged animation/non-weight data. Export-relative checks alone cannot hide original-reference drift. No renderer/physics/live/continuous/human approval.')
        save(output/'result.json',result);return result
