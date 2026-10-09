"""Runner lifecycle without downloaded native assets or inference."""
import sys
import shutil
from pathlib import Path
from contextlib import nullcontext
import pytest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import guarded_pose_restoration as module


@pytest.mark.parametrize('options',[dict(frame=True),dict(iterations=0),dict(trust=.31),dict(seconds=float('nan')),
    dict(proposal='guess'),dict(solve_iterations=True),dict(solve_iterations=0),dict(row_chunk=True),dict(row_chunk=33),dict(point_policy='guess'),
    dict(point_proposal='guess'),dict(point_headroom=-1e-5),dict(point_headroom=float('nan')),dict(point_headroom=True),
    dict(tangent_guard=1),dict(tangent_guard=True),dict(resume=False),dict(resume=''),dict(body_proposal='guess'),
    dict(proposal_start='guess'),dict(proposal_start=True),dict(proposal_start='linear-feasible')])
def test_invalid_options_never_acquire_or_run_worker(tmp_path,monkeypatch,options):
    def forbidden(*args,**kwargs):raise AssertionError('Invalid request reached worker')
    monkeypatch.setattr(module,'worker_lock',forbidden)
    args=dict(frame=72);args.update(options)
    with pytest.raises(ValueError):module.run(tmp_path,tmp_path/'new',**args)
    assert not (tmp_path/'new').exists()


def test_failure_receipt_preserves_existing_output(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'worker_lock',nullcontext)
    monkeypatch.setattr(module,'threadpool_limits',lambda **kwargs:nullcontext())
    def fail(study,output,*args):output.mkdir();raise ValueError('Bound input rejected')
    monkeypatch.setattr(module,'_run',fail);output=tmp_path/'study'
    with pytest.raises(ValueError):module.run(tmp_path,output,72)
    receipt=(output/'pipeline.json').read_bytes()
    assert module.read(output/'pipeline.json')['status']=='failed'
    with pytest.raises(FileExistsError):module.run(tmp_path,output,72)
    assert (output/'pipeline.json').read_bytes()==receipt


def test_worker_lock_covers_the_entire_source_and_result_lifecycle(tmp_path,monkeypatch):
    from contextlib import contextmanager
    active=[]
    @contextmanager
    def lock():
        active.append(True)
        try:yield
        finally:active.pop()
    monkeypatch.setattr(module,'worker_lock',lock)
    monkeypatch.setattr(module,'threadpool_limits',lambda **kwargs:nullcontext())
    def run(*args):assert active;return 'preserved-result'
    monkeypatch.setattr(module,'_run',run)
    assert module.run(tmp_path,tmp_path/'out',72)=='preserved-result'
    assert not active


