"""Bounded object handoff plus actual actor skin and complete sampled scene gates.

This CPU/headless authoring workflow preserves the original selection. Numerical
scene success is separate from playback, physical plausibility and review.
"""
import argparse,copy,shutil
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts
from native_object_asset import ObjectAsset,audit as asset_audit
from native_object_bounded_fit import METHODS as FIT_METHODS
from native_object_bounded_handoff import validate_fit,evaluate,METHODS as HANDOFF_METHODS
from native_object_scene_engine import CombinedObservations,run as combine,METHODS as SCENE_METHODS
from native_scene_engine import run as import_actors
from verify_native_object_scene_engine import run as verify
from strep import ROOT,read,save,sha256,now

METHODS=tuple(dict.fromkeys(FIT_METHODS+HANDOFF_METHODS+SCENE_METHODS+('verify_native_object_scene_engine.py','native_object_bounded_scene.py')))
SCHEMA='strep-native-object-bounded-scene-v1'


def require(condition,message):
    if not condition:raise ValueError(message)


def validate_handoff(fit,handoff,engine):
    with worker_lock(),threadpool_limits(limits=1):return _validate_handoff(fit,handoff,engine)


def _validate_handoff(fit,handoff,engine):
    result,source,candidate,request=validate_fit(fit)
    receipt=read(handoff/'result.json')
    require(read(handoff/'pipeline.json')['status']==receipt['status']=='complete','Complete object handoff required')
    require(receipt.get('object_handoff_conditions_pass') is True,'Passing object handoff required')
    require(receipt['bindings']==dict(fit_result_sha256=sha256(fit/'result.json'),engine_sha256=sha256(engine)),'Exact fit and engine handoff binding required')
    require(set(receipt['implementation_sha256'])==set(HANDOFF_METHODS),'Complete handoff methods required')
    for name,digest in receipt['implementation_sha256'].items():
        require(sha256(ROOT/'scripts'/name)==sha256(handoff/'implementation'/name)==digest,'Handoff implementation changed')
    for name,digest in receipt['files_sha256'].items():
        path=(handoff/name).resolve();require(path.is_relative_to(handoff),'Handoff file escapes output')
        require(sha256(path)==digest,'Handoff file changed')
    original=read(handoff/'original-contacts.json')
    # Only the original actor-file paths may be rebased to bound snapshots.
    restored=copy.deepcopy(original)
    require(set(restored['actors'])==set(source['actors']),'Original actor population changed')
    for name in source['actors']:
        require(sha256((handoff/original['actors'][name]['glb']).resolve())==source['actors'][name]['sha256'],'Original actor snapshot changed')
        restored['actors'][name]['glb']=source['actors'][name]['glb']
    require(restored==source,'Original author epoch changed')
    require(sha256(handoff/'candidate-contacts.json')==sha256(fit/'proposal-contacts.json') and read(handoff/'fit-request.json')==request,'Handoff candidate or fit request changed')
    ref_asset=ObjectAsset(handoff/'original-asset/objects.glb');cand_asset=ObjectAsset(handoff/'candidate-asset/objects.glb')
    times=np.array(read(handoff/'candidate-prepared/engine-payload.json')['sample_times_s'])
    require(read(handoff/'original-prepared/engine-payload.json')['sample_times_s']==times.tolist(),'Identical complete handoff clocks required')
    scene=SceneContacts(original,handoff);proposed=SceneContacts(candidate,fit)
    refraw=read(handoff/'original-engine/engine-output.json');candraw=read(handoff/'candidate-engine/engine-output.json')
    reports={}
    for mode in ('float32-asset','default-import','native-authoring'):
        reference,candidate_provider=(ref_asset,cand_asset) if mode=='float32-asset' else (
            CombinedObservations(scene,None,refraw[mode],times),CombinedObservations(scene,None,candraw[mode],times))
        report,_=evaluate(scene,ref_asset,cand_asset,reference,candidate_provider,times,request)
        require(report==read(handoff/(mode+'-epoch.json')),'Handoff epoch observations differ')
        require(receipt['object_epoch_conditions'][mode]==report['object_epoch_conditions_pass'],'Handoff epoch decision differs')
        actual,_=asset_audit(proposed,candidate_provider,times)
        if mode!='float32-asset':
            require(actual['sampled_conditions_pass']==receipt['object_engine_contact_conditions'][mode],'Actual object pose/contact decision differs')
        else:require(actual['sampled_conditions_pass'],'Actual Float32 asset conditions failed')
        reports[mode]=report
    require(reports['float32-asset']['object_epoch_conditions_pass'] and reports['native-authoring']['object_epoch_conditions_pass']
        and receipt['object_engine_contact_conditions']['native-authoring'],'Object handoff conditions failed')
    require(receipt['actor_bytes_unchanged'] and receipt['original_selected'] and not receipt['quality_approved'] and not receipt['release_approved'],'Object handoff review state changed')
    return receipt,times


