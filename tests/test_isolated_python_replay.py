"""Real child lifecycle, complete frozen replay and evidence preservation guards."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
import psutil
import pytest

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def fixture(tmp_path):
    scripts=tmp_path/'scripts';scripts.mkdir();(tmp_path/'reports').mkdir()
    for name in ['isolated_python_replay.py','process_monitor.py']:
        shutil.copyfile(ROOT/'scripts'/name,scripts/name)
    modules=tmp_path/'frozen';modules.mkdir()
    (modules/'probe.py').write_text('count=0\n',encoding='utf8')
    entries=[]
    for index in range(2):
        target=tmp_path/'reports'/f'phase-{index}.json';script=tmp_path/f'phase-{index}.py'
        script.write_text("import os,json,probe\nfrom pathlib import Path\nprobe.count+=1\nPath("+repr(str(target))+" ).write_text(json.dumps(dict(pid=os.getpid(),count=probe.count,module=probe.__file__)))\n",encoding='utf8')
        entries.append(dict(name=f'phase-{index}',script=str(script),outputs=[str(target)]))
    protocol=dict(schema='strep-isolated-python-replay-v1',project_root=str(tmp_path),module_root=str(modules),preload_modules=['probe'],
        sources_sha256={str(p):sha(p) for p in [*scripts.glob('*.py'),*modules.glob('*.py'),*(Path(e['script']) for e in entries)]},
        entries=entries,phase_seconds=10,forbid_torch=False,launcher_sha256=sha(scripts/'isolated_python_replay.py'))
    return tmp_path,scripts/'isolated_python_replay.py',protocol


def execute(fixture):
    root,launcher,protocol=fixture;path=root/'protocol.json';path.write_text(json.dumps(protocol),encoding='utf8')
    completed=subprocess.run([sys.executable,str(launcher),str(path),str(root/'reports'/'execution')],cwd=root,capture_output=True,text=True,timeout=30)
    return completed,root/'reports'/'execution'


def change_script(fixture,index,body):
    _,_,p=fixture;path=Path(p['entries'][index]['script']);path.write_text(body,encoding='utf8');p['sources_sha256'][str(path)]=sha(path)


def test_complete_phases_use_fresh_reaped_processes_and_frozen_imports(fixture):
    completed,output=execute(fixture);assert completed.returncode==0,completed.stderr
    root,_,p=fixture;records=[json.loads(Path(e['outputs'][0]).read_text()) for e in p['entries']]
    assert records[0]['pid']!=records[1]['pid']
    assert all(r['count']==1 and Path(r['module'])==root/'frozen'/'probe.py' and not psutil.pid_exists(r['pid']) for r in records)
    result=json.loads((output/'result.json').read_text());assert result['status']=='complete' and len(result['phases'])==2
    assert not result['quality_approved'] and not result['release_approved']
    for receipt,e in zip(result['phases'],p['entries']):
        assert receipt['outputs_sha256']=={name:sha(Path(name)) for name in e['outputs']}
        assert receipt['log_sha256']==sha(output/(e['name']+'.log'))


@pytest.mark.parametrize('fault',['missing-output','nonzero','source-tamper','prior-output-tamper'])
def test_partial_failed_or_changed_replays_never_publish_success(fixture,fault):
    _,_,p=fixture
    if fault=='missing-output':body='pass\n'
    elif fault=='nonzero':body='raise SystemExit(23)\n'
    else:
        target=p['entries'][0]['script'] if fault=='source-tamper' else p['entries'][0]['outputs'][0]
        body=Path(p['entries'][1]['script']).read_text()+f'Path({target!r}).write_text("changed")\n'
    change_script(fixture,1,body);completed,output=execute(fixture)
    assert completed.returncode!=0 and not (output/'result.json').exists()
    pipeline=json.loads((output/'pipeline.json').read_text());assert pipeline['status']=='failed'
    assert not pipeline['quality_approved'] and not pipeline['release_approved']
    assert Path(p['entries'][0]['outputs'][0]).exists()


def test_existing_phase_output_is_preserved_without_launch(fixture):
    _,_,p=fixture;target=Path(p['entries'][0]['outputs'][0]);target.write_bytes(b'original review')
    completed,output=execute(fixture);assert completed.returncode!=0 and target.read_bytes()==b'original review'
    assert not list(output.glob('*.log'))


@pytest.mark.parametrize('fault',['changed-source','duplicate-output','unbound-cleanup','bad-module-name','duplicate-name','escaping-output'])
def test_protocol_rejects_unbound_or_incomplete_evidence_before_launch(fixture,fault):
    root,launcher,p=fixture
    if fault=='changed-source':Path(p['entries'][0]['script']).write_text('changed')
    elif fault=='duplicate-output':p['entries'][1]['outputs']=p['entries'][0]['outputs']
    elif fault=='unbound-cleanup':del p['sources_sha256'][str(launcher.with_name('process_monitor.py'))]
    elif fault=='bad-module-name':p['preload_modules']=[[]]
    elif fault=='duplicate-name':p['entries'][1]['name']=p['entries'][0]['name']
    else:p['entries'][0]['outputs']=[str(root.parent/'escape.json')]
    completed,output=execute(fixture);assert completed.returncode!=0 and not output.exists()


def test_timeout_stops_and_reaps_owned_child_and_descendant(fixture):
    root,_,p=fixture;p['phase_seconds']=1;identity=root/'owned.json'
    change_script(fixture,0,"import os,json,subprocess,sys,time\nfrom pathlib import Path\nchild=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\nPath("+repr(str(identity))+").write_text(json.dumps([os.getpid(),child.pid]))\ntime.sleep(60)\n")
    completed,output=execute(fixture);assert completed.returncode!=0 and not (output/'result.json').exists()
    assert all(not psutil.pid_exists(pid) or psutil.Process(pid).status()==psutil.STATUS_ZOMBIE for pid in json.loads(identity.read_text()))
    assert json.loads((output/'pipeline.json').read_text())['status']=='failed'
