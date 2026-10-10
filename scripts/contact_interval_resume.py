"""Replay globally preserving saved interval states without rebasing references."""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np
import torch
from strep import ROOT,read,sha256
from audit_contact_interval import pose_tracks,overlay_pose_tracks,evaluate_interval
from pose_proposal_archive import load_record
from pose_restoration_policy import row_diagnostics,proposal_headroom
from protected_inequality_step import retain,score,margin_start_attempts
from contact_interval_coverage import partition_frames,select_window

FILES={'baseline-motion.npz','proposed-motion.npz','retained-motion.npz','baseline.json','proposed.json','row-diagnostics.json','preflight.json'}


class IntervalReplaySession:
    """One worker's last fully replayed state; never loads a saved attestation."""
    def __init__(self):
        self.__context=None;self.__entry=None;self.__factory=None
        self.__bindings={};self.hits=0;self.full_replays=0

    @staticmethod
    def source_digest(source):
        digest=hashlib.sha256()
        for key in sorted(source):
            value=np.asarray(source[key])
            if value.dtype.hasobject:raise ValueError('Numeric original pose arrays required')
            digest.update(json.dumps([key,value.dtype.str,value.shape]).encode())
            digest.update(np.ascontiguousarray(value).tobytes())
        return digest.hexdigest()

    @staticmethod
    def request(study,source,frames,width,original_bindings,methods,definitions,origin_type):
        return dict(study=str(Path(study).resolve()),source=IntervalReplaySession.source_digest(source),
            frames=list(frames),width=width,original_bindings=dict(original_bindings),methods=list(methods),
            definitions=str(Path(definitions).resolve()),definitions_sha256=sha256(definitions),
            origin_type=id(origin_type))

    @staticmethod
    def check_bindings(bindings):
        try:
            if any(not Path(p).resolve().is_relative_to(ROOT.resolve()) or sha256(p)!=h for p,h in bindings.items()):
                raise ValueError('Same-worker history binding changed')
        except OSError as exc:raise ValueError('Same-worker history binding disappeared') from exc

    def prepare(self,study,factory,source,frames,width,original_bindings,methods,definitions,origin_type,*,implementation_bindings):
        partition_frames(frames,width)
        if not callable(factory) or not isinstance(implementation_bindings,dict) or not implementation_bindings:
            raise ValueError('Explicit bound implementation and owned factory required')
        bindings={**original_bindings,**implementation_bindings}
        self.check_bindings(bindings)
        context=self.request(study,source,frames,width,original_bindings,methods,definitions,origin_type)
        context['implementation_bindings']=dict(implementation_bindings)
        if self.__context is None:
            self.__context=copy.deepcopy(context);self.__factory=factory;self.__bindings=bindings.copy()
        elif context!=self.__context:
            raise ValueError('Same-worker history context changed; use a fresh session')
        return self.__factory

    def _check_request(self,study,factory,source,frames,width,original_bindings,methods,definitions,origin_type):
        context=self.request(study,source,frames,width,original_bindings,methods,definitions,origin_type)
        expected=None if self.__context is None else {k:v for k,v in self.__context.items() if k!='implementation_bindings'}
        if factory is not self.__factory or context!=expected:
            raise ValueError('History reuse requires the exact owned replay context')
        self.check_bindings(self.__bindings)

    @staticmethod
    def clone(payload):
        motion,parameters,receipt,bindings=payload
        return ({k:v.copy() for k,v in motion.items()},{k:v.copy() for k,v in parameters.items()},copy.deepcopy(receipt),bindings.copy())

    def _load_verified(self,directory,ancestors):
        if self.__entry is None or self.__entry[0]!=directory:return None
        _,lineage,payload=self.__entry
        if len(ancestors)+len(lineage)>32 or set(ancestors).intersection(lineage):
            raise ValueError('Reused history exceeds the original acyclic ancestry bound')
        self.check_bindings(payload[3])
        value=self.clone(payload)
        value[2].update(replay_mode='same-worker-bound-reuse',geometry_replayed_this_call=False,
            verified_chain_stages=len(lineage),scope='Same-worker reuse of a previously complete native replay; every artifact/input/implementation binding rechecked. No saved attestation, new geometry evaluation or quality approval.')
        self.hits+=1
        print(dict(stage='interval_resume_reused',directory=directory.relative_to(ROOT).as_posix(),verified_chain_stages=len(lineage)),flush=True)
        return value

    def _save_verified(self,directory,payload):
        # This method is reached only after complete local/global replay succeeds.
        bindings=payload[3];self.check_bindings(bindings);lineage=[];current=directory
        while current is not None:
            if current in lineage or len(lineage)>=32:
                raise ValueError('Original acyclic ancestry bound required before reuse')
            for name in ['protocol.json','result.json']:
                if str(current/name) not in bindings:raise ValueError('Complete bound history lineage required')
            lineage.append(current);protocol=read(current/'protocol.json');prior=protocol.get('interval_resume')
            current=(ROOT/prior['directory']).resolve() if prior is not None else None
            if prior is not None and bindings.get(str(current/'result.json'))!=prior['result_sha256']:
                raise ValueError('Exact verified ancestor result required')
        self.check_bindings(bindings)
        self.__entry=(directory,tuple(lineage),self.clone(payload));self.full_replays+=1

    def statistics(self):
        return dict(schema='strep-same-worker-history-v1',cached_states=int(self.__entry is not None),
            reused_histories=self.hits,full_native_replays=self.full_replays,
            scope='One in-memory state, fixed original context, full binding checks; new stages still receive complete local/global replay. No cross-worker saved cache or quality approval.',
            quality_approved=False,release_approved=False)


