"""Pinned offline reserve/restoration using a completely replayed saved model."""
import argparse,copy,shutil,traceback,types
from pathlib import Path
import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits
import native_partner_depth_restore as phase_engine
from native_affine_surface_restore import restore
from native_stored_pair_job import Job,METHODS as JOB_METHODS
from native_scene_contacts import SceneContacts,fields,scalar
from native_scene_norms import NormRows,rows
from native_stored_curve_proxy import StoredCurveProxy
from native_scene_geometry import evaluate_to_archive
from native_surface_model import surface_points,geometry_score
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-stored-surface-restore-job-v1'
METHODS=tuple(sorted(set(JOB_METHODS)|{'native_stored_surface_restore_job.py','native_affine_surface_restore.py'}))
REQUIRED=('system.npz','native-jacobian.npz','surface-jacobian.npz','blocks.json','guide-scene.json','guide-policy.json',
          'clock-reference.npz','source-rate-caps.npz','job.json','model.json','reduction.json')


class RestoreJob:
    def __init__(self,path):
        self.path=Path(path).resolve();r=read(self.path);self.request=r;self.inputs={str(self.path):sha256(self.path)};self.roles={}
        fields(r,('schema','job','study','independent_replay','settings','label'),'surface restoration job')
        if r['schema']!=SCHEMA:raise ValueError('Explicit saved-model surface restoration schema required')
        for role in ('job','study','independent_replay'):
            pin=r[role];fields(pin,('path','sha256'),'pinned '+role)
            if not isinstance(pin['path'],str) or not pin['path']:raise ValueError('Explicit pinned path required')
            p=(self.path.parent/pin['path']).resolve()
            if not p.is_file() or sha256(p)!=pin['sha256']:raise ValueError('Pinned '+role+' bytes differ')
            self.roles[role]=p;self.inputs[str(p)]=pin['sha256']
        settings=r['settings'];fields(settings,('depth_reserve_m','iterations','append_native_passing'),'restoration settings')
        scalar(settings['depth_reserve_m'],0.,.0001,'local depth reserve')
        if type(settings['iterations']) is not int or not 1<=settings['iterations']<=64:raise ValueError('Bounded interpolation iterations required')
        if type(settings['append_native_passing']) is not bool:raise ValueError('Explicit diagnostic append flag required')
        if not isinstance(r['label'],str) or not r['label'].strip() or not 1<=len(r['label'])<=160:raise ValueError('Explicit variant label required')
        self.job=Job(self.roles['job']);self.inputs.update(self.job.inputs);self.study=read(self.roles['study']);self.folder=self.roles['study'].parent
        s=self.study;proof=read(self.roles['independent_replay'])
        if (s.get('status')!='complete' or s.get('schema')!=self.job.request['schema'] or s.get('job_request_sha256')!=sha256(self.job.path)
                or s.get('inputs_sha256')!=self.job.inputs or s.get('methods_sha256')!={n:sha256(ROOT/'scripts'/n) for n in JOB_METHODS}
                or s.get('original_selected') is not True or s.get('quality_approved') is not False or s.get('release_approved') is not False):
            raise ValueError('Complete exact original study and implementation bindings required')
        files=s.get('files_sha256')
        if not isinstance(files,dict) or not files or not all(n in files for n in REQUIRED):raise ValueError('Complete saved-model artifact population required')
        for name,h in files.items():
            if not isinstance(name,str):raise ValueError('Local study artifact names required')
            p=(self.folder/name).resolve()
            if not p.is_relative_to(self.folder) or not p.is_file() or sha256(p)!=h:raise ValueError('Study artifact bytes or boundary differ')
            self.inputs[str(p)]=h
        for n,h in s['methods_sha256'].items():
            if sha256(self.folder/'implementation'/n)!=h:raise ValueError('Archived model implementation differs')
        if (proof.get('status')!='complete' or proof.get('producer_result_sha256')!=sha256(self.roles['study'])
                or proof.get('all_original_native_norms_and_jacobian_exact') is not True
                or proof.get('all_scalar_derivative_columns')!=self.job.problem.size
                or proof.get('original_rate_arrays_recomputed') is not True
                or proof.get('reference_displacement_replayed_at_all_native_times') is not True):
            raise ValueError('Complete original native/Jacobian/scalar-column replay required')
        if self.job.static_reference_keys and proof.get('original_static_reference_tracks_replayed') is not True:
            raise ValueError('Original static reference replay required')
        with np.load(self.folder/'system.npz',allow_pickle=False) as z:self.state={k:z[k].copy() for k in z.files}
        a=self.state;x=self.job.value;n=len(x)
        for key,value in (('controls',x),('lower',self.job.problem.lower),('upper',self.job.problem.upper)):
            if key not in a or not np.array_equal(a[key],value):raise ValueError('Original model controls/boxes differ')
        self.native=NormRows(a['vectors'],a['caps'],a['scales'])
        self.nj=sparse.load_npz(self.folder/'native-jacobian.npz').tocsr();self.sj=sparse.load_npz(self.folder/'surface-jacobian.npz').tocsr()
        gaps=a['gaps'];offsets=a['offsets'];ids=a['guard_ids'];self.blocks=read(self.folder/'blocks.json')
        if (gaps.ndim!=1 or not len(gaps) or not np.isfinite(gaps).all() or len(gaps)>self.job.request['settings']['maximum_rows']
                or self.nj.shape!=(self.native.vectors.size,n) or self.sj.shape!=(len(gaps),n)
                or not np.isfinite(self.nj.data).all() or not np.isfinite(self.sj.data).all()
                or self.nj.nnz+self.sj.nnz>self.job.request['settings']['maximum_nonzeros']):
            raise ValueError('Complete finite bounded original matrix population required')
        if (offsets.ndim!=1 or offsets.dtype.kind not in 'iu' or len(offsets)!=len(self.blocks)+1
                or offsets[0]!=0 or offsets[-1]!=len(gaps) or np.any(np.diff(offsets)<=0)
                or ids.ndim!=1 or ids.dtype.kind not in 'iu'):
            raise ValueError('Complete original block/witness population required')
        expected=np.array([offsets[i] for i,b in enumerate(self.blocks) if b.get('kind')=='penetrating-vertex'],int)
        if not np.array_equal(ids,expected):raise ValueError('Original depth witnesses differ')
        if (type(proof.get('original_surface_rows')) is not int or type(proof.get('exact_partner_guard_rows')) is not int
                or proof.get('original_surface_rows')!=len(gaps) or proof.get('exact_partner_guard_rows')!=len(ids)
                or s.get('surface_rows')!=len(gaps) or s.get('original_native_norms')!=len(self.native.caps)):
            raise ValueError('Original model population counts differ')
        actual,worlds=self.job.problem.decoded(self.job.files,x);current=rows(self.job.problem,x,worlds)
        if np.any(actual>0) or any(not np.array_equal(getattr(current,k),getattr(self.native,k)) for k in ('vectors','caps','scales')):
            raise ValueError('Native-feasible anchor and exact original norm population required')
        with np.load(self.folder/'clock-reference.npz',allow_pickle=False) as z:
            if not np.array_equal(z['times_s'],self.job.problem.times) or not np.array_equal(z['geometry_times_s'],self.job.geometry_times):raise ValueError('Original complete clocks differ')
            for name,w in self.job.problem.source_world.items():
                if not np.array_equal(z[name+'_reference_worlds'],w):raise ValueError('Original reference worlds differ')
        if sha256(self.folder/'source-rate-caps.npz')!=sha256(self.job.roles['source_rate_caps']) or read(self.folder/'job.json')!=self.job.request:
            raise ValueError('Original job/cap payloads differ')
        spec=copy.deepcopy(self.job.spec)
        for name,entry in spec['actors'].items():
            p=self.job.files[name] if name in self.job.files else self.job.roles['source_'+name];entry.update(glb=str(p),sha256=sha256(p))
        if read(self.folder/'guide-scene.json')!=spec:raise ValueError('Original guide scene differs')
        self.guide_digest=sha256(self.folder/'guide-scene.json');self.guide=SceneContacts(spec,self.folder)
        policy=copy.deepcopy(self.job.policy);policy['contacts_sha256']=self.guide_digest
        if read(self.folder/'guide-policy.json')!=policy:raise ValueError('Original guide policy differs')
        if settings['depth_reserve_m']>policy['limits']['penetration_m']:raise ValueError('Reserve exceeds original depth limit')
        self.policy=copy.deepcopy(policy);self.policy['limits']['penetration_m']-=settings['depth_reserve_m'];self.check()

    def check(self):
        self.job.check()
        if any(sha256(p)!=h for p,h in self.inputs.items()):raise ValueError('Restoration input bytes changed')


