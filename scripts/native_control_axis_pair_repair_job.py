"""Explicit finite storage repair for completed control-aware surface studies.

The legacy repair command and its study schemas remain unchanged. This command
binds the complete alternative producer and exact model/export replay directly;
it never relabels their receipts as legacy studies or grants collision approval."""
import argparse,copy,shutil,traceback
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from native_scene_contacts import fields,scalar
from native_stored_pair_job import Job,METHODS as JOB_METHODS
from native_control_axis_surface_model import METHODS as MODEL_METHODS
from native_rotation_storage_search import search
from native_rotation_storage_repair import StorageAdjustedEdits
from native_stored_curve_proxy import StoredCurveProxy
from native_scene_geometry import evaluate_to_archive
from native_surface_model import surface_points,geometry_score
from native_support_clock import NativeSupportSampler
from rig_asset import RigAsset
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-control-axis-pair-repair-job-v1'
STUDY_SCHEMA='strep-native-control-axis-pair-study-v1'
STUDY_METHODS=tuple(sorted(set(JOB_METHODS)|set(MODEL_METHODS)))
METHODS=tuple(sorted(set(STUDY_METHODS)|{'native_control_axis_pair_repair_job.py','native_rotation_storage_search.py','native_rotation_storage_repair.py','native_stored_curve_proxy.py'}))


class RepairJob:
    def __init__(self,path):
        self.path=Path(path).resolve();r=read(self.path);self.request=r;self.inputs={str(self.path):sha256(self.path)};self.roles={}
        fields(r,('schema','job','study','independent_replay','settings','label'),'stored repair job')
        if r['schema']!=SCHEMA:raise ValueError('Explicit stored repair job schema required')
        for role in ('job','study','independent_replay'):
            pin=r[role];fields(pin,('path','sha256'),'pinned '+role)
            if not isinstance(pin['path'],str) or not pin['path']:raise ValueError('Explicit pinned path required')
            p=(self.path.parent/pin['path']).resolve()
            if not p.is_file() or sha256(p)!=pin['sha256']:raise ValueError('Pinned '+role+' bytes differ')
            self.roles[role]=p;self.inputs[str(p)]=pin['sha256']
        settings=r['settings'];fields(settings,('maximum_stages','maximum_probes_per_stage'),'repair settings')
        for k,limit in (('maximum_stages',8),('maximum_probes_per_stage',64)):
            if type(settings[k]) is not int or not 1<=settings[k]<=limit:raise ValueError('Finite explicit repair budgets required')
        if not isinstance(r['label'],str) or not 1<=len(r['label'])<=160 or not r['label'].strip():raise ValueError('Explicit appended clip label required')
        self.job=Job(self.roles['job']);self.inputs.update(self.job.inputs);self.study=read(self.roles['study']);self.folder=self.roles['study'].parent
        study=self.study;replay=read(self.roles['independent_replay'])
        if not isinstance(study,dict) or not isinstance(replay,dict):raise ValueError('Structured completed study and replay required')
        if (study.get('status')!='complete' or study.get('schema')!=STUDY_SCHEMA or study.get('job_schema')!=self.job.request['schema'] or study.get('job_request_sha256')!=sha256(self.job.path)
                or study.get('inputs_sha256')!=self.job.inputs or study.get('methods_sha256')!={n:sha256(ROOT/'scripts'/n) for n in STUDY_METHODS}):
            raise ValueError('Completed study must bind this exact job, inputs and implementation')
        if (replay.get('status')!='complete' or replay.get('producer_result_sha256')!=sha256(self.roles['study'])
                or replay.get('all_original_native_norms_and_jacobian_exact') is not True
                or type(replay.get('all_point_derivative_columns')) is not int or replay['all_point_derivative_columns']!=self.job.problem.size
                or replay.get('every_axis_choice_scalar_gap_and_surface_jacobian_exact') is not True
                or replay.get('every_export_payload_world_native_centered_count_and_reference_bound_exact') is not True
                or replay.get('geometry_transport_verified') is not True or replay.get('records')!=study.get('records')
                or replay.get('quality_approved') is not False or replay.get('release_approved') is not False):
            raise ValueError('Complete control-aware study-bound model/export replay required')
        files=study.get('files_sha256')
        if not isinstance(files,dict) or not files:raise ValueError('Complete immutable study artifact bindings required')
        for name,digest in files.items():
            if not isinstance(name,str):raise ValueError('Study artifact names required')
            p=(self.folder/name).resolve()
            if not p.is_relative_to(self.folder) or not p.is_file() or sha256(p)!=digest:raise ValueError('Study artifact bytes or boundary differ')
            self.inputs[str(p)]=digest
        population={str(p.relative_to(self.folder)) for p in self.folder.rglob('*')
            if p.is_file() and p not in (self.roles['study'],self.folder/'pipeline.json')}
        if population!=set(files):raise ValueError('Complete saved study artifact population differs')
        if study.get('original_selected') is not True or study.get('quality_approved') is not False or study.get('release_approved') is not False:
            raise ValueError('Original selection and unapproved study contract required')
        for n,digest in study['methods_sha256'].items():
            archived=self.folder/'implementation'/n
            if self.inputs.get(str(archived.resolve()))!=digest:
                raise ValueError('Complete archived producer implementation required')
        if not isinstance(study.get('records'),list) or not study['records']:raise ValueError('Completed actual export observations required')
        choices=[];labels=set()
        for record in study['records']:
            label=record.get('label')
            if not isinstance(label,str) or not label or Path(label).name!=label or label in labels or label in ('.','..'):raise ValueError('Distinct local fraction labels required')
            labels.add(label);score=record.get('geometry_score')
            if not isinstance(score,list) or len(score)!=4:raise ValueError('Complete four-component geometry score required')
            for v in score:scalar(v,0,1e12,'geometry score')
            if record.get('unrounded_failed_native_rows')==0 and record.get('reference_bounds',{}).get('passed') is True and record.get('geometry_assessed') is True:choices.append(record)
        if study.get('complete_native_samples')!=len(self.job.problem.times) or study.get('geometry_samples')!=len(self.job.geometry_times) or study.get('controls')!=self.job.problem.size:
            raise ValueError('Complete original native/geometry population required')
        if not choices:raise ValueError('No centered-native and original-reference passing exported fraction')
        self.selected=min(choices,key=lambda c:tuple(c['geometry_score']));folder=self.folder/self.selected['label']
        needed=[folder/'observations.npz',folder/'result.json',folder/'geometry.json']+[folder/(n+'.glb') for n in self.job.edits.actors]
        if any(str(p.resolve()) not in self.inputs for p in needed):raise ValueError('Selected fraction must bind every actual observation and actor')
        if read(folder/'result.json')!=self.selected:raise ValueError('Selected result differs from completed study record')
        geometry=read(folder/'geometry.json')
        if (list(geometry_score(geometry))!=self.selected['geometry_score'] or geometry['sampled_conditions_pass']!=self.selected.get('geometry_conditions_pass')
                or geometry['limits']!=self.job.policy['limits'] or not np.array_equal(geometry['times_s'],self.job.geometry_times)):
            raise ValueError('Selected geometry must retain the actual score, original limits and complete clock')
        with np.load(folder/'observations.npz',allow_pickle=False) as data:self.value=data['controls'].copy()
        self.value=self.job.edits.controls(self.value);self.problem=copy.copy(self.job.problem);self.problem.edits=self.job.edits.base
        centered=copy.copy(self.job.problem);centered.edits=StoredCurveProxy(self.job.edits,self.job.value,self.job.files)
        if not np.all(centered.constraints(self.value,centered.worlds(self.value,quantized=False))<=0):raise ValueError('Actual centered proposal is not native feasible')
        self.check()

    def check(self):
        self.job.check()
        if any(sha256(p)!=h for p,h in self.inputs.items()):raise ValueError('Repair job input bytes changed')


