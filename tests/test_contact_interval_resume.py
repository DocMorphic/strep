"""Bound whole-interval history, exact origins and changed exterior contexts."""
import sys,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import contact_interval_resume as module
from repair_contact_interval import ExactSavedOrigin
from pose_proposal_archive import ProposalArchive
from pose_restoration_policy import row_diagnostics,proposal_headroom
from protected_inequality_step import score


def motion():
    return dict(posed_joints=np.zeros((4,77,3),dtype=np.float32),root_positions=np.zeros((4,3),dtype=np.float32),
        local_rot_mats=np.tile(np.eye(3,dtype=np.float32),(4,77,1,1)),global_rot_mats=np.tile(np.eye(3,dtype=np.float32),(4,77,1,1)))


class Window:
    pose_dim=4
    def __init__(self,frames):
        self.frames=frames;self.dim=4*len(frames);self.seed=np.zeros(self.dim);self.scale=np.ones(self.dim)
        self.labels=['object:box:frame-'+str(f) for f in frames];self.representation_labels=self.labels
        self.problems=[SimpleNamespace(frame=f,neighbors={n:torch.zeros((77,3),dtype=torch.float64) for n in [f-1,f+1]},
            point_limits=np.array([.00499]),config=dict(normal_tolerance_degrees=10,clearance_m=.002,max_root_lift_m=.2),limits=np.array([1.]),
            t=lambda a:torch.as_tensor(a,dtype=torch.float64),audit_motion=lambda *a,**k:dict(pose_checks_passed=False)) for f in frames]
    def controls(self,x):
        x=np.asarray(x,dtype=float)
        if x.shape!=(self.dim,) or not np.isfinite(x).all():raise ValueError('Complete controls')
        return x
    def set_fixed_neighbors(self,positions):
        for p in self.problems:
            for f in p.neighbors:
                if f in positions:p.neighbors[f]=p.t(positions[f].copy())
    def geometry_slack(self,x):return x[::4]-.4
    def saved_representation(self,x,*,motion):return motion['posed_joints'][:,0,0].astype(float)-.4
    def independent(self,x):
        m={k:v[self.frames].copy() for k,v in motion().items()};m['posed_joints'][:,0,0]=np.asarray(x)[::4]
        return {},m


def evaluate(factory,frames,m,parameters=None,**k):
    w=factory(frames);parameters=parameters or {};parts=[np.asarray(parameters.get(f,np.zeros(4))) for f in frames]
    audits=[dict(frame=f,pose_checks_passed=False) for f in frames]
    summary=dict(parameters=[dict(frame=f,controls=part.tolist()) for f,part in zip(frames,parts)],
        ranked_windows=[dict(frames=frames)],per_frame_physical=audits)
    return summary,w.labels,m['posed_joints'][frames,0,0].astype(float)-.4


