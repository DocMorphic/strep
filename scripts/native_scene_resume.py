"""Rechecked completed native-fit controls, retaining the original source epoch."""
from pathlib import Path
import shutil
import numpy as np
from strep import read,sha256


class ResumeState:
    def __init__(self, folder, contacts_digest, permissions_digest, edits):
        self.folder=Path(folder).resolve();self.bindings={}
        def file(relative):
            value=Path(relative)
            if value.is_absolute() or '..' in value.parts:raise ValueError('Relative contained resume artifacts required')
            path=(self.folder/value).resolve()
            if not path.is_relative_to(self.folder) or not path.is_file():raise ValueError('Complete contained resume artifacts required')
            self.bindings[str(path)]=sha256(path);return path
        self.file=file
        request=read(file('request.json'));result=read(file('result.json'));pipeline=read(file('pipeline.json'))
        if result['status']!='complete' or pipeline['status']!='complete' or not result['original_selected']:
            raise ValueError('Completed original-retaining native fit required for resume')
        contacts=file('contacts.json');permissions=file('permissions.json')
        if sha256(contacts)!=contacts_digest or sha256(permissions)!=permissions_digest:
            raise ValueError('Resume must retain the exact original source inputs')
        if (request['inputs_sha256'].get(request['contacts_source_path'])!=contacts_digest
                or request['inputs_sha256'].get(request['permissions_source_path'])!=permissions_digest):
            raise ValueError('Resume authored snapshots differ from original inputs')
        if request['controls']!=edits.size or set(request['actor_snapshots'])!=set(edits.scene.actors):
            raise ValueError('Resume control/actor population differs')
        authored=read(contacts)
        for name,entry in request['actor_snapshots'].items():
            if sha256(file(entry['path']))!=entry['sha256']:raise ValueError('Resume original actor snapshot changed')
            if entry['sha256']!=authored['actors'][name]['sha256']:raise ValueError('Resume actor is not its original input')
        for name,h in request['implementation_sha256'].items():
            if len(Path(name).parts)!=1 or sha256(file('implementation/'+name))!=h:
                raise ValueError('Resume method archive changed')
        if request.get('geometry_policy_sha256') is not None:
            if sha256(file('geometry-policy.json'))!=request['geometry_policy_sha256']:raise ValueError('Resume geometry snapshot changed')
        self.caps_path=file('source-rate-caps.npz')
        if sha256(self.caps_path)!=result['source_rate_caps_sha256']:raise ValueError('Resume source caps changed')
        record=read(file('probes/final/probe.json'))
        finals=[r for r in result['probes'] if r['label']=='final']
        if len(finals)!=1 or finals[0]!=record:raise ValueError('Resume final control receipt differs')
        self.controls=edits.controls(record['controls']).copy()
        if np.any(self.controls<edits.lower) or np.any(self.controls>edits.upper):raise ValueError('Resume controls exceed original boxes')
        self.expected={}
        if set(record['files_sha256'])!={'probes/final/'+n+'.glb' for n in edits.actors}:
            raise ValueError('Complete resume final edited actor population required')
        for n in edits.actors:
            relative='probes/final/'+n+'.glb';h=record['files_sha256'][relative]
            if sha256(file(relative))!=h:raise ValueError('Resume final exported actor changed')
            self.expected[n]=h
        if request['frame_contract_sha256'] is None:raise ValueError('Resume frame contract required')
        self.frame_contract=request['frame_contract_sha256'];self.rate_tolerance=result['source_rate_tolerance']
        self.prior_iterations=len(result['optimization']['history'])
        previous=request.get('resume')
        if previous is not None:
            for relative,h in previous['files_sha256'].items():
                if sha256(file('resume/'+relative))!=h:raise ValueError('Resume ancestor snapshot changed')
            count=previous['completed_primary_iterations']
            if type(count) is not int or count<0:raise ValueError('Valid completed resume iteration count required')
            self.prior_iterations+=count
        self.prior_merit=record['merit']

    def check_caps(self, problem, frame_contract):
        if self.frame_contract!=frame_contract:raise ValueError('Resume frame sampling contract differs')
        expected={'times_s':problem.uniform}
        for name,c in problem.caps.items():
            if c.tolerance!=self.rate_tolerance:raise ValueError('Resume rate tolerance differs')
            expected.update({f'{name}_metric_{i}':a for i,a in enumerate(c.caps)})
        with np.load(self.caps_path,allow_pickle=False) as stored:
            if set(stored.files)!=set(expected) or any(not np.array_equal(stored[k],v) for k,v in expected.items()):
                raise ValueError('Resume must retain original source-rate arrays')

    def check_start(self, files, residual, protected_rows):
        if set(files)!=set(self.expected) or any(sha256(files[n])!=h for n,h in self.expected.items()):
            raise ValueError('Current controls cannot replay the exact resume exports')
        if not np.all(np.asarray(residual)[:protected_rows]<=0):
            raise ValueError('Resume starting clip exceeds original protected constraints')

    def snapshot(self, output):
        output=Path(output);snapshots={}
        for path,h in self.bindings.items():
            relative=Path(path).relative_to(self.folder);target=output/relative
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
            if sha256(target)!=h:raise ValueError('Resume snapshot differs')
            snapshots[relative.as_posix()]=h
        return dict(source_directory=str(self.folder),files_sha256=snapshots,controls=self.controls.tolist(),
            prior_merit=self.prior_merit,completed_primary_iterations=self.prior_iterations,
            original_source_caps_required=True,current_start_replay_required=True,quality_approved=False)

    def check_inputs(self):
        if any(sha256(p)!=h for p,h in self.bindings.items()):raise ValueError('Resume source artifact changed')
