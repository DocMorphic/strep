"""Complete an engine audit from its sealed capture and full geometry journal.

Raw executed request/receipt/resources remain unchanged. A separate completion
request identifies current measurement code. This never launches an engine or
turns a partial journal into a full result.
"""
import argparse
from pathlib import Path
import shutil
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256
import native_geometry_journal as journal
from native_scene_capture import bindings as capture_bindings,load as capture_load
from native_scene_engine import SKIN_POSITION_TOLERANCE
from native_godot_payload import payload
from native_observation_archive import verify as verify_archive,logical_sha256

SCHEMA='strep-native-scene-engine-journal-completion-v1'
METHODS=tuple(dict.fromkeys(journal.METHODS+('native_scene_engine_complete.py',)))
FILES=('result.json','pipeline.json','request.json','completion-request.json','raw-engine-receipt.json',
    'engine-output.json','engine.log','native-observations.npz','imported-contact-observations.npz',
    'geometry.json','geometry-observations.npz','geometry-observations.npz.receipt.json')
FLAGS=('gpu_skin_verified','physics_playback_verified','gameplay_event_playback_verified',
    'continuous_collision_certified','quality_approved','training_admitted','release_approved')


def require(value,message):
    if not value:raise ValueError(message)


def completed_journal(folder,result_path,result_sha256):
    """Replay the complete assembly against all pinned frame/array receipts."""
    folder,result_path=Path(folder).resolve(),Path(result_path).resolve()
    require(sha256(result_path)==result_sha256,'Caller-pinned full journal result required')
    final=read(result_path)
    require(final['schema']=='strep-native-geometry-journal-result-v1' and final['status']=='complete',
        'Completed geometry journal result required')
    require(final['quality_approved'] is False and final['release_approved'] is False,'Unapproved geometry evidence required')
    journal.anchor(folder,final['source_checkpoint'],final['source_checkpoint_sha256'])
    request,scene,policy,times=journal.context(folder)
    require(sha256(folder/'request.json')==final['request_sha256'],'Journal request binding differs')
    last=journal.chain(folder,final['source_checkpoint'],final['source_checkpoint_sha256'],request)
    require(final['samples']==last['next_sample']==len(times) and final['sampled_conditions_pass'] is last['checked_prefix_pass'],
        'Complete original geometry clock required')
    require(request['engine_capture'] is not None and final['measurement_source']=='Sealed actual engine capture CPU skin',
        'Geometry must use the sealed imported observer, not native source poses')
    source=result_path.parent
    for name,key in (('geometry.json','geometry_sha256'),('observations.npz','observations_sha256'),
            ('observations.npz.receipt.json','observation_receipt_sha256')):
        require(sha256(source/name)==final[key],'Completed journal artifact changed')
    verify_archive(source/'observations.npz')
    geometry=read(source/'geometry.json');entries=[];row=last
    while row['previous'] is not None:
        entries.append(row['frame']);row=read(journal.local(folder,row['previous']['checkpoint']))
    entries.reverse();require(len(geometry['samples'])==len(times),'Full ordered geometry sample population required')
    transport=read(source/'observations.npz.receipt.json')['arrays'];expected_names={'times_s'}
    expected_clock=dict(shape=list(times.shape),dtype=times.dtype.str,bytes=times.nbytes,logical_sha256=logical_sha256(times))
    require(transport['times_s']==expected_clock,'Complete final array clock differs')
    for i,entry in enumerate(entries):
        part,archive=journal.frame(folder,entry,request)
        require(geometry['samples'][i]==part['samples'][0],'Completed geometry sample differs from pinned journal')
        if i==0:
            expected=journal.header(part);expected.update(schema='strep-native-scene-geometry-result-v1',status='complete',
                times_s=times.tolist(),sampled_conditions_pass=last['checked_prefix_pass'])
            require({k:v for k,v in geometry.items() if k!='samples'}==expected,'Completed geometry header differs')
        for name,value in read(Path(str(archive)+'.receipt.json'))['arrays'].items():
            if name=='times_s':continue
            require(name not in expected_names and transport.get(name)==value,'Final numeric geometry assembly differs')
            expected_names.add(name)
    require(set(transport)==expected_names,'Complete final numeric geometry population required')
    return request,scene,policy,final,geometry


