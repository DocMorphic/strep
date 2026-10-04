"""Actual object-only game export with budgets anchored to original author poses.

Protected export poses are compared against independently exported originals,
not Float64 author values or a fitted initialization. Actor import is separate.
"""
import argparse,copy,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from native_scene_contacts import SceneContacts
from native_scene_geometry import policy_for
from native_object_asset import ObjectAsset,run as export_asset,run_engine,METHODS as ASSET_METHODS
from native_object_scene_engine import prepare,CombinedObservations,METHODS as SCENE_METHODS
from native_object_bounded_fit import SCHEMA,METHODS as FIT_METHODS
from strep import ROOT,read,save,sha256,now

METHODS=tuple(dict.fromkeys(FIT_METHODS+ASSET_METHODS+SCENE_METHODS+('native_object_bounded_handoff.py',)))


def check(condition,message):
    if not condition:raise ValueError(message)


def evaluate(original,reference_asset,candidate_asset,reference,candidate,times,request):
    times=np.asarray(times,float)
    check(times.ndim==1 and len(times)>=2 and np.isfinite(times).all() and np.all(np.diff(times)>0) and times[0]==0 and times[-1]==original.duration,'Complete finite handoff clock required')
    names=set(original.objects)
    check(set(reference_asset.objects)==set(candidate_asset.objects)==set(reference.objects)==set(candidate.objects)==names,'Complete original object populations required')
    expected_geometry={name:value['geometry'].record() for name,value in original.objects.items()}
    for asset in (reference_asset,candidate_asset):
        declared={n['extras']['strep_object_id']:n['extras']['strep_geometry'] for n in asset.document['nodes']}
        check(declared==expected_geometry,'Original object geometry must survive both exports')
    name=request['object'];window=request['edit_window_s'];frozen=(times<=window[0])|(times>=window[1]);arrays={'times_s':times}
    p,r=original.object_poses(name,times);q,s=candidate.object_poses(name,times)
    check(p.shape==q.shape==(len(times),3) and r.shape==s.shape==(len(times),3,3) and all(np.isfinite(a).all() for a in [p,q,r,s]),'Complete finite original-epoch object poses required')
    shifts=np.linalg.norm(q-p,axis=1);angles=np.rad2deg(Rotation.from_matrix(s@r.transpose(0,2,1)).magnitude())
    arrays.update(original_author_positions=p,original_author_rotations=r,candidate_positions=q,candidate_rotations=s,
        original_relative_translation_m=shifts,original_relative_rotation_degrees=angles)
    movement=bool(shifts.max()<=request['maximum_translation_m'] and angles.max()<=request['maximum_rotation_degrees'])
    encoded=[];imported=[]
    for obj in sorted(names):
        original_clock=reference_asset.objects[obj]['translation'][0]
        protected=original_clock if obj!=name else original_clock[(original_clock<=window[0])|(original_clock>=window[1])]
        check(len(protected)>0,'Protected original object keys required')
        a,b=reference_asset.object_poses(obj,protected);c,d=candidate_asset.object_poses(obj,protected)
        check(all(np.isfinite(x).all() for x in (a,b,c,d)),'Finite encoded protected values required')
        error=float(max(np.max(abs(a-c)),np.max(abs(b-d))));passed=bool(np.array_equal(a,c) and np.array_equal(b,d))
        if obj!=name:
            for prop in ('translation','rotation','scale'):
                ta,va=reference_asset.objects[obj][prop];tb,vb=candidate_asset.objects[obj][prop]
                passed &= bool(np.array_equal(ta,tb) and np.array_equal(va,vb))
        arrays[obj+'_protected_times_s']=protected;arrays[obj+'_reference_encoded_positions']=a;arrays[obj+'_candidate_encoded_positions']=c
        arrays[obj+'_reference_encoded_rotations']=b;arrays[obj+'_candidate_encoded_rotations']=d
        encoded.append(dict(object=obj,keys=len(protected),maximum_component_error=error,passed=bool(passed)))
        a,b=reference.object_poses(obj,times);c,d=candidate.object_poses(obj,times);mask=np.ones(len(times),bool) if obj!=name else frozen
        check(all(np.isfinite(x).all() for x in (a,b,c,d)),'Finite actual protected object observations required')
        error=float(max(np.max(abs(a[mask]-c[mask])),np.max(abs(b[mask]-d[mask]))))
        # Both actual pipelines use the same engine and complete clock. This tests
        # preservation, without accepting an arbitrary export-error allowance.
        passed=bool(np.array_equal(a[mask],c[mask]) and np.array_equal(b[mask],d[mask]))
        arrays[obj+'_reference_positions']=a;arrays[obj+'_reference_rotations']=b
        imported.append(dict(object=obj,samples=int(mask.sum()),maximum_component_error=error,passed=passed))
    author_frozen_error=float(max(np.max(abs(q[frozen]-p[frozen])),np.max(abs(s[frozen]-r[frozen]))))
    passed=bool(movement and all(v['passed'] for v in encoded+imported))
    return dict(samples=len(times),maximum_original_relative_translation_m=float(shifts.max()),maximum_original_relative_rotation_degrees=float(angles.max()),
        movement_limits_pass=movement,encoded_protected_originals=encoded,actual_protected_originals=imported,
        author_frozen_roundtrip_maximum_component_error=author_frozen_error,author_frozen_float64_identity=False,
        object_epoch_conditions_pass=passed,original_epoch='Original Float64 author object path; never initialization or imported reference for movement budgets.',
        protected_epoch='Identical independently exported original key values and actual original engine/asset poses outside edits; unedited objects protected everywhere.',
        actor_engine_import_checked=False,full_imported_geometry_checked=False,continuous_bounds_certified=False,quality_approved=False,release_approved=False),arrays


