"""Run complete frozen numeric replays serially in fresh Python processes.

No metric, motion or admission-policy changes. Use the owned outer RAM guard.
"""
import argparse,hashlib,importlib,importlib.util,json,re,runpy,subprocess,sys,time
from pathlib import Path

SCHEMA='strep-isolated-python-replay-v1'


def require(value,message):
    if not value:raise ValueError(message)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1048576),b''):h.update(part)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_bytes())


def save(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')


def validate(protocol):
    require(isinstance(protocol,dict) and set(protocol)=={'schema','project_root','module_root','preload_modules','sources_sha256','entries','phase_seconds','forbid_torch','launcher_sha256'} and protocol['schema']==SCHEMA,'Complete replay protocol required')
    root=Path(protocol['project_root']).resolve();modules=Path(protocol['module_root']).resolve()
    require(root.is_dir() and modules.is_dir() and modules.is_relative_to(root),'In-project frozen module root required')
    require(type(protocol['forbid_torch']) is bool and type(protocol['phase_seconds']) is int and 1<=protocol['phase_seconds']<=1800,'Explicit replay environment/time policy required')
    require(protocol['launcher_sha256']==digest(__file__),'Replay launcher changed')
    names=protocol['preload_modules'];bindings=protocol['sources_sha256'];entries=protocol['entries']
    require(isinstance(names,list) and len(names)<=64 and all(isinstance(n,str) and re.fullmatch(r'[a-zA-Z_][a-zA-Z_0-9]*',n) for n in names) and len(names)==len(set(names)),'Explicit frozen preload names required')
    require(isinstance(bindings,dict) and 1<=len(bindings)<=5000,'Complete bounded frozen source bindings required')
    for path,h in bindings.items():
        p=Path(path).resolve();require(p.is_relative_to(root) and p.is_file() and isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h) and digest(p)==h,'Frozen source binding changed')
    for path in [Path(__file__).resolve(),Path(__file__).resolve().with_name('process_monitor.py')]:
        require(str(path) in bindings,'Launcher and owned-process cleanup must be source-bound')
    require(isinstance(entries,list) and 1<=len(entries)<=64,'Complete bounded replay entries required')
    seen=set();outputs=set()
    for entry in entries:
        require(isinstance(entry,dict) and set(entry)=={'name','script','outputs'} and isinstance(entry['name'],str) and re.fullmatch('[a-zA-Z][a-zA-Z0-9_-]{0,79}',entry['name']) and entry['name'] not in seen,'Unique named replay entry required');seen.add(entry['name'])
        script=Path(entry['script']).resolve();require(script.suffix=='.py' and str(script) in bindings,'Bound Python replay required')
        require(isinstance(entry['outputs'],list) and 1<=len(entry['outputs'])<=32,'Explicit complete output population required')
        for name in entry['outputs']:
            p=Path(name).resolve();require(p.is_relative_to(root) and p not in outputs and str(p) not in bindings,'Distinct in-project outputs separate from source required');outputs.add(p)
    for name in names:
        require(str(modules/(name+'.py')) in bindings,'Preloaded module not source-bound')
    return root,modules


def child(protocol_path,index):
    protocol=read(protocol_path);root,modules=validate(protocol)
    require(type(index) is int and 0<=index<len(protocol['entries']),'Bound replay index required')
    if protocol['forbid_torch']:require(importlib.util.find_spec('torch') is None,'Torch-free replay interpreter required')
    sys.path.insert(0,str(modules))
    for name in protocol['preload_modules']:
        module=importlib.import_module(name);require(Path(module.__file__).resolve().parent==modules,'Frozen module import differs')
        if name=='strep':module.ROOT=root
    runpy.run_path(protocol['entries'][index]['script'],run_name='__main__')
    validate(protocol)


def run(protocol_path,output):
    protocol_path=Path(protocol_path).resolve();output=Path(output).resolve();protocol=read(protocol_path);root,_=validate(protocol)
    require(output.is_relative_to(root/'reports') and not output.exists(),'Fresh ignored execution folder required')
    output.mkdir();snapshot=output/'protocol.json';snapshot.write_bytes(protocol_path.read_bytes());binding=digest(snapshot)
    pipeline=output/'pipeline.json';save(pipeline,dict(status='processing',protocol_sha256=binding,quality_approved=False,release_approved=False))
    receipts=[];started=time.monotonic();process=None
    def verify_completed_outputs():
        require(all(Path(p).is_file() and digest(p)==h for receipt in receipts for p,h in receipt['outputs_sha256'].items()),'Completed replay output changed')
    try:
        for index,entry in enumerate(protocol['entries']):
            validate(protocol);require(digest(protocol_path)==binding,'Replay protocol changed')
            verify_completed_outputs()
            require(all(not Path(p).exists() for p in entry['outputs']),'Preserve existing phase outputs')
            log=output/(entry['name']+'.log');phase_start=time.monotonic()
            with log.open('w',encoding='utf8') as stream:
                process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),str(snapshot),'--child-entry',str(index)],cwd=root,stdout=stream,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                save(pipeline,dict(status='processing',active_phase=entry['name'],child_pid=process.pid,completed_phases=len(receipts),protocol_sha256=binding,quality_approved=False,release_approved=False))
                try:code=process.wait(timeout=protocol['phase_seconds'])
                except subprocess.TimeoutExpired:
                    from process_monitor import kill_tree
                    kill_tree(process.pid,reap_parent=False);process.wait();raise RuntimeError('Replay phase exceeded its bound')
            require(code==0,'Replay phase failed: '+entry['name'])
            require(all(Path(p).is_file() for p in entry['outputs']),'Complete replay outputs required')
            receipt=dict(name=entry['name'],exit_code=code,seconds=time.monotonic()-phase_start,child_pid=process.pid,
                outputs_sha256={p:digest(p) for p in entry['outputs']},log_sha256=digest(log))
            receipts.append(receipt);save(output/'phases.json',receipts);print(json.dumps(receipt),flush=True)
        validate(protocol);require(digest(protocol_path)==binding,'Replay protocol changed');verify_completed_outputs()
        result=dict(status='complete',seconds=time.monotonic()-started,protocol_sha256=binding,phases=receipts,
            scope='Serial process lifecycle and complete frozen source/output binding. Numerical conclusions belong to the unchanged individual auditors; no quality or release approval.',quality_approved=False,release_approved=False)
        save(output/'result.json',result);save(pipeline,dict(status='complete',protocol_sha256=binding,quality_approved=False,release_approved=False));return result
    except BaseException as exc:
        if process is not None and process.poll() is None:
            from process_monitor import kill_tree
            kill_tree(process.pid,reap_parent=False);process.wait()
        save(pipeline,dict(status='failed',error=repr(exc),completed_phases=len(receipts),protocol_sha256=binding,quality_approved=False,release_approved=False));raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('protocol',type=Path);parser.add_argument('output',type=Path,nargs='?');parser.add_argument('--child-entry',type=int);args=parser.parse_args()
    if args.child_entry is not None:child(args.protocol,args.child_entry)
    else:
        if args.output is None:parser.error('Fresh output folder required')
        print(json.dumps(run(args.protocol,args.output)))
