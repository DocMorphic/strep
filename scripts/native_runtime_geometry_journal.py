"""Resume complete-frame geometry queries from an explicitly pinned runtime surface.

Uses the existing checkpoint/frame protocol and unchanged geometry predicates.
The request identifies the mode-file surface producer directly; it does not
pretend to be the older native scene-import capture. Partial prefixes cannot
approve the complete clock. No model, engine, GPU or physics is executed here.
"""
import argparse,gc,json,shutil,uuid
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,sha256
from native_scene_geometry import evaluate,policy_for
from native_observation_archive import ObservationArchive
from native_runtime_surface_capture import load,METHODS as SURFACE_METHODS
from native_geometry_journal import (
    METHODS as JOURNAL_METHODS,require,runtime,fresh_json,local,header,
    header_digest,publish,anchor,chain,frame,
)

SCHEMA='strep-runtime-geometry-journal-v1'
METHODS=tuple(dict.fromkeys(JOURNAL_METHODS+SURFACE_METHODS+('native_runtime_geometry_journal.py',)))


def _methods(folder,expected):
    require(set(expected)==set(METHODS),'Complete runtime geometry methods required')
    require(all(sha256(ROOT/'scripts'/n)==sha256(folder/'implementation'/n)==h for n,h in expected.items()),
        'Runtime geometry implementation changed')


def prepare(capture,receipt_sha256,output):
    capture=Path(capture).resolve();output=Path(output).resolve()
    require(not output.exists() and not capture.is_relative_to(output) and not output.is_relative_to(capture),
        'Fresh separate runtime geometry journal required')
    with worker_lock(),threadpool_limits(limits=1):
        observed=load(capture,receipt_sha256);meta=observed.meta
        contacts=Path(meta['contacts_path']);policy_path=Path(meta['policy_path'])
        times=policy_for(read(policy_path),observed.scene,sha256(contacts))[0]
        inputs=dict(observed._bindings)
        require(all(not Path(p).is_relative_to(output) for p in inputs),'Journal contains its own input')
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True)
        for name in ('implementation','checkpoints','frames'):(output/name).mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,output/'implementation'/n)
        request=dict(schema=SCHEMA,surface_capture=str(capture),surface_receipt_sha256=receipt_sha256,
            contacts=str(contacts),policy=str(policy_path),inputs_sha256=inputs,
            implementation_sha256=methods,times_s=times.tolist(),runtime=runtime(),
            mode=meta['mode'],selected_root_modes=meta['selected_root_modes'],
            matches_export_configuration=meta['matches_export_configuration'],
            source_runtime_conditions_pass=meta['source_runtime_conditions_pass'],
            source_scene_conditions_pass=meta['source_scene_conditions_pass'],
            reference_based=True,quality_approved=False,physics_verified=False,release_approved=False)
        observed.check_inputs();_methods(output,methods)
        fresh_json(output/'request.json',request)
        return publish(output,dict(schema='strep-native-geometry-checkpoint-v1',
            request_sha256=sha256(output/'request.json'),next_sample=0,total_samples=len(times),
            previous=None,frame=None,header_sha256=None,checked_prefix_pass=True,
            sampled_conditions_pass=False,quality_approved=False,release_approved=False))


def context(folder):
    request=read(folder/'request.json')
    require(request['schema']==SCHEMA and request['runtime']==runtime()
        and request['reference_based'] is True
        and all(request[k] is False for k in ('quality_approved','physics_verified','release_approved')),
        'Explicit unapproved runtime geometry request required')
    _methods(folder,request['implementation_sha256'])
    observed=load(request['surface_capture'],request['surface_receipt_sha256']);meta=observed.meta
    require(request['inputs_sha256']==observed._bindings,'Complete pinned surface bindings required')
    require(request['contacts']==meta['contacts_path'] and request['policy']==meta['policy_path'],
        'Original surface scene and geometry policy required')
    for key in ('mode','selected_root_modes','matches_export_configuration',
            'source_runtime_conditions_pass','source_scene_conditions_pass'):
        require(request[key]==meta[key],'Surface scope or source acceptance changed')
    policy=read(request['policy']);times=policy_for(policy,observed.scene,sha256(request['contacts']))[0]
    require(request['times_s']==times.tolist(),'Complete original geometry clock required')
    return request,observed,policy,times