def source(folder,result_path,result_sha256):
    request,scene,policy,final,geometry=completed_journal(folder,result_path,result_sha256)
    contacts,policy_path=Path(request['contacts']),Path(request['policy']);capture=request['engine_capture']
    inputs=capture_bindings(scene,contacts,policy_path,capture['path'],capture['receipt_sha256'])
    inputs.update(request['inputs_sha256'])
    inputs.update({str(Path(folder).resolve()/'request.json'):sha256(Path(folder)/'request.json'),
        str(journal.local(Path(folder).resolve(),final['source_checkpoint'])):final['source_checkpoint_sha256']})
    for path in (Path(result_path).resolve(),Path(result_path).resolve().parent/'geometry.json',
            Path(result_path).resolve().parent/'observations.npz',Path(result_path).resolve().parent/'observations.npz.receipt.json'):
        inputs[str(path)]=sha256(path)
    return request,scene,policy,final,geometry,inputs


def checked_capture(request,scene):
    contacts,policy=Path(request['contacts']),Path(request['policy']);capture=request['engine_capture']
    observed=capture_load(scene,contacts,policy,capture['path'],capture['receipt_sha256'])
    executed=read(Path(capture['path'])/'request.json');spec=read(contacts)
    for case in executed['cases']:
        actor=scene.actors[case['id']]
        require(case.get('native_payload')==payload(actor['rig'],actor['sampler'],spec['actors'][case['id']]['sha256']),
            'Complete captured source-derived native payload required')
    return observed


def expected_geometry(geometry,output):
    result=dict(geometry)
    result.update(imported_triangle_identity_checked=True,
        measurement_source='Imported CPU skin and engine Node3D prop transforms; authored placements after skin',
        observations_sha256=sha256(output/'geometry-observations.npz'),
        observation_receipt_sha256=sha256(output/'geometry-observations.npz.receipt.json'))
    return result


