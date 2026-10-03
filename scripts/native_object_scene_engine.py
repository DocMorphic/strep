"""Combine bound imported actor skins with actual native object-resource poses.

All producers must be terminal, source-identical and use unchanged recorded
methods and complete identical clocks. Complete sampled geometry is queried
again using these combined observations, rather than transferred from sources.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts
from native_scene_engine import EngineObservations, METHODS as ACTOR_METHODS, SKIN_POSITION_TOLERANCE
from native_object_asset import METHODS as OBJECT_METHODS, POSITION_LIMIT_M, BASIS_LIMIT, ObjectAsset, audit as asset_audit
from native_scene_geometry import evaluate as geometry_audit, policy_for
from strep import ROOT,read,save,sha256,now

METHODS=tuple(dict.fromkeys(ACTOR_METHODS+OBJECT_METHODS+('native_object_scene_engine.py',)))


def require(condition,message):
    if not condition:raise ValueError(message)


def method_bindings(folder,record,expected):
    values=record['implementation_sha256']
    require(set(values)==set(expected),'Complete expected producer implementation required')
    for n,h in values.items():
        require(sha256(ROOT/'scripts'/n)==sha256(folder/'implementation'/n)==h,'Producer implementation changed: '+n)


def prepare(contacts,policy_path,asset_dir,output):
    """Create a derived asset bundle and common policy without changing originals."""
    contacts,policy_path,asset_dir,output=[Path(p).resolve() for p in (contacts,policy_path,asset_dir,output)]
    require(not output.exists(),'Fresh prepared object bundle required')
    with worker_lock(),threadpool_limits(limits=1):
        source=read(asset_dir/'result.json');digest=sha256(contacts)
        require(read(asset_dir/'pipeline.json')['status']==source['status']=='complete','Complete source object asset required')
        require(source['source_contacts_sha256']==sha256(asset_dir/'source-contacts.json')==digest,'Prepare must bind the same original contact scene')
        method_bindings(asset_dir,source,OBJECT_METHODS)
        require(set(source['files_sha256'])=={'objects.glb','source-contacts.json','clock-storage.json','asset-audit.json','contact-observations.npz','engine-payload.json'},'Complete source object asset receipts required')
        for n,h in source['files_sha256'].items():require(sha256(asset_dir/n)==h,'Source object asset changed')
        scene=SceneContacts(read(contacts),contacts.parent);policy=read(policy_path);required,_,_=policy_for(policy,scene,digest)
        require(set(source['actor_snapshots'])==set(scene.actors),'Complete source actor snapshots required')
        for name,snapshot in source['actor_snapshots'].items():
            saved=(asset_dir/snapshot['path']).resolve();require(saved.is_relative_to(asset_dir),'Source actor snapshot escapes asset')
            require(sha256(saved)==snapshot['sha256']==scene.inputs[str((contacts.parent/read(contacts)['actors'][name]['glb']).resolve())],'Source actor snapshot changed')
        asset=ObjectAsset(asset_dir/'objects.glb');payload=read(asset_dir/'engine-payload.json')
        times=np.unique(np.concatenate([required,np.asarray(payload['sample_times_s'])]+
            [np.clip(o['translation'][0],0,scene.duration) for o in asset.objects.values()]))
        derived_policy=copy.deepcopy(policy);derived_policy['clock']['times_s']=times.tolist()
        policy_for(derived_policy,scene,digest)
        report,arrays=asset_audit(scene,asset,times)
        output.mkdir(parents=True);shutil.copytree(asset_dir/'implementation',output/'implementation');shutil.copytree(asset_dir/'input',output/'input')
        for name in ('objects.glb','source-contacts.json','clock-storage.json'):shutil.copyfile(asset_dir/name,output/name)
        try:
            save(output/'pipeline.json',dict(status='processing',original_selected=True))
            save(output/'common-policy.json',derived_policy);save(output/'asset-audit.json',report)
            np.savez_compressed(output/'contact-observations.npz',**arrays)
            payload['sample_times_s']=times.tolist();save(output/'engine-payload.json',payload)
            shutil.copyfile(ROOT/'scripts/native_object_scene_engine.py',output/'clock-preparation.py')
            preparation=dict(source_asset_dir=str(asset_dir),source_result_sha256=sha256(asset_dir/'result.json'),
                source_files_sha256=source['files_sha256'],source_policy_path=str(policy_path),source_policy_sha256=sha256(policy_path),
                common_policy_sha256=sha256(output/'common-policy.json'),implementation_sha256=sha256(output/'clock-preparation.py'),
                samples=len(times),policy='Union of original required geometry clock, all original object-engine audit times and actual stored object key times. Source contacts and limits unchanged.')
            result=copy.deepcopy(source);result.update(at=now(),samples=len(times),sampled_asset_conditions_pass=report['sampled_conditions_pass'],clock_preparation=preparation,
                files_sha256={n:sha256(output/n) for n in source['files_sha256']})
            require(sha256(output/'objects.glb')==source['files_sha256']['objects.glb'],'Prepared GLB bytes changed')
            scene.check_inputs();require(sha256(contacts)==digest and sha256(policy_path)==preparation['source_policy_sha256'],'Clock preparation source changed')
            require(sha256(ROOT/'scripts/native_object_scene_engine.py')==preparation['implementation_sha256'],'Clock preparation implementation changed')
            for n,h in source['files_sha256'].items():require(sha256(asset_dir/n)==h,'Source object asset changed during preparation')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


class CombinedObservations:
    def __init__(self,scene,actor,raw,times):
        self.scene=scene;self.actor=actor;self.times=np.asarray(times,float);self.objects={}
        require(self.times.ndim==1 and len(self.times)>=2 and np.isfinite(self.times).all() and np.all(np.diff(self.times)>0) and self.times[0]==0 and self.times[-1]==scene.duration,'Complete sorted combined clock required')
        require(set(raw)==set(scene.objects),'Complete original engine object population required')
        for name,rows in raw.items():
            require(len(rows)==len(times),'Incomplete object-resource clock')
            require(np.allclose([r['time_s'] for r in rows],times,rtol=0,atol=1e-14),'Object-resource clock differs')
            p=np.asarray([r['translation_m'] for r in rows],float);q=np.asarray([r['rotation_xyzw'] for r in rows],float)
            require(p.shape==(len(times),3) and q.shape==(len(times),4) and np.isfinite(p).all() and np.isfinite(q).all(),'Complete finite rigid object observations required')
            require(np.all(abs(np.linalg.norm(q,axis=1)-1)<1e-6),'Unit-range actual object rotations required')
            self.objects[name]=(p,Rotation.from_quat(q).as_matrix())

    def object_poses(self,name,times):
        ids=np.searchsorted(self.times,times)
        require(not np.any(ids>=len(self.times)) and np.array_equal(self.times[ids],times),'Missing exact combined object clock')
        p,r=self.objects[name];return p[ids],r[ids]


def load(contacts,policy_path,actor_dir,object_dir):
    contacts,policy_path,actor_dir,object_dir=[Path(p).resolve() for p in (contacts,policy_path,actor_dir,object_dir)]
    require(read(actor_dir/'pipeline.json')['status']=='complete' and read(object_dir/'pipeline.json')['status']=='complete','Both producer jobs must be terminal and complete')
    a=read(actor_dir/'result.json');o=read(object_dir/'result.json')
    require(a['status']==o['status']=='complete','Complete producer results required')
    spec=read(contacts);scene=SceneContacts(spec,contacts.parent);digest=sha256(contacts);policy=read(policy_path)
    required,_,_=policy_for(policy,scene,digest)
    require(a['inputs_sha256'].get(str(contacts))==digest and a['inputs_sha256'].get(str(policy_path))==sha256(policy_path),'Actor producer must bind these exact contacts and geometry policy')
    request=read(actor_dir/'request.json');receipt=read(actor_dir/'raw-engine-receipt.json')
    require(request['inputs_sha256']==a['inputs_sha256'] and a['playback_mode']==request['playback_mode']=='native-authoring','Bound native actor authoring producer required')
    require(sha256(actor_dir/'request.json')==receipt['request_sha256'] and sha256(actor_dir/'engine-output.json')==receipt['engine_output_sha256']==a['engine_output_sha256'],'Raw actor engine receipt differs')
    require(sha256(actor_dir/'raw-engine-receipt.json')==a['raw_engine_receipt_sha256'],'Actor engine receipt changed')
    require(receipt['returncode']==0 and receipt['engine_executable_sha256']==request['engine_sha256']==a['engine_executable_sha256'],'Actor engine executable receipt differs')
    require(sha256(actor_dir/'native-observations.npz')==a['native_observations_sha256'],'Actor native observations changed')
    method_bindings(actor_dir,a,ACTOR_METHODS)
    for path,h in a['inputs_sha256'].items():require(sha256(path)==h,'Actor producer input changed')
    require(set(a['source_snapshots'])=={p for p,h in a['inputs_sha256'].items() if h!=a['engine_executable_sha256']},'Complete actor producer snapshots required')
    for path,snapshot in a['source_snapshots'].items():
        saved=(actor_dir/snapshot['path']).resolve();require(saved.is_relative_to(actor_dir),'Actor snapshot escapes producer')
        require(sha256(path)==sha256(saved)==snapshot['sha256'],'Actor producer snapshot changed')
    require(set(receipt['executed_scripts_sha256'])=={'godot_native_scene_audit.gd','native_godot_tracks.gd','native_godot_preview.gd'},'Complete executed actor scripts required')
    for n,h in receipt['executed_scripts_sha256'].items():
        require(n in ACTOR_METHODS and h==a['implementation_sha256'][n],'Unbound executed actor script')
        require(sha256(actor_dir/'project'/('audit.gd' if n=='godot_native_scene_audit.gd' else n))==h,'Executed actor script changed')
    require(set(a['animation_resources_sha256'])==set(scene.actors) and a['animation_resources_sha256']==receipt['animation_resources_sha256'],'Complete actor Animation resource receipts required')
    for name,h in a['animation_resources_sha256'].items():require(sha256(actor_dir/(name+'-animation.res'))==h,'Actor Animation resource changed')
    object_request=read(object_dir/'request.json');asset_path=Path(object_request['asset_path']).resolve();asset_dir=asset_path.parent
    asset=read(asset_dir/'result.json')
    require(asset['status']=='complete' and asset_path==asset_dir/'objects.glb','Complete actual object asset required')
    require(sha256(asset_dir/'result.json')==o['bindings']['source_result_sha256'] and asset['source_contacts_sha256']==digest,'Object producer uses another source scene')
    require(sha256(asset_dir/'source-contacts.json')==digest,'Object source snapshot differs')
    require(sha256(object_dir/'request.json')==o['bindings']['request_sha256'],'Object request changed')
    require(object_request['payload']==read(asset_dir/'engine-payload.json'),'Object engine payload differs from actual asset')
    require(o['bindings']['engine_sha256']==a['engine_executable_sha256'],'Actor and object producers use different engines')
    method_bindings(asset_dir,asset,OBJECT_METHODS)
    if 'clock_preparation' in asset:
        prepared=asset['clock_preparation'];previous=Path(prepared['source_asset_dir'])
        require(sha256(asset_dir/'clock-preparation.py')==sha256(ROOT/'scripts/native_object_scene_engine.py')==prepared['implementation_sha256'],'Clock preparation implementation changed')
        require(sha256(asset_dir/'common-policy.json')==sha256(policy_path)==prepared['common_policy_sha256'],'Prepared common geometry policy changed')
        require(sha256(prepared['source_policy_path'])==prepared['source_policy_sha256'],'Original preparation policy changed')
        require(sha256(previous/'result.json')==prepared['source_result_sha256'],'Original preparation result changed')
        for n,h in prepared['source_files_sha256'].items():require(sha256(previous/n)==h,'Original preparation asset changed')
    require(o['implementation_sha256']==asset['implementation_sha256'],'Object implementation bindings differ')
    require(set(asset['files_sha256'])=={'objects.glb','source-contacts.json','clock-storage.json','asset-audit.json','contact-observations.npz','engine-payload.json'},'Complete actual asset receipts required')
    require(set(o['files_sha256'])=={'engine-output.json','engine.log','observations.npz','native-animation.res','default-import-audit.json','native-authoring-audit.json'},'Complete object engine receipts required')
    for folder,record in ((asset_dir,asset),(object_dir,o)):
        for name,h in record['files_sha256'].items():
            path=(folder/name).resolve();require(path.is_relative_to(folder),'Producer file escapes output')
            require(sha256(path)==h,'Object producer file changed: '+name)
    require(set(asset['actor_snapshots'])==set(scene.actors),'Complete object actor snapshots required')
    for name,snapshot in asset['actor_snapshots'].items():
        saved=(asset_dir/snapshot['path']).resolve();require(saved.is_relative_to(asset_dir),'Object actor snapshot escapes producer')
        require(sha256(saved)==spec['actors'][name]['sha256']==snapshot['sha256'],'Object actor snapshot differs')
    require(sha256(object_dir/'project/audit.gd')==o['bindings']['script_sha256']==asset['implementation_sha256']['godot_native_object_asset.gd'],'Executed object script changed')
    times=np.asarray(request['sample_times_s'],float)
    require(np.array_equal(times,np.asarray(object_request['payload']['sample_times_s'])),'Complete identical actor/object clocks required')
    require(np.isfinite(times).all() and np.all(np.diff(times)>0) and times[0]==0 and times[-1]==scene.duration and np.isin(required,times).all(),'Complete declared scene clock required')
    require([c['id'] for c in request['cases']]==list(scene.actors),'Complete original actor selection required')
    for case in request['cases']:
        name=case['id'];require(case['animation_index']==spec['actors'][name]['animation_index'] and sha256(case['path'])==spec['actors'][name]['sha256'],'Actor selection differs from source')
    actor_raw=read(actor_dir/'engine-output.json')
    actor=EngineObservations(scene,actor_raw,request['cases'],times)
    raw=read(object_dir/'engine-output.json')
    require(actor_raw['engine']==a['engine']==raw['engine']==o['engine'],'Recorded engine versions differ')
    providers={mode:CombinedObservations(scene,actor,raw[mode],times) for mode in ('default-import','native-authoring')}
    bindings={str(contacts):digest,str(policy_path):sha256(policy_path),str(actor_dir/'result.json'):sha256(actor_dir/'result.json'),str(object_dir/'result.json'):sha256(object_dir/'result.json')}
    return scene,policy,actor,providers,times,bindings


def run(contacts,policy_path,actor_dir,object_dir,output):
    output=Path(output).resolve()
    require(not output.exists(),'Fresh combined engine output required')
    with worker_lock(),threadpool_limits(limits=1):
        scene,policy,actor,providers,times,bindings=load(contacts,policy_path,actor_dir,object_dir)
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS};output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        save(output/'pipeline.json',dict(status='processing',stage='full-imported-skin',original_selected=True))
        try:
            skin={};arrays={'times_s':times}
            for name,a in scene.actors.items():
                p,r=a['placement'];values=[]
                for i,t in enumerate(times):
                    native=a['rig'].vertices(a['sampler'].sample(float(t)))@r.T+p
                    values.append(float(np.linalg.norm(actor.actor_vertices(name,float(t))-native,axis=1).max()))
                    if i%100==0:save(output/'pipeline.json',dict(status='processing',stage='full-imported-skin',actor=name,completed_samples=i,total_samples=len(times),original_selected=True))
                arrays[name+'_skin_errors_m']=np.asarray(values)
                skin[name]=dict(maximum_position_error_m=max(values),limit_m=SKIN_POSITION_TOLERANCE,passed=max(values)<=SKIN_POSITION_TOLERANCE)
            contacts_by_mode={};objects_by_mode={}
            for mode,provider in providers.items():
                report,data=scene.evaluate(actor_points=actor.actor_points,object_poses=provider.object_poses)
                report.update(loaded_skin_weights_normalized=False,measurement_source='Complete imported CPU skin and actual saved object Animation resource poses')
                contacts_by_mode[mode]=report;save(output/(mode+'-contacts.json'),report)
                arrays.update({mode+'_'+k:v for k,v in data.items()});objects_by_mode[mode]={}
                for name in scene.objects:
                    p,r=scene.object_poses(name,times);q,s=provider.object_poses(name,times)
                    position=float(np.linalg.norm(q-p,axis=1).max());basis=float(abs(s-r).max())
                    objects_by_mode[mode][name]=dict(maximum_position_error_m=position,maximum_basis_error=basis,passed=position<=POSITION_LIMIT_M and basis<=BASIS_LIMIT)
            geometry,data=geometry_audit(scene,policy,sha256(contacts),
                lambda p:save(output/'pipeline.json',dict(**p,stage='combined-scene-geometry',original_selected=True)),
                actor_vertices=actor.actor_vertices,object_poses=providers['native-authoring'].object_poses)
            save(output/'geometry.json',geometry);np.savez_compressed(output/'geometry-observations.npz',**data)
            np.savez_compressed(output/'observations.npz',**arrays)
            native,_=scene.evaluate();scene.check_inputs()
            for p,h in bindings.items():require(sha256(p)==h,'Combined producer/source binding changed')
            for n,h in methods.items():require(sha256(ROOT/'scripts'/n)==sha256(archive/n)==h,'Combined audit implementation changed')
            # Revalidate every raw producer, resource and snapshot after the audit.
            load(contacts,policy_path,actor_dir,object_dir)
            passed=bool(native['passed'] and contacts_by_mode['native-authoring']['passed'] and geometry['sampled_conditions_pass']
                and all(r['pose_samples_pass'] for r in actor.reports.values()) and all(r['passed'] for r in skin.values())
                and all(r['passed'] for r in objects_by_mode['native-authoring'].values()))
            result=dict(at=now(),status='complete',samples=len(times),source_bindings_sha256=bindings,implementation_sha256=methods,
                actor_pose_reports=actor.reports,skin_errors=skin,object_pose_reports=objects_by_mode,
                source_contacts_pass=native['passed'],contacts_pass={m:r['passed'] for m,r in contacts_by_mode.items()},
                geometry_pass=geometry['sampled_conditions_pass'],all_sampled_conditions_pass=passed,
                files_sha256={n:sha256(output/n) for n in ('default-import-contacts.json','native-authoring-contacts.json','geometry.json','geometry-observations.npz','observations.npz')},
                original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,
                gpu_render_checked=False,physics_verified=False,real_time_playback_verified=False,continuous_collision_certified=False,
                scope='Complete imported CPU actor skin and actual object native-resource authoring at all original clocks. Full declared sampled scene geometry; no object/object, self/continuous, physics, runtime events or human-quality approval.')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare')
    for n in ('contacts','policy','asset','output'):q.add_argument(n,type=Path)
    q=sub.add_parser('combine')
    for n in ('contacts','policy','actor_engine','object_engine','output'):q.add_argument(n,type=Path)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.contacts,a.policy,a.asset,a.output)
    else:run(a.contacts,a.policy,a.actor_engine,a.object_engine,a.output)