def run(fit,handoff,output,engine):
    fit,handoff,output,engine=[Path(p).resolve() for p in (fit,handoff,output,engine)]
    require(not output.exists(),'Fresh bounded scene output required')
    receipt,times=validate_handoff(fit,handoff,engine)
    bindings={str(fit/'result.json'):sha256(fit/'result.json'),str(handoff/'result.json'):sha256(handoff/'result.json'),str(engine):sha256(engine)}
    methods={name:sha256(ROOT/'scripts'/name) for name in METHODS};output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,archive/name)
    contacts=handoff/'candidate-contacts.json';policy=handoff/'candidate-prepared/common-policy.json';objects=handoff/'candidate-engine'
    save(output/'request.json',dict(schema=SCHEMA,fit=str(fit),handoff=str(handoff),contacts=str(contacts),policy=str(policy),engine=str(engine),bindings=bindings,samples=len(times)))
    save(output/'pipeline.json',dict(status='processing',stage='actual-actor-import',original_selected=True))
    try:
        import_actors(contacts,output/'actor-engine',geometry_policy=policy,engine=engine,playback_mode='native-authoring')
        save(output/'pipeline.json',dict(status='processing',stage='combined-imported-scene',original_selected=True))
        combined=combine(contacts,policy,output/'actor-engine',objects,output/'combined')
        save(output/'pipeline.json',dict(status='processing',stage='saved-scene-replay',original_selected=True))
        verified=verify(contacts,policy,output/'actor-engine',objects,output/'combined',output/'verification')
        validate_handoff(fit,handoff,engine)
        require(all(sha256(path)==digest for path,digest in bindings.items()),'Bounded scene source changed')
        require(all(sha256(ROOT/'scripts'/name)==sha256(archive/name)==digest for name,digest in methods.items()),'Bounded scene implementation changed')
        passed=bool(receipt['object_handoff_conditions_pass'] and combined['all_sampled_conditions_pass'] and verified['recorded_sampled_conditions_pass'])
        files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file() and not (p.parent==output and p.name in ('result.json','pipeline.json'))}
        result=dict(schema=SCHEMA,at=now(),status='complete',samples=len(times),bindings=bindings,implementation_sha256=methods,files_sha256=files,
            object_handoff_conditions_pass=receipt['object_handoff_conditions_pass'],combined_scene_conditions_pass=combined['all_sampled_conditions_pass'],
            saved_scene_replay_pass=verified['recorded_sampled_conditions_pass'],bounded_scene_conditions_pass=passed,
            actor_engine_import_checked=True,complete_imported_skin_checked=True,complete_sampled_scene_geometry_checked=True,
            default_import_contacts_pass=combined['contacts_pass']['default-import'],original_selected=True,quality_approved=False,training_admitted=False,release_approved=False,
            gpu_render_checked=False,physics_verified=False,real_time_playback_verified=False,continuous_collision_certified=False,
            scope='Unchanged actors imported with native authoring on the complete bound object handoff clock. Full imported CPU skin, actual object transforms, declared sampled scene geometry and saved-array replay. Original-relative movement and protected original epochs rechecked separately. No default-import approval, GPU playback, dynamics, continuous collision, human action quality or release approval.')
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
    except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('fit','handoff','output'):p.add_argument(n,type=Path)
    p.add_argument('--engine',type=Path,required=True);a=p.parse_args()
    r=run(a.fit,a.handoff,a.output,a.engine);print(dict(samples=r['samples'],bounded_scene_conditions_pass=r['bounded_scene_conditions_pass'],quality_approved=False),flush=True)