def validate_fit(folder):
    result=read(folder/'result.json');check(read(folder/'pipeline.json')['status']==result['status']=='complete','Terminal bounded fit required')
    check(result.get('schema')==SCHEMA and result.get('sampled_constraints_pass') is True,'Passing bounded fit required; diagnostic proposals stay separate')
    check(set(result['implementation_sha256'])==set(FIT_METHODS),'Complete fit methods required')
    for name,digest in result['implementation_sha256'].items():check(sha256(ROOT/'scripts'/name)==sha256(folder/'implementation'/name)==digest,'Fit method changed')
    for name,digest in result['files_sha256'].items():check(sha256(folder/name)==digest,'Fit file changed')
    for path,digest in result['input_sha256'].items():check(sha256(path)==digest,'Fit input changed')
    source=read(folder/'source-contacts.json');candidate=read(folder/'proposal-contacts.json');request=read(folder/'fit-request.json')
    check(source['contacts']==candidate['contacts'] and source['duration_s']==candidate['duration_s'],'Source contact intent changed')
    check(set(source['actors'])==set(candidate['actors'])==set(result['actor_snapshots']),'Complete actor population required')
    for name,snapshot in result['actor_snapshots'].items():
        check(sha256(folder/snapshot['path'])==snapshot['sha256']==source['actors'][name]['sha256']==candidate['actors'][name]['sha256'],'Actor snapshot changed')
        check({k:v for k,v in source['actors'][name].items() if k!='glb'}=={k:v for k,v in candidate['actors'][name].items() if k!='glb'},'Actor identity/placement changed')
    check(set(source['objects'])==set(candidate['objects']),'Source objects changed')
    for name in source['objects']:
        check(source['objects'][name]['geometry']==candidate['objects'][name]['geometry'],'Object geometry changed')
        if name!=request['object']:check(source['objects'][name]==candidate['objects'][name],'Unedited object path changed')
    return result,source,candidate,request