def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(module,'ROOT',tmp_path);monkeypatch.setattr(module,'evaluate_interval',evaluate)
    study=tmp_path/'source';study.mkdir();source=motion();np.savez_compressed(study/'motion.npz',**source)
    definitions=tmp_path/'definitions.py';definitions.write_text('native reference')
    bindings={str(study/'motion.npz'):module.sha256(study/'motion.npz')};frames=[1,2]
    def make(name,state=None,parameters=None,prior=None):
        state=source if state is None else state;parameters={} if parameters is None else parameters
        directory=tmp_path/name;archive=directory/'implementation';archive.mkdir(parents=True)
        (archive/'toy.py').write_text('immutable original method');(archive/'kimodo-skeleton-definitions.py').write_bytes(definitions.read_bytes())
        baseline,labels,before=evaluate(Window,frames,state,parameters);current={r['frame']:np.asarray(r['controls']) for r in baseline['parameters']}
        w=module.seed_window(Window,frames,state,current);origin=ExactSavedOrigin(w,state)
        accepted=origin.seed.copy();accepted[::4]+=.05;proposed=module.overlay_pose_tracks(state,frames,origin.motion(accepted))
        current={f:accepted[4*i:4*(i+1)] for i,f in enumerate(frames)};after_summary,_,after=evaluate(Window,frames,proposed,current)
        protocol=dict(source_study='source',frames=frames,width=3,fps=30,selected_frames=frames,inputs_sha256=bindings,
            methods_sha256={'toy.py':module.sha256(archive/'toy.py')},native_metadata_sha256=module.sha256(definitions),
            inequality_labels=w.labels,representation_labels=w.representation_labels,original_limits=module.original_limits(w),pose_dim=4,
            tradeoff_mask=[False,False],proposal_feasible_mask=[False,False],proposal_headroom_normalized=proposal_headroom(w.labels,object=.001).tolist(),
            proposal='nonlinear',proposal_start='geometry-descent',proposal_priority='worst-first',proposal_tangent_guard=True,
            proposal_margin_fallback=True,proposal_trial_correction=True,representation_guard=True,trust_normalized=.1,
            interval_resume=prior,metadata_approved=False,quality_approved=False,release_approved=False)
        observations=[];trials=[]
        for label,x,retained in [('seed',origin.seed,False),('kept',accepted,True),('final',accepted,True)]:
            path=directory/'trials'/label;path.mkdir(parents=True);m=origin.motion(x);np.savez_compressed(path/'window.npz',**m)
            audit=dict(label=label,parameters=x.tolist(),retained=retained,candidate=origin.audit(x,m),solver_slacks=w.geometry_slack(torch.as_tensor(x)).numpy().tolist(),
                represented_slacks=w.saved_representation(x,motion=m).tolist(),motion_sha256=module.sha256(path/'window.npz'),quality_approved=False,release_approved=False)
            write(path/'audit.json',audit);trials.append(dict(label=label,retained=retained,audit_sha256=module.sha256(path/'audit.json')))
        jac=np.zeros((2,8));jac[0,0]=jac[1,4]=1;store=ProposalArchive(directory)
        solver_before=w.geometry_slack(torch.as_tensor(origin.seed)).numpy();solver_after=w.geometry_slack(torch.as_tensor(accepted)).numpy()
        saved_before=origin.initial_rows;saved_after=origin.rows(accepted)
        linear=store('linearization',dict(iteration=1,controls=origin.normalized_seed.tolist(),slacks=solver_before.tolist(),jacobian=jac.tolist(),
            protected_rows=[0,1],preservation_caps=np.minimum(solver_before,0).tolist(),tangent_proposal_caps=(np.minimum(solver_before,0)+1e-6).tolist()))
        fit={k:protocol[k] for k in ['proposal','proposal_start','proposal_priority','proposal_tangent_guard','proposal_margin_fallback','proposal_trial_correction','representation_guard','tradeoff_mask','proposal_feasible_mask','proposal_headroom_normalized']}
        fit.update(failure_policy='merit',representation_tradeoff_mask=[False,False],initial_slacks=solver_before.tolist(),final_slacks=solver_after.tolist(),
            initial_represented_slacks=saved_before.tolist(),final_represented_slacks=saved_after.tolist(),represented_source_rows_preserved=True,
            proposal_queries=[],proposal_starts=[],proposal_corrections=[],proposal_linearizations=[linear],trials=[dict(label='kept',controls=accepted.tolist(),iteration=1,stage='optimized',accepted=True,
            score=list(score(solver_after)),represented_slacks=saved_after.tolist(),retention_guard_passed=True,tangent_guard_passed=True,representation_guard_passed=True)])
        write(directory/'protocol.json',protocol);write(directory/'baseline.json',baseline);write(directory/'proposed.json',after_summary)
        for name,m in [('baseline-motion.npz',state),('proposed-motion.npz',proposed),('retained-motion.npz',proposed)]:np.savez_compressed(directory/name,**m)
        write(directory/'row-diagnostics.json',row_diagnostics(labels,before,after,[False,False]));write(directory/'preflight.json',{})
        for kind,s,values in [('baseline',baseline,before),('proposed',after_summary,after)]:
            path=directory/kind/'window-0.json';path.parent.mkdir();write(path,dict(frames=frames,labels=labels,slacks=values.tolist(),physical=s['per_frame_physical']))
            observations.append(dict(kind=kind,index=0,frames=frames,path=path.relative_to(directory).as_posix(),sha256=module.sha256(path)))
        result=dict(status='complete',selected_frames=frames,parameters=accepted.tolist(),decision=dict(update_retained=True,source_rows_preserved=True),
            protocol_sha256=module.sha256(directory/'protocol.json'),files_sha256={n:module.sha256(directory/n) for n in module.FILES},fit=fit,trials=trials,observations=observations,quality_approved=False,release_approved=False)
        write(directory/'result.json',result);write(directory/'pipeline.json',dict(status='complete',quality_approved=False,release_approved=False))
        return directory,proposed,current
    args=(study,Window,source,frames,3,bindings,['toy.py','contact_interval_resume.py'],definitions,ExactSavedOrigin)
    return make,args


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def reseal(directory):
    result=module.read(directory/'result.json');result['protocol_sha256']=module.sha256(directory/'protocol.json')
    result['files_sha256']={n:module.sha256(directory/n) for n in module.FILES}
    for t in result['trials']:t['audit_sha256']=module.sha256(directory/'trials'/t['label']/'audit.json')
    for o in result['observations']:o['sha256']=module.sha256(directory/o['path'])
    write(directory/'result.json',result)


