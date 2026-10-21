"""Pinned full-frame recovery for the complete imported-mesh geometry audit.

Uses MeshPropScene's existing queries, limits and original triangles. An
unfinished prefix never supplies a complete geometry decision to correction.
"""
import argparse
import gc
import hashlib
import json
import os
from contextlib import nullcontext
from pathlib import Path
import shutil
import uuid
import numpy as np
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_verification_lock as worker_lock
from strep import ROOT,read,sha256
from native_mesh_prop_scene import MeshPropScene,_json,METHODS as MESH_METHODS
from native_observation_archive import ObservationArchive,verify as verify_archive
from native_geometry_journal import require,local,fresh_json,anchor,publish,runtime
from native_geometry_journal import METHODS as JOURNAL_METHODS

METHODS=tuple(sorted(set(MESH_METHODS)|set(JOURNAL_METHODS)|{'native_mesh_geometry_journal.py'}))
VARIABLE={'samples','times_s','sample_indices','complete_clock_s',
          'all_policy_samples_evaluated','sampled_conditions_pass'}


def batch_size(value):
    require(type(value) is int and 1<=value<=32,'Mesh query batch size must be an integer from 1 through 32')
    return value


def header(report):return {k:v for k,v in report.items() if k not in VARIABLE}


def header_digest(report):
    return hashlib.sha256(json.dumps(header(report),sort_keys=True,allow_nan=False).encode()).hexdigest()


def check_bindings(request):
    require(request['runtime']==runtime(),'Mesh journal runtime changed')
    require(all(sha256(p)==h for p,h in request['inputs_sha256'].items()),'Mesh journal source changed')
    require(all(sha256(ROOT/'scripts'/n)==h for n,h in request['implementation_sha256'].items()),'Mesh journal implementation changed')


def prepare(manifest_path,policy_path,folder,*,query_batch_size=4):
    batch_size(query_batch_size)
    manifest_path,policy_path,folder=[Path(p).resolve() for p in (manifest_path,policy_path,folder)]
    require(not folder.exists(),'Fresh mesh geometry journal required')
    with worker_lock(),threadpool_limits(limits=1):
        scene=MeshPropScene(manifest_path);policy,policy_digest=_json(policy_path)
        times,_,_=scene._clock(policy)
        inputs={**scene.inputs,str(policy_path):policy_digest}
        require(all(not Path(p).is_relative_to(folder) for p in inputs),'Journal contains its own input')
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        folder.mkdir(parents=True)
        for name in ('implementation','input','checkpoints','frames'):(folder/name).mkdir()
        for name in methods:shutil.copyfile(ROOT/'scripts'/name,folder/'implementation'/name)
        snapshots={}
        for i,(path,digest) in enumerate(inputs.items()):
            target=folder/'input'/f'{i}{Path(path).suffix}'
            shutil.copyfile(path,target);require(sha256(target)==digest,'Mesh input snapshot differs')
            snapshots[path]=dict(path=target.relative_to(folder).as_posix(),sha256=digest)
        request=dict(schema='strep-native-mesh-geometry-journal-v1',mesh_scene=str(manifest_path),policy=str(policy_path),
                     inputs_sha256=inputs,source_snapshots=snapshots,implementation_sha256=methods,
                     runtime=runtime(),times_s=times.tolist(),query_batch_size=query_batch_size,
                     quality_approved=False,release_approved=False)
        check_bindings(request)
        require(all(sha256(folder/'implementation'/n)==h for n,h in methods.items()),'Mesh method snapshot differs')
        fresh_json(folder/'request.json',request)
        return publish(folder,dict(schema='strep-native-mesh-geometry-checkpoint-v1',request_sha256=sha256(folder/'request.json'),
            next_sample=0,total_samples=len(times),previous=None,frame=None,header_sha256=None,checked_prefix_pass=True,
            sampled_conditions_pass=False,quality_approved=False,release_approved=False))


def context(folder):
    request=read(folder/'request.json')
    require(request['schema']=='strep-native-mesh-geometry-journal-v1','Explicit mesh journal required')
    batch_size(request['query_batch_size'])
    require(request['quality_approved'] is False and request['release_approved'] is False,'Journal cannot approve release')
    require(set(request['implementation_sha256'])==set(METHODS),'Complete mesh journal methods required')
    check_bindings(request)
    require(all(sha256(folder/'implementation'/n)==h for n,h in request['implementation_sha256'].items()),'Mesh method archive changed')
    require(set(request['source_snapshots'])==set(request['inputs_sha256']),'Complete mesh input snapshots required')
    for path,snapshot in request['source_snapshots'].items():
        require(sha256(local(folder,snapshot['path']))==snapshot['sha256']==request['inputs_sha256'][path],'Mesh snapshot changed')
    scene=MeshPropScene(request['mesh_scene']);policy,policy_digest=_json(Path(request['policy']))
    require({**scene.inputs,request['policy']:policy_digest}==request['inputs_sha256'],'Complete mesh source bindings required')
    times,_,_=scene._clock(policy)
    require(times.tolist()==request['times_s'],'Complete mesh clock changed')
    return request,scene,policy,times


