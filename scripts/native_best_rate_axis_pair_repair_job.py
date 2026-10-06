"""Explicit fixed-control best-improvement resume repair on joint-rate support.

The legacy repair command and its study schemas remain unchanged. This command
binds the declared producer/cache format and exact model/export replay directly;
it never relabels their receipts as legacy studies or grants collision approval."""
import argparse,copy,shutil,traceback
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from native_scene_contacts import fields,scalar
from native_stored_pair_job import Job,METHODS as JOB_METHODS
from native_control_axis_surface_model import METHODS as MODEL_METHODS
from native_best_rate_storage_search import search
from native_axis_pair_repair_job import RepairJob as AxisRepairJob,SCHEMA as BASE_SCHEMA,METHODS as BASE_REPAIR_METHODS
from native_rotation_storage_repair import StorageAdjustedEdits
from native_stored_curve_proxy import StoredCurveProxy
from native_scene_geometry import evaluate_to_archive
from native_surface_model import surface_points,geometry_score
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-best-rate-axis-pair-repair-job-v1'
METHODS=tuple(sorted(set(BASE_REPAIR_METHODS)|{'native_rate_storage_search.py','native_best_rate_storage_search.py','native_best_rate_axis_pair_repair_job.py'}))


class RepairJob:
    """Explicitly resume a complete, independently replayed registered repair."""
    def __init__(self,path):
        self.path=Path(path).resolve();self.request=read(self.path);r=self.request
        fields(r,('schema','base_request','resume_result','resume_replay','settings','label'),'rate repair job')
        if r['schema']!=SCHEMA:raise ValueError('Explicit rate repair schema required')
        self.inputs={str(self.path):sha256(self.path)};self.roles={}
        for role in ('base_request','resume_result','resume_replay'):
            pin=r[role];fields(pin,('path','sha256'),'pinned '+role)
            if not isinstance(pin['path'],str) or not pin['path']:raise ValueError('Explicit pinned path required')
            p=(self.path.parent/pin['path']).resolve()
            if not p.is_file() or sha256(p)!=pin['sha256']:raise ValueError('Pinned '+role+' bytes differ')
            self.roles[role]=p;self.inputs[str(p)]=pin['sha256']
        settings=r['settings'];fields(settings,('maximum_stages','maximum_probes_per_stage'),'rate repair settings')
        for k,limit in (('maximum_stages',8),('maximum_probes_per_stage',64)):
            if type(settings[k]) is not int or not 1<=settings[k]<=limit:raise ValueError('Finite explicit repair budgets required')
        if not isinstance(r['label'],str) or not 1<=len(r['label'])<=160 or not r['label'].strip():raise ValueError('Explicit appended clip label required')
        self.base=AxisRepairJob(self.roles['base_request']);self.job=self.base.job;self.inputs.update(self.base.inputs)
        self.roles.update(self.base.roles);self.study=self.base.study;self.profile=self.base.profile;self.folder=self.base.folder
        self.value=self.base.value;self.problem=self.base.problem;self.selected=self.base.selected
        self.immutable_populations=dict(self.base.immutable_populations)
        result=read(self.roles['resume_result']);peer=read(self.roles['resume_replay']);folder=self.roles['resume_result'].parent
        if (result.get('schema')!=BASE_SCHEMA or result.get('status')!='complete' or result.get('source_study_schema')!=self.study['schema']
                or result.get('cache_lineage_bound') is not self.profile['cached'] or result.get('inputs_sha256')!=self.base.inputs
                or result.get('methods_sha256')!={n:sha256(ROOT/'scripts'/n) for n in BASE_REPAIR_METHODS}
                or result.get('controls')!=self.problem.size or result.get('selected_label')!=self.selected['label']
                or result.get('selected_fraction')!=self.selected['fraction'] or result.get('raw_geometry_score')!=self.selected['geometry_score']
                or result.get('original_selected') is not True or result.get('quality_approved') is not False or result.get('release_approved') is not False):
            raise ValueError('Complete unchanged registered repair and original selection required')
        if (read(folder/'request.json')!=self.base.request or not isinstance(result.get('records'),list) or not result['records']
                or type(result.get('tested_neighbors')) is not int or len(result['records'])!=result['tested_neighbors']+1):
            raise ValueError('Complete resume probe population and original request required')
        files=result.get('files_sha256');population={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p not in (self.roles['resume_result'],folder/'pipeline.json')}
        if not isinstance(files,dict) or population!=set(files):raise ValueError('Complete resume artifact population required')
        self.immutable_populations[folder]=(self.roles['resume_result'],population)
        for name,h in files.items():
            p=(folder/name).resolve()
            if not p.is_relative_to(folder) or not p.is_file() or sha256(p)!=h:raise ValueError('Resume artifact bytes or boundary differ')
            self.inputs[str(p)]=h
        for n,h in result['methods_sha256'].items():
            if self.inputs.get(str((folder/'implementation'/n).resolve()))!=h:raise ValueError('Complete archived resume implementation required')
        flags=('every_probe_controls_payloads_native_worlds_and_residuals_exact','every_absolute_one_neighbor_choice_verified',
            'original_rate_arrays_recomputed','original_static_reference_tracks_replayed','all_native_reference_bounds_replayed','no_receipt_schema_normalization')
        summaries=[dict(label=v['label'],failed_native_rows=v['failed_native_rows'],failed_contact_rows=v['failed_contact_rows'],absolute_choices=len(v['corrections'])) for v in result['records']]
        if (peer.get('status')!='complete' or peer.get('producer_result_sha256')!=sha256(self.roles['resume_result'])
                or peer.get('controls')!=self.problem.size or peer.get('selected_fraction')!=self.selected['fraction']
                or any(peer.get(k) is not True for k in flags) or peer.get('records')!=summaries
                or peer.get('complete_native_samples')!=len(self.problem.times) or peer.get('geometry_samples')!=len(self.job.geometry_times)
                or peer.get('native_conditions_pass') is not result.get('native_conditions_pass')
                or peer.get('geometry_conditions_pass') is not result.get('geometry_conditions_pass')
                or peer.get('quality_approved') is not False or peer.get('release_approved') is not False):
            raise ValueError('Complete exact resume probe/rate/reference replay required')
        for name,h in self.inputs.items():
            if name==str(self.path) or name==str(self.roles['resume_replay']):continue
            if peer.get('inputs_sha256',{}).get(name)!=h:raise ValueError('Complete replayed resume input and artifact bindings required')
        final=[v for v in result['records'] if v['label']==result.get('final_label')]
        if len(final)!=1 or final[0]['corrections']!=result.get('corrections') or final[0]['failed_native_rows']!=result.get('failed_native_rows'):
            raise ValueError('Exact distinct final resume probe required')
        self.start_folder=folder/result['final_label'];self.seed=copy.deepcopy(result['corrections']);self.resumed_result_sha256=sha256(self.roles['resume_result'])
        if not self.start_folder.is_relative_to(folder):raise ValueError('Resume probe must stay inside immutable study')
        with np.load(folder/'controls.npz',allow_pickle=False) as z:np.testing.assert_array_equal(z['controls'],self.value)
        with np.load(self.start_folder/'observations.npz',allow_pickle=False) as z:np.testing.assert_array_equal(z['controls'],self.value)
        editor=StorageAdjustedEdits(self.problem.edits,read(self.job.roles['storage_policy']),self.seed)
        for name in editor.actors:editor.values(name,self.value)
        self.check()

    def check(self):
        self.base.check()
        if any(sha256(p)!=h for p,h in self.inputs.items()):raise ValueError('Rate repair input bytes changed')
        for folder,(header,population) in self.immutable_populations.items():
            current={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p not in (header,folder/'pipeline.json')}
            if current!=population:raise ValueError('Immutable resume artifact population changed')