def run(folder,result_path,result_sha256,output):
    folder,result_path,output=[Path(p).resolve() for p in (folder,result_path,output)]
    require(not output.exists() and not folder.is_relative_to(output),'Fresh separate completed engine audit required')
    with worker_lock(),threadpool_limits(limits=1):
        request,scene,policy,final,geometry,inputs=source(folder,result_path,result_sha256)
        require(all(not Path(p).is_relative_to(output) for p in inputs),'Completion contains its own input')
        capture=Path(request['engine_capture']['path']);executed=read(capture/'request.json');receipt=read(capture/'raw-engine-receipt.json')
        observed=checked_capture(request,scene);times=observed.times
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True)
        try:
            (output/'implementation').mkdir();(output/'input').mkdir();(output/'project').mkdir()
            for n in methods:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
            snapshots={}
            for i,(p,h) in enumerate(inputs.items()):
                if Path(p).suffix.lower()=='.exe':continue
                target=output/'input'/f'{i}{Path(p).suffix}';shutil.copyfile(p,target);require(sha256(target)==h,'Completion input snapshot differs')
                snapshots[p]=dict(path=target.relative_to(output).as_posix(),sha256=h)
            for name in ('request.json','raw-engine-receipt.json','engine-output.json','engine.log'):
                shutil.copyfile(capture/name,output/name)
            for name in receipt['executed_scripts_sha256']:
                relative='audit.gd' if name=='godot_native_scene_audit.gd' else name
                shutil.copyfile(capture/'project'/relative,output/'project'/relative)
            for name in scene.actors:shutil.copyfile(capture/(name+'-animation.res'),output/(name+'-animation.res'))
            completion=dict(schema=SCHEMA,journal=str(folder),journal_result=str(result_path),journal_result_sha256=result_sha256,
                captured_receipt_sha256=request['engine_capture']['receipt_sha256'],inputs_sha256=inputs,
                implementation_sha256=methods,engine_executed=False,quality_approved=False,release_approved=False)
            save(output/'completion-request.json',completion)
            save(output/'pipeline.json',dict(status='processing',stage='full-imported-skin',original_selected=True))
            native,native_arrays=scene.evaluate();skin={}
            for name,actor in scene.actors.items():
                errors=[];maximum=0.;peak=None;p,r=actor['placement']
                for i,time in enumerate(times):
                    expected=actor['rig'].vertices(actor['sampler'].sample(float(time)))@r.T+p
                    error=float(np.linalg.norm(observed.actor_vertices(name,float(time))-expected,axis=1).max());errors.append(error)
                    if error>maximum:maximum,peak=error,float(time)
                    if i%100==0:save(output/'pipeline.json',dict(status='processing',stage='full-imported-skin',actor=name,completed_samples=i,total_samples=len(times)))
                native_arrays[name+'_skin_errors_m']=np.array(errors)
                skin[name]=dict(maximum_engine_native_vertex_error_m=maximum,peak_time_s=peak,tolerance_m=SKIN_POSITION_TOLERANCE,
                    position_samples_pass=bool(maximum<=SKIN_POSITION_TOLERANCE))
            imported,arrays=scene.evaluate(actor_points=observed.actor_points,object_poses=observed.object_poses)
            imported.update(loaded_skin_weights_normalized=False,measurement_source='Raw imported skin and object poses')
            np.savez_compressed(output/'native-observations.npz',**native_arrays)
            np.savez_compressed(output/'imported-contact-observations.npz',**arrays)
            shutil.copyfile(result_path.parent/'observations.npz',output/'geometry-observations.npz')
            shutil.copyfile(result_path.parent/'observations.npz.receipt.json',output/'geometry-observations.npz.receipt.json')
            save(output/'geometry.json',expected_geometry(geometry,output))
            pose=all(r['pose_samples_pass'] for r in observed.reports.values());objects=all(r['pose_samples_pass'] for r in observed.object_report.values())
            positions=all(r['position_samples_pass'] for r in skin.values())
            passed=bool(pose and objects and positions and native['passed'] and imported['passed'] and geometry['sampled_conditions_pass'])
            result=dict(schema=SCHEMA,status='complete',engine=read(capture/'engine-output.json')['engine'],
                import_bake_fps=executed['import_bake_fps'],engine_executable_sha256=receipt['engine_executable_sha256'],playback_mode='native-authoring',samples=len(times),
                actors=observed.reports,objects=observed.object_report,skin_errors=skin,native_contacts=native,imported_contacts=imported,
                imported_pose_samples_pass=pose,imported_object_pose_samples_pass=objects,imported_contact_samples_pass=imported['passed'],
                imported_skin_position_samples_pass=positions,all_sampled_conditions_available=True,all_sampled_conditions_pass=passed,
                imported_geometry_samples_pass=geometry['sampled_conditions_pass'],geometry_sha256=sha256(output/'geometry.json'),
                source_snapshots=snapshots,inputs_sha256=inputs,implementation_sha256=methods,
                engine_output_sha256=sha256(output/'engine-output.json'),raw_engine_receipt_sha256=sha256(output/'raw-engine-receipt.json'),
                native_observations_sha256=sha256(output/'native-observations.npz'),imported_contact_observations_sha256=sha256(output/'imported-contact-observations.npz'),
                animation_resources_sha256=receipt['animation_resources_sha256'],completion_request_sha256=sha256(output/'completion-request.json'),
                runtime=journal.runtime(),original_selected=True,engine_executed_in_completion=False,
                **{flag:False for flag in FLAGS},scope='Completed full geometry journal plus fresh full-clock imported/native skin and contact comparisons. '
                    'Copied executed request, raw engine receipt/output and animation resources remain unchanged. Completion does not execute an engine, '
                    'select a correction or approve rendering, physics, independent geometry requery, human quality or release.')
            require(all(sha256(p)==h for p,h in inputs.items()) and all(sha256(ROOT/'scripts'/n)==h for n,h in methods.items()),'Completion source or method changed')
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',original_selected=True));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),original_selected=True,quality_approved=False,release_approved=False))
            raise