def original_limits(window):
    return [dict(frame=p.frame,position_m=.22,added_speed_m_s=1.5,point_working_m=p.point_limits.tolist(),
        normal_degrees=p.config['normal_tolerance_degrees'],floor_m=p.config['clearance_m'],
        root_lift_m=p.config['max_root_lift_m'],rotation_radians=p.limits.tolist()) for p in window.problems]


def same_motion(actual,expected,*,exact=True):
    if set(actual)!=set(expected):raise ValueError('Every pose track must be retained')
    for key in expected:
        if actual[key].dtype!=expected[key].dtype or actual[key].shape!=expected[key].shape:
            raise ValueError('Original pose shape and saved precision required')
        if exact:np.testing.assert_array_equal(actual[key],expected[key])
        else:np.testing.assert_allclose(actual[key],expected[key],rtol=0,atol=2e-6)


def seed_window(factory,block,motion,parameters):
    window=factory(block)
    if parameters:window.seed=np.concatenate([np.asarray(parameters[f],dtype=float) for f in block])
    window.controls(window.seed)
    exterior={f for p in window.problems for f in p.neighbors if f not in block}
    window.set_fixed_neighbors({f:motion['posed_joints'][f] for f in exterior})
    return window


def replay_local(directory,protocol,result,window,origin,bind):
    report=result['fit'];scale=window.scale;size=len(window.labels)
    trust=protocol.get('trust_normalized')
    if type(trust) not in [int,float] or not np.isfinite(trust) or not 1e-5<=trust<=.3:
        raise ValueError('Explicit bounded original trust policy required')
    lower=np.tile(np.r_[np.full(window.pose_dim-1,-1.),0.],len(window.frames));upper=np.ones(window.dim)
    def bounded(value):
        z=np.asarray(value,dtype=float)
        if z.shape!=(window.dim,) or not np.isfinite(z).all() or np.any(z<lower) or np.any(z>upper):
            raise ValueError('Complete original bounded normalized controls required')
        return z
    masks=np.zeros(size,dtype=bool);represented_mask=np.zeros(len(window.representation_labels),dtype=bool)
    point_rows=[label.startswith('point:') for label in window.labels]
    headroom=proposal_headroom(window.labels,point=1e-5,normal=1e-3,object=1e-3,body=1e-3).tolist()
    if (protocol.get('inequality_labels')!=window.labels or protocol.get('representation_labels')!=window.representation_labels
            or protocol.get('original_limits')!=original_limits(window) or protocol.get('pose_dim')!=window.pose_dim
            or protocol.get('tradeoff_mask')!=masks.tolist() or report.get('tradeoff_mask')!=masks.tolist()
            or report.get('representation_tradeoff_mask')!=represented_mask.tolist() or report.get('failure_policy')!='merit'):
        raise ValueError('Identical complete original rig/geometry rows and preservation policy required')
    for field,value in [('proposal','nonlinear'),('proposal_start','geometry-descent'),('proposal_priority','worst-first'),
            ('proposal_tangent_guard',True),('proposal_margin_fallback',True),('proposal_trial_correction',True),('representation_guard',True),
            ('proposal_feasible_mask',point_rows),('proposal_headroom_normalized',headroom)]:
        if protocol.get(field)!=value or report.get(field)!=value:raise ValueError('Bound original proposal policy differs')
    geometry_solver=protocol.get('proposal_geometry_solver','supporting-planes')
    if geometry_solver not in ['supporting-planes','conic'] or report.get('proposal_geometry_solver','supporting-planes')!=geometry_solver:
        raise ValueError('Bound original geometry-start solver differs')
    observations={}
    for entry in result['trials']:
        label=entry['label']
        if type(label) is not str or Path(label).name!=label or label in observations:
            raise ValueError('Unique local saved observation identities required')
        trial=directory/'trials'/label;audit=read(trial/'audit.json')
        bind(trial/'audit.json',entry['audit_sha256']);bind(trial/'window.npz',audit['motion_sha256'])
        if (audit.get('label')!=label or audit.get('retained') is not entry['retained']
                or any(audit.get(k) is not False for k in ['quality_approved','release_approved'])):
            raise ValueError('Observation identity/classification differs')
        controls=window.controls(audit['parameters']);bounded(controls/scale)
        with torch.no_grad():solver=window.geometry_slack(torch.as_tensor(controls,dtype=torch.float64)).numpy()
        np.testing.assert_allclose(solver,audit['solver_slacks'],rtol=1e-10,atol=1e-10)
        motion=dict(np.load(trial/'window.npz',allow_pickle=False))
        same_motion(motion,origin.motion(controls),exact=np.array_equal(controls,origin.seed))
        if origin.audit(controls,motion)!=audit['candidate']:raise ValueError('Saved physical audit differs')
        saved=window.saved_representation(controls,motion=motion)
        np.testing.assert_array_equal(saved,audit['represented_slacks'])
        observations[label]=dict(audit,saved=saved)
        if len(observations)%16==0:print(dict(stage='interval_resume_local',observations=len(observations)),flush=True)
    if not {'seed','final'}.issubset(observations):raise ValueError('Original and retained terminal observations required')
    seed=observations['seed'];np.testing.assert_array_equal(seed['parameters'],origin.seed)
    np.testing.assert_array_equal(seed['represented_slacks'],origin.initial_rows)
    np.testing.assert_array_equal(seed['solver_slacks'],report['initial_slacks'])
    np.testing.assert_array_equal(seed['represented_slacks'],report['initial_represented_slacks'])
    def record(reference,kind):
        if reference.get('kind')!=kind or 'archive_schema' not in reference:raise ValueError('Complete streamed proposal record required')
        value,bindings=load_record(directory,reference,array_values=True)
        for path,digest in bindings.items():bind(path,digest)
        return value
    linear_refs={r['iteration']:r for r in report['proposal_linearizations']}
    if len(linear_refs)!=len(report['proposal_linearizations']):raise ValueError('Unique complete tangent populations required')
    for r in linear_refs.values():record(r,'linearization')
    start_records={}
    for reference in report['proposal_starts']:
        start=record(reference,'start');linear=record(linear_refs[start['iteration']],'linearization');before=np.asarray(linear['slacks'])
        if start['iteration'] in start_records:raise ValueError('Unique complete start per iteration required')
        # Later backoff checks need only this small identity/direction, not the
        # complete norm/Jacobian archive for every preceding outer iteration.
        start_records[start['iteration']]=dict(success=start['success'],
            delta=np.asarray(start['delta']).copy() if start['success'] else None)
        if start.get('retained') is not False or start.get('priority')!='worst-first':raise ValueError('Initializer cannot be retained')
        floor=np.minimum(before,0);floor[point_rows]=np.maximum(floor[point_rows],0)
        caps=np.maximum(floor+headroom,np.minimum(before,0)+1e-6)
        np.testing.assert_array_equal(start['margin_floor_caps'],floor)
        for attempt in margin_start_attempts(start):
            np.testing.assert_array_equal(attempt['caps'],floor+attempt['margin_factor']*(caps-floor))
            if geometry_solver=='conic':
                from geometry_conic_start import replay
                center=bounded(linear['controls']);np.testing.assert_array_equal(start['controls'],center)
                np.testing.assert_array_equal(attempt['lower_delta'],np.maximum(lower,center-trust)-center)
                np.testing.assert_array_equal(attempt['upper_delta'],np.minimum(upper,center+trust)-center)
                replay(attempt,before,linear['jacobian'])
            elif attempt.get('algorithm')=='Complete affine norm cones':raise ValueError('Conic start requires explicit solver provenance')
    corrections={};counts={}
    for reference in report['proposal_corrections']:
        correction=record(reference,'correction');number=correction['attempt'];iteration=correction['iteration']
        counts[iteration]=counts.get(iteration,0)+1
        if number!=len(corrections)+1 or correction.get('retained') is not False or counts[iteration]>2:
            raise ValueError('Ordered at most two unretained corrections per iteration required')
        linear=record(linear_refs[iteration],'linearization');current=np.asarray(linear['slacks']);base=np.asarray(linear['controls']);jac0=np.asarray(linear['jacobian'])
        parent=observations[correction['parent_trial']];parents=[t for t in report['trials'] if t['label']==correction['parent_trial']]
        if len(parents)!=1 or parents[0]['accepted'] or parents[0]['stage']!='geometry-start' or parents[0]['fraction'] not in [.25,.125]:
            raise ValueError('Correction must bind a rejected geometry trial')
        z=bounded(correction['controls']);np.testing.assert_allclose(z*scale,parent['parameters'],rtol=0,atol=1e-12)
        np.testing.assert_array_equal(correction['base_controls'],base);np.testing.assert_array_equal(correction['slacks'],parent['solver_slacks'])
        jac=np.asarray(correction['jacobian'])
        if jac.shape!=(size,window.dim) or not np.isfinite(jac).all():raise ValueError('Complete finite correction tangent required')
        trust=protocol['trust_normalized'];lo=np.maximum(lower,base-trust);hi=np.minimum(upper,base+trust)
        np.testing.assert_equal(correction['correction_limit_normalized'],.25*trust)
        np.testing.assert_array_equal(correction['lower_delta'],np.maximum(lo-z,-.25*trust));np.testing.assert_array_equal(correction['upper_delta'],np.minimum(hi-z,.25*trust))
        floor=np.minimum(current,0);floor[point_rows]=np.maximum(floor[point_rows],0)
        caps=np.r_[floor+1e-6,np.minimum(current,0)+1e-6];np.testing.assert_array_equal(correction['caps'],caps)
        if not 0<correction['time_limit_seconds']<=20:raise ValueError('Bounded correction budget required')
        if correction['success']:
            delta=np.asarray(correction['delta'])
            if delta.shape!=z.shape or not np.isfinite(delta).all() or np.any(delta<correction['lower_delta']) or np.any(delta>correction['upper_delta']):
                raise ValueError('Correction exceeds its local bounds')
            tangent=current+jac0@(z-base)
            if np.any(np.r_[parent['solver_slacks'],tangent]+np.vstack([jac,jac0])@delta<caps-1e-8):raise ValueError('Correction failed complete linear replay')
        corrections[number]=correction
    before=np.asarray(seed['solver_slacks']);saved=seed['saved'];last=origin.normalized_seed.copy();retained={'final'};cached=None
    for trial in report['trials']:
        if trial.get('nonlinear_replay') is False:
            if trial['accepted']:raise ValueError('Unmeasured proposal cannot be retained')
            continue
        audit=observations[trial['label']];z=bounded(trial['controls']);after=np.asarray(audit['solver_slacks'])
        np.testing.assert_allclose(origin.controls(z),audit['parameters'],rtol=0,atol=1e-12)
        if np.any(np.abs(z-last)>protocol['trust_normalized']+1e-12):raise ValueError('Trial exceeded its original trust bounds')
        if cached is None or cached['iteration']!=trial['iteration']:cached=record(linear_refs[trial['iteration']],'linearization')
        jac=np.asarray(cached['jacobian'])
        if jac.shape!=(size,window.dim) or not np.isfinite(jac).all():raise ValueError('Complete finite tangent rows required')
        np.testing.assert_array_equal(cached['protected_rows'],np.arange(size));np.testing.assert_array_equal(cached['slacks'],before)
        np.testing.assert_allclose(cached['controls'],last,rtol=0,atol=1e-12)
        np.testing.assert_array_equal(cached['preservation_caps'],np.minimum(before,0));np.testing.assert_array_equal(cached['tangent_proposal_caps'],np.minimum(before,0)+1e-6)
        if geometry_solver=='conic' and trial['stage']=='geometry-start':
            start=start_records.get(trial['iteration']);fraction=trial.get('fraction')
            if start is None or start['success'] is not True or fraction not in [1.,.5,.25,.125,.0625,.03125,.015625,.0078125]:
                raise ValueError('Conic trial must bind a checked complete start and backoff')
            np.testing.assert_allclose(z,np.clip(last+fraction*np.asarray(start['delta']),
                np.maximum(lower,last-trust),np.minimum(upper,last+trust)),rtol=0,atol=1e-12)
        if trial['stage']=='geometry-start-correction':
            correction=corrections[trial['correction_attempt']]
            if not correction['success'] or trial['parent_trial']!=correction['parent_trial'] or trial['iteration']!=correction['iteration']:
                raise ValueError('Corrected trial must bind its successful proposal')
            base=np.asarray(correction['base_controls']);lo=np.maximum(lower,base-protocol['trust_normalized']);hi=np.minimum(upper,base+protocol['trust_normalized'])
            np.testing.assert_allclose(z,np.clip(np.asarray(correction['controls'])+correction['delta'],lo,hi),rtol=0,atol=1e-12)
        keep=retain(before,after,failure_policy='merit',tradeoff_mask=masks)
        tangent=bool(np.all(before+jac@(z-last)>=np.minimum(before,0)))
        saved_keep=retain(saved,audit['saved'],failure_policy='merit',tradeoff_mask=represented_mask)
        accepted=keep and tangent and saved_keep
        if any(trial.get(k) is not v for k,v in [('retention_guard_passed',keep),('tangent_guard_passed',tangent),('representation_guard_passed',saved_keep),('accepted',accepted)]) or audit['retained'] is not accepted:
            raise ValueError('Complete nonlinear/tangent/saved decision differs')
        np.testing.assert_array_equal(trial['represented_slacks'],audit['saved']);np.testing.assert_allclose(trial['score'],score(after),rtol=0,atol=1e-12)
        if accepted:before=after;saved=audit['saved'];last=z;retained.add(trial['label'])
    if any(audit['retained'] is not (label in retained) for label,audit in observations.items()):raise ValueError('Unaccepted observation cannot be promoted')
    for query in report['proposal_queries']:
        audit=observations[query['label']]
        if query['retained'] is not False or audit['retained'] is not False:raise ValueError('Inner query cannot be promoted')
        np.testing.assert_allclose(origin.controls(bounded(query['controls'])),audit['parameters'],rtol=0,atol=1e-12)
        np.testing.assert_allclose(query['score'],score(audit['solver_slacks']),rtol=0,atol=1e-12)
    controls=window.controls(result['parameters']);np.testing.assert_allclose(controls,origin.controls(last),rtol=0,atol=1e-12)
    np.testing.assert_array_equal(controls,observations['final']['parameters']);np.testing.assert_array_equal(before,report['final_slacks'])
    np.testing.assert_array_equal(before,observations['final']['solver_slacks'])
    np.testing.assert_array_equal(saved,report['final_represented_slacks']);np.testing.assert_array_equal(saved,observations['final']['saved'])
    if np.any(before<np.minimum(seed['solver_slacks'],0)) or np.any(saved<np.minimum(seed['saved'],0)) or report.get('represented_source_rows_preserved') is not True:
        raise ValueError('Terminal local origin protection failed')
    return controls,dict(np.load(directory/'trials/final/window.npz',allow_pickle=False)),len(observations)