def advance(folder,checkpoint,expected_sha256,*,maximum_samples=16):
    folder=Path(folder).resolve()
    require(type(maximum_samples) is int and 1<=maximum_samples<=4096,'Bounded complete-frame work count required')
    with worker_lock(),threadpool_limits(limits=1):
        anchor(folder,checkpoint,expected_sha256)
        request,observed,policy,times=context(folder)
        current=chain(folder,checkpoint,expected_sha256,request)
        require(current['next_sample']<len(times),'Complete prefix is ready for finalization')
        receipt=dict(checkpoint=checkpoint,sha256=expected_sha256)
        for index in range(current['next_sample'],min(len(times),current['next_sample']+maximum_samples)):
            directory=folder/'frames'/f'{index:06d}-{uuid.uuid4().hex}';directory.mkdir()
            with ObservationArchive(directory/'observations.npz') as sink:
                sample,_=evaluate(observed.scene,policy,sha256(request['contacts']),
                    actor_vertices=observed.actor_vertices,object_poses=observed.object_poses,
                    observation_sink=sink,sample_indices=[index])
            fresh_json(directory/'geometry.json',sample);digest=header_digest(sample)
            require(current['header_sha256'] in (None,digest),'Geometry header differs across frames')
            observed.check_inputs();_methods(folder,request['implementation_sha256'])
            require(sha256(folder/'request.json')==current['request_sha256'],'Journal request changed during frame')
            fresh_json(directory/'receipt.json',dict(index=index,request_sha256=current['request_sha256'],
                files_sha256={n:sha256(directory/n) for n in ('geometry.json','observations.npz','observations.npz.receipt.json')}))
            current=dict(schema='strep-native-geometry-checkpoint-v1',request_sha256=current['request_sha256'],
                next_sample=index+1,total_samples=len(times),previous=receipt,
                frame=dict(index=index,directory=directory.relative_to(folder).as_posix(),receipt_sha256=sha256(directory/'receipt.json')),
                header_sha256=digest,checked_prefix_pass=bool(current['checked_prefix_pass'] and sample['checked_conditions_pass']),
                sampled_conditions_pass=False,quality_approved=False,release_approved=False)
            receipt=publish(folder,current);gc.collect()
        return receipt


def verify(folder,checkpoint,expected_sha256):
    folder=Path(folder).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        anchor(folder,checkpoint,expected_sha256);request,_,_,times=context(folder)
        last=chain(folder,checkpoint,expected_sha256,request)
        return dict(schema=SCHEMA,status='verified',completed_samples=last['next_sample'],
            total_samples=len(times),population_complete=last['next_sample']==len(times),
            checked_prefix_pass=last['checked_prefix_pass'],sampled_conditions_pass=False,
            quality_approved=False,physics_verified=False,release_approved=False)


def finalize(folder,checkpoint,expected_sha256,output):
    folder=Path(folder).resolve();output=Path(output).resolve()
    require(not output.exists() and not folder.is_relative_to(output),'Fresh separate geometry result required')
    with worker_lock(),threadpool_limits(limits=1):
        anchor(folder,checkpoint,expected_sha256);request,observed,_,times=context(folder)
        last=chain(folder,checkpoint,expected_sha256,request)
        require(last['next_sample']==len(times),'Full original geometry population required before finalization')
        entries=[];row=last
        while row['previous'] is not None:
            entries.append(row['frame']);row=read(local(folder,row['previous']['checkpoint']))
        entries.reverse();output.mkdir(parents=True);first,_=frame(folder,entries[0],request)
        metadata=header(first);metadata.update(schema='strep-native-scene-geometry-result-v1',status='complete',
            times_s=times.tolist(),sampled_conditions_pass=last['checked_prefix_pass'])
        with (output/'geometry.json').open('x',encoding='utf8',newline='\n') as stream,ObservationArchive(output/'observations.npz') as sink:
            stream.write('{"samples":[');sink['times_s']=times
            for i,entry in enumerate(entries):
                sample,archive=frame(folder,entry,request)
                if i:stream.write(',')
                json.dump(sample['samples'][0],stream,allow_nan=False)
                with np.load(archive,allow_pickle=False) as arrays:
                    for name in arrays.files:
                        if name!='times_s':sink[name]=arrays[name]
            stream.write('],');stream.write(json.dumps(metadata,allow_nan=False)[1:]);stream.write('\n')
        observed.check_inputs();_methods(folder,request['implementation_sha256'])
        require(sha256(folder/'request.json')==last['request_sha256'],'Journal request changed during finalization')
        result=dict(schema=SCHEMA,status='complete',samples=len(times),
            source_checkpoint=checkpoint,source_checkpoint_sha256=expected_sha256,
            request_sha256=last['request_sha256'],surface_receipt_sha256=request['surface_receipt_sha256'],
            files_sha256={n:sha256(output/n) for n in ('geometry.json','observations.npz','observations.npz.receipt.json')},
            sampled_conditions_pass=last['checked_prefix_pass'],mode=request['mode'],
            selected_root_modes=request['selected_root_modes'],matches_export_configuration=request['matches_export_configuration'],
            source_runtime_conditions_pass=request['source_runtime_conditions_pass'],
            source_scene_conditions_pass=request['source_scene_conditions_pass'],
            measurement_source='Explicit sealed mode-file runtime surface; CPU affine skin and declared rigid object projection.',
            reference_based=True,quality_approved=False,physics_verified=False,release_approved=False,
            scope='Complete declared geometry clock, original predicates and tolerances. No continuous/self collision, GPU, physics or human approval.')
        fresh_json(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('capture');p.add_argument('receipt_sha256');p.add_argument('output')
    for command in ('advance','verify','finalize'):
        p=sub.add_parser(command);p.add_argument('journal');p.add_argument('checkpoint');p.add_argument('checkpoint_sha256')
        if command=='advance':p.add_argument('--maximum-samples',type=int,default=16)
        if command=='finalize':p.add_argument('output')
    a=parser.parse_args()
    if a.command=='prepare':result=prepare(a.capture,a.receipt_sha256,a.output)
    elif a.command=='advance':result=advance(a.journal,a.checkpoint,a.checkpoint_sha256,maximum_samples=a.maximum_samples)
    elif a.command=='verify':result=verify(a.journal,a.checkpoint,a.checkpoint_sha256)
    else:result=finalize(a.journal,a.checkpoint,a.checkpoint_sha256,a.output)
    print(json.dumps(result))
