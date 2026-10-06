"""Pinned offline stored-centered correction job; originals remain selected."""
import argparse,copy,shutil,traceback
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from native_scene_contacts import SceneContacts,fields,scalar
from native_scene_boundary_edit import BoundarySceneEdits
from native_rotation_storage_repair import StorageAdjustedEdits
from native_stored_pair_model import model, METHODS as MODEL_METHODS
from native_scene_fit import SceneProblem,METHODS as FIT_METHODS
from native_scene_geometry import policy_for,evaluate_to_archive
from native_surface_model import include_times,surface_points,geometry_score
from native_scene_norms import rows
from native_partner_depth_guard import augment
from native_partner_depth_restore import direction
from native_scene_conic import solver_identity
from native_support_clock import NativeSupportSampler
from sampled_motion_caps import SampledMotionCaps,features
from rig_asset import RigAsset
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-stored-pair-job-v1'
METHODS=tuple(sorted(set(FIT_METHODS)|set(MODEL_METHODS)|{
    'native_stored_pair_job.py','native_partner_depth_guard.py','native_partner_depth_limit.py',
    'native_partner_depth_restore.py','native_pair_surface_reduction.py',
    'native_pair_surface_reduced_conic.py','native_pair_surface_conic.py'}))


class Job:
    def __init__(self,path):
        self.path=Path(path).resolve();self.request=read(self.path);self.inputs={str(self.path):sha256(self.path)};self.roles={}
        r=self.request
        fields(r,('schema','source_scene','reference_scene','edit_request','storage_policy','geometry_policy',
            'source_rate_caps','anchor','settings'),'stored-pair job')
        if r['schema']!=SCHEMA:raise ValueError('Explicit stored-pair job schema required')
        def pin(value,role):
            fields(value,('path','sha256'),'pinned '+role)
            if not isinstance(value['path'],str) or not value['path']:raise ValueError('Explicit pinned file path required')
            p=(self.path.parent/value['path']).resolve()
            if not p.is_file() or sha256(p)!=value['sha256']:raise ValueError('Pinned '+role+' bytes differ')
            self.inputs[str(p)]=value['sha256'];self.roles[role]=p;return p
        self.pin=pin
        for role in ('source_scene','reference_scene','edit_request','storage_policy','geometry_policy','source_rate_caps'):pin(r[role],role)
        a=r['anchor'];fields(a,('controls','array','corrections','actor_files'),'stored anchor')
        if not isinstance(a['array'],str) or not a['array'] or not isinstance(a['actor_files'],dict):raise ValueError('Explicit anchor array and actor files required')
        control_path=pin(a['controls'],'anchor_controls')
        with np.load(control_path,allow_pickle=False) as data:
            if a['array'] not in data or data[a['array']].dtype.kind not in 'fiu':raise ValueError('Numeric named anchor controls required')
            self.value=data[a['array']].astype(float).copy()
        for n in a['actor_files']:SceneContacts.name(n)
        self.files={n:pin(v,'anchor_'+n) for n,v in a['actor_files'].items()}
        settings=r['settings'];fields(settings,('trust','difference_step','maximum_rows','maximum_nonzeros','fractions'),'job settings')
        scalar(settings['trust'],1e-6,.02,'trust');scalar(settings['difference_step'],1e-6,.01,'difference step')
        for k,maximum in (('maximum_rows',400000),('maximum_nonzeros',60000000)):
            if type(settings[k]) is not int or not 1<=settings[k]<=maximum:raise ValueError('Bounded complete-model resource settings required')
        f=settings['fractions']
        if not isinstance(f,list) or not 1<=len(f)<=8:raise ValueError('Choose one to eight explicit fractions')
        for v in f:scalar(v,1e-4,1.,'fraction')
        if any(a<=b for a,b in zip(f,f[1:])):raise ValueError('Unique descending fractions required')
        self.spec=read(self.roles['source_scene']);self.scene=SceneContacts(self.spec,self.roles['source_scene'].parent)
        self.reference=SceneContacts(read(self.roles['reference_scene']),self.roles['reference_scene'].parent)
        for role,scene in (('source',self.scene),('reference',self.reference)):
            self.inputs.update(scene.inputs)
            for n,entry in read(self.roles[role+'_scene'])['actors'].items():self.roles[role+'_'+n]=(self.roles[role+'_scene'].parent/entry['glb']).resolve()
        if self.scene.duration!=self.reference.duration or set(self.scene.actors)!=set(self.reference.actors):raise ValueError('Reference must retain actor population and duration')
        for n,a in self.scene.actors.items():
            b=self.reference.actors[n]
            if (a['rig'].document['nodes']!=b['rig'].document['nodes'] or a['rig'].joints!=b['rig'].joints
                    or any(not np.array_equal(getattr(a['skin'],k),getattr(b['skin'],k)) for k in ('nodes','points','weights','vertex_references'))):
                raise ValueError('Source and reference must retain the exact rig and skin geometry')
        digest=sha256(self.roles['source_scene']);self.policy=read(self.roles['geometry_policy'])
        self.geometry_times=policy_for(self.policy,self.scene,digest)[0]
        base=BoundarySceneEdits(read(self.roles['edit_request']),self.scene,digest,rotation_storage_policy='source-scale')
        self.edits=StorageAdjustedEdits(base,read(self.roles['storage_policy']),r['anchor']['corrections'])
        if set(self.files)!=set(base.actors):raise ValueError('Exact edited anchor actor population required')
        self.value=base.controls(self.value)
        for n,p in self.files.items():
            if not self.edits.audit(n,p,self.scene.actors[n]['animation_index'],value=self.value)['passed']:raise ValueError('Anchor authoring audit failed')
        self.problem=SceneProblem(self.scene,self.edits);include_times(self.problem,self.geometry_times)
        # Restore original references only for edited actors; frozen playback is actual source motion.
        for n in base.actors:self.problem.source_world[n]=np.array([self.reference.actors[n]['sampler'].sample(float(t)) for t in self.problem.times])
        with np.load(self.roles['source_rate_caps'],allow_pickle=False) as data:
            np.testing.assert_array_equal(data['times_s'],self.problem.uniform)
            actors={n for n in self.scene.actors if all(n+'_metric_'+str(i) in data for i in range(4))}
            expected={'times_s'}|{n+'_metric_'+str(i) for n in actors for i in range(4)}
            if set(data.files)!=expected or not set(base.actors)<=actors:raise ValueError('Complete original rate arrays required for every edited actor')
            for n in actors:
                ref=self.reference.actors[n];worlds=np.array([ref['sampler'].sample(float(t)) for t in self.problem.uniform])
                caps=SampledMotionCaps(features(worlds,ref['rig'].joints),self.problem.uniform,np.linspace(0,self.scene.duration,5),tolerance=1e-5)
                for i,v in enumerate(caps.caps):
                    stored=data[n+'_metric_'+str(i)]
                    if stored.dtype!=v.dtype or not np.array_equal(stored,v):raise ValueError('Rate caps must exactly recompute from pinned reference motion')
                if n in base.actors:self.problem.caps[n]=caps
        for n,actor in base.actors.items():
            for e in actor['tracks']:
                matches=[c for c in self.reference.actors[n]['sampler'].channels if c[:2]==(e['node'],e['path'])]
                if len(matches)!=1 or not np.array_equal(matches[0][2],e['clock']):raise ValueError('Permitted tracks require matching original reference clocks')
        self.check()

    def check(self):
        if any(sha256(p)!=h for p,h in self.inputs.items()):raise ValueError('Job input bytes changed')

    def reference_bounds(self,files,worlds):
        passed=True;displacement={};tracks=[]
        for n,actor in self.edits.actors.items():
            ids=self.scene.actors[n]['rig'].joints
            maximum=float(np.linalg.norm(worlds[n][:,ids,:3,3]-self.problem.source_world[n][:,ids,:3,3],axis=2).max())
            displacement[n]=maximum;passed=passed and maximum<=actor['displacement']
            rig=RigAsset.load(files[n]);sampler=NativeSupportSampler(rig.document,rig.binary,self.scene.actors[n]['animation_index'])
            for e in actor['tracks']:
                before=next(c for c in self.reference.actors[n]['sampler'].channels if c[:2]==(e['node'],e['path']))
                after=next(c for c in sampler.channels if c[:2]==(e['node'],e['path']))
                if not np.array_equal(before[2],after[2]):raise ValueError('Export changed original reference key clock')
                change=float(np.rad2deg((Rotation.from_quat(before[3]).inv()*Rotation.from_quat(after[3])).magnitude()).max()) if e['path']=='rotation' else float(np.linalg.norm(after[3]-before[3],axis=1).max())
                passed=passed and change<=e['maximum'];tracks.append(dict(actor=n,node=e['node'],path=e['path'],maximum_change=change,limit=e['maximum']))
        return dict(passed=bool(passed),joint_displacement_m=displacement,tracks=tracks)