def resume_interval(directory,study,factory,source,frames,width,original_bindings,methods,definitions,origin_type,*,ancestors=(),replay_session=None):
    directory=Path(directory).resolve()
    if not directory.is_relative_to(ROOT.resolve()) or directory in ancestors or len(ancestors)>=32:
        raise ValueError('In-project acyclic interval chain of at most32 stages required')
    if replay_session is not None:
        if type(replay_session) is not IntervalReplaySession:raise ValueError('Owned in-memory interval session required')
        replay_session._check_request(study,factory,source,frames,width,original_bindings,methods,definitions,origin_type)
        reused=replay_session._load_verified(directory,ancestors)
        if reused is not None:return reused
    print(dict(stage='interval_resume_reading',directory=directory.relative_to(ROOT).as_posix()),flush=True)
    protocol=read(directory/'protocol.json');result=read(directory/'result.json');pipeline=read(directory/'pipeline.json')
    if protocol.get('schema')=='strep-saved-contact-candidate-recovery-v1':
        from contact_candidate_recovery import replay_recovery
        return replay_recovery(directory,study,factory,source,frames,width,original_bindings,methods,definitions,origin_type,
            ancestors=ancestors,replay_session=replay_session)
    partition_frames(protocol.get('frames'),protocol.get('width'))
    if (result.get('status')!='complete' or pipeline.get('status')!='complete' or protocol.get('source_study')!=study.relative_to(ROOT).as_posix()
            or protocol.get('frames')!=frames or protocol.get('width')!=width or protocol.get('fps')!=30
            or result.get('decision',{}).get('update_retained') is not True or result['decision'].get('source_rows_preserved') is not True
            or any(d.get(k) is not False for d in [protocol,result,pipeline] for k in ['quality_approved','release_approved'])
            or protocol.get('metadata_approved') is not False):
        raise ValueError('Complete globally preserving unapproved interval with identical original source/clock/coverage required')
    checked={}
    def bind(path,digest):
        path=Path(path).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha256(path)!=digest:raise ValueError('Interval resume binding differs')
        checked[str(path)]=digest
    inputs=protocol.get('inputs_sha256',{})
    if any(inputs.get(p)!=h for p,h in original_bindings.items()):raise ValueError('Original interval inputs differ')
    for path,digest in inputs.items():bind(path,digest)
    archived=protocol.get('methods_sha256',{});expected=set(methods)
    if protocol.get('proposal_geometry_solver','supporting-planes')=='conic' and 'geometry_conic_start.py' not in archived:
        raise ValueError('Conic-start implementation must be archived')
    optional={'geometry_conic_start.py'} if protocol.get('proposal_geometry_solver','supporting-planes')=='supporting-planes' else set()
    legacy_optional={'contact_candidate_recovery.py'}
    allowed=[expected-extra for extra in [set(),{'contact_interval_resume.py'},optional,optional|{'contact_interval_resume.py'}]]
    if set(archived) not in allowed+[names-legacy_optional for names in allowed]:
        raise ValueError('Complete archived interval implementation required')
    for name,digest in archived.items():bind(directory/'implementation'/name,digest)
    if protocol.get('native_metadata_sha256')!=sha256(definitions):raise ValueError('Original native metadata differs')
    bind(directory/'implementation/kimodo-skeleton-definitions.py',protocol['native_metadata_sha256']);bind(directory/'protocol.json',result['protocol_sha256'])
    if set(result.get('files_sha256',{}))!=FILES:raise ValueError('Complete immutable interval outputs required')
    for name,digest in result['files_sha256'].items():bind(directory/name,digest)
    for name in ['result.json','pipeline.json']:checked[str(directory/name)]=sha256(directory/name)
    prior=protocol.get('interval_resume');state=pose_tracks(source);parameters={}
    if prior is not None:
        state,parameters,receipt,extra=resume_interval(ROOT/prior['directory'],study,factory,source,frames,width,original_bindings,methods,definitions,origin_type,ancestors=ancestors+(directory,),replay_session=replay_session)
        if receipt['result_sha256']!=prior['result_sha256']:raise ValueError('Interval ancestor result differs')
        checked.update(extra)
    baseline,labels,before=evaluate_interval(factory,frames,state,parameters,width=width)
    if baseline!=read(directory/'baseline.json'):raise ValueError('Complete saved starting interval differs')
    same_motion(dict(np.load(directory/'baseline-motion.npz',allow_pickle=False)),state)
    block=select_window(frames,baseline,width,protocol.get('selection_exclusions',[]))
    if block is None:raise ValueError('Retained interval must select a remaining measured window')
    if protocol.get('selected_frames')!=block or result.get('selected_frames')!=block:raise ValueError('Bound failure-first selection differs')
    current={r['frame']:np.asarray(r['controls']) for r in baseline['parameters']}
    window=seed_window(factory,block,state,current);origin=origin_type(window,state)
    controls,motion,count=replay_local(directory,protocol,result,window,origin,bind)
    proposed=overlay_pose_tracks(state,block,motion)
    for i,f in enumerate(block):current[f]=controls[i*window.pose_dim:(i+1)*window.pose_dim]
    summary,current_labels,after=evaluate_interval(factory,frames,proposed,current,width=width)
    if summary!=read(directory/'proposed.json') or current_labels!=labels:raise ValueError('Complete saved proposed interval differs')
    same_motion(dict(np.load(directory/'proposed-motion.npz',allow_pickle=False)),proposed)
    same_motion(dict(np.load(directory/'retained-motion.npz',allow_pickle=False)),proposed)
    diagnostics=row_diagnostics(labels,before,after,np.zeros(len(labels),dtype=bool))
    if diagnostics!=read(directory/'row-diagnostics.json') or not retain(before,after,failure_policy='merit',tradeoff_mask=np.zeros(len(labels),dtype=bool)):
        raise ValueError('Complete original interval retention failed')
    expected_observations=[(kind,i,block) for kind in ['baseline','proposed'] for i,block in enumerate(partition_frames(frames,width))]
    actual=[(o['kind'],o['index'],o['frames']) for o in result['observations']]
    if actual!=expected_observations:raise ValueError('Complete ordered interval observations required')
    for o in result['observations']:
        path=(directory/o['path']).resolve()
        if not path.is_relative_to(directory):raise ValueError('Local interval observation required')
        bind(path,o['sha256']);record=read(path);measured=baseline if o['kind']=='baseline' else summary
        all_rows={r['label']:r['initial_slack' if o['kind']=='baseline' else 'final_slack'] for r in diagnostics['rows']}
        if record['frames']!=o['frames'] or record['physical']!=[p for p in measured['per_frame_physical'] if p['frame'] in o['frames']]:raise ValueError('Interval observation physical audit differs')
        measured_window=factory(o['frames'])
        if record['labels']!=measured_window.representation_labels:raise ValueError('Complete per-block saved rows required')
        np.testing.assert_array_equal(record['slacks'],[all_rows[label] for label in record['labels']])
    if any(sha256(Path(path))!=digest for path,digest in checked.items()):raise ValueError('Interval artifacts changed during replay')
    receipt=dict(directory=directory.relative_to(ROOT).as_posix(),result_sha256=checked[str(directory/'result.json')],
        replayed_local_observations=count,replayed_contact_keys=2*len(frames),replayed_complete_rows=2*len(labels),
        original_references_preserved=True,quality_approved=False,release_approved=False,
        scope='Fully bound diagnostic interval history with exact saved origins, current exterior keys and complete local/global retention replay; no animation/export/engine/human certificate.')
    print(dict(stage='interval_resume_verified',directory=receipt['directory']),flush=True)
    payload=(proposed,current,receipt,checked)
    if replay_session is not None:replay_session._save_verified(directory,payload)
    return payload
