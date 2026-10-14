"""Execute trusted key continuation using immutable recorded Python source bytes."""
import argparse
from pathlib import Path
import re
import shutil
import sys
from strep import ROOT,read,save,sha256

HELPERS=('native_key_restoration_continuation.py','native_key_continuation_job.py','audit_native_key_continuation_job.py')
NAME=re.compile(r'[A-Za-z_][A-Za-z_0-9]*\.py')
SCHEMA='strep-frozen-key-continuation-runtime-v1'


def require(condition,message):
    if not condition:raise ValueError(message)


def digest(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def contained(path):
    path=Path(path).resolve()
    require(path.is_relative_to((ROOT/'reports').resolve()),'Only project report inputs and outputs are supported')
    return path


def build(recipe_path,output,*,audit=None):
    recipe_path=contained(recipe_path);output=contained(output)
    require(not output.exists() and not recipe_path.is_relative_to(output),'Fresh separate frozen runtime required')
    recipe=read(recipe_path);require(recipe.get('schema')=='strep-native-key-continuation-job-v1','Explicit public continuation recipe required')
    parent=recipe['parent'];producer=contained(recipe_path.parent/parent['path']);proof=contained(recipe_path.parent/parent['replay'])
    require(not output.is_relative_to(producer) and not proof.is_relative_to(output),'Original parent and replay must remain separate')
    pins={str(recipe_path):sha256(recipe_path)}
    for path,value in ((producer/'result.json',parent['result_sha256']),(producer/'request.json',parent['request_sha256']),(proof,parent['replay_sha256'])):
        require(digest(value) and sha256(path)==value,'Trusted parent/request/replay binding changed');pins[str(path)]=value
    request=read(producer/'request.json');result=read(producer/'result.json');replay=read(proof)
    require(request['schema']==result['schema']=='strep-native-key-interval-restoration-v1' and result['status']=='complete','Completed standard parent required')
    require(result['source_request_sha256']==parent['request_sha256'] and replay['schema']=='strep-native-key-restoration-replay-v1'
        and replay['status']=='complete' and replay['producer_result_sha256']==parent['result_sha256']
        and replay['producer_request_sha256']==parent['request_sha256'] and replay['retention_history_replayed'] is True,'Bound complete original numerical replay required')
    for value in (request,result,replay):
        require(value['original_selected'] is True and value['quality_approved'] is False and value['release_approved'] is False,'Frozen execution cannot inherit approval')
    recipes=[contained(p) for p in request['source_bindings_sha256'] if Path(p).suffix=='.json' and read(p).get('schema')=='strep-native-key-interval-restoration-v1']
    require(len(recipes)==1 and read(recipes[0])==request['recipe'],'Original initializer recipe required')
    initial=contained(recipes[0].parent/request['recipe']['producer']['path'])
    for filename,key in (('request.json','request_sha256'),('result.json','result_sha256')):
        path=initial/filename;value=request['recipe']['producer'][key]
        require(digest(value) and sha256(path)==value,'Original initializer binding changed');pins[str(path)]=value
    initial_request=read(initial/'request.json');files={};origins={};archives=[(initial,initial_request),(producer,request)];target=None
    if audit is not None:
        path,rd,qd=audit;path=contained(path)
        require(not output.is_relative_to(path),'Audited job must remain separate')
        for filename,h in (('result.json',rd),('request.json',qd)):
            require(digest(h) and sha256(path/filename)==h,'Trusted audited-job binding changed');pins[str(path/filename)]=h
        job=read(path/'request.json');value=read(path/'result.json')
        require(job['schema']==value['schema']=='strep-native-key-continuation-job-v1' and value['status']=='complete'
            and value['source_request_sha256']==qd,'Completed public continuation job required')
        for record in (job,value):require(record['original_selected'] is True and record['quality_approved'] is False
            and record['release_approved'] is False,'Audited job cannot inherit approval')
        archives.append((path,job));target=dict(path=str(path),result_sha256=rd,request_sha256=qd)
    # Reconcile all recorded files, not just a guessed dependency subset.
    for archive,metadata in archives:
        for name,h in metadata['implementation_sha256'].items():
            require(isinstance(name,str) and NAME.fullmatch(name) and digest(h),'Contained recorded Python source required')
            source=(archive/'implementation'/name).resolve()
            require(source.parent==(archive/'implementation').resolve() and sha256(source)==h,'Archived method changed')
            require(name not in files or sha256(files[name])==h,'Recorded source versions conflict; explicit migration required')
            files[name]=source;origins.setdefault(name,[]).append(dict(path=str(source),sha256=h));pins[str(source)]=h
        for path,h in metadata['source_bindings_sha256'].items():
            require(sha256(contained(path))==h,'Original source input changed');pins[str(Path(path).resolve())]=h
    for name in HELPERS:
        if name not in files:
            source=ROOT/'scripts'/name;files[name]=source;origins[name]=[dict(path=str(source),sha256=sha256(source))];pins[str(source)]=sha256(source)
    require('strep.py' in files and 'action_worker_lock.py' in files and len(files)<=2048
        and sum(p.stat().st_size for p in files.values())<=32*1024**2,'Bounded complete frozen runtime required')
    output.mkdir(parents=True);scripts=output/'scripts';scripts.mkdir()
    try:
        for name,path in files.items():shutil.copyfile(path,scripts/name)
        hashes={name:sha256(scripts/name) for name in files}
        require(all(sha256(p)==h for p,h in pins.items()),'Inputs changed while freezing runtime')
        receipt=dict(schema=SCHEMA,project_root=str(ROOT.resolve()),recipe=str(recipe_path),recipe_sha256=sha256(recipe_path),
            inputs_sha256=pins,implementation_sha256=hashes,origins=origins,bootstrap_sha256=sha256(Path(__file__)),
            audit_producer=target,shared_worker_lock_root=str(ROOT.resolve()),original_reference_unchanged=True,original_selected=True,quality_approved=False,release_approved=False)
        save(output/'runtime.json',receipt);return receipt
    except BaseException:
        # Partial bytes are retained; absence of the complete receipt prevents execution.
        raise


def execute(runtime,output,*,audit=None):
    runtime=contained(runtime);output=contained(output);receipt=read(runtime/'runtime.json')
    require(set(receipt)=={'schema','project_root','recipe','recipe_sha256','inputs_sha256','implementation_sha256','origins',
        'bootstrap_sha256','audit_producer','shared_worker_lock_root','original_reference_unchanged','original_selected','quality_approved','release_approved'},'Explicit frozen runtime receipt required')
    require(receipt['schema']==SCHEMA and receipt['project_root']==str(ROOT.resolve())
        and receipt['bootstrap_sha256']==sha256(Path(__file__)),'Bound current frozen-runtime bootstrap required')
    require(receipt['shared_worker_lock_root']==str(ROOT.resolve()) and receipt['original_reference_unchanged'] is True
        and receipt['original_selected'] is True and receipt['quality_approved'] is False and receipt['release_approved'] is False,'Frozen runtime scope changed')
    require(not output.exists() and not output.is_relative_to(runtime),'Fresh output outside frozen runtime required')
    names=receipt['implementation_sha256']
    require(0<len(names)<=2048 and all(NAME.fullmatch(n) and digest(h) for n,h in names.items()),'Contained complete runtime methods required')
    entries=list((runtime/'scripts').iterdir())
    require(set(p.name for p in entries)==set(names) and all(p.is_file() and not p.is_symlink() for p in entries),
        'No unrecorded files, packages, links or bytecode may enter frozen imports')
    require(all((runtime/'scripts'/n).resolve().parent==(runtime/'scripts').resolve() for n in names),'Frozen source escapes runtime')
    require(sha256(contained(receipt['recipe']))==receipt['recipe_sha256'],'Frozen recipe changed')
    require(all(sha256(p)==h for p,h in receipt['inputs_sha256'].items()),'Frozen-runtime input binding changed')
    require(all(sha256(runtime/'scripts'/n)==h for n,h in receipt['implementation_sha256'].items()),'Frozen-runtime source changed')
    # A fresh process is required: no already-imported numerical module may leak
    # current implementations into the recorded source environment.
    require(not any(n in sys.modules for n in ('numpy','native_key_interval_model','native_key_continuation_job','action_worker_lock')),'Fresh worker process required')
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(runtime/'scripts'))
    del sys.modules['strep']
    import strep as frozen_strep
    import action_worker_lock
    require(Path(frozen_strep.__file__).resolve()==runtime/'scripts/strep.py'
        and Path(action_worker_lock.__file__).resolve()==runtime/'scripts/action_worker_lock.py','Recorded runtime import required')
    # Keep the historical source hash root; only coordinate the OS worker lock
    # with the live project. This assignment is recorded by the bootstrap hash.
    action_worker_lock.ROOT=ROOT.resolve()
    if audit is None:
        from native_key_continuation_job import run
        value=run(receipt['recipe'],output)
    else:
        producer,rd,qd=audit;producer=contained(producer)
        require(receipt['audit_producer'] is None or receipt['audit_producer']==dict(path=str(producer),result_sha256=rd,request_sha256=qd),'Frozen audited-job identity changed')
        from audit_native_key_continuation_job import run
        value=run(producer,output,rd,qd)
    require(all(sha256(p)==h for p,h in receipt['inputs_sha256'].items())
        and all(sha256(runtime/'scripts'/n)==h for n,h in receipt['implementation_sha256'].items()),'Frozen bindings changed during execution')
    save(output/'frozen-runtime-execution.json',dict(schema='strep-frozen-key-continuation-execution-v1',runtime_sha256=sha256(runtime/'runtime.json'),
        bootstrap_sha256=receipt['bootstrap_sha256'],shared_worker_lock_root=str(ROOT.resolve()),auditor_executed=audit is not None,
        source_request_sha256=sha256(output/'request.json') if audit is None else value['producer_request_sha256'],
        original_reference_unchanged=True,original_selected=True,quality_approved=False,release_approved=False))
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('build');p.add_argument('recipe',type=Path);p.add_argument('runtime',type=Path)
    p.add_argument('--audit-producer',type=Path);p.add_argument('--expected-result-sha256');p.add_argument('--expected-request-sha256')
    p=sub.add_parser('run');p.add_argument('runtime',type=Path);p.add_argument('output',type=Path)
    p=sub.add_parser('audit');p.add_argument('runtime',type=Path);p.add_argument('producer',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--expected-result-sha256',required=True);p.add_argument('--expected-request-sha256',required=True)
    a=parser.parse_args()
    if a.command=='build':
        require(bool(a.audit_producer)==bool(a.expected_result_sha256)==bool(a.expected_request_sha256),'Audited-job path and both digests must be supplied together')
        build(a.recipe,a.runtime,audit=None if a.audit_producer is None else (a.audit_producer,a.expected_result_sha256,a.expected_request_sha256))
    elif a.command=='run':execute(a.runtime,a.output)
    else:execute(a.runtime,a.output,audit=(a.producer,a.expected_result_sha256,a.expected_request_sha256))