def frame(folder,entry,request):
    index=entry['index']
    require(type(index) is int and 0<=index<len(request['times_s']),'Existing mesh frame index required')
    directory=local(folder,entry['directory']);receipt=directory/'receipt.json'
    require(sha256(receipt)==entry['receipt_sha256'],'Mesh frame receipt changed')
    value=read(receipt)
    require(value['index']==index and value['request_sha256']==sha256(folder/'request.json'),'Mesh frame request or index differs')
    require(set(value['files_sha256'])=={'geometry.json','observations.npz','observations.npz.receipt.json'},'Complete mesh frame artifacts required')
    require(all(sha256(directory/n)==h for n,h in value['files_sha256'].items()),'Mesh frame artifact changed')
    verify_archive(directory/'observations.npz')
    report=read(directory/'geometry.json');time=request['times_s'][index]
    require(report['schema']=='strep-native-mesh-prop-geometry-result-v1'
        and report['complete_clock_s']==request['times_s'] and report['sample_indices']==[index]
        and report['times_s']==[time] and len(report['samples'])==1
        and report['samples'][0]['index']==index and report['samples'][0]['time_s']==time,
        'Exact original mesh frame identity required')
    require(report['all_policy_samples_evaluated'] is (len(request['times_s'])==1)
        and type(report['sampled_conditions_pass']) is bool
        and report['sampled_conditions_pass'] is report['samples'][0]['passed'],
        'Mesh frame coverage or decision differs')
    require(report['query_batch_size']==request['query_batch_size'],'Mesh frame query batch differs')
    require(all(report[key] is False for key in ('quality_approved','release_approved','topology_modified','collision_verified',
        'continuous_collision_certified','self_collision_verified','motion_fitted','physics_verified')),'Mesh frame cannot claim certification')
    with np.load(directory/'observations.npz',allow_pickle=False) as arrays:
        require(np.array_equal(arrays['times_s'],np.array([time])),'Mesh frame observation clock differs')
    return report,directory/'observations.npz'


def chain(folder,checkpoint,expected_sha256,request,*,consume=None):
    path=local(folder,checkpoint);rows=[];seen=set();binding=sha256(folder/'request.json');total=len(request['times_s'])
    while True:
        require(path not in seen and sha256(path)==expected_sha256,'Pinned mesh checkpoint changed or cyclic chain')
        seen.add(path);row=read(path)
        require(row['schema']=='strep-native-mesh-geometry-checkpoint-v1' and row['request_sha256']==binding
            and type(row['next_sample']) is int and 0<=row['next_sample']<=total and row['total_samples']==total,
            'Mesh checkpoint request or population differs')
        require(row['sampled_conditions_pass'] is False and row['quality_approved'] is False
            and row['release_approved'] is False,'Mesh checkpoint cannot approve complete geometry')
        rows.append(row)
        if row['previous'] is None:break
        require(len(rows)<=total+1,'Mesh checkpoint chain exceeds complete clock')
        path=local(folder,row['previous']['checkpoint']);expected_sha256=row['previous']['sha256']
    rows.reverse()
    require(rows[0]['next_sample']==0 and rows[0]['frame'] is None and rows[0]['header_sha256'] is None
        and rows[0]['checked_prefix_pass'] is True,'Empty mesh checkpoint genesis required')
    passed=True;first_header=None
    for i,row in enumerate(rows[1:]):
        require(row['next_sample']==i+1 and row['frame']['index']==i,'Complete ordered mesh prefix required')
        report,archive=frame(folder,row['frame'],request);digest=header_digest(report)
        if first_header is None:first_header=digest
        passed &= report['sampled_conditions_pass']
        require(row['header_sha256']==digest==first_header and row['checked_prefix_pass'] is passed,'Mesh checkpoint reduction differs')
        if consume is not None:consume(row['frame'],report,archive)
    return rows[-1]