def run(request_path,output):
    output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        if output.exists():raise ValueError('Fresh immutable repair output required')
        request=RepairJob(request_path)
        if any(output.is_relative_to(folder) or folder.is_relative_to(output) for folder in request.immutable_populations):
            raise ValueError('Repair output must be outside the immutable saved study and cache source')
        job=request.job;problem=request.problem;value=request.value;selected=request.selected
        hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);(output/'implementation').mkdir();(output/'inputs').mkdir()
        for n in hashes:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
        for role,p in request.roles.items():shutil.copyfile(p,output/'inputs'/(role+p.suffix))
        save(output/'request.json',request.request);save(output/'input-bindings.json',request.inputs);save(output/'fraction-selection.json',dict(record=selected,reason='Lowest geometry score among actual centered-native and original-reference passing fractions; search guidance only.'))
        np.savez_compressed(output/'controls.npz',controls=value);policy=read(job.roles['storage_policy']);seed=request.seed;records=[];cache={}
        def phase(name,**details):save(output/'pipeline.json',dict(status='processing',phase=name,at=now(),**details));print(name,details,flush=True)
        try:
            def decode(corrections,label):
                folder=output/label;folder.mkdir();editor=StorageAdjustedEdits(problem.edits,policy,corrections);files={}
                for n in editor.actors:
                    p=folder/(n+'.glb');editor.export(n,value,p)
                    if not editor.audit(n,p,job.scene.actors[n]['animation_index'],value=value)['passed']:raise ValueError('Stored export authoring audit failed')
                    files[n]=p
                residual,worlds=problem.decoded(files,value)
                if label=='start':
                    previous=request.start_folder
                    with np.load(previous/'observations.npz',allow_pickle=False) as z:
                        np.testing.assert_array_equal(residual,z['residual'])
                        for n,w in worlds.items():
                            np.testing.assert_array_equal(w,z[n+'_worlds'])
                            if n in files and files[n].read_bytes()!=(previous/(n+'.glb')).read_bytes():raise ValueError('Initial repaired export differs from saved raw fraction')
                np.savez_compressed(folder/'observations.npz',controls=value,residual=residual,**{n+'_worlds':w for n,w in worlds.items()})
                record=dict(label=label,corrections=copy.deepcopy(corrections),failed_native_rows=int((residual>0).sum()),failed_source_rows=int((residual[:problem.protected_rows]>0).sum()),
                    failed_contact_rows=int((residual[problem.protected_rows:]>0).sum()),native_conditions_pass=bool(np.all(residual<=0)),quality_approved=False,release_approved=False)
                save(folder/'result.json',record);records.append(record);cache[label]=files;phase('stored-native-search',probe=label,failed_native_rows=record['failed_native_rows']);return residual,worlds
            settings=request.request['settings'];corrections,search_report=search(problem,value,policy,seed,decode,stages=settings['maximum_stages'],probes_per_stage=settings['maximum_probes_per_stage'])
            save(output/'search.json',search_report);files=cache[search_report['final_label']]
            residual,worlds=problem.decoded(files,value)
            with np.load(output/search_report['final_label']/'observations.npz',allow_pickle=False) as saved:
                np.testing.assert_array_equal(residual,saved['residual'])
                for n,w in worlds.items():np.testing.assert_array_equal(w,saved[n+'_worlds'])
            bounds=job.reference_bounds(files,worlds);geometry=None;library=[]
            if search_report['native_conditions_pass'] and bounds['passed']:
                phase('complete-final-geometry')
                geometry,_=evaluate_to_archive(job.scene,job.policy,sha256(job.roles['source_scene']),output/'geometry-observations.npz',actor_vertices=surface_points(problem,worlds))
                np.testing.assert_array_equal(geometry['times_s'],job.geometry_times);save(output/'geometry.json',geometry)
                folder=output/'appended';folder.mkdir();editor=StorageAdjustedEdits(problem.edits,policy,corrections)
                for n in editor.actors:
                    p=folder/(n+'.glb');index=editor.append_candidate(n,value,p,request.request['label']);rig=RigAsset.load(p);sampler=NativeSupportSampler(rig.document,rig.binary,index)
                    np.testing.assert_array_equal(np.array([sampler.sample(float(t)) for t in problem.times]),worlds[n]);library.append(dict(actor=n,animation_index=index,original_library_retained=True,complete_native_worlds_exact=True))
                save(folder/'library.json',library)
            request.check()
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(output/'implementation'/n)!=h for n,h in hashes.items()):raise ValueError('Repair implementation bytes changed')
            result=dict(resumed_result_sha256=request.resumed_result_sha256,source_study_schema=request.study['schema'],cache_lineage_bound=request.profile['cached'],schema=SCHEMA,status='complete',at=now(),original_selected=True,selected_fraction=selected['fraction'],selected_label=selected['label'],controls=problem.size,
                records=records,final_label=search_report['final_label'],corrections=corrections,tested_neighbors=search_report['tested_neighbors'],native_conditions_pass=search_report['native_conditions_pass'],
                failed_native_rows=int((residual>0).sum()),reference_bounds=bounds,geometry_assessed=geometry is not None,geometry_conditions_pass=None if geometry is None else geometry['sampled_conditions_pass'],
                geometry_score=None if geometry is None else list(geometry_score(geometry)),raw_geometry_score=selected['geometry_score'],appended_library=library,
                inputs_sha256=request.inputs,methods_sha256=hashes,files_sha256={str(p.relative_to(output)):sha256(p) for p in output.rglob('*') if p.is_file() and p.name!='pipeline.json'},
                quality_approved=False,release_approved=False,scope='Explicit registered study format, complete declared cache lineage when used, and exact model/export replay, never normalized into legacy receipts. Finite best-improvement absolute one-neighbor repair on all joint-rate support at fixed continuous controls after a pinned completed study and independently replayed registered repair. Original reference/rate/contact/geometry limits remain. Every raw probe is decoded and retained; full final geometry and separate appended variants follow native/reference pass. No exhaustive feasibility, automatic selection, engine, physics or motion-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except BaseException as exc:
            save(output/'failure.json',dict(error=str(exc),traceback=traceback.format_exc(),at=now()));save(output/'pipeline.json',dict(status='failed',at=now()));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    result=run(a.request,a.output);print('Complete repair; native',result['native_conditions_pass'],'geometry',result['geometry_conditions_pass'],'original selected')

if __name__=='__main__':main()
