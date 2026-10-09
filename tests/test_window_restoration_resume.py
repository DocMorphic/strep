"""Bound retention history and immutable ancestors without native assets."""
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import window_restoration_resume as module
from pose_proposal_archive import ProposalArchive
from protected_inequality_step import score
from pose_restoration_policy import row_diagnostics


class Window:
    frames=[1,2];pose_dim=4;dim=8;scale=np.ones(8);seed=np.zeros(8)
    labels=['point:left:frame-1','point:left:frame-2'];problems=[]
    def geometry_slack(self,x):return torch.stack([x[0]-.4,x[4]-.4])
    def independent(self,x):
        motion=dict(posed_joints=np.asarray(x).reshape(2,4)[:,:3,None].transpose(0,2,1).copy())
        return dict(window_checks_passed=False,positions=[float(x[0]),float(x[4])]),motion


def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);window=Window();study=tmp_path/'source';study.mkdir()
    source=study/'source.npz';source.write_bytes(b'original references')
    definitions=tmp_path/'definitions.py';definitions.write_text('original native metadata')
    bindings={str(source):module.sha256(source),str(definitions):module.sha256(definitions)}
    directory=tmp_path/'window';archive=directory/'implementation';archive.mkdir(parents=True)
    (archive/'method.py').write_text('original method');(archive/'kimodo-skeleton-definitions.py').write_bytes(definitions.read_bytes())
    limits=[dict(frame=f,position_m=.22) for f in window.frames]
    protocol=dict(source_study='source',frames=window.frames,fps=30,pose_dim=4,inequality_labels=window.labels,
        original_limits=limits,inputs_sha256=bindings,methods_sha256={'method.py':module.sha256(archive/'method.py')},
        native_metadata_sha256=module.sha256(definitions),failure_policy='merit',proposal='nonlinear',proposal_start='geometry-descent',
        proposal_priority='worst-first',proposal_tangent_guard=True,archive_proposals=True,tradeoff_mask=[False,False],
        point_policy='preserve',normal_policy='preserve',object_policy='preserve',proposal_feasible_mask=[True,True],
        proposal_headroom_normalized=[1e-5,1e-5],trust_normalized=.1,temporal_edges=[],resumes=[],quality_approved=False,release_approved=False)
    module_data=lambda path,value:path.write_text(__import__('json').dumps(value,indent=2)+'\n')
    module_data(directory/'protocol.json',protocol)
    seed=window.seed.copy();accepted=seed.copy();accepted[[0,4]]=.05;query=seed.copy();query[[0,4]]=.07
    observations=[]
    for label,parameters,retained in [('seed',seed,False),('kept',accepted,True),('query',query,False),('final',accepted,True)]:
        trial=directory/'trials'/label;trial.mkdir(parents=True)
        actual,motion=window.independent(parameters);np.savez_compressed(trial/'window.npz',**motion)
        slacks=window.geometry_slack(torch.as_tensor(parameters)).numpy()
        audit=dict(label=label,parameters=parameters.tolist(),solver_slacks=slacks.tolist(),retained=retained,candidate=actual,
            motion_sha256=module.sha256(trial/'window.npz'),quality_approved=False,release_approved=False)
        module_data(trial/'audit.json',audit)
        observations.append(dict(label=label,retained=retained,audit_sha256=module.sha256(trial/'audit.json')))
    before=window.geometry_slack(torch.as_tensor(seed)).numpy();after=window.geometry_slack(torch.as_tensor(accepted)).numpy()
    jac=np.zeros((2,8));jac[0,0]=jac[1,4]=1
    store=ProposalArchive(directory)
    window.archive=store
    linear=store('linearization',dict(iteration=1,controls=seed.tolist(),slacks=before.tolist(),jacobian=jac.tolist(),
        protected_rows=[0,1],preservation_caps=before.tolist(),tangent_proposal_caps=(before+1e-6).tolist()))
    report={k:protocol[k] for k in ['tradeoff_mask','failure_policy','proposal','proposal_start','proposal_priority',
        'proposal_tangent_guard','proposal_feasible_mask','proposal_headroom_normalized']}
    report.update(initial_slacks=before.tolist(),final_slacks=after.tolist(),proposal_starts=[],proposal_linearizations=[linear],
        trials=[dict(label='kept',iteration=1,controls=accepted.tolist(),score=list(score(after)),accepted=True,retention_guard_passed=True,tangent_guard_passed=True)],
        proposal_queries=[dict(label='query',controls=query.tolist(),retained=False,score=list(score(window.geometry_slack(torch.as_tensor(query)).numpy())))])
    actual,motion=window.independent(accepted);np.savez_compressed(directory/'window.npz',**motion)
    module_data(directory/'row-diagnostics.json',row_diagnostics(window.labels,before,after,[False,False]))
    result=dict(status='complete',fit=report,observations=observations,parameters=accepted.tolist(),candidate=actual,
        protocol_sha256=module.sha256(directory/'protocol.json'),motion_sha256=module.sha256(directory/'window.npz'),
        row_diagnostics_sha256=module.sha256(directory/'row-diagnostics.json'),quality_approved=False,release_approved=False)
    module_data(directory/'result.json',result);module_data(directory/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
    def forbidden(*a,**k):pytest.fail('Unexpected individual-pose predecessor')
    return (directory,study,window,bindings,limits,['method.py','window_restoration_resume.py'],definitions,forbidden),module_data


def test_selects_only_replayed_terminal_window_and_binds_full_archives(tmp_path,monkeypatch):
    args,_=fixture(tmp_path,monkeypatch);parameters,motion,receipt,bindings=module.resume_window(*args)
    assert parameters[0]==parameters[4]==.05 and motion['posed_joints'].shape==(2,1,3)
    assert receipt['replayed_observations']==4 and receipt['original_references_preserved']
    assert str(args[0]/'proposals/linearization-1.npz') in bindings
    assert str(args[0]/'trials/query/window.npz') in bindings


@pytest.mark.parametrize('damage',['clock','frames','limits','inputs','method','motion','metadata','mask','policy','margin','edges',
    'query-promotion','last-query','slacks','tangent','linear-promotion','archive','ancestor','precision','physical','trust','unbound-seed','correction-policy','correction-promotion'])
def test_changed_history_or_unretained_query_is_rejected(tmp_path,monkeypatch,damage):
    args,save=fixture(tmp_path,monkeypatch);directory=args[0];protocol=module.read(directory/'protocol.json');result=module.read(directory/'result.json')
    if damage=='clock':protocol['fps']=60
    if damage=='frames':protocol['frames']=[0,1]
    if damage=='limits':protocol['original_limits'][0]['position_m']=.23
    if damage=='inputs':(args[1]/'source.npz').write_bytes(b'changed references')
    if damage=='method':(directory/'implementation/method.py').write_text('changed')
    if damage=='metadata':(directory/'implementation/kimodo-skeleton-definitions.py').write_text('changed')
    if damage=='motion':(directory/'window.npz').write_bytes(b'changed')
    if damage=='mask':result['fit']['tradeoff_mask']=[True,False]
    if damage=='policy':protocol['normal_policy']='tradeoff'
    if damage=='correction-policy':protocol['proposal_trial_correction']=True
    if damage=='correction-promotion':
        protocol['proposal_trial_correction']=True;result['fit']['proposal_trial_correction']=True
        result['fit']['proposal_corrections']=[args[2].archive('correction',dict(iteration=1,attempt=1,retained=True,controls=[0.]*8))]
    if damage=='margin':protocol['proposal_headroom_normalized']=[0,0]
    if damage=='edges':protocol['temporal_edges']=[dict(frame=1,neighbor=2,neighbor_edited=False)]
    if damage=='query-promotion':result['fit']['proposal_queries'][0]['retained']=True
    if damage=='last-query':result['parameters'][0]=.07
    if damage=='slacks':result['fit']['final_slacks'][0]=0
    if damage=='archive':(directory/'proposals/linearization-1.npz').write_bytes(b'changed')
    if damage=='ancestor':protocol['window_resume']=dict(directory='window',result_sha256=module.sha256(directory/'result.json'))
    if damage=='trust':protocol['trust_normalized']=.01
    if damage=='unbound-seed':args[2].seed=np.ones(8)*.01
    if damage in ['precision','physical']:
        path=directory/'trials/query';audit=module.read(path/'audit.json')
        if damage=='physical':audit['candidate']['positions'][0]=.9
        else:
            data=dict(np.load(path/'window.npz'));np.savez_compressed(path/'window.npz',**{k:v.astype(np.float32) for k,v in data.items()})
            audit['motion_sha256']=module.sha256(path/'window.npz')
        save(path/'audit.json',audit);result['observations'][2]['audit_sha256']=module.sha256(path/'audit.json')
    if damage=='linear-promotion':result['fit']['proposal_starts']=[args[2].archive('start',dict(iteration=1,retained=True,priority='worst-first',controls=[0.]*8))]
    if damage=='tangent':
        reference=result['fit']['proposal_linearizations'][0];linear=module.load_record(directory,reference)[0];linear['jacobian'][0][0]=-1
        linear['iteration']=2;result['fit']['trials'][0]['iteration']=2
        result['fit']['proposal_linearizations']=[args[2].archive('linearization',linear)]
    save(directory/'protocol.json',protocol);result['protocol_sha256']=module.sha256(directory/'protocol.json');save(directory/'result.json',result)
    with pytest.raises((ValueError,AssertionError)):module.resume_window(*args)


def test_recursive_window_origin_is_bound_without_rebasing_controls(tmp_path,monkeypatch):
    args,save=fixture(tmp_path,monkeypatch);directory=args[0]
    import shutil
    second=tmp_path/'continued';shutil.copytree(directory,second)
    protocol=module.read(second/'protocol.json');protocol['window_resume']=dict(directory='window',result_sha256=module.sha256(directory/'result.json'))
    # A copied seed is still the original seed, so it cannot pretend to continue the retained ancestor.
    save(second/'protocol.json',protocol);result=module.read(second/'result.json');result['protocol_sha256']=module.sha256(second/'protocol.json');save(second/'result.json',result)
    with pytest.raises(AssertionError):module.resume_window(second,*args[1:])


@pytest.mark.parametrize('damage',[None,'order','budget','promotion','caps','policy'])
def test_margin_history_is_bound_and_only_search_margins_can_change(tmp_path,monkeypatch,damage):
    from protected_inequality_step import _geometry_margin_start
    args,save=fixture(tmp_path,monkeypatch);directory=args[0];window=args[2]
    protocol=module.read(directory/'protocol.json');result=module.read(directory/'result.json')
    protocol['proposal_margin_fallback']=True;result['fit']['proposal_margin_fallback']=True
    linear=module.load_record(directory,result['fit']['proposal_linearizations'][0])[0]
    linear.update(iteration=2,controls=[.05,0,0,0,.05,0,0,0],slacks=[-.35,-.35],preservation_caps=[-.35,-.35],tangent_proposal_caps=[-.35+1e-6]*2)
    result['fit']['proposal_linearizations'].append(window.archive('linearization',linear))
    derivatives=np.zeros((2,3,8));derivatives[0,0,0]=derivatives[1,0,4]=-1
    vectors=dict(offsets=np.array([[1.35,0,0],[1.35,0,0]]),jacobian=derivatives,
        limits=np.ones(2),scales=np.ones(2),rows=np.array([0,1]),distance=np.ones(2,dtype=bool))
    _,start=_geometry_margin_start(np.array([-.35,-.35]),np.array(linear['jacobian']),np.zeros(2),np.ones(2)*1e-5,
        np.ones(8)*-.1,np.ones(8)*.1,20.,vectors,'worst-first')
    start.update(iteration=2,controls=linear['controls'],retained=False)
    if damage=='order':start['margin_fallback_attempts'][0]['margin_factor']=.5
    if damage=='budget':start['margin_fallback_attempts'][0]['time_limit_seconds']=21.
    if damage=='promotion':start['margin_fallback_attempts'][0]['success']=True
    if damage=='caps':start['caps'][0]=-.01
    if damage=='policy':protocol['proposal_margin_fallback']=False
    result['fit']['proposal_starts']=[window.archive('start',start)]
    save(directory/'protocol.json',protocol);result['protocol_sha256']=module.sha256(directory/'protocol.json');save(directory/'result.json',result)
    if damage is None:
        parameters,*_=module.resume_window(*args);assert parameters[0]==parameters[4]==.05
    else:
        with pytest.raises((ValueError,AssertionError)):module.resume_window(*args)