def run(request_path,output):
    output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        if output.exists():raise ValueError('Fresh output directory required; prior jobs are immutable')
        job=Job(request_path);settings=job.request['settings'];hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True);(output/'implementation').mkdir();(output/'inputs').mkdir()
        snapshots={}
        for role,path in job.roles.items():
            target=output/'inputs'/(role+path.suffix);shutil.copyfile(path,target);snapshots[role]=dict(path=str(target.relative_to(output)),sha256=sha256(target),original_path=str(path))
        for n in hashes:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
        save(output/'job.json',job.request);save(output/'input-snapshots.json',snapshots)
        for role,name in (('edit_request','request.json'),('storage_policy','storage-policy.json'),('geometry_policy','geometry-policy.json'),('source_rate_caps','source-rate-caps.npz')):shutil.copyfile(job.roles[role],output/name)
        save(output/'corrections.json',job.request['anchor']['corrections'])
        problem=job.problem;x=job.value
        np.savez_compressed(output/'clock-reference.npz',times_s=problem.times,geometry_times_s=job.geometry_times,**{n+'_reference_worlds':w for n,w in problem.source_world.items()})
        def phase(name,**extra):save(output/'pipeline.json',dict(status='processing',phase=name,at=now(),**extra));print(name,flush=True)
        try:
            phase('anchor-and-guide')
            spec=copy.deepcopy(job.spec)
            # Resolve frozen actors too; the guide file has a different base directory.
            for n,entry in spec['actors'].items():
                path=job.files[n] if n in job.files else job.roles['source_'+n]
                entry.update(glb=str(path),sha256=sha256(path))
            save(output/'guide-scene.json',spec);digest=sha256(output/'guide-scene.json')
            guide_scene=SceneContacts(spec,output);policy=copy.deepcopy(job.policy);policy['contacts_sha256']=digest;save(output/'guide-policy.json',policy)
            residual,decoded=problem.decoded(job.files,x)
            np.savez_compressed(output/'anchor-observations.npz',controls=x,residual=residual,**{n+'_worlds':w for n,w in decoded.items()})
            phase('complete-model')
            centered,native,nj,guides,gaps,sj,identity=model(problem,x,job.files,guide_scene,policy,digest,settings['trust'],source_policy=job.policy,
                step=settings['difference_step'],maximum_rows=settings['maximum_rows'],maximum_nonzeros=settings['maximum_nonzeros'])
            combined,cj,ids,guard=augment(native,nj,gaps,sj,guides.offsets,guides.compact.rows,x,problem.lower,problem.upper,settings['trust'])
            save(output/'model.json',identity);save(output/'blocks.json',guides.compact.rows);save(output/'guard.json',guard)
            np.savez_compressed(output/'system.npz',vectors=native.vectors,caps=native.caps,scales=native.scales,controls=x,lower=problem.lower,upper=problem.upper,
                gaps=gaps,offsets=guides.offsets,guarded_vectors=combined.vectors,guarded_caps=combined.caps,guarded_scales=combined.scales,guard_ids=ids)
            sparse.save_npz(output/'native-jacobian.npz',nj);sparse.save_npz(output/'surface-jacobian.npz',sj);sparse.save_npz(output/'guarded-native-jacobian.npz',cj)
            phase('depth-first-direction')
            delta,solver,reduction=direction(native,nj,gaps,sj,guides.offsets,guides.compact.rows,x,problem.lower,problem.upper,settings['trust'],policy=policy,scene=guide_scene,digest=digest)
            save(output/'solver.json',dict(identity=solver_identity(),result=solver,delta=None if delta is None else delta.tolist()))
            save(output/'reduction.json',reduction.report);np.savez_compressed(output/'reduction.npz',roots=reduction.roots,kinds=reduction.kinds,upper_bounds=reduction.upper_bounds,retained=reduction.retained)
            save(output/'depth-floor.json',dict(guide_policy_sha256=sha256(output/'guide-policy.json'),depth_limit_m=job.policy['limits']['penetration_m'],guard_scalar_ids=ids.tolist()))
            records=[]
            if delta is not None:
                for i,fraction in enumerate(settings['fractions']):
                    label='fraction-'+str(i).zfill(2);folder=output/label;folder.mkdir();value=np.clip(x+fraction*delta,problem.lower,problem.upper);files={}
                    for n in job.edits.actors:
                        path=folder/(n+'.glb');job.edits.export(n,value,path)
                        if not job.edits.audit(n,path,job.scene.actors[n]['animation_index'],value=value)['passed']:raise ValueError('Exported authoring audit failed')
                        files[n]=path
                    actual,worlds=problem.decoded(files,value);smooth=centered.constraints(value,centered.worlds(value,quantized=False))
                    guide_gaps=guides.gaps(surface_points(problem,worlds));affine=gaps+sj@(value-x)
                    np.savez_compressed(folder/'observations.npz',controls=value,residual=actual,guide_gaps=guide_gaps,affine_gaps=affine,**{n+'_worlds':w for n,w in worlds.items()})
                    bounds=job.reference_bounds(files,worlds);phase('complete-export-geometry',label=label)
                    geometry,_=evaluate_to_archive(job.scene,job.policy,sha256(job.roles['source_scene']),folder/'geometry-observations.npz',actor_vertices=surface_points(problem,worlds))
                    np.testing.assert_array_equal(geometry['times_s'],job.geometry_times);save(folder/'geometry.json',geometry)
                    record=dict(label=label,fraction=fraction,failed_native_rows=int((actual>0).sum()),failed_source_rows=int((actual[:problem.protected_rows]>0).sum()),
                        failed_contact_rows=int((actual[problem.protected_rows:]>0).sum()),unrounded_failed_native_rows=int((smooth>0).sum()),
                        native_conditions_pass=bool(np.all(actual<=0)),reference_bounds=bounds,geometry_assessed=True,geometry_conditions_pass=geometry['sampled_conditions_pass'],
                        geometry_score=list(geometry_score(geometry)),numerical_conditions_pass=bool(np.all(actual<=0) and bounds['passed'] and geometry['sampled_conditions_pass']),
                        retained=False,quality_approved=False,release_approved=False)
                    save(folder/'result.json',record);records.append(record)
            job.check()
            if any(sha256(ROOT/'scripts'/n)!=h or sha256(output/'implementation'/n)!=h for n,h in hashes.items()):raise ValueError('Worker implementation bytes changed')
            result=dict(schema=SCHEMA,status='complete',at=now(),original_selected=True,job_request_sha256=sha256(job.path),inputs_sha256=job.inputs,methods_sha256=hashes,
                input_snapshots=snapshots,original_rate_caps_recomputed=True,complete_native_samples=len(problem.times),geometry_samples=len(job.geometry_times),controls=problem.size,
                original_native_norms=len(native.caps),surface_rows=len(gaps),partner_guard_rows=len(ids),equivalent_encoded_rows=len(reduction.retained),solver_status=solver['status'],
                records=records,files_sha256={str(p.relative_to(output)):sha256(p) for p in output.rglob('*') if p.is_file() and p.name!='pipeline.json'},
                scope='One complete source-bound correction direction and every requested actual export/geometry audit. No storage search, automatic selection, engine or animation quality approval.',quality_approved=False,release_approved=False)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',at=now()));return result
        except BaseException as exc:
            save(output/'failure.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc()))
            save(output/'pipeline.json',dict(status='failed',at=now()));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();result=run(args.request,args.output);print('Complete:',len(result['records']),'proposals; original selected; quality unapproved')

if __name__=='__main__':main()
