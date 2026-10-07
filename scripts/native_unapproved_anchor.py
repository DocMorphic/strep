"""Assemble a motion-feasible internal seed without geometry or asset approval."""
import argparse,copy,shutil
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from native_stored_pair_job import Job,METHODS as JOB_METHODS
from native_scene_norms import rows
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-unapproved-anchor-v1'
METHODS=tuple(sorted(set(JOB_METHODS)|{'native_unapproved_anchor.py'}))

def assemble(job_path, controls_path, actor_files, output, *, array='controls'):
    """Keep original constraints, storage choices and source selection exactly.

    Geometry is deliberately not an eligibility gate for this internal seed.
    The next genuine Job still carries the original geometry policy, and no
    clip is appended, selected, published to an engine or approved here.
    """
    job_path,controls_path,output=[Path(p).resolve() for p in (job_path,controls_path,output)]
    with worker_lock(),threadpool_limits(limits=1):
        if output.exists():raise ValueError('Fresh internal-anchor output required')
        if not isinstance(array,str) or not array or not isinstance(actor_files,dict):
            raise ValueError('Explicit named controls and edited actor files required')
        job=Job(job_path);bindings=dict(job.inputs)
        if set(actor_files)!=set(job.edits.actors):raise ValueError('Every edited actor file required; frozen actors stay original')
        files={name:Path(p).resolve() for name,p in actor_files.items()}
        if not controls_path.is_file() or any(not p.is_file() for p in files.values()):raise ValueError('Existing candidate inputs required')
        bindings[str(controls_path)]=sha256(controls_path)
        bindings.update({str(p):sha256(p) for p in files.values()})
        if any(Path(p).is_relative_to(output) for p in bindings):raise ValueError('Output cannot contain an input')
        # Exact original request fields can be retained in another directory
        # only when its external non-anchor role paths are already absolute.
        roles=('source_scene','reference_scene','edit_request','storage_policy','geometry_policy','source_rate_caps')
        if 'static_reference_tracks' in job.request:roles+=('static_reference_tracks',)
        if any(not Path(job.request[k]['path']).is_absolute() for k in roles):raise ValueError('Absolute original role paths required')
        with np.load(controls_path,allow_pickle=False) as data:
            if array not in data or data[array].dtype.kind not in 'fiu':raise ValueError('Numeric named candidate controls required')
            value=job.edits.controls(data[array].astype(float).copy())
        step=value-job.value;trust=job.request['settings']['trust']
        if (not np.any(step!=0) or np.any(value<job.problem.lower) or np.any(value>job.problem.upper)
                or np.max(abs(step))>trust):raise ValueError('Nonzero represented step inside original control/trust box required')
        for name,p in files.items():
            if not job.edits.audit(name,p,job.scene.actors[name]['animation_index'],value=value)['passed']:
                raise ValueError('Candidate authoring/storage audit failed')
        residual,worlds=job.problem.decoded(files,value);native=rows(job.problem,value,worlds)
        bounds=job.reference_bounds(files,worlds)
        if not np.isfinite(residual).all() or np.any(residual>0) or np.any(native.residual()>0) or not bounds['passed']:
            raise ValueError('Every original decoded native norm/contact/rate/reference bound must pass')
        job.check()
        if any(sha256(p)!=h for p,h in bindings.items()):raise ValueError('Candidate input bytes changed')
        methods={name:sha256(ROOT/'scripts'/name) for name in METHODS}
        output.mkdir(parents=True);(output/'implementation').mkdir()
        for name in methods:shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name)
        copies={}
        for name,p in files.items():
            copies[name]=output/(name+'.glb');shutil.copyfile(p,copies[name])
            if sha256(p)!=sha256(copies[name]):raise ValueError('Copied candidate differs')
        control=output/'controls.npz';np.savez_compressed(control,controls=value)
        request=copy.deepcopy(job.request);pin=lambda p:dict(path=str(p),sha256=sha256(p))
        request['anchor'].update(controls=pin(control),array='controls',actor_files={n:pin(p) for n,p in copies.items()})
        if {k:v for k,v in request.items() if k!='anchor'}!={k:v for k,v in job.request.items() if k!='anchor'}:
            raise ValueError('Original non-anchor contract changed')
        path=output/'job.json';save(path,request);next_job=Job(path)
        again,decoded=next_job.problem.decoded(next_job.files,next_job.value)
        np.testing.assert_array_equal(value,next_job.value);np.testing.assert_array_equal(residual,again)
        for n,w in worlds.items():np.testing.assert_array_equal(w,decoded[n])
        if next_job.reference_bounds(next_job.files,decoded)!=bounds:raise ValueError('Original reference bounds changed')
        np.savez_compressed(output/'observations.npz',controls=value,residual=residual,vectors=native.vectors,caps=native.caps,scales=native.scales,
                            **{n+'_worlds':w for n,w in worlds.items()})
        next_job.check();job.check()
        if any(sha256(p)!=h for p,h in bindings.items()):raise ValueError('Input bytes changed')
        if any(not sha256(ROOT/'scripts'/n)==sha256(output/'implementation'/n)==h for n,h in methods.items()):
            raise ValueError('Implementation changed')
        result=dict(schema=SCHEMA,status='complete',at=now(),source_job_sha256=sha256(job_path),new_job_sha256=sha256(path),
            controls=len(value),complete_native_samples=len(job.problem.times),original_native_norm_rows=len(native.caps),
            maximum_represented_control_step=float(abs(step).max()),original_trust=trust,
            original_native_maximum_excess=float(native.residual().max()),native_conditions_pass=True,reference_bounds=bounds,
            unchanged_original_non_anchor_fields=True,unchanged_absolute_storage_choices=True,
            original_selected=True,geometry_assessed=False,geometry_approved=False,quality_approved=False,release_approved=False,
            inputs_sha256=bindings,methods_sha256=methods,
            files_sha256={str(p.relative_to(output)):sha256(p) for p in output.rglob('*') if p.is_file()},
            scope='Fresh internal proposal seed after complete decoded original native/rate/contact/reference and exact storage/authoring checks. '
                  'The genuine next Job preserves every original non-anchor field and absolute storage choice. Geometry may be worse or unassessed; '
                  'original geometry gates are preserved for later evaluation and no clip/library/source selection, transition approval, engine or quality promotion occurs.')
        save(output/'result.json',result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True);parser.add_argument('--controls',required=True)
    parser.add_argument('--array',default='controls');parser.add_argument('--actor',action='append',required=True,help='NAME=GLB')
    parser.add_argument('--out',required=True);args=parser.parse_args();files={}
    for item in args.actor:
        name,separator,path=item.partition('=')
        if not separator or not name or not path or name in files:parser.error('Distinct NAME=GLB entries required')
        files[name]=path
    result=assemble(args.job,args.controls,files,args.out,array=args.array)
    print(result['schema'],result['status'],args.out)

if __name__=='__main__':main()
