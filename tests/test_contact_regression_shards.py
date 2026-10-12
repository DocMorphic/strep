"""Explicit focused inventory selection and complete portable shard dispatch."""
import json,sys,subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_source_checks as runner


def test_real_focused_shards_partition_without_dropping_or_repeating_modules():
    focused=runner.inventory(runner.ROOT/'.github/contact-rig-source-tests.json')
    complete=runner.inventory();assert set(focused['python_tests'])<=set(complete['python_tests'])
    shards=[runner.partition(focused['python_tests'],i,2) for i in range(2)]
    assert not set(shards[0])&set(shards[1]) and set(shards[0]+shards[1])==set(focused['python_tests'])
    assert all(shards) and abs(len(shards[0])-len(shards[1]))<=1


def test_focused_list_does_not_execute_tests(capsys,monkeypatch):
    monkeypatch.setattr(runner.subprocess,'run',lambda *a,**k:pytest.fail('List must not execute tests'))
    manifest=runner.ROOT/'.github/contact-rig-source-tests.json';assert runner.run('python',1,2,list_only=True,manifest=manifest)==0
    data=json.loads(capsys.readouterr().out);assert data['tests']==runner.inventory(manifest)['python_tests'][1::2]
    assert data['shard_index']==1 and data['shard_count']==2


def test_default_still_selects_whole_inventory(capsys):
    assert runner.run('python',0,4,list_only=True)==0
    data=json.loads(capsys.readouterr().out);assert data['tests']==runner.inventory()['python_tests'][0::4]


def test_execution_uses_only_selected_shard_and_propagates_failure(monkeypatch):
    manifest=runner.ROOT/'.github/contact-rig-source-tests.json';calls=[]
    def execute(command,**kwargs):calls.append((command,kwargs));return SimpleNamespace(returncode=7)
    monkeypatch.setattr(runner.subprocess,'run',execute)
    assert runner.run('python',0,2,manifest=manifest)==7
    assert calls==[([sys.executable,'-m','pytest','-q',*runner.inventory(manifest)['python_tests'][0::2]],dict(cwd=runner.ROOT))]


@pytest.mark.parametrize('fault',['duplicate','missing','escape','schema'])
def test_custom_manifest_rejects_invalid_population(tmp_path,fault):
    focused=runner.inventory(runner.ROOT/'.github/contact-rig-source-tests.json')
    if fault=='duplicate':focused['python_tests'].append(focused['python_tests'][0])
    elif fault=='missing':focused['python_tests'][0]='tests/test_missing_focused_runner_case.py'
    elif fault=='escape':focused['python_tests'][0]='../tests/test_elsewhere.py'
    else:focused['schema']='implicit'
    path=tmp_path/'manifest.json';path.write_text(json.dumps(focused),encoding='utf-8')
    with pytest.raises(ValueError):runner.inventory(path)


def test_cli_accepts_explicit_manifest_and_lists_portably():
    output=subprocess.check_output([sys.executable,str(runner.ROOT/'scripts/run_source_checks.py'),'--manifest',str(runner.ROOT/'.github/contact-rig-source-tests.json'),'--shard-index','1','--shard-count','2','--list'],text=True,cwd=runner.ROOT)
    assert json.loads(output)['tests']==runner.inventory(runner.ROOT/'.github/contact-rig-source-tests.json')['python_tests'][1::2]
