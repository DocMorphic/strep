"""Bind and replay a retained diagnostic window without rebasing its budgets."""
from pathlib import Path
import numpy as np
import torch
from strep import ROOT,read,sha256
from protected_inequality_step import retain,score,margin_start_attempts
from pose_proposal_archive import load_record
from pose_restoration_policy import row_diagnostics,tradeoff_policy,proposal_headroom


def resume_window(directory,study,window,original_bindings,limits,methods,definitions,pose_resume,*,ancestors=()):
    directory=Path(directory).resolve()
    if not directory.is_relative_to(ROOT.resolve()) or directory in ancestors or len(ancestors)>=32:
        raise ValueError('In-project acyclic window chain of at most 32 studies required')
    print(dict(stage='window_resume_reading',directory=directory.relative_to(ROOT).as_posix()),flush=True)
    protocol=read(directory/'protocol.json');result=read(directory/'result.json');pipeline=read(directory/'pipeline.json')
    if (result.get('status') not in ['complete','interrupted_resource_guard'] or pipeline.get('status')!=result['status']
            or protocol.get('source_study')!=study.relative_to(ROOT).as_posix() or protocol.get('frames')!=window.frames
            or protocol.get('fps')!=30 or protocol.get('pose_dim')!=window.pose_dim
            or protocol.get('inequality_labels')!=window.labels or protocol.get('original_limits')!=limits
            or any(doc.get('quality_approved') is not False or doc.get('release_approved') is not False for doc in [protocol,result,pipeline])):
        raise ValueError('Terminal unapproved window with identical source/frames/rows/clock and budgets required')
    old=protocol.get('inputs_sha256',{})
    if any(old.get(path)!=digest for path,digest in original_bindings.items()):raise ValueError('Original window inputs differ')
    checked={}
    def bind(path,digest):
        path=Path(path).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha256(path)!=digest:raise ValueError('Window resume binding differs')
        checked[str(path)]=digest
    for path,digest in old.items():bind(path,digest)
    expected=set(methods);archived=protocol.get('methods_sha256',{})
    if set(archived) not in [expected,expected-{'window_restoration_resume.py'}]:raise ValueError('Complete archived window methods required')
    for name,digest in archived.items():bind(directory/'implementation'/name,digest)
    if protocol.get('native_metadata_sha256')!=sha256(definitions):raise ValueError('Window native metadata differs')
    bind(directory/'implementation/kimodo-skeleton-definitions.py',protocol['native_metadata_sha256'])
    bind(directory/'protocol.json',result['protocol_sha256']);bind(directory/'window.npz',result['motion_sha256'])
    bind(directory/'row-diagnostics.json',result['row_diagnostics_sha256'])
    for name in ['result.json','pipeline.json']:checked[str(directory/name)]=sha256(directory/name)
    report=result['fit'];mask=np.asarray(report['tradeoff_mask']);baseline=np.asarray(report['initial_slacks'],dtype=float)
    size=len(window.labels);scale=window.scale
    lower=np.tile(np.r_[np.full(window.pose_dim-1,-1.),0.],len(window.frames));upper=np.ones(window.dim)
    def controls(value):
        z=np.asarray(value,dtype=float)
        if z.shape!=(window.dim,) or not np.isfinite(z).all() or np.any(z<lower) or np.any(z>upper):
            raise ValueError('Complete original bounded window controls required')
        return z
    if (mask.shape!=(size,) or mask.dtype!=bool or mask.any() or report['tradeoff_mask']!=protocol['tradeoff_mask']
            or baseline.shape!=(size,) or not np.isfinite(baseline).all()):raise ValueError('Complete preserved window rows required')
    for field,value in [('failure_policy','merit'),('proposal','nonlinear'),('proposal_start','geometry-descent'),
            ('proposal_priority','worst-first'),('proposal_tangent_guard',True)]:
        if report.get(field)!=value or protocol.get(field)!=value:raise ValueError('Window proposal/retention policy differs')
    if protocol.get('archive_proposals') is not True:raise ValueError('Complete streamed window reports required')
    fallback=protocol.get('proposal_margin_fallback',False)
    if type(fallback) is not bool or report.get('proposal_margin_fallback',False) is not fallback:
        raise ValueError('Bound window margin-search policy required')
    if any(protocol.get(field)!='preserve' for field in ['point_policy','normal_policy','object_policy']):
        raise ValueError('Window point/normal/object policy differs')
    point_rows=[label.startswith('point:') for label in window.labels]
    headroom=proposal_headroom(window.labels,point=1e-5,normal=1e-3,object=1e-3,body=1e-3).tolist()
    if (protocol['proposal_feasible_mask']!=point_rows or report['proposal_feasible_mask']!=point_rows
            or protocol['proposal_headroom_normalized']!=headroom or report['proposal_headroom_normalized']!=headroom):
        raise ValueError('Original window proposal masks/margins differ')
    edges=[dict(frame=p.frame,neighbor=f,neighbor_edited=f in window.frames) for p in window.problems for f in p.neighbors]
    if protocol.get('temporal_edges')!=edges:raise ValueError('Original edited/fixed temporal edges differ')
    def record(reference,kind):
        if reference.get('kind')!=kind or 'archive_schema' not in reference:raise ValueError('Bound streamed window record required')
        value,extra=load_record(directory,reference)
        for path,digest in extra.items():bind(path,digest)
        return value
    for reference in report['proposal_starts']:
        value=record(reference,'start')
        if value.get('retained') is not False or value.get('priority')!='worst-first':raise ValueError('Window LP start cannot be promoted')
        if ('margin_factor' in value) is not fallback:raise ValueError('Window margin history differs from its policy')
        if fallback:
            matching=[r for r in report['proposal_linearizations'] if r['iteration']==reference['iteration']]
            if len(matching)!=1:raise ValueError('Complete margin-origin linearization required')
            linear=record(matching[0],'linearization');current=np.asarray(linear['slacks'])
            floor=np.minimum(current,0);floor[point_rows]=np.maximum(floor[point_rows],0)
            caps=np.maximum(floor+headroom,np.minimum(current,0)+1e-6)
            np.testing.assert_array_equal(value['margin_floor_caps'],floor)
            for attempt in margin_start_attempts(value):
                np.testing.assert_array_equal(attempt['caps'],floor+attempt['margin_factor']*(caps-floor))
    for reference in report['proposal_linearizations']:record(reference,'linearization')
    # Drop the last hydrated start before recursively loading predecessor history.
    value=None
    origin=window.seed.copy();prior=protocol.get('window_resume');poses=protocol.get('resumes',[])
    if prior is not None:
        if poses:raise ValueError('Window and individual-pose predecessors are mutually exclusive')
        origin,_,_,extra=resume_window(ROOT/prior['directory'],study,window,original_bindings,limits,methods,definitions,pose_resume,
            ancestors=ancestors+(directory,))
        if extra.get(str((ROOT/prior['directory']/'result.json').resolve()))!=prior['result_sha256']:
            raise ValueError('Window ancestor result differs')
        checked.update(extra)
    else:
        seen=set()
        for pose in poses:
            frame=pose['frame']
            if type(frame) is not int or frame not in window.frames or frame in seen:raise ValueError('Unique original pose predecessors required')
            seen.add(frame);index=window.frames.index(frame);problem=window.problems[index]
            labels,_=tradeoff_policy(problem.labels,[problem.names[j] for j in problem.editable])
            pose_limits={key:value for key,value in limits[index].items() if key!='frame'}
            parameters,_,receipt,extra=pose_resume(ROOT/pose['directory'],study,frame,original_bindings,pose_limits,labels,problem)
            if receipt['result_sha256']!=pose['result_sha256']:raise ValueError('Original pose predecessor differs')
            origin[index*window.pose_dim:(index+1)*window.pose_dim]=parameters;checked.update(extra)
    controls(origin/scale)
    observations={}
    print(dict(stage='window_resume_replaying',observations=len(result['observations'])),flush=True)
    for entry in result['observations']:
        label=entry['label']
        if not isinstance(label,str) or Path(label).name!=label or label in observations:raise ValueError('Unique local window observations required')
        trial=directory/'trials'/label;audit=read(trial/'audit.json')
        bind(trial/'audit.json',entry['audit_sha256']);bind(trial/'window.npz',audit['motion_sha256'])
        if (audit['label']!=label or audit['retained'] is not entry['retained']
                or audit.get('quality_approved') is not False or audit.get('release_approved') is not False):
            raise ValueError('Window observation classification differs')
        parameters=controls(np.asarray(audit['parameters'])/scale)*scale
        with torch.no_grad():measured=window.geometry_slack(torch.as_tensor(parameters,dtype=torch.float64)).numpy()
        np.testing.assert_allclose(measured,audit['solver_slacks'],rtol=1e-10,atol=1e-10)
        actual,motion=window.independent(parameters)
        if actual!=audit['candidate']:raise ValueError('Window observation physical audit differs')
        with np.load(trial/'window.npz',allow_pickle=False) as saved:
            if set(saved.files)!=set(motion):raise ValueError('Complete native window arrays required')
            for key in motion:
                if saved[key].dtype!=motion[key].dtype or saved[key].shape!=motion[key].shape:raise ValueError('Window array precision/shape differs')
                np.testing.assert_allclose(saved[key],motion[key],rtol=0,atol=2e-6)
        observations[label]=audit
        if len(observations)%16==0:print(dict(stage='window_resume_replayed',observations=len(observations)),flush=True)
    np.testing.assert_allclose(observations['seed']['parameters'],origin,rtol=0,atol=1e-12)
    np.testing.assert_array_equal(observations['seed']['solver_slacks'],baseline)
    before=baseline.copy();last=origin/scale;retained={'final'};cached=None
    for trial in report['trials']:
        if trial.get('nonlinear_replay') is False:
            if trial['accepted']:raise ValueError('Unmeasured window proposal cannot be retained')
            continue
        audit=observations[trial['label']];after=np.asarray(audit['solver_slacks']);z=controls(trial['controls'])
        np.testing.assert_allclose(audit['parameters'],z*scale,rtol=0,atol=1e-12)
        if np.any(np.abs(z-last)>protocol['trust_normalized']+1e-12):raise ValueError('Window backoff exceeded its declared trust bounds')
        if cached is None or cached['iteration']!=trial['iteration']:
            references=[r for r in report['proposal_linearizations'] if r['iteration']==trial['iteration']]
            if len(references)!=1:raise ValueError('Unique complete window linearization required')
            cached=record(references[0],'linearization')
        jac=np.asarray(cached['jacobian']);ids=np.arange(size)
        if jac.shape!=(size,window.dim) or not np.isfinite(jac).all():raise ValueError('Complete finite window tangent rows required')
        np.testing.assert_array_equal(cached['protected_rows'],ids);np.testing.assert_array_equal(cached['slacks'],before)
        np.testing.assert_allclose(cached['controls'],last,rtol=0,atol=1e-12)
        np.testing.assert_array_equal(cached['preservation_caps'],np.minimum(before,0))
        np.testing.assert_array_equal(cached['tangent_proposal_caps'],np.minimum(before,0)+1e-6)
        keep=retain(before,after,failure_policy='merit',tradeoff_mask=mask)
        tangent=bool(np.all(before+jac@(z-last)>=np.minimum(before,0)))
        if (trial['retention_guard_passed'] is not keep or trial['tangent_guard_passed'] is not tangent
                or trial['accepted'] is not (keep and tangent) or audit['retained'] is not (keep and tangent)):
            raise ValueError('Window retained decision differs from complete replay')
        np.testing.assert_allclose(trial['score'],score(after),rtol=0,atol=1e-12)
        if keep and tangent:before=after;last=z;retained.add(trial['label'])
    if any(audit['retained'] is not (label in retained) for label,audit in observations.items()):raise ValueError('Unaccepted window record cannot be promoted')
    for query in report['proposal_queries']:
        audit=observations[query['label']]
        if query['retained'] is not False or audit['retained'] is not False:raise ValueError('Inner window query cannot be retained')
        np.testing.assert_allclose(query['controls'],np.asarray(audit['parameters'])/scale,rtol=0,atol=1e-12)
        np.testing.assert_allclose(query['score'],score(audit['solver_slacks']),rtol=0,atol=1e-12)
    parameters=controls(np.asarray(result['parameters'])/scale)*scale
    np.testing.assert_allclose(parameters,last*scale,rtol=0,atol=1e-12)
    np.testing.assert_allclose(parameters,observations['final']['parameters'],rtol=0,atol=1e-12)
    np.testing.assert_array_equal(before,report['final_slacks']);np.testing.assert_array_equal(before,observations['final']['solver_slacks'])
    if np.any(before<np.minimum(baseline,0)):raise ValueError('Window lost a passing/protected source row')
    if read(directory/'row-diagnostics.json')!=row_diagnostics(window.labels,baseline,before,mask):raise ValueError('Window diagnostics differ')
    actual,motion=window.independent(parameters)
    if actual!=result['candidate'] or actual!=observations['final']['candidate']:raise ValueError('Terminal window audit differs')
    with np.load(directory/'window.npz',allow_pickle=False) as saved:
        if set(saved.files)!=set(motion):raise ValueError('Complete terminal window required')
        for key in motion:
            if saved[key].dtype!=motion[key].dtype or saved[key].shape!=motion[key].shape:raise ValueError('Terminal array precision/shape differs')
            np.testing.assert_allclose(saved[key],motion[key],rtol=0,atol=2e-6)
    print(dict(stage='window_resume_verified',directory=directory.relative_to(ROOT).as_posix()),flush=True)
    return parameters,motion,dict(directory=directory.relative_to(ROOT).as_posix(),result_sha256=checked[str(directory/'result.json')],
        replayed_observations=len(observations),replayed_backoffs=len(report['trials']),original_references_preserved=True,
        scope='Bound retained diagnostic window; original budgets and exterior keys unchanged. No quality approval.'),checked