def resume_fixture(tmp_path,monkeypatch):
    """A real archived retained step followed by an unaccepted inner query."""
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'METHODS',['method.py'])
    definitions=tmp_path/'definitions.py';definitions.write_text('native metadata')
    monkeypatch.setattr(module,'DEFINITIONS',definitions)
    study=tmp_path/'source';study.mkdir();original=study/'source.npz';original.write_bytes(b'original references')
    bindings={str(original):module.sha256(original),str(definitions):module.sha256(definitions)}
    output=tmp_path/'repair';archive=output/'implementation';archive.mkdir(parents=True)
    (archive/'method.py').write_text('archived implementation');(archive/'kimodo-skeleton-definitions.py').write_bytes(definitions.read_bytes())
    labels=['point:left','normal:left','floor','rotation:x'];mask=[False,True,False,False];limits={'position_m':.22}
    class Problem:
        seed=np.zeros(4);dim=4;limits=np.ones(1);config={'max_root_lift_m':1.}
        t=staticmethod(module.torch.as_tensor)
        def geometry_slack(self,x):return module.torch.stack([x[0]-.4,x[0]-1,x[0]*0+1])
        def independent(self,x):return {'pose_checks_passed':False,'point':float(x[0])},{'posed_joints':np.asarray(x)[None]}
    problem=Problem();seed=np.zeros(4);accepted=np.array([.5,0,0,0]);query=np.array([.7,0,0,0])
    def slacks(x):return np.r_[problem.geometry_slack(problem.t(x)).numpy(),module.norm_slack_and_jacobian(x,problem.limits)[0]]
    before=slacks(seed);after=slacks(accepted);observations=[]
    for label,x,retained in [('seed',seed,False),('kept',accepted,True),('query',query,False),('final',accepted,True)]:
        folder=output/'trials'/label;folder.mkdir(parents=True);audit,motion=problem.independent(x)
        np.savez(folder/'pose.npz',**motion)
        module.save(folder/'audit.json',dict(label=label,retained=retained,candidate=audit,solver_slacks=slacks(x).tolist(),
            parameters=x.tolist(),pose_sha256=module.sha256(folder/'pose.npz'),quality_approved=False,release_approved=False))
        observations.append(dict(label=label,retained=retained,audit_sha256=module.sha256(folder/'audit.json')))
    protocol=dict(source_study='source',frame=98,grouping='native-joint',inequality_labels=labels,original_limits=limits,
        inputs_sha256=bindings,methods_sha256={'method.py':module.sha256(archive/'method.py')},native_metadata_sha256=module.sha256(definitions),
        failure_policy='merit',proposal_tangent_guard=True,tradeoff_mask=mask,quality_approved=False,release_approved=False)
    ids=np.array([0,2,3]);jac=np.zeros((4,4));jac[:2,0]=1
    fit=dict(initial_slacks=before.tolist(),final_slacks=after.tolist(),tradeoff_mask=mask,failure_policy='merit',proposal_tangent_guard=True,
        trials=[dict(label='kept',iteration=1,controls=accepted.tolist(),accepted=True)],
        proposal_queries=[dict(label='query',retained=False)],
        proposal_linearizations=[dict(iteration=1,protected_rows=ids.tolist(),slacks=before.tolist(),controls=seed.tolist(),jacobian=jac.tolist(),
            preservation_caps=np.minimum(before[ids],0).tolist())])
    module.save(output/'protocol.json',protocol);module.save(output/'row-diagnostics.json',module.row_diagnostics(labels,before,after,mask))
    audit,motion=problem.independent(accepted);np.savez(output/'pose.npz',**motion)
    result=dict(status='interrupted_resource_guard',protocol_sha256=module.sha256(output/'protocol.json'),pose_sha256=module.sha256(output/'pose.npz'),
        row_diagnostics_sha256=module.sha256(output/'row-diagnostics.json'),observations=observations,fit=fit,parameters=accepted.tolist(),candidate=audit,
        quality_approved=False,release_approved=False)
    module.save(output/'result.json',result);module.save(output/'pipeline.json',dict(status=result['status'],quality_approved=False,release_approved=False))
    return (output,study,98,bindings,limits,labels,problem)


def test_resume_retains_checked_correction_instead_of_last_inner_query(tmp_path,monkeypatch):
    args=resume_fixture(tmp_path,monkeypatch)
    parameters,motion,receipt,bindings=module._resume_seed(*args)
    np.testing.assert_array_equal(parameters,[.5,0,0,0]);np.testing.assert_array_equal(motion['posed_joints'],[[.5,0,0,0]])
    assert receipt['last_retained_label']=='kept' and receipt['original_references_preserved']
    assert str(args[0]/'trials/query/audit.json') in bindings


@pytest.mark.parametrize('damage',['frame','budget','original','method','pose','promoted-query','last-query','slacks','tangent','ancestor',
    'start-policy','linear-start-promotion'])