def test_complete_resume_and_recursive_continuation_keep_original_references(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);first,_,_=make('first');state,params,receipt,bindings=module.resume_interval(first,*args)
    assert receipt['replayed_local_observations']==3 and params[1][0]==.05
    second,expected,_=make('second',state,params,receipt)
    again,_,record,extra=module.resume_interval(second,*args)
    for key in again:np.testing.assert_array_equal(again[key],expected[key])
    assert again['posed_joints'][1,0,0]==np.float32(.1) and not args[2]['posed_joints'].any()
    assert set(bindings).issubset(extra) and record['original_references_preserved']


@pytest.mark.parametrize('field,value',[('source_study','elsewhere'),('frames',[2,3]),('frames',[True,2]),('fps',60),('width',2),('width',True),('metadata_approved',True),('quality_approved',True),('release_approved',True)])
def test_scope_clock_or_approval_changes_cannot_resume(tmp_path,monkeypatch,field,value):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first');p=module.read(directory/'protocol.json');p[field]=value;write(directory/'protocol.json',p);reseal(directory)
    with pytest.raises(ValueError):module.resume_interval(directory,*args)


@pytest.mark.parametrize('damage',['hash','method','native','retained','baseline','selection','controls','passing-claim','trial-decision','trial-pose','rows','observation','archive','trust','exclude-selected'])
def test_tampered_history_rejected_even_after_outer_hashes_resealed(tmp_path,monkeypatch,damage):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first');result=module.read(directory/'result.json');p=module.read(directory/'protocol.json')
    if damage=='hash':(directory/'baseline.json').write_text('{}');
    elif damage=='method':p['methods_sha256']={}
    elif damage=='native':p['native_metadata_sha256']='0'*64
    elif damage in ['retained','baseline']:
        path=directory/(damage+'-motion.npz');m=dict(np.load(path));m['posed_joints'][1,0,0]=.7;np.savez_compressed(path,**m)
    elif damage=='selection':p['selected_frames']=[2,3]
    elif damage=='controls':result['parameters'][0]=.06
    elif damage=='passing-claim':result['decision']['source_rows_preserved']=False
    elif damage=='trial-decision':result['fit']['trials'][0]['accepted']=False
    elif damage=='trial-pose':
        path=directory/'trials/kept/window.npz';m=dict(np.load(path));m['posed_joints'][0,0,0]=.07;np.savez_compressed(path,**m)
        a=module.read(path.parent/'audit.json');a['motion_sha256']=module.sha256(path);write(path.parent/'audit.json',a)
    elif damage=='rows':result['fit']['initial_represented_slacks'][0]=-.1
    elif damage=='observation':result['observations'].pop()
    elif damage=='archive':result['fit']['proposal_linearizations'][0]['archive_sha256']='0'*64
    elif damage=='trust':p['trust_normalized']=True
    elif damage=='exclude-selected':p['selection_exclusions']=[[1,2]]
    write(directory/'protocol.json',p);write(directory/'result.json',result)
    if damage!='hash':reseal(directory)
    with pytest.raises((ValueError,AssertionError)):module.resume_interval(directory,*args)


