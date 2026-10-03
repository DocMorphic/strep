"""Byte replay, original caps, chain provenance and unsafe checkpoint rejection."""
from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_native_scene_fit import prepare
from native_scene_fit import run
from native_support_feasibility import merit
from strep import read,save,sha256


def checkpoint(tmp_path,monkeypatch,*,unsafe=False):
    import native_scene_fit as fit
    source,spec,contacts,p,permissions,scene,edits=prepare(tmp_path)
    x=edits.initial.copy();peak=.002 if unsafe else 10*float(np.spacing(np.float32(1.2)))
    x.reshape(-1,3)[:,1]=np.array([.5,1,.5])*peak/.02
    def authored(problem,evaluate,*args):
        evaluate(problem.initial,'start')
        return x,dict(history=[dict(iteration=1)],final_merit=list(merit(problem.model(x))))
    monkeypatch.setattr(fit,'optimize',authored);job=tmp_path/'prior';r=run(contacts,permissions,job,iterations=1)
    return source,contacts,permissions,job,r,x


def test_resume_and_chain_replay_controls_without_recapping(tmp_path,monkeypatch):
    import native_scene_fit as fit
    source,c,p,prior,r,x=checkpoint(tmp_path,monkeypatch);original=sha256(source)
    def keep(problem,evaluate,*args):
        np.testing.assert_array_equal(problem.initial,x);evaluate(problem.initial,'start')
        return problem.initial.copy(),dict(history=[],final_merit=list(merit(problem.model(problem.initial))))
    monkeypatch.setattr(fit,'optimize',keep)
    second=tmp_path/'second';a=run(c,p,second,resume_from=prior)
    third=tmp_path/'third';b=run(c,p,third,resume_from=second)
    assert a['completed_primary_iterations']==b['completed_primary_iterations']==1
    for job,result in [(second,a),(third,b)]:
        assert result['original_selected'] and not result['release_approved']
        assert sha256(job/'probes/start/A.glb')==sha256(prior/'probes/final/A.glb')
        assert sha256(job/'input/actor-0.glb')==original
        with np.load(job/'source-rate-caps.npz') as current,np.load(prior/'source-rate-caps.npz') as old:
            for key in old.files:np.testing.assert_array_equal(current[key],old[key])
        for relative,h in result['resume']['files_sha256'].items():assert sha256(job/'resume'/relative)==h
    assert sha256(source)==original


@pytest.mark.parametrize('fault',['unfinished','export','receipt','snapshot','method','path','changed-contact','changed-permission'])
def test_corrupt_or_rebound_checkpoints_reject_before_output(tmp_path,monkeypatch,fault):
    source,c,p,prior,r,x=checkpoint(tmp_path,monkeypatch)
    if fault=='unfinished':save(prior/'pipeline.json',dict(status='processing'))
    if fault=='export':(prior/'probes/final/A.glb').write_bytes(b'corrupt')
    if fault=='receipt':
        v=read(prior/'probes/final/probe.json');v['controls'][1]+=.001;save(prior/'probes/final/probe.json',v)
    if fault=='snapshot':(prior/'input/actor-0.glb').write_bytes(b'corrupt')
    if fault=='method':
        path=prior/'implementation/native_scene_edit.py';path.write_bytes(path.read_bytes()+b'\n')
    if fault=='path':
        v=read(prior/'request.json');v['actor_snapshots']['A']['path']='../outside.glb';save(prior/'request.json',v)
    if fault=='changed-contact':
        v=read(c);v['contacts'][0]['limits']['position_m']*=2;save(c,v)
        v=read(p);v['contacts_sha256']=sha256(c);save(p,v)
    if fault=='changed-permission':
        v=read(p);v['actors']['A']['maximum_joint_displacement_m']*=.5;save(p,v)
    output=tmp_path/'resumed'
    with pytest.raises(ValueError):run(c,p,output,resume_from=prior)
    assert not output.exists()


@pytest.mark.parametrize('fault',['caps','tolerance','frame','unsafe','archive-mutation'])
def test_resume_rechecks_current_caps_and_initial_source_safety(tmp_path,monkeypatch,fault):
    import native_scene_fit as fit
    source,c,p,prior,r,x=checkpoint(tmp_path,monkeypatch,unsafe=fault=='unsafe')
    if fault=='caps':
        values=dict(np.load(prior/'source-rate-caps.npz'));values['A_metric_0']*=2
        np.savez(prior/'source-rate-caps.npz',**values);v=read(prior/'result.json');v['source_rate_caps_sha256']=sha256(prior/'source-rate-caps.npz');save(prior/'result.json',v)
    if fault=='tolerance':
        v=read(prior/'result.json');v['source_rate_tolerance']=.1;save(prior/'result.json',v)
    if fault=='frame':
        v=read(prior/'request.json');v['frame_contract_sha256']='0'*64;save(prior/'request.json',v)
    def forbidden(problem,evaluate,*args):
        evaluate(problem.initial,'start')
        if fault=='archive-mutation':
            path=tmp_path/'resumed/resume/result.json';path.write_bytes(path.read_bytes()+b' ')
            return problem.initial.copy(),dict(history=[],final_merit=list(merit(problem.model(problem.initial))))
        pytest.fail('Optimizer ran before an invalid checkpoint was rejected')
    monkeypatch.setattr(fit,'optimize',forbidden);output=tmp_path/'resumed'
    with pytest.raises(ValueError):run(c,p,output,resume_from=prior)
    assert read(output/'pipeline.json')['status']=='failed'
    assert sha256(output/'input/actor-0.glb')==sha256(source)