def advance(folder,checkpoint,expected_sha256,*,maximum_samples=16):
    folder=Path(folder).resolve()
    require(type(maximum_samples) is int and 1<=maximum_samples<=4096,'Bounded complete-frame mesh work count required')
    with worker_lock(),threadpool_limits(limits=1):
        anchor(folder,checkpoint,expected_sha256)
        request,scene,policy,times=context(folder);current=chain(folder,checkpoint,expected_sha256,request)
        require(current['next_sample']<len(times),'Complete mesh prefix is ready for finalization')
        receipt=dict(checkpoint=checkpoint,sha256=expected_sha256)
        for index in range(current['next_sample'],min(len(times),current['next_sample']+maximum_samples)):
            directory=folder/'frames'/f'{index:06d}-{uuid.uuid4().hex}';directory.mkdir()
            with ObservationArchive(directory/'observations.npz') as sink:
                report,_=scene.geometry(policy,sample_indices=[index],observation_sink=sink,query_batch_size=request['query_batch_size'])
            fresh_json(directory/'geometry.json',report);digest=header_digest(report)
            require(current['header_sha256'] in (None,digest),'Mesh geometry header differs across frames')
            check_bindings(request)
            anchor(folder,checkpoint,expected_sha256)
            fresh_json(directory/'receipt.json',dict(index=index,request_sha256=sha256(folder/'request.json'),
                files_sha256={n:sha256(directory/n) for n in ('geometry.json','observations.npz','observations.npz.receipt.json')}))
            current=dict(schema='strep-native-mesh-geometry-checkpoint-v1',request_sha256=sha256(folder/'request.json'),
                next_sample=index+1,total_samples=len(times),previous=receipt,
                frame=dict(index=index,directory=directory.relative_to(folder).as_posix(),receipt_sha256=sha256(directory/'receipt.json')),
                header_sha256=digest,checked_prefix_pass=bool(current['checked_prefix_pass'] and report['sampled_conditions_pass']),
                sampled_conditions_pass=False,quality_approved=False,release_approved=False)
            receipt=publish(folder,current)
            gc.collect()
        return receipt


def ordered_entries(folder,last):
    entries=[];row=last
    while row['previous'] is not None:
        entries.append(row['frame']);row=read(local(folder,row['previous']['checkpoint']))
    return list(reversed(entries))


def verify(folder,checkpoint,expected_sha256):
    """Verify a pinned prefix without treating it as a finalized geometry pass."""
    folder=Path(folder).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        anchor(folder,checkpoint,expected_sha256)
        request,_,_,times=context(folder)
        last=chain(folder,checkpoint,expected_sha256,request)
        check_bindings(request)
        anchor(folder,checkpoint,expected_sha256)
        return dict(schema='strep-native-mesh-geometry-verification-v1',status='verified',
            source_checkpoint=checkpoint,source_checkpoint_sha256=expected_sha256,
            request_sha256=last['request_sha256'],completed_samples=last['next_sample'],
            total_samples=len(times),population_complete=last['next_sample']==len(times),
            checked_prefix_pass=last['checked_prefix_pass'],sampled_conditions_pass=False,
            query_batch_size=request['query_batch_size'],quality_approved=False,release_approved=False)


def finalize(folder,checkpoint,expected_sha256,output,*,materialize_observations=True):
    require(type(materialize_observations) is bool,'Explicit observation materialization choice required')
    folder,output=Path(folder).resolve(),Path(output).resolve()
    require(not output.exists() and not folder.is_relative_to(output),'Fresh separate mesh geometry output required')
    with worker_lock(),threadpool_limits(limits=1):
        anchor(folder,checkpoint,expected_sha256)
        request,_,_,times=context(folder)
        # This early check only rejects partial work. The complete chain and
        # every frame are still verified before a final result can publish.
        require(read(local(folder,checkpoint))['next_sample']==len(times),'Full original mesh population required before finalization')
        output.mkdir(parents=True);entries=[];metadata={}
        transport=ObservationArchive(output/'observations.npz') if materialize_observations else nullcontext(None)
        with (output/'geometry.json').open('x',encoding='utf8',newline='\n') as stream,transport as sink:
            stream.write('{"samples":[')
            if sink is not None:sink['times_s']=times
            def consume(entry,report,archive):
                # Stream the report just validated by the chain instead of
                # decompressing and validating that frame a second time.
                if entries:stream.write(',')
                else:metadata.update(header(report))
                json.dump(report['samples'][0],stream,allow_nan=False)
                if sink is not None:
                    with np.load(archive,allow_pickle=False) as arrays:
                        for name in arrays.files:
                            if name!='times_s':sink[name]=arrays[name]
                entries.append(entry)
            last=chain(folder,checkpoint,expected_sha256,request,consume=consume)
            require(last['next_sample']==len(times) and len(entries)==len(times),'Full verified mesh population required')
            metadata.update(times_s=times.tolist(),complete_clock_s=times.tolist(),sample_indices=list(range(len(times))),
                            all_policy_samples_evaluated=True,sampled_conditions_pass=last['checked_prefix_pass'])
            stream.write('],');stream.write(json.dumps(metadata,allow_nan=False)[1:]);stream.write('\n')
        check_bindings(request)
        anchor(folder,checkpoint,expected_sha256)
        if materialize_observations:
            verify_archive(output/'observations.npz')
            observation=dict(observations_format='npz',observations_sha256=sha256(output/'observations.npz'),
                observation_receipt_sha256=sha256(output/'observations.npz.receipt.json'))
        else:
            # Reference the pinned completed frames; do not duplicate every
            # humanoid vertex array just to concatenate it into another ZIP.
            index=dict(schema='strep-native-mesh-observation-index-v1',source_journal=os.path.relpath(folder,output),
                source_checkpoint=checkpoint,source_checkpoint_sha256=expected_sha256,
                request_sha256=sha256(folder/'request.json'),times_s=times.tolist(),frames=entries,
                population_complete=True,source_values_preserved=True,quality_approved=False,release_approved=False)
            fresh_json(output/'observations-index.json',index)
            observation=dict(observations_format='frame-index',observation_index_sha256=sha256(output/'observations-index.json'))
        result=dict(schema='strep-native-mesh-geometry-journal-result-v1',status='complete',samples=len(times),
            source_checkpoint=checkpoint,source_checkpoint_sha256=expected_sha256,request_sha256=sha256(folder/'request.json'),
            geometry_sha256=sha256(output/'geometry.json'),**observation,sampled_conditions_pass=last['checked_prefix_pass'],
            query_batch_size=request['query_batch_size'],quality_approved=False,release_approved=False,
            scope='Complete declared MeshPropScene geometry assembled from pinned full-frame observations. Original triangles, '
                  'queries, planes, native/frame clocks and limits retained. No clip correction, continuous collision, '
                  'self-collision, engine, dynamics, semantic or animation-quality approval.')
        fresh_json(output/'result.json',result);return result