@pytest.mark.parametrize('ancestry',['cycle','capacity'])
def test_cycle_and_bound_rejected_before_reading_payload(tmp_path,monkeypatch,ancestry):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first')
    ancestors=(directory,) if ancestry=='cycle' else tuple(tmp_path/str(i) for i in range(32))
    with pytest.raises(ValueError):module.resume_interval(directory,*args,ancestors=ancestors)


def test_explicit_current_neighbors_and_controls_dont_rebase_factory_seed():
    m=motion();m['posed_joints'][3,0,0]=.12;params={1:np.array([.05,0,0,0]),2:np.array([.06,0,0,0])}
    w=module.seed_window(Window,[1,2],m,params);np.testing.assert_array_equal(w.seed[::4],[.05,.06])
    assert w.problems[-1].neighbors[3][0,0]==pytest.approx(.12)
    m['posed_joints'][3,0,0]=0
    assert w.problems[-1].neighbors[3][0,0]==pytest.approx(.12) and not Window([1,2]).seed.any()


def session_for(args):
    session=module.IntervalReplaySession()
    factory=session.prepare(*args,implementation_bindings={str(args[-2]):module.sha256(args[-2])})
    assert factory is args[1]
    return session


def test_same_worker_reuse_skips_geometry_but_preserves_exact_state(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first');calls=[]
    def counted(*a,**k):calls.append(True);return evaluate(*a,**k)
    monkeypatch.setattr(module,'evaluate_interval',counted);session=session_for(args)
    cold=module.resume_interval(directory,*args,replay_session=session);assert len(calls)==2
    warm=module.resume_interval(directory,*args,replay_session=session);assert len(calls)==2
    for key in cold[0]:np.testing.assert_array_equal(cold[0][key],warm[0][key])
    for key in cold[1]:np.testing.assert_array_equal(cold[1][key],warm[1][key])
    assert cold[3]==warm[3] and warm[2]['geometry_replayed_this_call'] is False
    assert warm[2]['replay_mode']=='same-worker-bound-reuse' and not warm[2]['quality_approved']
    assert session.statistics()['reused_histories']==session.statistics()['full_native_replays']==1


def test_cached_returned_arrays_receipts_and_bindings_are_detached(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);directory,expected,_=make('first');session=session_for(args)
    cold=module.resume_interval(directory,*args,replay_session=session)
    cold[0]['posed_joints'][:]=99;cold[1][1][:]=99;cold[2]['release_approved']=True;cold[3].clear()
    warm=module.resume_interval(directory,*args,replay_session=session)
    for key in expected:np.testing.assert_array_equal(warm[0][key],expected[key])
    assert warm[1][1][0]==.05 and warm[2]['release_approved'] is False and warm[3]
    warm[0]['posed_joints'][:]=88;warm[2]['quality_approved']=True
    again=module.resume_interval(directory,*args,replay_session=session)
    assert again[0]['posed_joints'][1,0,0]==np.float32(.05) and not again[2]['quality_approved']


def test_new_stage_fully_replays_with_one_verified_parent_and_cold_worker_matches(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);first,_,_=make('first');session=session_for(args)
    state,params,receipt,_=module.resume_interval(first,*args,replay_session=session)
    second,expected,_=make('second',state,params,receipt);calls=[]
    def counted(*a,**k):calls.append(True);return evaluate(*a,**k)
    monkeypatch.setattr(module,'evaluate_interval',counted)
    warm=module.resume_interval(second,*args,replay_session=session);assert len(calls)==2
    fresh=session_for(args);cold=module.resume_interval(second,*args,replay_session=fresh);assert len(calls)==6
    for key in expected:
        np.testing.assert_array_equal(warm[0][key],expected[key]);np.testing.assert_array_equal(warm[0][key],cold[0][key])
    assert warm[3]==cold[3] and warm[2]==cold[2]
    assert session.statistics()['cached_states']==1 and session.statistics()['full_native_replays']==2
    assert fresh.statistics()['reused_histories']==0 and fresh.statistics()['full_native_replays']==2


@pytest.mark.parametrize('damage',['source','native','method','result','pipeline','protocol','retained','trial','observation','archive','ancestor'])
def test_reuse_rechecks_every_bound_artifact_even_after_resealing(tmp_path,monkeypatch,damage):
    make,args=fixture(tmp_path,monkeypatch);first,_,_=make('first');session=session_for(args)
    state,params,receipt,_=module.resume_interval(first,*args,replay_session=session)
    second,_,_=make('second',state,params,receipt);module.resume_interval(second,*args,replay_session=session)
    targets={'source':args[0]/'motion.npz','native':args[-2],'method':second/'implementation/toy.py',
        'result':second/'result.json','pipeline':second/'pipeline.json','protocol':second/'protocol.json',
        'retained':second/'retained-motion.npz','trial':second/'trials/kept/audit.json',
        'observation':second/'baseline/window-0.json','archive':next((second/'proposals').rglob('*.json')),
        'ancestor':first/'result.json'}
    target=targets[damage];target.write_bytes(target.read_bytes()+b' ')
    if damage in ['trial','observation','retained']:reseal(second)
    with pytest.raises((ValueError,AssertionError)):module.resume_interval(second,*args,replay_session=session)
    assert session.statistics()['reused_histories']==1


@pytest.mark.parametrize('change',['source-value','source-dtype','frames','width','inputs','methods','origin','factory'])
def test_reuse_rejects_changed_runtime_context(tmp_path,monkeypatch,change):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first');session=session_for(args)
    module.resume_interval(directory,*args,replay_session=session);changed=list(args)
    if change.startswith('source-'):
        changed[2]={k:v.copy() for k,v in args[2].items()}
        if change=='source-value':changed[2]['posed_joints'][0,0,0]=np.nextafter(np.float32(0),np.float32(1))
        else:changed[2]['posed_joints']=changed[2]['posed_joints'].astype(np.float64)
    elif change=='frames':changed[3]=[2,3]
    elif change=='width':changed[4]=2
    elif change=='inputs':changed[5]={}
    elif change=='methods':changed[6]=['toy.py']
    elif change=='origin':changed[-1]=type('DifferentOrigin',(ExactSavedOrigin,),{})
    elif change=='factory':changed[1]=lambda frames:Window(frames)
    with pytest.raises(ValueError):module.resume_interval(directory,*changed,replay_session=session)
    assert session.statistics()['reused_histories']==0


def test_context_preparation_keeps_the_owned_factory_and_rejects_changed_bindings(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);session=session_for(args);new=list(args)
    new[1]=lambda frames:(_ for _ in ()).throw(AssertionError('Fresh factory must not replace the bound one'))
    assert session.prepare(*new,implementation_bindings={str(args[-2]):module.sha256(args[-2])}) is Window
    changed=list(args);changed[4]=2
    with pytest.raises(ValueError):session.prepare(*changed,implementation_bindings={str(args[-2]):module.sha256(args[-2])})


@pytest.mark.parametrize('bad_session',[{},True,None])
def test_saved_attestations_and_unprepared_sessions_cannot_skip_replay(tmp_path,monkeypatch,bad_session):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first')
    session=module.IntervalReplaySession() if bad_session is None else bad_session
    with pytest.raises(ValueError):module.resume_interval(directory,*args,replay_session=session)


@pytest.mark.parametrize('fault',['cycle','capacity'])
def test_reused_ancestry_preserves_the_full_original_bound(tmp_path,monkeypatch,fault):
    make,args=fixture(tmp_path,monkeypatch);first,_,_=make('first');session=session_for(args)
    state,params,receipt,_=module.resume_interval(first,*args,replay_session=session)
    second,_,_=make('second',state,params,receipt);module.resume_interval(second,*args,replay_session=session)
    ancestors=(first,) if fault=='cycle' else tuple(tmp_path/str(i) for i in range(31))
    with pytest.raises(ValueError):module.resume_interval(second,*args,ancestors=ancestors,replay_session=session)


def test_failed_new_stage_does_not_replace_the_verified_parent(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);first,_,_=make('first');session=session_for(args)
    state,params,receipt,_=module.resume_interval(first,*args,replay_session=session)
    second,_,_=make('second',state,params,receipt);result=module.read(second/'result.json')
    result['fit']['trials'][0]['accepted']=False;write(second/'result.json',result);reseal(second)
    with pytest.raises((ValueError,AssertionError)):module.resume_interval(second,*args,replay_session=session)
    restored=module.resume_interval(first,*args,replay_session=session)
    assert restored[0]['posed_joints'][1,0,0]==np.float32(.05)
    assert session.statistics()['cached_states']==1 and session.statistics()['full_native_replays']==1


def conic_archive(directory,args,*,geometry_backoff=False):
    from protected_inequality_step import _geometry_margin_start
    result=module.read(directory/'result.json');protocol=module.read(directory/'protocol.json')
    linear,_=module.load_record(directory,result['fit']['proposal_linearizations'][0],array_values=True)
    values=np.asarray(linear['slacks']);jac=np.asarray(linear['jacobian']);floor=np.minimum(values,0)
    caps=np.maximum(floor+protocol['proposal_headroom_normalized'],floor+1e-6)
    derivative=np.zeros((2,3,8));derivative[0,0,0]=derivative[1,0,4]=-1.
    vectors=dict(offsets=np.array([[.5,0.,0.],[.5,0.,0.]]),jacobian=derivative,
        limits=np.full(2,.1),scales=np.ones(2),rows=np.arange(2),distance=np.ones(2,dtype=bool))
    lower=np.tile(np.r_[np.full(3,-.1),0.],2);upper=np.full(8,.1)
    _,start=_geometry_margin_start(values,jac,floor,caps,lower,upper,5.,vectors,'worst-first','conic')
    assert start['success']
    if geometry_backoff:
        # The fixture's unused coordinates have identically zero scalar and
        # vector derivatives. Zero them to match its original kept test pose.
        start['delta']=np.asarray(start['delta']);start['delta'][[1,2,3,5,6,7]]=0.
        start['delta']=start['delta'].tolist()
        result['fit']['trials'][0].update(stage='geometry-start',fraction=.5)
    # Reuse the fixture archive writer; it may add bound records after its creation.
    store=object.__new__(ProposalArchive);store.directory=directory
    ref=store('start',dict(start,iteration=1,controls=np.zeros(8).tolist(),retained=False))
    result['fit']['proposal_starts']=[ref]
    protocol['proposal_geometry_solver']=result['fit']['proposal_geometry_solver']='conic'
    method=directory/'implementation/geometry_conic_start.py';method.write_text('pinned conic fixture method')
    protocol['methods_sha256'][method.name]=module.sha256(method)
    write(directory/'protocol.json',protocol);write(directory/'result.json',result);reseal(directory)
    args[6].append('geometry_conic_start.py')
    return args


def test_complete_conic_proposals_replay_before_original_native_retention(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);directory,expected,_=make('first');conic_archive(directory,args)
    state,_,receipt,_=module.resume_interval(directory,*args)
    for key in state:np.testing.assert_array_equal(state[key],expected[key])
    assert receipt['original_references_preserved'] and not receipt['quality_approved']


def test_conic_replay_requires_archived_solver_implementation(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first');conic_archive(directory,args)
    protocol=module.read(directory/'protocol.json');protocol['methods_sha256'].pop('geometry_conic_start.py')
    write(directory/'protocol.json',protocol);reseal(directory)
    with pytest.raises(ValueError,match='must be archived'):module.resume_interval(directory,*args)


def test_conic_solver_choice_cannot_be_removed_from_protocol(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first');conic_archive(directory,args)
    protocol=module.read(directory/'protocol.json');protocol.pop('proposal_geometry_solver')
    write(directory/'protocol.json',protocol);reseal(directory)
    with pytest.raises(ValueError):module.resume_interval(directory,*args)


def test_checked_conic_backoff_is_bound_to_its_saved_native_trial(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);directory,expected,_=make('first');conic_archive(directory,args,geometry_backoff=True)
    actual,_,_,_=module.resume_interval(directory,*args)
    for key in actual:np.testing.assert_array_equal(actual[key],expected[key])


def test_changed_conic_backoff_cannot_hide_a_different_saved_pose(tmp_path,monkeypatch):
    make,args=fixture(tmp_path,monkeypatch);directory,_,_=make('first');conic_archive(directory,args,geometry_backoff=True)
    result=module.read(directory/'result.json');result['fit']['trials'][0]['fraction']=.25
    write(directory/'result.json',result);reseal(directory)
    with pytest.raises(AssertionError):module.resume_interval(directory,*args)
