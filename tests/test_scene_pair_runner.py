"""Orchestration regression for a rejected proposal, without a costly mesh scan."""
import sys
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import study_scene_pair_fit as worker
from strep import save,read,sha256
from gltf_tools import write_glb
from test_timed_rotation_edit import fixture


def test_solver_status_is_reported_and_no_proposal_retains_only_inputs(tmp_path,monkeypatch):
    prepared=tmp_path/'prepared';prepared.mkdir();save(prepared/'request.json',{'test_fixture':True});save(prepared/'state.json',{'status':'prepared'})
    save(prepared/'scene.json',{'test_fixture':True});doc,binary=fixture(); actors=[]
    for name in ['one','two']:
        source=prepared/(name+'.glb');write_glb(source,doc,binary)
        actors.append(dict(name=name,source=source,rig=SimpleNamespace(document=doc,binary=binary),model=SimpleNamespace(world=lambda value:np.zeros(1))))
    monkeypatch.setattr(worker,'load_actors',lambda folder:({'scene_snapshot':{'path':'scene.json'}},actors))
    rows=[dict(directions=[dict(records=[dict(gap_m=-.01)]) for _ in range(2)])]
    def samples(actors,output):save(output/'sample-000.json',rows[0]);return rows
    monkeypatch.setattr(worker,'source_samples',samples)
    linear=dict(gaps=np.full(2,-.01),gap_jacobian=np.zeros((2,6)),depth_caps=np.full(2,.01),vectors=np.empty((0,3)),
        jacobians=np.empty((0,3,6)),radii=np.empty(0),kinds=np.array([],dtype='U12'),surface_vectors=np.zeros((2,3)),surface_jacobians=np.zeros((2,3,6)))
    problem=SimpleNamespace(size=6,linearize=lambda value:linear,split=lambda value:np.split(value,2),surface_rows=lambda worlds:{'gaps':linear['gaps']})
    monkeypatch.setattr(worker,'ScenePairProblem',lambda actors,samples:problem)
    monkeypatch.setattr(worker,'solve',lambda **kwargs:(None,dict(status='PrimalInfeasible',proposal_hard_checks=False,quality_approved=False)))
    output=tmp_path/'out';worker.run(prepared,output)
    assert read(output/'solver.json')['solver']['status']=='PrimalInfeasible'
    result=read(output/'result.json');assert result['status']=='complete' and result['selected'] is None and result['trials']==0
    cases=read(output/'manifest.json')['cases'];assert {c['id'] for c in cases}=={'input-one','input-two'}
    assert all(sha256(output/c['path'])==c['sha256'] for c in cases)


@pytest.mark.skipif(os.name!='nt',reason='Windows local worker lock')
def test_standalone_cli_obeys_the_same_worker_lock_before_loading_inputs(tmp_path):
    from action_worker_lock import worker_lock
    destination=tmp_path/'must-not-be-created'
    with worker_lock():
        result=subprocess.run([sys.executable,str(worker.ROOT/'scripts/study_scene_pair_fit.py'),str(tmp_path/'missing-input'),str(destination)],
            cwd=worker.ROOT,capture_output=True,text=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode!=0 and 'Another local action job is running' in result.stderr
    assert not destination.exists()