def run(request_path,output):
    output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        if output.exists():raise ValueError('Fresh immutable repair output required')
        request=RepairJob(request_path)
        if output.is_relative_to(request.folder) or request.folder.is_relative_to(output):raise ValueError('Repair output must be outside the immutable saved study')
        job=request.job;problem=request.problem;value=request.value;selected=request.selected
        hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);(output/'implementation').mkdir();(output/'inputs').mkdir()
        for n in hashes:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
        for role,p in request.roles.items():shutil.copyfile(p,output/'inputs'/(role+p.suffix))
        save(output/'request.json',request.request);save(output/'input-bindings.json',request.inputs);save(output/'fraction-selection.json',dict(record=selected,reason='Lowest geometry score among actual centered-native and original-reference passing fractions; search guidance only.'))
        np.savez_compressed(output/'controls.npz',controls=value);policy=read(job.roles['storage_policy']);seed=job.request['anchor']['corrections'];records=[];cache={}
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
                    previous=request.folder/selected['label']
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
            result=dict(schema=SCHEMA,status='complete',at=now(),original_selected=True,selected_fraction=selected['fraction'],selected_label=selected['label'],controls=problem.size,
                records=records,final_label=search_report['final_label'],corrections=corrections,tested_neighbors=search_report['tested_neighbors'],native_conditions_pass=search_report['native_conditions_pass'],
                failed_native_rows=int((residual>0).sum()),reference_bounds=bounds,geometry_assessed=geometry is not None,geometry_conditions_pass=None if geometry is None else geometry['sampled_conditions_pass'],
                geometry_score=None if geometry is None else list(geometry_score(geometry)),raw_geometry_score=selected['geometry_score'],appended_library=library,
                inputs_sha256=request.inputs,methods_sha256=hashes,files_sha256={str(p.relative_to(output)):sha256(p) for p in output.rglob('*') if p.is_file() and p.name!='pipeline.json'},
                quality_approved=False,release_approved=False,scope='Explicit control-aware completed study and exact model/export replay, never normalized into legacy receipts. Finite absolute one-neighbor repair at fixed continuous controls after a pinned completed study and native/derivative replay. Original reference/rate/contact/geometry limits remain. Every raw probe is decoded and retained; full final geometry and separate appended variants follow native/reference pass. No exhaustive feasibility, automatic selection, engine, physics or motion-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except BaseException as exc:
            save(output/'failure.json',dict(error=str(exc),traceback=traceback.format_exc(),at=now()));save(output/'pipeline.json',dict(status='failed',at=now()));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    result=run(a.request,a.output);print('Complete repair; native',result['native_conditions_pass'],'geometry',result['geometry_conditions_pass'],'original selected')

if __name__=='__main__':main()