def run(fit,output,engine):
    fit,output,engine=[Path(p).resolve() for p in (fit,output,engine)]
    check(not output.exists(),'Fresh bounded handoff output required');result,source,candidate,request=validate_fit(fit)
    bindings=dict(fit_result_sha256=sha256(fit/'result.json'),engine_sha256=sha256(engine));methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
    output.mkdir(parents=True);archive=output/'implementation';archive.mkdir()
    for name in methods:shutil.copyfile(ROOT/'scripts'/name,archive/name)
    # Rebase only paths to the unchanged actor snapshots; author motion stays original.
    for name,snapshot in result['actor_snapshots'].items():source['actors'][name]['glb']=str(fit/snapshot['path'])
    save(output/'original-contacts.json',source);save(output/'candidate-contacts.json',candidate);save(output/'fit-request.json',request)
    save(output/'pipeline.json',dict(status='exporting',original_selected=True))
    try:
        export_asset(output/'original-contacts.json',output/'original-asset');export_asset(output/'candidate-contacts.json',output/'candidate-asset')
        clocks=[]
        for prefix in ('original','candidate'):
            folder=output/(prefix+'-asset');clocks.append(np.array(read(folder/'engine-payload.json')['sample_times_s']))
            clocks.extend(np.clip(o['translation'][0],0,source['duration_s']) for o in ObjectAsset(folder/'objects.glb').objects.values())
        clocks.append(np.array(read(fit/'geometry-policy.json')['clock']['times_s']));times=np.unique(np.concatenate(clocks))
        base_policy=read(fit/'source-policy.json')
        for prefix in ('original','candidate'):
            policy=copy.deepcopy(base_policy);policy['contacts_sha256']=sha256(output/(prefix+'-contacts.json'));policy['clock']['times_s']=times.tolist()
            save(output/(prefix+'-policy.json'),policy)
            prepare(output/(prefix+'-contacts.json'),output/(prefix+'-policy.json'),output/(prefix+'-asset'),output/(prefix+'-prepared'))
        a=read(output/'original-prepared/engine-payload.json');b=read(output/'candidate-prepared/engine-payload.json')
        check(a['sample_times_s']==b['sample_times_s']==times.tolist(),'Complete identical original/candidate clocks required')
        for prefix in ('original','candidate'):run_engine(output/(prefix+'-prepared'),output/(prefix+'-engine'),engine)
        with worker_lock(),threadpool_limits(limits=1):
            original=SceneContacts(source,output);ref_asset=ObjectAsset(output/'original-asset/objects.glb');cand_asset=ObjectAsset(output/'candidate-asset/objects.glb')
            refraw=read(output/'original-engine/engine-output.json');candraw=read(output/'candidate-engine/engine-output.json');reports={}
            report,arrays=evaluate(original,ref_asset,cand_asset,ref_asset,cand_asset,times,request);reports['float32-asset']=report
            save(output/'float32-asset-epoch.json',report);np.savez_compressed(output/'float32-asset-observations.npz',**arrays)
            for mode in ('default-import','native-authoring'):
                ref=CombinedObservations(original,None,refraw[mode],times);cand=CombinedObservations(original,None,candraw[mode],times)
                report,arrays=evaluate(original,ref_asset,cand_asset,ref,cand,times,request);reports[mode]=report
                save(output/(mode+'-epoch.json'),report);np.savez_compressed(output/(mode+'-epoch-observations.npz'),**arrays)
            object_engine=read(output/'candidate-engine/result.json');asset_report=read(output/'candidate-prepared/asset-audit.json')
            passed=bool(reports['float32-asset']['object_epoch_conditions_pass'] and reports['native-authoring']['object_epoch_conditions_pass']
                and asset_report['sampled_conditions_pass'] and object_engine['modes']['native-authoring'])
            validate_fit(fit);check(sha256(fit/'result.json')==bindings['fit_result_sha256'] and sha256(engine)==bindings['engine_sha256'],'Handoff source changed')
            check(all(sha256(ROOT/'scripts'/n)==sha256(archive/n)==h for n,h in methods.items()),'Handoff implementation changed')
            source_files=[p for p in output.rglob('*') if p.is_file() and not (p.parent==output and p.name in ('result.json','pipeline.json'))]
            files={p.relative_to(output).as_posix():sha256(p) for p in source_files}
            receipt=dict(at=now(),status='complete',bindings=bindings,implementation_sha256=methods,files_sha256=files,
                samples=len(times),object_epoch_conditions={k:v['object_epoch_conditions_pass'] for k,v in reports.items()},
                object_engine_contact_conditions=object_engine['modes'],object_handoff_conditions_pass=passed,
                actor_bytes_unchanged=True,actor_engine_import_checked=False,full_imported_geometry_checked=False,
                gpu_render_checked=False,physics_checked=False,original_selected=True,quality_approved=False,release_approved=False,
                scope='Actual object-only Float32 assets and headless Godot transforms. Budgets stay anchored to original Float64 author poses; protected encoding and actual exterior states match independently exported originals. Full imported actor skin/geometry, real-time playback and human quality remain separate.')
            save(output/'result.json',receipt);save(output/'pipeline.json',dict(status='complete',original_selected=True));return receipt
    except Exception as exc:save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('fit',type=Path);p.add_argument('output',type=Path);p.add_argument('--engine',type=Path,required=True)
    a=p.parse_args();r=run(a.fit,a.output,a.engine);print(dict(samples=r['samples'],object_handoff_conditions_pass=r['object_handoff_conditions_pass'],quality_approved=False),flush=True)
