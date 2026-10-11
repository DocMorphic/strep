"""Interrupted surface fits retain immutable, request-bound iteration evidence."""
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from native_surface_trace import SurfaceTrace
from native_scene_norms import NormRows
import native_surface_model as surface
from strep import read,save,sha256
from test_native_surface_model import report


def trace(tmp_path):
    request=tmp_path/'request.json';save(request,dict(iterations=16,quality_approved=False))
    return SurfaceTrace(tmp_path/'iterations',request)


def test_receipts_bind_request_and_do_not_share_mutable_history(tmp_path):
    record=dict(iteration=1,probes=[dict(accepted=False)])
    sink=trace(tmp_path);sink(record);record['probes'][0]['accepted']=True
    receipt=read(tmp_path/'iterations/01.json')
    assert receipt['request_sha256']==sha256(tmp_path/'request.json')
    assert not receipt['iteration']['probes'][0]['accepted']
    assert receipt['original_selected'] and not receipt['quality_approved'] and not receipt['release_approved']
    assert sink.files==[dict(path='01.json',sha256=sha256(tmp_path/'iterations/01.json'))]


@pytest.mark.parametrize('number',[0,2,True,1.0,17])
def test_skipped_or_invalid_iterations_reject_without_receipt(tmp_path,number):
    sink=trace(tmp_path)
    with pytest.raises(ValueError,match='sequential'):sink(dict(iteration=number))
    assert not sink.files and not list((tmp_path/'iterations').iterdir())


def test_changed_request_or_existing_evidence_reject(tmp_path):
    sink=trace(tmp_path);sink(dict(iteration=1));before=sha256(tmp_path/'iterations/01.json')
    with pytest.raises(ValueError,match='sequential'):sink(dict(iteration=1))
    assert sha256(tmp_path/'iterations/01.json')==before
    save(tmp_path/'request.json',dict(iterations=1))
    with pytest.raises(ValueError,match='request changed'):sink(dict(iteration=2))
    with pytest.raises(ValueError,match='Fresh'):SurfaceTrace(tmp_path/'iterations',tmp_path/'request.json')


def prepare_model(monkeypatch):
    problem=SimpleNamespace(initial=np.zeros(1),lower=-np.ones(1),upper=np.ones(1))
    system=NormRows([[0.,0.,0.]],[1.],[1.]);jac=sparse.csr_matrix((3,1))
    monkeypatch.setattr(surface,'model',lambda *a,**kw:(system,jac,None,{}))
    monkeypatch.setattr(surface,'direction',lambda *a,**kw:(np.array([.01]),dict(status='Solved')))
    def evaluate(value,label):
        # Every changed proposal fails native constraints, despite better geometry.
        return dict(native=np.array([-1. if label=='start' else .01]),
            geometry=report(depth=2. if label=='start' else 1.),scene=None,policy=None,digest=None,worlds=None)
    return problem,evaluate


def test_completed_iteration_survives_later_interruption(tmp_path,monkeypatch):
    problem,evaluate=prepare_model(monkeypatch);sink=trace(tmp_path)
    original=surface.model;calls=0
    def interrupt(*a,**kw):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('simulated worker interruption')
        return original(*a,**kw)
    monkeypatch.setattr(surface,'model',interrupt)
    with pytest.raises(RuntimeError,match='interruption'):
        surface.optimize(problem,evaluate,iterations=2,restoration_steps=0,on_iteration=sink)
    receipt=read(tmp_path/'iterations/01.json')['iteration']
    assert receipt['selected_fraction'] is None and len(receipt['probes'])==10
    assert all(not p['accepted'] for p in receipt['probes'])
    assert not (tmp_path/'iterations/02.json').exists()


def test_callback_mutation_cannot_rewrite_optimizer_history(monkeypatch):
    problem,evaluate=prepare_model(monkeypatch)
    def mutate(record):record['selected_fraction']=1.;record['probes'].clear()
    value,result=surface.optimize(problem,evaluate,iterations=1,restoration_steps=0,on_iteration=mutate)
    np.testing.assert_array_equal(value,[0.])
    assert result['history'][0]['selected_fraction'] is None and len(result['history'][0]['probes'])==10


def test_callback_error_is_not_silently_discarded(monkeypatch):
    problem,evaluate=prepare_model(monkeypatch)
    def fail(record):raise OSError('receipt unavailable')
    with pytest.raises(OSError,match='receipt unavailable'):
        surface.optimize(problem,evaluate,iterations=1,restoration_steps=0,on_iteration=fail)


def test_unavailable_restoration_step_is_retained(tmp_path,monkeypatch):
    problem,evaluate=prepare_model(monkeypatch);calls=0;sink=trace(tmp_path)
    def step(*a,**kw):
        nonlocal calls
        calls+=1
        return (np.array([.01]),dict(status='Solved')) if calls==1 else (None,dict(status='Infeasible'))
    monkeypatch.setattr(surface,'direction',step)
    _,result=surface.optimize(problem,evaluate,iterations=1,restoration_steps=1,on_iteration=sink)
    attempts=result['history'][0]['restoration_attempts'];assert len(attempts)==1
    assert not attempts[0]['available'] and attempts[0]['conic_step']['status']=='Infeasible'
    assert attempts[0]['margin']['failed_protected_rows']==1
    assert read(tmp_path/'iterations/01.json')['iteration']['restoration_attempts']==attempts


def test_noncallable_callback_rejects_before_model_evaluation():
    with pytest.raises(ValueError,match='callback'):
        surface.optimize(None,lambda *a:pytest.fail('must not evaluate'),on_iteration=False)


def test_actual_fit_binds_completed_iteration_to_request_and_result(tmp_path):
    from native_scene_fit import run
    from test_native_partner_surface_rows import scene_fixture
    scene,policy,digest=scene_fixture(tmp_path);contacts=tmp_path/'contacts.json';spec=read(contacts)
    row=spec['contacts'][0];row.update(mode='touch',interval_s=[1.,1.],limits=dict(position_m=.03))
    row['target']=dict(space='world',points_m=[scene.actor_points('A',np.array([0]),[1.])[0,0].tolist()])
    save(contacts,spec);digest=sha256(contacts);policy['contacts_sha256']=digest
    policy_path=tmp_path/'policy.json';save(policy_path,policy)
    permissions=tmp_path/'permissions.json'
    save(permissions,dict(schema='strep-native-scene-edit-v1',contacts_sha256=digest,actors=dict(A=dict(
        window_s=[0.,2.],protected_s=[],knots_s=[0.,1.,2.],tracks=[dict(node=0,path='translation',maximum_change=.02)],maximum_joint_displacement_m=.02))))
    output=tmp_path/'fit'
    result=run(contacts,permissions,output,proposal_model='surface-vector',geometry_policy=policy_path,iterations=1,restoration_steps=1)
    assert len(result['surface_iteration_receipts'])==len(result['optimization']['history'])==1
    item=result['surface_iteration_receipts'][0];receipt=read(output/item['path'])
    assert sha256(output/item['path'])==item['sha256']
    assert receipt['request_sha256']==sha256(output/'request.json')
    assert receipt['iteration']==result['optimization']['history'][0]
    assert result['original_selected'] and not result['release_approved']