def iter_observations(index_path,expected_sha256):
    """Yield the complete original array population from a pinned frame index.

    Consuming only part of this iterator is not a complete replay. Original
    inputs and methods remain bound, as for the journal itself; this is not a
    standalone portable asset or a permission to detach it from provenance.
    """
    index_path=Path(index_path).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        require(sha256(index_path)==expected_sha256,'Pinned observation index changed')
        index=read(index_path)
        require(index['schema']=='strep-native-mesh-observation-index-v1'
            and index['population_complete'] is True and index['source_values_preserved'] is True
            and index['quality_approved'] is False and index['release_approved'] is False,'Complete unchanged observation index required')
        source=index['source_journal']
        require(isinstance(source,str) and bool(source) and not Path(source).is_absolute(),'Relative source journal required')
        folder=(index_path.parent/source).resolve()
        anchor(folder,index['source_checkpoint'],index['source_checkpoint_sha256'])
        request,_,_,times=context(folder)
        require(index['request_sha256']==sha256(folder/'request.json'),'Observation index request differs')
        last=chain(folder,index['source_checkpoint'],index['source_checkpoint_sha256'],request)
        entries=ordered_entries(folder,last)
        require(last['next_sample']==len(times) and index['times_s']==times.tolist() and index['frames']==entries,
                'Complete ordered observation population required')
        yield 'times_s',times
        seen={'times_s'}
        for entry in entries:
            _,archive=frame(folder,entry,request)
            with np.load(archive,allow_pickle=False) as arrays:
                for name in arrays.files:
                    if name=='times_s':continue
                    require(name not in seen,'Duplicate indexed observation name')
                    seen.add(name);yield name,arrays[name]
        check_bindings(request)
        anchor(folder,index['source_checkpoint'],index['source_checkpoint_sha256'])
        require(sha256(index_path)==expected_sha256,'Observation index changed during replay')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare')
    p.add_argument('mesh_scene',type=Path);p.add_argument('policy',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--query-batch-size',type=int,default=4)
    for command in ('advance','verify','finalize'):
        p=sub.add_parser(command)
        p.add_argument('journal',type=Path);p.add_argument('checkpoint');p.add_argument('checkpoint_sha256')
        if command=='advance':p.add_argument('--maximum-samples',type=int,default=16)
        if command=='finalize':
            p.add_argument('output',type=Path)
            p.add_argument('--indexed-observations',action='store_true',
                help='Reference the pinned frame archives instead of duplicating arrays into a combined NPZ.')
    args=parser.parse_args(argv)
    if args.command=='prepare':
        result=prepare(args.mesh_scene,args.policy,args.output,query_batch_size=args.query_batch_size)
    elif args.command=='advance':
        result=advance(args.journal,args.checkpoint,args.checkpoint_sha256,maximum_samples=args.maximum_samples)
    elif args.command=='verify':
        result=verify(args.journal,args.checkpoint,args.checkpoint_sha256)
    else:
        result=finalize(args.journal,args.checkpoint,args.checkpoint_sha256,args.output,
            materialize_observations=not args.indexed_observations)
    print(json.dumps(result,allow_nan=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
