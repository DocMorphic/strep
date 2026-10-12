"""Native-checked export repair, keeping the fitter's original scene epoch.

Search archives are motion-only probes. The fitting workflow must separately
check complete contact/surface geometry on the returned export before retention.
"""
import copy
import hashlib
from pathlib import Path
import numpy as np
from native_scene_boundary_edit import BoundarySceneEdits
from native_rotation_storage_repair import StorageAdjustedEdits,authoring_digest
from native_rotation_storage_search import search
from native_storage_continuation import StorageContinuationEdits,fingerprint,state_for
from native_scene_norms import rows
from native_support_feasibility import merit
from strep import save,sha256


class _DecodedSearchProblem:
    """Use the exact fresh key audits, including authored serialized speeds.

Norms remain the original model. Independent serialized-key arithmetic may
differ from reconstructed rotations; search acceptance uses the decoded audit.
No caller-provided residual, replacement cap or alternate source is accepted.
"""
    def __init__(self,owner):self.owner=owner;self.edits=owner.base
    def __getattr__(self,name):return getattr(self.owner.problem,name)
    def constraints(self,value,worlds=None):
        observed=self.owner.last_decoded
        if observed is None or worlds is not observed[1] or not np.array_equal(value,observed[2]):
            raise ValueError('Exact current decoded export required for storage search')
        return observed[0].copy()