def load(contacts,policy_path,output,*,actor_only=False):
    """Strict loader shared by ordinary replay and original-fidelity consumers."""
    contacts,policy_path,output=[Path(p).resolve() for p in (contacts,policy_path,output)]
    result=read(output/'result.json');completion=read(output/'completion-request.json')
    require(read(output/'pipeline.json')['status']=='complete' and result['schema']==completion['schema']==SCHEMA
        and result['status']=='complete','Complete journal-derived engine audit required')
    require(sha256(output/'completion-request.json')==result['completion_request_sha256'],'Completion request changed')
    require(result['original_selected'] is True and result['engine_executed_in_completion'] is False
        and completion['engine_executed'] is False and all(result[k] is False for k in FLAGS)
        and completion['quality_approved'] is False and completion['release_approved'] is False,'Unapproved non-executing completion required')
    request,scene,policy,final,geometry,inputs=source(completion['journal'],completion['journal_result'],completion['journal_result_sha256'])
    require(Path(request['contacts'])==contacts and Path(request['policy'])==policy_path,'Exact journal scene and policy required')
    require(not actor_only or not scene.objects,'Actor-only replay cannot omit objects')
    require(inputs==completion['inputs_sha256']==result['inputs_sha256'],'Complete completion input bindings differ')
    require(set(result['implementation_sha256'])==set(METHODS) and completion['implementation_sha256']==result['implementation_sha256'],'Complete completion methods required')
    require(all(sha256(ROOT/'scripts'/n)==sha256(output/'implementation'/n)==h for n,h in result['implementation_sha256'].items()),'Completion implementation changed')
    require(set(result['source_snapshots'])=={p for p in inputs if Path(p).suffix.lower()!='.exe'},'Complete completion snapshots required')
    for p,entry in result['source_snapshots'].items():
        require(sha256(journal.local(output,entry['path']))==entry['sha256']==inputs[p],'Completion input snapshot differs')
    capture=Path(request['engine_capture']['path']);receipt=read(capture/'raw-engine-receipt.json')
    require(completion['captured_receipt_sha256']==request['engine_capture']['receipt_sha256'],'Captured receipt binding differs')
    for name in ('request.json','raw-engine-receipt.json','engine-output.json','engine.log'):
        require(sha256(output/name)==sha256(capture/name),'Copied actual capture changed')
    for name,h in receipt['executed_scripts_sha256'].items():
        require(sha256(output/'project'/('audit.gd' if name=='godot_native_scene_audit.gd' else name))==h,'Copied executed script changed')
    require(result['animation_resources_sha256']==receipt['animation_resources_sha256'],'Complete captured animation resources required')
    for name,h in result['animation_resources_sha256'].items():require(sha256(output/(name+'-animation.res'))==h,'Copied animation resource changed')
    for name,key in (('engine-output.json','engine_output_sha256'),('raw-engine-receipt.json','raw_engine_receipt_sha256'),
            ('native-observations.npz','native_observations_sha256'),('imported-contact-observations.npz','imported_contact_observations_sha256'),('geometry.json','geometry_sha256')):
        require(sha256(output/name)==result[key],'Completed engine observation changed')
    require(sha256(output/'geometry-observations.npz')==final['observations_sha256']
        and sha256(output/'geometry-observations.npz.receipt.json')==final['observation_receipt_sha256'],'Completed numeric geometry changed')
    require(read(output/'geometry.json')==expected_geometry(geometry,output),'Completed geometry report differs from journal')
    observed=checked_capture(request,scene);executed=read(capture/'request.json')
    require(result['samples']==len(observed.times) and result['playback_mode']=='native-authoring'
        and result['import_bake_fps']==executed['import_bake_fps'] and result['engine_executable_sha256']==receipt['engine_executable_sha256']
        and result['engine']==read(capture/'engine-output.json')['engine'],'Captured engine mode/clock/version differs')
    bindings=dict(inputs);bindings.update({str(output/n):sha256(output/n) for n in FILES})
    bindings.update({str(output/(n+'-animation.res')):h for n,h in result['animation_resources_sha256'].items()})
    return scene,policy,observed,observed.times,bindings


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('journal','journal_result','journal_result_sha256','output'):parser.add_argument(name)
    a=parser.parse_args();print(run(a.journal,a.journal_result,a.journal_result_sha256,a.output)['all_sampled_conditions_pass'])