def solve(request,*,on_phase=None):
    real=phase_engine.solver_module();points=[];phases=[]
    class Capture:
        __version__=real.__version__;NonnegativeConeT=real.NonnegativeConeT;SecondOrderConeT=real.SecondOrderConeT;DefaultSettings=real.DefaultSettings
        @staticmethod
        def DefaultSolver(*args):
            solver=real.DefaultSolver(*args)
            class Call:
                def solve(self):
                    result=solver.solve();points.append(np.asarray(result.x,float).copy())
                    phases.append(dict(status=str(result.status),iterations=result.iterations,solve_time=getattr(result,'solve_time',None)))
                    if on_phase is not None:on_phase(points,phases)
                    return result
            return Call()
    # Inject a recorder through a private globals copy, leaving the original
    # module/function untouched, including when the solver raises.
    original=phase_engine.direction
    function=types.FunctionType(original.__code__,dict(original.__globals__,solver_module=lambda:Capture),original.__name__,original.__defaults__,original.__closure__)
    function.__kwdefaults__=original.__kwdefaults__
    a=request.state;job=request.job;trust=job.request['settings']['trust']
    delta,info,reduction=function(request.native,request.nj,a['gaps'],request.sj,a['offsets'],request.blocks,
        job.value,job.problem.lower,job.problem.upper,trust,policy=request.policy,scene=request.guide,digest=request.guide_digest)
    restoration=None
    checks=info.get('phase_checks',[])
    if (delta is not None and len(points)>=2 and len(checks)>=2 and checks[0]['accepted']
            and checks[0]['predicted_native_excess']<=0. and checks[1]['rejections']==['native_conditions']):
        lo=np.maximum(-trust,job.problem.lower-job.value);hi=np.minimum(trust,job.problem.upper-job.value)
        ends=[np.clip(job.value+np.clip(p[:-2]*trust,lo,hi),job.problem.lower,job.problem.upper)-job.value for p in points[:2]]
        delta,restoration=restore(request.native,request.nj,a['gaps'],request.sj,a['guard_ids'],*ends,lo,hi,
            depth_limit=float(request.policy['limits']['penetration_m']),depth_bound=max(0.,float(points[0][-2]))+info['phase_lock_tolerance'],
            iterations=request.request['settings']['iterations'])
    return delta,info,reduction,points,phases,restoration