class FitStorage:
    adjusted_type=StorageAdjustedEdits
    continuation_type=StorageContinuationEdits
    state_factory=staticmethod(state_for)

    def search_method(self,*args,**kwargs):
        return search(*args,**kwargs)

    def __init__(self,problem,policy,*,stages=8,probes=32):
        if type(stages) is not int or not 1<=stages<=8 or type(probes) is not int or not 1<=probes<=64:
            raise ValueError('Choose 1-8 storage stages and 1-64 probes per stage')
        self.problem=problem;editor=problem.edits
        self.continuation=editor if isinstance(editor,self.continuation_type) else None
        self.base=editor.base if self.continuation is not None else editor
        if not isinstance(self.base,BoundarySceneEdits) or self.base.scene is not problem.scene:
            raise ValueError('Original explicit boundary authoring contract required')
        self.seed=copy.deepcopy(editor.corrections if self.continuation is not None else [])
        self.adjusted_type(self.base,policy,self.seed)
        self.policy=copy.deepcopy(policy);self.policy_digest=fingerprint(policy)
        self.seed_digest=fingerprint(self.seed);self.authoring_digest=authoring_digest(self.base)
        self.stages,self.probes=stages,probes;self.last_decoded=None
        self.passing_repairs={};self.passing_repair_digests={}
        self.reference=rows(problem,problem.initial)
        self.clocks={k:getattr(problem,k).copy() for k in ('times','uniform','lower','upper')}
        self.original_worlds={k:v.copy() for k,v in problem.source_world.items()}
        self.check()

    def check(self):
        self.base.scene.check_inputs()
        if self.continuation is not None:self.continuation.check_continuation()
        if (fingerprint(self.policy)!=self.policy_digest or fingerprint(self.seed)!=self.seed_digest
                or authoring_digest(self.base)!=self.authoring_digest
                or any(not np.array_equal(getattr(self.problem,k),v) for k,v in self.clocks.items())
                or set(self.problem.source_world)!=set(self.original_worlds)
                or any(not np.array_equal(self.problem.source_world[k],v) for k,v in self.original_worlds.items())):
            raise ValueError('Original storage fitting reference changed')

    def decoded(self,files,value,editor):
        if hasattr(self.problem,'audit_outputs'):
            return self.problem.decoded(files,value,output_edits=editor)
        return self.problem.decoded(files,value)

    def evaluate(self,value,folder):
        self.check();value=self.base.controls(value).copy();folder=Path(folder).resolve()
        if np.any(value<self.problem.lower) or np.any(value>self.problem.upper):
            raise ValueError('Original control boxes remain required')
        value_key=hashlib.sha256(value.tobytes()).hexdigest()
        replay=self.passing_repairs.get(value_key)
        if replay is not None:
            if (fingerprint(replay)!=self.passing_repair_digests[value_key]
                    or any(sha256(path)!=checksum for path,checksum in replay['bindings'].items())):
                raise ValueError('Previously passing repair evidence changed')
        seed=copy.deepcopy(self.seed if replay is None else replay['corrections'])
        archive=folder/'storage-search'
        if archive.exists():raise ValueError('Fresh storage proposal archive required')
        archive.mkdir();observations={};receipts={}
        continuous_worlds=self.problem.worlds(value,quantized=False)
        continuous=self.problem.constraints(value,continuous_worlds)
        if not np.isfinite(continuous).all():raise ValueError('Complete finite intended motion required')
        unrounded_arrays=dict(controls=value,times_s=self.problem.times,residual=continuous,
            caps=self.reference.caps,scales=self.reference.scales)
        for i,(name,world) in enumerate(continuous_worlds.items()):unrounded_arrays[f'actor_{i}_worlds']=world
        np.savez_compressed(folder/'unrounded-observations.npz',**unrounded_arrays)
        unrounded_digest=sha256(folder/'unrounded-observations.npz')
        del continuous_worlds,unrounded_arrays,world

        def decode(corrections,label):
            self.check()
            if label in observations:
                residual,files,editor,checksums,observations_digest=observations[label]
                if corrections!=seed:raise ValueError('Stored start corrections changed')
                if any(sha256(files[n])!=h for n,h in checksums.items()):raise ValueError('Stored search export changed')
                fresh,worlds=self.decoded(files,value,editor);np.testing.assert_array_equal(fresh,residual)
                self.last_decoded=(fresh,worlds,value.copy());return fresh,worlds
            dest=archive/label;dest.mkdir();editor=self.adjusted_type(self.base,self.policy,corrections)
            files={};audits={}
            for i,name in enumerate(editor.actors):
                path=dest/f'actor-{i}.glb';editor.export(name,value,path);files[name]=path
                audits[name]=editor.audit(name,path,self.problem.scene.actors[name]['animation_index'],value=value)
                if not audits[name]['passed']:raise ValueError('Storage probe exceeds original authoring bounds')
            residual,worlds=self.decoded(files,value,editor)
            system=rows(self.problem,value,worlds)
            if (residual.shape!=continuous.shape or not np.isfinite(residual).all()
                    or not np.array_equal(system.caps,self.reference.caps)
                    or not np.array_equal(system.scales,self.reference.scales)):
                raise ValueError('Complete original native population/caps/scales required')
            arrays=dict(controls=value,times_s=self.problem.times,uniform_times_s=self.problem.uniform,
                residual=residual,caps=system.caps,scales=system.scales)
            for i,(name,world) in enumerate(worlds.items()):arrays[f'actor_{i}_worlds']=world
            np.savez_compressed(dest/'observations.npz',**arrays)
            speed=getattr(self.problem,'last_speed_output_audit',None)
            save(dest/'probe.json',dict(label=label,corrections=corrections,edit_audits=audits,
                actors=list(worlds),files={n:dict(path=p.name,sha256=sha256(p)) for n,p in files.items()},
                native_conditions=len(residual),native_failed=int((residual>0).sum()),native_merit=list(merit(residual)),
                rotation_speed_audit=speed,observations_sha256=sha256(dest/'observations.npz'),
                geometry_assessed=False,original_selected=True,quality_approved=False,release_approved=False))
            self.check();observations[label]=(residual,files,editor,{n:sha256(p) for n,p in files.items()},sha256(dest/'observations.npz'))
            receipts[label]=sha256(dest/'probe.json')
            self.last_decoded=(residual,worlds,value.copy());return residual,worlds

        before,_=decode(seed,'start');selected='start';search_result=None
        if replay is not None:
            if (np.any(before>0) or np.any(continuous>0)
                    or hashlib.sha256(before.tobytes()).hexdigest()!=replay['native_sha256']
                    or any(sha256(observations['start'][1][n])!=h for n,h in replay['files_sha256'].items())):
                raise ValueError('Previously passing repair differs from fresh original checks')
            status='native-repair-replayed'
        elif np.all(before<=0):status='already-native-feasible'
        elif np.any(continuous>0):status='intended-motion-failed'
        else:
            corrected,search_result=self.search_method(_DecodedSearchProblem(self),value,self.policy,seed,decode,
                stages=self.stages,probes_per_stage=self.probes)
            save(archive/'search-result.json',search_result)
            if search_result['native_conditions_pass']:
                selected=search_result['final_label'];status='native-repaired'
            else:status='native-repair-failed'
        residual,files,editor,checksums,observations_digest=observations[selected]
        for label,checksum in receipts.items():
            _,raw_files,_,raw_checksums,raw_observations=observations[label]
            if (sha256(archive/label/'probe.json')!=checksum or sha256(archive/label/'observations.npz')!=raw_observations
                    or any(sha256(raw_files[n])!=h for n,h in raw_checksums.items())):
                raise ValueError('Recorded native search probe changed')
        if (any(sha256(files[n])!=h for n,h in checksums.items())
                or sha256(archive/selected/'observations.npz')!=observations_digest):
            raise ValueError('Selected search export or complete observation changed')
        # Return only a fully passing repair; a failed search preserves the
        # original proposal and every failed search observation for diagnosis.
        copied={}
        for name,path in files.items():
            target=folder/(name+'.glb')
            if target.exists():raise ValueError('Fresh selected storage export required')
            target.write_bytes(path.read_bytes());copied[name]=target
        fresh,fresh_worlds=self.decoded(copied,value,editor)
        np.testing.assert_array_equal(fresh,residual)
        with np.load(archive/selected/'observations.npz',allow_pickle=False) as expected:
            for i,(name,worlds) in enumerate(fresh_worlds.items()):np.testing.assert_array_equal(worlds,expected[f'actor_{i}_worlds'])
        if sha256(folder/'unrounded-observations.npz')!=unrounded_digest:raise ValueError('Intended-motion observation changed')
        report=dict(status=status,selected_native_label=selected,corrections=copy.deepcopy(editor.corrections),
            native_conditions=len(residual),native_failed_before=int((before>0).sum()),native_failed_after=int((fresh>0).sum()),
            unrounded_failed=int((continuous>0).sum()),native_conditions_pass=bool(np.all(fresh<=0)),
            search_result_sha256=None if search_result is None else sha256(archive/'search-result.json'),
            unrounded_observations_sha256=unrounded_digest,
            native_probe_receipts_sha256=receipts,
            reused_repair=None if replay is None else dict(path=replay['report_path'],sha256=replay['bindings'][replay['report_path']]),
            original_authoring_sha256=self.authoring_digest,storage_policy_sha256=self.policy_digest,
            geometry_assessed=False,original_selected=True,quality_approved=False,release_approved=False)
        save(folder/'storage-repair.json',report);self.check()
        if status=='native-repaired':
            bindings={str(folder/'storage-repair.json'):sha256(folder/'storage-repair.json'),
                str(folder/'unrounded-observations.npz'):unrounded_digest}
            bindings[str(archive/'search-result.json')]=report['search_result_sha256']
            for label,checksum in receipts.items():
                bindings[str(archive/label/'probe.json')]=checksum
                _,raw_files,_,raw_checksums,raw_observations=observations[label]
                bindings[str(archive/label/'observations.npz')]=raw_observations
                bindings.update({str(path):raw_checksums[name] for name,path in raw_files.items()})
            bindings.update({str(path):sha256(path) for path in copied.values()})
            memo=dict(corrections=copy.deepcopy(editor.corrections),bindings=bindings,
                report_path=str(folder/'storage-repair.json'),native_sha256=hashlib.sha256(fresh.tobytes()).hexdigest(),
                files_sha256={name:sha256(path) for name,path in copied.items()})
            self.passing_repairs[value_key]=memo;self.passing_repair_digests[value_key]=fingerprint(memo)
        return fresh,fresh_worlds,editor,report
