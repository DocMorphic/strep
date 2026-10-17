"""Append-only complete-frame checkpoints for full native scene geometry.

Partial checkpoints never pass the full-clock condition. Resume requires a
caller-pinned checkpoint digest; completed geometry is assembled only after
the complete original clock is present. Originals and abandoned attempts stay.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid
import numpy as np
import scipy
import trimesh
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT,read,save,sha256
from native_scene_contacts import SceneContacts
from native_scene_geometry import evaluate,policy_for,METHODS as GEOMETRY_METHODS
from native_scene_engine import METHODS as ENGINE_METHODS
from native_scene_capture import bindings as capture_bindings,load as load_capture
from native_observation_archive import ObservationArchive,verify as verify_archive

METHODS=tuple(dict.fromkeys(GEOMETRY_METHODS+ENGINE_METHODS+('native_geometry_journal.py','native_scene_capture.py','strep.py')))
VARIABLE=('schema','status','samples','times_s','sample_indices','complete_clock_s','checked_conditions_pass','sampled_conditions_pass')


def require(value,message):
    if not value:raise ValueError(message)


def partner_batch(value):
    require(type(value) is int and 1<=value<=32,'Partner query batch size must be an integer from 1 through 32')
    return value


def runtime():return dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,trimesh=trimesh.__version__)


def fresh_json(path,value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def local(folder,relative):
    require(isinstance(relative,str) and bool(relative),'Relative journal artifact required')
    path=(folder/relative).resolve()
    require(path.is_relative_to(folder) and path!=folder and not Path(relative).is_absolute(),'Journal artifact escapes its directory')
    return path


def header(row):return {k:v for k,v in row.items() if k not in VARIABLE}


def header_digest(row):return hashlib.sha256(json.dumps(header(row),sort_keys=True,allow_nan=False).encode()).hexdigest()


def publish(folder,value):
    target=folder/'checkpoints'/f"{value['next_sample']:06d}-{uuid.uuid4().hex}.json"
    fresh_json(target,value)
    receipt=dict(checkpoint=target.relative_to(folder).as_posix(),sha256=sha256(target),
        completed_samples=value['next_sample'],total_samples=value['total_samples'],
        population_complete=value['next_sample']==value['total_samples'],
        sampled_conditions_pass=False,quality_approved=False,release_approved=False)
    save(folder/'progress.json',receipt)
    return receipt


def prepare(contacts,policy_path,folder,*,engine_capture=None,capture_receipt_sha256=None,partner_query_batch_size=32):
    partner_query_batch_size=partner_batch(partner_query_batch_size)
    contacts,policy_path,folder=[Path(p).resolve() for p in (contacts,policy_path,folder)]
    require(not folder.exists(),'Fresh geometry journal required')
    require((engine_capture is None)==(capture_receipt_sha256 is None),'Capture path and explicit receipt digest must be paired')
    with worker_lock(),threadpool_limits(limits=1):
        scene=SceneContacts(read(contacts),contacts.parent);policy=read(policy_path);times=policy_for(policy,scene,sha256(contacts))[0]
        inputs={str(contacts):sha256(contacts),str(policy_path):sha256(policy_path),**scene.inputs}
        capture=None
        if engine_capture is not None:
            engine_capture=Path(engine_capture).resolve()
            inputs.update(capture_bindings(scene,contacts,policy_path,engine_capture,capture_receipt_sha256))
            capture=dict(path=str(engine_capture),receipt_sha256=capture_receipt_sha256)
        require(all(not Path(p).is_relative_to(folder) for p in inputs),'Journal contains its own input')
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        folder.mkdir(parents=True);(folder/'implementation').mkdir();(folder/'input').mkdir();(folder/'checkpoints').mkdir();(folder/'frames').mkdir()
        for n in methods:shutil.copyfile(ROOT/'scripts'/n,folder/'implementation'/n)
        snapshots={}
        for i,(p,h) in enumerate(inputs.items()):
            if Path(p).suffix.lower()=='.exe':continue  # Hash executable; never duplicate its payload.
            target=folder/'input'/f'{i}{Path(p).suffix}';shutil.copyfile(p,target);require(sha256(target)==h,'Journal input snapshot differs')
            snapshots[p]=dict(path=target.relative_to(folder).as_posix(),sha256=h)
        request=dict(schema='strep-native-geometry-journal-v1',contacts=str(contacts),policy=str(policy_path),
            engine_capture=capture,inputs_sha256=inputs,source_snapshots=snapshots,implementation_sha256=methods,
            times_s=times.tolist(),runtime=runtime(),partner_query_batch_size=partner_query_batch_size,
            quality_approved=False,release_approved=False)
        require(all(sha256(p)==h for p,h in inputs.items()) and all(sha256(ROOT/'scripts'/n)==sha256(folder/'implementation'/n)==h for n,h in methods.items()),'Journal preparation binding changed')
        fresh_json(folder/'request.json',request)
        return publish(folder,dict(schema='strep-native-geometry-checkpoint-v1',request_sha256=sha256(folder/'request.json'),
            next_sample=0,total_samples=len(times),previous=None,frame=None,header_sha256=None,checked_prefix_pass=True,
            sampled_conditions_pass=False,quality_approved=False,release_approved=False))


def context(folder):
    request=read(folder/'request.json')
    require(request['schema']=='strep-native-geometry-journal-v1' and request['runtime']==runtime(),'Journal runtime differs')
    partner_batch(request.get('partner_query_batch_size',32))
    require(set(request['implementation_sha256'])==set(METHODS),'Complete journal methods required')
    require(all(sha256(ROOT/'scripts'/n)==sha256(folder/'implementation'/n)==h for n,h in request['implementation_sha256'].items()),'Journal implementation changed')
    require(all(sha256(p)==h for p,h in request['inputs_sha256'].items()),'Journal source changed')
    require(set(request['source_snapshots'])=={p for p in request['inputs_sha256'] if Path(p).suffix.lower()!='.exe'},'Complete journal input snapshots required')
    for p,snapshot in request['source_snapshots'].items():
        require(sha256(local(folder,snapshot['path']))==snapshot['sha256']==request['inputs_sha256'][p],'Journal snapshot changed')
    contacts=Path(request['contacts']);policy_path=Path(request['policy']);scene=SceneContacts(read(contacts),contacts.parent);policy=read(policy_path)
    times=policy_for(policy,scene,sha256(contacts))[0]
    require(times.tolist()==request['times_s'],'Complete journal clock changed')
    return request,scene,policy,times


def anchor(folder,checkpoint,expected_sha256):
    path=local(folder,checkpoint)
    require(sha256(path)==expected_sha256,'Pinned checkpoint changed')
    require(read(path)['request_sha256']==sha256(folder/'request.json'),'Pinned journal request changed')


def chain(folder,checkpoint,expected_sha256,request):
    path=local(folder,checkpoint);rows=[];seen=set();binding=sha256(folder/'request.json');total=len(request['times_s'])
    while True:
        require(path not in seen and sha256(path)==expected_sha256,'Pinned checkpoint changed or cyclic chain')
        seen.add(path);row=read(path)
        require(row['schema']=='strep-native-geometry-checkpoint-v1' and row['request_sha256']==binding
            and type(row['next_sample']) is int and 0<=row['next_sample']<=total and row['total_samples']==total,
            'Checkpoint request or population differs')
        require(row['sampled_conditions_pass'] is False and row['quality_approved'] is False
            and row['release_approved'] is False,'Partial checkpoint cannot approve geometry')
        rows.append(row)
        if row['previous'] is None:break
        require(len(rows)<=total+1,'Checkpoint chain exceeds complete clock')
        path=local(folder,row['previous']['checkpoint']);expected_sha256=row['previous']['sha256']
    rows.reverse();require(rows[0]['next_sample']==0 and rows[0]['frame'] is None and rows[0]['header_sha256'] is None
        and rows[0]['checked_prefix_pass'] is True,'Empty checkpoint genesis required')
    passed=True;first_header=None
    for i,row in enumerate(rows[1:]):
        require(row['next_sample']==i+1 and row['frame']['index']==i,'Complete ordered prefix required')
        sample,archive=frame(folder,row['frame'],request)
        digest=header_digest(sample)
        if first_header is None:first_header=digest
        passed &= sample['checked_conditions_pass']
        require(row['header_sha256']==digest==first_header and row['checked_prefix_pass'] is passed,'Checkpoint reduction differs')
    return rows[-1]


def frame(folder,entry,request):
    index=entry['index'];require(type(index) is int and 0<=index<len(request['times_s']),'Existing geometry frame required')
    directory=local(folder,entry['directory']);receipt=directory/'receipt.json'
    require(sha256(receipt)==entry['receipt_sha256'],'Geometry frame receipt changed')
    value=read(receipt)
    require(value['index']==index and value['request_sha256']==sha256(folder/'request.json'),'Frame request or index differs')
    require(set(value['files_sha256'])=={'geometry.json','observations.npz','observations.npz.receipt.json'},'Complete frame artifact population required')
    require(all(sha256(directory/n)==h for n,h in value['files_sha256'].items()),'Saved geometry frame changed')
    verify_archive(directory/'observations.npz')
    sample=read(directory/'geometry.json');time=request['times_s'][index]
    require(sample['schema']=='strep-native-scene-geometry-slice-v1' and sample['status']=='partial'
        and sample['sample_indices']==[index] and sample['complete_clock_s']==request['times_s']
        and sample['times_s']==[time] and len(sample['samples'])==1 and sample['samples'][0]['time_s']==time,
        'Exact full-clock sample identity required')
    require(sample['sampled_conditions_pass'] is False and type(sample['checked_conditions_pass']) is bool
        and sample['checked_conditions_pass'] is sample['samples'][0]['passed'],'Partial sample decision differs')
    with np.load(directory/'observations.npz',allow_pickle=False) as arrays:
        require(np.array_equal(arrays['times_s'],np.array([time])),'Saved frame array clock differs')
    return sample,directory/'observations.npz'


def advance(folder,checkpoint,expected_sha256,*,maximum_samples=16):
    folder=Path(folder).resolve()
    require(type(maximum_samples) is int and 1<=maximum_samples<=4096,'Bounded complete-frame work count required')
    with worker_lock(),threadpool_limits(limits=1):
        anchor(folder,checkpoint,expected_sha256)
        request,scene,policy,times=context(folder);current=chain(folder,checkpoint,expected_sha256,request)
        receipt=dict(checkpoint=checkpoint,sha256=expected_sha256)
        require(current['next_sample']<len(times),'Complete prefix is ready for finalization')
        observed=None
        if request['engine_capture'] is not None:
            capture=request['engine_capture'];observed=load_capture(scene,Path(request['contacts']),Path(request['policy']),capture['path'],capture['receipt_sha256'])
        kwargs={} if observed is None else dict(actor_vertices=observed.actor_vertices,object_poses=observed.object_poses)
        kwargs['partner_query_batch_size']=partner_batch(request.get('partner_query_batch_size',32))
        for index in range(current['next_sample'],min(len(times),current['next_sample']+maximum_samples)):
            directory=folder/'frames'/f'{index:06d}-{uuid.uuid4().hex}';directory.mkdir()
            with ObservationArchive(directory/'observations.npz') as sink:
                sample,_=evaluate(scene,policy,sha256(request['contacts']),observation_sink=sink,sample_indices=[index],**kwargs)
            fresh_json(directory/'geometry.json',sample)
            digest=header_digest(sample)
            require(current['header_sha256'] in (None,digest),'Geometry header differs across frames')
            require(all(sha256(p)==h for p,h in request['inputs_sha256'].items()),'Source changed during frame evaluation')
            require(all(sha256(ROOT/'scripts'/n)==h for n,h in request['implementation_sha256'].items()),'Method changed during frame evaluation')
            fresh_json(directory/'receipt.json',dict(index=index,request_sha256=sha256(folder/'request.json'),
                files_sha256={n:sha256(directory/n) for n in ('geometry.json','observations.npz','observations.npz.receipt.json')}))
            current=dict(schema='strep-native-geometry-checkpoint-v1',request_sha256=sha256(folder/'request.json'),
                next_sample=index+1,total_samples=len(times),previous=receipt,
                frame=dict(index=index,directory=directory.relative_to(folder).as_posix(),receipt_sha256=sha256(directory/'receipt.json')),
                header_sha256=digest,checked_prefix_pass=bool(current['checked_prefix_pass'] and sample['checked_conditions_pass']),
                sampled_conditions_pass=False,quality_approved=False,release_approved=False)
            receipt=publish(folder,current)
            # Trimesh's ray/cache objects can form cycles around large arrays.
            # Each completed frame owns a checkpoint; free unreachable queries.
            gc.collect()
        return receipt


def finalize(folder,checkpoint,expected_sha256,output):
    folder,output=Path(folder).resolve(),Path(output).resolve()
    require(not output.exists() and not folder.is_relative_to(output),'Fresh separate final geometry output required')
    with worker_lock(),threadpool_limits(limits=1):
        anchor(folder,checkpoint,expected_sha256)
        request,scene,policy,times=context(folder);last=chain(folder,checkpoint,expected_sha256,request)
        require(last['next_sample']==len(times),'Full original geometry population required before finalization')
        # Walk the already verified chain for ordered frame references only.
        entries=[];row=last
        while row['previous'] is not None:
            entries.append(row['frame']);row=read(local(folder,row['previous']['checkpoint']))
        entries.reverse();output.mkdir(parents=True);first,_=frame(folder,entries[0],request)
        metadata=header(first);metadata.update(schema='strep-native-scene-geometry-result-v1',status='complete',
            times_s=times.tolist(),sampled_conditions_pass=last['checked_prefix_pass'])
        # Stream complete JSON samples and one numeric array at a time. No
        # all-frame geometry or object-depth tensor is rebuilt in memory.
        with (output/'geometry.json').open('x',encoding='utf-8',newline='\n') as stream,ObservationArchive(output/'observations.npz') as sink:
            stream.write('{"samples":[');sink['times_s']=times
            for i,entry in enumerate(entries):
                sample,archive=frame(folder,entry,request)
                if i:stream.write(',')
                json.dump(sample['samples'][0],stream,allow_nan=False)
                with np.load(archive,allow_pickle=False) as arrays:
                    for name in arrays.files:
                        if name!='times_s':sink[name]=arrays[name]
            stream.write('],');stream.write(json.dumps(metadata,allow_nan=False)[1:]);stream.write('\n')
        require(all(sha256(p)==h for p,h in request['inputs_sha256'].items()),'Source changed during finalization')
        require(all(sha256(ROOT/'scripts'/n)==h for n,h in request['implementation_sha256'].items()),'Method changed during finalization')
        result=dict(schema='strep-native-geometry-journal-result-v1',status='complete',samples=len(times),
            source_checkpoint=checkpoint,source_checkpoint_sha256=expected_sha256,request_sha256=sha256(folder/'request.json'),
            geometry_sha256=sha256(output/'geometry.json'),observations_sha256=sha256(output/'observations.npz'),
            observation_receipt_sha256=sha256(output/'observations.npz.receipt.json'),sampled_conditions_pass=last['checked_prefix_pass'],
            measurement_source='Native source skin' if request['engine_capture'] is None else 'Sealed actual engine capture CPU skin',
            partner_query_batch_size=partner_batch(request.get('partner_query_batch_size',32)),
            quality_approved=False,release_approved=False,scope='Complete declared scene geometry clock assembled from pinned full-frame results. '
                'Original query predicates and tolerances retained. No full engine-skin comparison, contact, GPU, physics, human or release approval.')
        fresh_json(output/'result.json',result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('contacts',type=Path);p.add_argument('policy',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--engine-capture',type=Path);p.add_argument('--capture-receipt-sha256')
    p.add_argument('--partner-query-batch-size',type=int,default=32)
    for command in ('advance','finalize'):
        p=sub.add_parser(command);p.add_argument('journal',type=Path);p.add_argument('checkpoint');p.add_argument('checkpoint_sha256')
        if command=='advance':p.add_argument('--maximum-samples',type=int,default=16)
        else:p.add_argument('output',type=Path)
    a=parser.parse_args()
    if a.command=='prepare':result=prepare(a.contacts,a.policy,a.output,engine_capture=a.engine_capture,capture_receipt_sha256=a.capture_receipt_sha256,partner_query_batch_size=a.partner_query_batch_size)
    elif a.command=='advance':result=advance(a.journal,a.checkpoint,a.checkpoint_sha256,maximum_samples=a.maximum_samples)
    else:result=finalize(a.journal,a.checkpoint,a.checkpoint_sha256,a.output)
    print(json.dumps(result))