def test_resume_rejects_changed_provenance_or_unretained_selection(tmp_path,monkeypatch,damage):
    args=resume_fixture(tmp_path,monkeypatch);output=args[0]
    protocol=module.read(output/'protocol.json');result=module.read(output/'result.json')
    if damage=='frame':protocol['frame']=99
    if damage=='budget':protocol['original_limits']['position_m']=.23
    if damage=='original':(args[1]/'source.npz').write_bytes(b'changed references')
    if damage=='method':(output/'implementation/method.py').write_text('changed')
    if damage=='pose':(output/'pose.npz').write_bytes(b'changed')
    if damage=='last-query':result['parameters']=[.7,0,0,0]
    if damage=='slacks':result['fit']['final_slacks'][0]=.2
    if damage=='tangent':result['fit']['proposal_linearizations'][0]['jacobian'][0][0]=-1
    if damage=='ancestor':protocol['resume']={'directory':'repair','result_sha256':module.sha256(output/'result.json')}
    if damage=='promoted-query':result['fit']['proposal_queries'][0]['retained']=True
    if damage=='start-policy':result['fit']['proposal_start']='linear-feasible'
    if damage=='linear-start-promotion':result['fit']['proposal_starts']=[dict(retained=True)]
    module.save(output/'protocol.json',protocol);result['protocol_sha256']=module.sha256(output/'protocol.json');module.save(output/'result.json',result)
    with pytest.raises((ValueError,AssertionError)):module._resume_seed(*args)


def test_resume_output_cannot_overwrite_or_extend_the_original_study(tmp_path,monkeypatch):
    def forbidden():raise AssertionError('Nested resume acquired worker')
    monkeypatch.setattr(module,'worker_lock',forbidden)
    with pytest.raises(ValueError):module.run(tmp_path,tmp_path/'old'/'new',98,resume=tmp_path/'old')


def test_chained_resume_keeps_original_budgets_and_replays_its_ancestor(tmp_path,monkeypatch):
    args=resume_fixture(tmp_path,monkeypatch);parent=args[0];problem=args[-1]
    _,_,_,bindings=module._resume_seed(*args)
    output=tmp_path/'second';shutil.copytree(parent,output)
    protocol=module.read(output/'protocol.json');protocol['inputs_sha256'].update(bindings)
    protocol['resume']=dict(directory='repair',result_sha256=module.sha256(parent/'result.json'))
    result=module.read(output/'result.json');seed=np.array([.5,0,0,0]);accepted=np.array([.6,0,0,0])
    def slacks(x):return np.r_[problem.geometry_slack(problem.t(x)).numpy(),module.norm_slack_and_jacobian(x,problem.limits)[0]]
    before=slacks(seed);after=slacks(accepted)
    for observation in result['observations']:
        label=observation['label'];x=seed if label=='seed' else accepted if label in ['kept','final'] else np.array([.7,0,0,0])
        folder=output/'trials'/label;audit=module.read(folder/'audit.json');physical,motion=problem.independent(x)
        np.savez(folder/'pose.npz',**motion)
        audit.update(candidate=physical,parameters=x.tolist(),solver_slacks=slacks(x).tolist(),pose_sha256=module.sha256(folder/'pose.npz'))
        module.save(folder/'audit.json',audit);observation['audit_sha256']=module.sha256(folder/'audit.json')
    result['fit']['initial_slacks']=before.tolist();result['fit']['final_slacks']=after.tolist()
    result['fit']['trials'][0]['controls']=accepted.tolist()
    linear=result['fit']['proposal_linearizations'][0];linear.update(controls=seed.tolist(),slacks=before.tolist(),preservation_caps=[0,0,0])
    linear['jacobian'][3][0]=-1
    physical,motion=problem.independent(accepted);result.update(parameters=accepted.tolist(),candidate=physical)
    np.savez(output/'pose.npz',**motion);module.save(output/'protocol.json',protocol)
    module.save(output/'row-diagnostics.json',module.row_diagnostics(args[-2],before,after,protocol['tradeoff_mask']))
    result.update(protocol_sha256=module.sha256(output/'protocol.json'),pose_sha256=module.sha256(output/'pose.npz'),
        row_diagnostics_sha256=module.sha256(output/'row-diagnostics.json'))
    module.save(output/'result.json',result)
    resumed,_,_,checked=module._resume_seed(output,*args[1:])
    np.testing.assert_array_equal(resumed,accepted)
    assert checked[str(parent/'result.json')]==module.sha256(parent/'result.json')
    (parent/'implementation/method.py').write_text('ancestor changed')
    with pytest.raises(ValueError):module._resume_seed(output,*args[1:])