def run(path,output):
    output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        if output.exists():raise ValueError('Fresh immutable restoration output required')
        request=RestoreJob(path)
        if output.is_relative_to(request.folder):raise ValueError('Correction output must be outside the immutable saved study')
        job=request.job;hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True);(output/'implementation').mkdir();(output/'inputs').mkdir()
        for n in hashes:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
        for role,p in request.roles.items():shutil.copyfile(p,output/'inputs'/(role+p.suffix))
        save(output/'request.json',request.request);save(output/'job.json',job.request);save(output/'input-bindings.json',request.inputs)
        save(output/'guidance-policy.json',request.policy)
        def phase(name,**details):save(output/'pipeline.json',dict(status='processing',phase=name,at=now(),**details));print(name,details,flush=True)
        try:
            def checkpoint(points,phases):
                np.savez_compressed(output/'phase-points.npz',**{'phase_'+str(i+1):p for i,p in enumerate(points)})
                save(output/'solver-phases.json',phases)
            phase('saved-model-direction');delta,info,reduction,points,phases,restoration=solve(request,on_phase=checkpoint)
            direction_source=('no-verified-direction' if delta is None else 'bounded-surface-restoration'
                if restoration is not None and restoration['status']=='RestoredSurfaceDirection' else 'original-phase-selection')
            save(output/'solver.json',dict(source_result=info,delta=None if delta is None else delta.tolist(),direction_source=direction_source,phases=phases))
            save(output/'restoration.json',restoration);np.savez_compressed(output/'phase-points.npz',**{'phase_'+str(i+1):p for i,p in enumerate(points)})
            save(output/'reduction.json',reduction.report)
            centered=copy.copy(job.problem);centered.edits=StoredCurveProxy(job.edits,job.value,job.files);records=[]
            if delta is not None:
                for i,fraction in enumerate(job.request['settings']['fractions']):
                    label='fraction-'+str(i).zfill(2);folder=output/label;folder.mkdir();value=np.clip(job.value+fraction*delta,job.problem.lower,job.problem.upper);files={}
                    for n in job.edits.actors:
                        p=folder/(n+'.glb');job.edits.export(n,value,p)
                        if not job.edits.audit(n,p,job.scene.actors[n]['animation_index'],value=value)['passed']:raise ValueError('Actual export authoring audit failed')
                        files[n]=p
                    actual,worlds=job.problem.decoded(files,value);smooth=centered.constraints(value,centered.worlds(value,quantized=False));bounds=job.reference_bounds(files,worlds)
                    np.savez_compressed(folder/'observations.npz',controls=value,residual=actual,centered_residual=smooth,**{n+'_worlds':w for n,w in worlds.items()})
                    phase('complete-original-geometry',label=label)
                    geometry,_=evaluate_to_archive(job.scene,job.policy,sha256(job.roles['source_scene']),folder/'geometry-observations.npz',actor_vertices=surface_points(job.problem,worlds))
                    np.testing.assert_array_equal(geometry['times_s'],job.geometry_times);save(folder/'geometry.json',geometry);library=[]
                    native_pass=bool(np.all(actual<=0))
                    if native_pass and bounds['passed'] and request.request['settings']['append_native_passing']:
                        appended=folder/'appended';appended.mkdir()
                        for n in job.edits.actors:
                            p=appended/(n+'.glb');index=job.edits.append_candidate(n,value,p,request.request['label']);rig=RigAsset.load(p);source=job.scene.actors[n]['rig']
                            if rig.document['animations'][:-1]!=source.document['animations'] or rig.binary[:len(source.binary)]!=source.binary:raise ValueError('Source library/payload changed')
                            reader=NativeSupportSampler(rig.document,rig.binary,index);np.testing.assert_array_equal(np.array([reader.sample(float(t)) for t in job.problem.times]),worlds[n])
                            library.append(dict(actor=n,path=str(p.relative_to(output)),animation_index=index,original_library_retained=True,complete_native_worlds_exact=True,diagnostic_only=True))
                    record=dict(label=label,fraction=fraction,failed_native_rows=int((actual>0).sum()),failed_contact_rows=int((actual[job.problem.protected_rows:]>0).sum()),
                        centered_failed_native_rows=int((smooth>0).sum()),native_conditions_pass=native_pass,reference_bounds=bounds,geometry_assessed=True,
                        geometry_score=list(geometry_score(geometry)),geometry_conditions_pass=geometry['sampled_conditions_pass'],
                        numerical_conditions_pass=bool(native_pass and bounds['passed'] and geometry['sampled_conditions_pass']),appended_library=library,
                        retained=False,quality_approved=False,release_approved=False)
                    save(folder/'result.json',record);records.append(record)
            request.check()
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(output/'implementation'/n)!=h for n,h in hashes.items()):raise ValueError('Restoration implementation bytes changed')
            result=dict(schema=SCHEMA,status='complete',at=now(),request_path=str(request.path),request_sha256=sha256(request.path),
                role_pins={role:dict(path=str(p),sha256=sha256(p)) for role,p in request.roles.items()},producer_model_sha256=sha256(request.roles['study']),
                independent_model_sha256=sha256(request.roles['independent_replay']),inputs_sha256=request.inputs,methods_sha256=hashes,controls=job.problem.size,
                complete_native_samples=len(job.problem.times),geometry_samples=len(job.geometry_times),surface_rows=len(request.state['gaps']),
                original_native_norms=len(request.native.caps),guidance_depth_limit_m=request.policy['limits']['penetration_m'],external_depth_limit_m=job.policy['limits']['penetration_m'],
                original_external_acceptance_unchanged=True,model_and_jacobian_rebuilt=False,direction_source=direction_source,
                surface_restoration_attempted=restoration is not None,records=records,original_selected=True,quality_approved=False,release_approved=False,
                files_sha256={str(p.relative_to(output)):sha256(p) for p in output.rglob('*') if p.is_file() and p.name!='pipeline.json'},
                scope='Pinned complete saved-model reserve/restoration and every requested actual export with original decoded/geometry acceptance. Optional appended diagnostic clips retain source libraries. No automatic selection, geometry/human/engine/release certification.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except BaseException as exc:
            save(output/'failure.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc()));save(output/'pipeline.json',dict(status='failed',at=now()));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();r=run(a.request,a.output);print('Complete:',len(r['records']),'actual fractions; original remains selected')


if __name__=='__main__':main()
