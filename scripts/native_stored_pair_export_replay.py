"""Replay every stored-pair export without its job/model/storage/proxy APIs.

Existing boundary edits, samplers, native constraints and geometry-archive
transport are reused. This is export fidelity, not an independent geometry
predicate, Jacobian, solver, engine or animation-quality certificate.
"""
import argparse,hashlib,json,shutil,traceback
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from native_scene_contacts import SceneContacts,fields,METHODS as CONTACT_METHODS
from native_scene_boundary_edit import BoundarySceneEdits
from native_scene_fit import SceneProblem,METHODS as FIT_METHODS
from native_surface_model import include_times,geometry_score
from native_scene_geometry import policy_for
from native_observation_archive import verify
from native_support_clock import NativeSupportSampler
from sampled_motion_caps import SampledMotionCaps,features
from rig_asset import RigAsset
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256,now

SCHEMA='strep-native-stored-pair-export-replay-v1'
METHODS=tuple(sorted(set(CONTACT_METHODS)|set(FIT_METHODS)|{
    'native_stored_pair_export_replay.py','native_scene_boundary_edit.py','native_surface_model.py'}))


def require(condition,message):
    if not condition:raise ValueError(message)


class ExportReplay:
    def __init__(self,path):
        self.path=Path(path).resolve();self.folder=self.path.parent;self.result=read(self.path)
        r=self.result
        require(isinstance(r,dict) and r.get('status')=='complete' and r.get('schema') in ('strep-native-stored-pair-job-v1','strep-native-stored-pair-job-v2'),
                'Completed stored-pair study required')
        require(r.get('original_selected') is True and r.get('quality_approved') is False and r.get('release_approved') is False,
                'Original selection and unapproved study contract required')
        require(isinstance(r.get('records'),list) and isinstance(r.get('inputs_sha256'),dict) and bool(r['inputs_sha256']),
                'Complete study bindings and export population required')
        self.bindings={str(self.path):sha256(self.path)}
        for name,digest in r['inputs_sha256'].items():self.bindings[str(Path(name).resolve())]=digest
        require(isinstance(r.get('files_sha256'),dict) and bool(r['files_sha256']),'Complete saved artifact bindings required')
        for name,digest in r['files_sha256'].items():
            p=(self.folder/name).resolve();require(p.is_relative_to(self.folder),'Study artifact escapes its directory')
            self.bindings[str(p)]=digest
        population={str(p.relative_to(self.folder)) for p in self.folder.rglob('*') if p.is_file() and p not in (self.path,self.folder/'pipeline.json')}
        require(population==set(r['files_sha256']),'Complete saved artifact population differs')
        require(isinstance(r.get('methods_sha256'),dict) and bool(r['methods_sha256']),'Archived producer methods required')
        for name,digest in r['methods_sha256'].items():
            require(Path(name).name==name and name.endswith('.py'),'Flat producer method names required')
            for p in (ROOT/'scripts'/name,self.folder/'implementation'/name):self.bindings[str(p)]=digest
        self.check();self.paths={}
        for role,pin in r['input_snapshots'].items():
            original=Path(pin['original_path']).resolve();snapshot=(self.folder/pin['path']).resolve()
            require(snapshot.is_relative_to(self.folder) and self.bindings.get(str(snapshot))==pin['sha256']
                    and self.bindings.get(str(original))==pin['sha256'],'Snapshot and original input identity differ')
            self.paths[role]=original
        self.job=read(self.folder/'job.json');job=self.job
        require(job['schema']==r['schema'],'Saved request schema differs')
        matches=[Path(p) for p,h in r['inputs_sha256'].items() if h==r['job_request_sha256']]
        require(any(read(p)==job for p in matches),'Saved request differs from its pinned original')
        self.scene=SceneContacts(read(self.paths['source_scene']),self.paths['source_scene'].parent)
        self.reference=SceneContacts(read(self.paths['reference_scene']),self.paths['reference_scene'].parent)
        require(self.scene.duration==self.reference.duration and set(self.scene.actors)==set(self.reference.actors),'Original reference population differs')
        self.edits=BoundarySceneEdits(read(self.paths['edit_request']),self.scene,sha256(self.paths['source_scene']),rotation_storage_policy='source-scale')
        self.policy=read(self.paths['geometry_policy']);self.geometry_times=policy_for(self.policy,self.scene,sha256(self.paths['source_scene']))[0]
        self.problem=SceneProblem(self.scene,self.edits);include_times(self.problem,self.geometry_times)
        for n in self.edits.actors:
            a,b=self.scene.actors[n],self.reference.actors[n]
            require(a['rig'].document['nodes']==b['rig'].document['nodes'] and a['rig'].joints==b['rig'].joints
                    and all(np.array_equal(getattr(a['skin'],k),getattr(b['skin'],k)) for k in ('nodes','points','weights','vertex_references')),
                    'Original rig or skin geometry differs')
            self.problem.source_world[n]=np.array([b['sampler'].sample(float(t)) for t in self.problem.times])
        require(r['complete_native_samples']==len(self.problem.times) and r['geometry_samples']==len(self.geometry_times)
                and r['controls']==self.problem.size,'Complete native population differs')
        with np.load(self.paths['source_rate_caps'],allow_pickle=False) as z:
            np.testing.assert_array_equal(z['times_s'],self.problem.uniform)
            actors={n for n in self.scene.actors if all(n+'_metric_'+str(i) in z for i in range(4))}
            require(set(z.files)=={'times_s'}|{n+'_metric_'+str(i) for n in actors for i in range(4)} and set(self.edits.actors)<=actors,
                    'Complete original rate arrays required')
            for n in actors:
                a=self.reference.actors[n];w=np.array([a['sampler'].sample(float(t)) for t in self.problem.uniform])
                caps=SampledMotionCaps(features(w,a['rig'].joints),self.problem.uniform,np.linspace(0,self.scene.duration,5),tolerance=1e-5)
                for i,c in enumerate(caps.caps):
                    require(c.dtype==z[n+'_metric_'+str(i)].dtype and np.array_equal(c,z[n+'_metric_'+str(i)]),'Original rate arrays do not recompute')
                if n in self.edits.actors:self.problem.caps[n]=caps
        with np.load(self.paths['anchor_controls'],allow_pickle=False) as z:self.anchor=self.edits.controls(z[job['anchor']['array']].astype(float))
        self.storage=read(self.paths['storage_policy']);fields(self.storage,('schema','authoring_sha256','maximum_component_steps','maximum_corrections','acknowledge_storage_adjustment'),'storage policy')
        identity=hashlib.sha256(json.dumps(self.edits.request,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        require(self.storage['schema']=='strep-native-rotation-storage-repair-v1' and self.storage['authoring_sha256']==identity
                and type(self.storage['maximum_component_steps']) is int and self.storage['maximum_component_steps']==1
                and type(self.storage['maximum_corrections']) is int and 1<=self.storage['maximum_corrections']<=64
                and self.storage['acknowledge_storage_adjustment'] is True,'Original one-neighbor storage envelope required')
        self.corrections=job['anchor']['corrections'];seen=set()
        require(isinstance(self.corrections,list) and len(self.corrections)<=self.storage['maximum_corrections'],'Bounded complete corrections required')
        for c in self.corrections:
            fields(c,('actor','node','key_index','component','step'),'absolute stored correction')
            n,node,k,component,step=[c[f] for f in ('actor','node','key_index','component','step')]
            require(n in self.edits.actors and all(type(v) is int for v in (node,k,component,step)) and 0<=component<4 and step in (-1,1),'Signed one-neighbor choice required')
            entries=[e for e in self.edits.actors[n]['tracks'] if (e['node'],e['path'])==(node,'rotation')]
            key=n,node,k,component;require(len(entries)==1 and k in entries[0]['ids'] and key not in seen,'Correction exceeds editable keys or duplicates a component');seen.add(key)
        self.static={}
        if job['schema']=='strep-native-stored-pair-job-v2':
            contract=read(self.paths['static_reference_tracks'])
            require(contract['schema']=='strep-native-static-reference-tracks-v1' and contract['source_scene_sha256']==sha256(self.paths['source_scene'])
                    and contract['reference_scene_sha256']==sha256(self.paths['reference_scene']) and contract['acknowledge_original_static_baselines'] is True,
                    'Explicit original static binding required')
            for n,tracks in contract['actors'].items():
                require(n in self.edits.actors and bool(tracks),'Edited static reference actor required')
                for row in tracks:
                    fields(row,('node','path','clock_from'),'static reference track');node=row['node'];key=n,node,row['path']
                    require(type(node) is int and row['path']=='rotation' and key not in self.static,'Distinct static rotation required')
                    entry=next(e for e in self.edits.actors[n]['tracks'] if (e['node'],e['path'])==key[1:])
                    ref=self.reference.actors[n];require(not any(c[:2]==key[1:] for c in ref['sampler'].channels),'Static baseline has an animated reference')
                    raw=np.asarray(ref['rig'].document['nodes'][node].get('rotation',[0.,0.,0.,1.]),float)
                    require(raw.shape==(4,) and np.isfinite(raw).all() and np.linalg.norm(raw)>=1e-8 and 'matrix' not in ref['rig'].document['nodes'][node],'Finite original TRS rotation required')
                    np.testing.assert_array_equal(entry['source'],np.tile((raw/np.linalg.norm(raw)).astype(np.float32),(len(entry['clock']),1)))
                    template=row['clock_from'];fields(template,('node','path'),'static clock template')
                    for actor in (self.scene.actors[n],ref):
                        matches=[c for c in actor['sampler'].channels if c[:2]==(template['node'],template['path'])]
                        require(len(matches)==1 and np.array_equal(matches[0][2],entry['clock']),'Original static template clock differs')
                    require(entry['clock'][0]==0 and float(entry['clock'][-1])==self.scene.duration,'Complete static reference clock required')
                    self.static[key]=np.tile(raw,(len(entry['clock']),1))
        self.check()

    def check(self):
        require(all(Path(p).is_file() and sha256(p)==h for p,h in self.bindings.items()),'Study inputs, artifacts or implementation bytes differ')

    def observe(self,files,value):
        value=self.edits.controls(value);require(np.all(value>=self.problem.lower) and np.all(value<=self.problem.upper),'Original control bounds exceeded')
        residual,worlds=self.problem.decoded(files,value);displacement={};tracks=[];passed=True
        for n,a in self.edits.actors.items():
            expected=self.edits.values(n,value)
            for c in self.corrections:
                if c['actor']==n:
                    key=c['node'],'rotation';k,component=c['key_index'],c['component'];nearest=np.float32(expected[key][k,component])
                    expected[key][k,component]=float(np.nextafter(nearest,np.float32(np.inf if c['step']>0 else -np.inf)))
            rig=RigAsset.load(files[n]);reader=NativeSupportSampler(rig.document,rig.binary,self.scene.actors[n]['animation_index'])
            actual={(node,path):data for node,path,t,data,mode in reader.channels}
            for key,data in expected.items():np.testing.assert_array_equal(actual[key],data)
            require(self.edits.audit(n,files[n],self.scene.actors[n]['animation_index'])['passed'],'Original authoring audit failed')
            joints=self.scene.actors[n]['rig'].joints
            maximum=float(np.linalg.norm(worlds[n][:,:,:3,3][:,joints]-self.problem.source_world[n][:,:,:3,3][:,joints],axis=2).max())
            displacement[n]=maximum;passed=passed and maximum<=a['displacement']
            for e in a['tracks']:
                key=n,e['node'],e['path'];after=next(c for c in reader.channels if c[:2]==key[1:]);refs=[c for c in self.reference.actors[n]['sampler'].channels if c[:2]==key[1:]]
                if key in self.static:before=self.static[key]
                else:
                    require(len(refs)==1 and np.array_equal(refs[0][2],after[2]),'Original reference clock missing or changed');before=refs[0][3]
                np.testing.assert_array_equal(after[2],e['clock'])
                change=float(np.rad2deg((Rotation.from_quat(before).inv()*Rotation.from_quat(after[3])).magnitude()).max()) if e['path']=='rotation' else float(np.linalg.norm(after[3]-before,axis=1).max())
                passed=passed and change<=e['maximum'];record=dict(actor=n,node=e['node'],path=e['path'],maximum_change=change,limit=e['maximum'])
                if key in self.static:record['baseline']='original-static-transform'
                tracks.append(record)
        return residual,worlds,dict(passed=bool(passed),joint_displacement_m=displacement,tracks=tracks)


def run(study,output):
    output=Path(output).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        require(not output.exists(),'Fresh immutable replay output required');replay=ExportReplay(study)
        require(not output.is_relative_to(replay.folder),'Replay output must be outside the immutable study directory')
        hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);(output/'implementation').mkdir()
        for n in hashes:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
        try:
            problem=replay.problem;base=replay.folder
            files={n:replay.paths['anchor_'+n] for n in replay.edits.actors}
            residual,worlds,bounds=replay.observe(files,replay.anchor)
            with np.load(base/'anchor-observations.npz',allow_pickle=False) as z:
                np.testing.assert_array_equal(replay.anchor,z['controls']);np.testing.assert_array_equal(residual,z['residual'])
                for n,w in worlds.items():np.testing.assert_array_equal(w,z[n+'_worlds'])
            solver=read(base/'solver.json');delta=solver['delta'];records=replay.result['records'];fractions=replay.job['settings']['fractions']
            require(len(records)==(0 if delta is None else len(fractions)),'Every requested actual export must be retained')
            if delta is not None:
                delta=np.asarray(delta,float);require(delta.shape==replay.anchor.shape and np.isfinite(delta).all(),'Finite complete correction direction required')
            summaries=[]
            for i,r in enumerate(records):
                label='fraction-'+str(i).zfill(2);require(r['label']==label and r['fraction']==fractions[i],'Export fraction order or identity differs')
                folder=base/label;require(read(folder/'result.json')==r,'Saved fraction record differs')
                value=np.clip(replay.anchor+r['fraction']*delta,problem.lower,problem.upper)
                residual,worlds,bounds=replay.observe({n:folder/(n+'.glb') for n in replay.edits.actors},value)
                with np.load(folder/'observations.npz',allow_pickle=False) as z:
                    np.testing.assert_array_equal(value,z['controls']);np.testing.assert_array_equal(residual,z['residual'])
                    for n,w in worlds.items():np.testing.assert_array_equal(w,z[n+'_worlds'])
                require(bounds==r['reference_bounds'],'All-native original reference bounds differ')
                require(all(type(r[k]) is int for k in ('failed_native_rows','failed_source_rows','failed_contact_rows'))
                        and r['failed_native_rows']==int((residual>0).sum())
                        and r['failed_source_rows']==int((residual[:problem.protected_rows]>0).sum())
                        and r['failed_contact_rows']==int((residual[problem.protected_rows:]>0).sum())
                        and r['native_conditions_pass'] is bool(np.all(residual<=0)),'Actual native/contact flags differ')
                geometry=read(folder/'geometry.json');verify(folder/'geometry-observations.npz')
                require(r['geometry_assessed'] is True and geometry['limits']==replay.policy['limits']
                        and np.array_equal(geometry['times_s'],replay.geometry_times)
                        and list(geometry_score(geometry))==r['geometry_score'] and geometry['sampled_conditions_pass']==r['geometry_conditions_pass'],
                        'Original complete geometry transport differs')
                require(r['numerical_conditions_pass'] is bool(np.all(residual<=0) and bounds['passed'] and geometry['sampled_conditions_pass'])
                        and r['retained'] is False and r['quality_approved'] is False and r['release_approved'] is False,'Acceptance or original-selection flags differ')
                summaries.append(dict(label=label,fraction=r['fraction'],failed_native_rows=r['failed_native_rows'],failed_contact_rows=r['failed_contact_rows'],
                    reference_bounds=bounds,geometry_conditions_pass=r['geometry_conditions_pass'],geometry_score=r['geometry_score']))
                print('Replayed',label,'native failures',r['failed_native_rows'],'geometry',r['geometry_conditions_pass'],flush=True)
            replay.check();require(all(sha256(ROOT/'scripts'/n)==h==sha256(output/'implementation'/n) for n,h in hashes.items()),'Replay implementation bytes changed')
            result=dict(schema=SCHEMA,status='complete',at=now(),producer_result_sha256=sha256(replay.path),complete_native_samples=len(problem.times),
                geometry_samples=len(replay.geometry_times),controls=problem.size,records=summaries,all_original_rate_arrays_recomputed=True,
                every_export_payload_world_and_native_observation_exact=True,reference_displacement_replayed_at_all_native_times=True,
                geometry_transport_verified=True,geometry_predicates_independently_recomputed=False,model_and_jacobian_replayed=False,
                original_selected=True,quality_approved=False,release_approved=False,inputs_sha256=replay.bindings,methods_sha256=hashes,
                scope='Read-only saved-export replay using manual absolute one-neighbor choices and existing boundary/sampler/native-constraint implementations. Complete exported population, original rate arrays and all-native reference bounds; saved geometry transport only. No job/model/storage/proxy imports, geometry predicate, Jacobian, solver, engine or human-quality certificate.')
            save(output/'result.json',result);return result
        except BaseException as exc:
            save(output/'failure.json',dict(status='failed',at=now(),error=str(exc),traceback=traceback.format_exc()));raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();run(a.study,a.output)

if __name__=='__main__':main()
