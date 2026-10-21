"""Pinned optimizer stages for the existing bounded mesh-character correction.

Worker APIs: run through resource admission and the shared worker lock. A
geometry checkpoint alone never commits an optimizer decision or selects a clip.
"""
import copy
import os
from pathlib import Path
import shutil
import uuid
import numpy as np
from threadpoolctl import threadpool_limits
import native_mesh_character_fit as fit
import native_mesh_geometry_journal as geometry
from native_geometry_journal import require,local,fresh_json,runtime
from action_worker_lock import worker_verification_lock as worker_lock
from strep import ROOT,read,save,sha256

METHODS=tuple(sorted(set(fit.METHODS)|set(geometry.METHODS)|{'native_mesh_character_recovery.py'}))
PHASES={'original','geometry','initialize','direction','proposal','decision','complete'}
TRANSITIONS=dict(original={'geometry'},geometry={'initialize','decision'},initialize={'direction'},
    direction={'proposal','complete'},proposal={'geometry','decision'},decision={'proposal','direction','complete'},complete=set())


def immutable_json(path,value):
    """Publish a complete new value, or verify an interrupted prior publication."""
    path=Path(path)
    if path.exists():
        require(read(path)==value,'Existing optimizer artifact differs')
        return
    temporary=path.parent/(path.name+'.assembly-'+uuid.uuid4().hex)
    fresh_json(temporary,value)
    os.link(temporary,path)
    temporary.unlink()


def problem_for(permissions,policy_path):
    problem=fit.MeshCharacterProblem(permissions)
    policy,digest=fit._json(Path(policy_path))
    times,_,_=problem.mesh._clock(policy)
    combined=np.unique(np.r_[problem.times,times])
    require(len(combined)<=10000 and len(combined)*sum(len(a['rig'].parents) for a in problem.scene.actors.values())*16*8<=128*1024**2,
            'Complete geometry/character clock exceeds memory budget; no samples dropped')
    fit.include_times(problem,times)
    return problem,policy,digest,times


def signature(problem,times):
    return dict(initial=problem.initial.tolist(),lower=problem.lower.tolist(),upper=problem.upper.tolist(),
        protected_rows=problem.protected_rows,contact_clock_s=problem.times.tolist(),geometry_clock_s=times.tolist())


def pin(folder,state,path):
    path=Path(path).resolve();relative=path.relative_to(folder).as_posix()
    digest=sha256(path)
    require(relative not in state['files'] or state['files'][relative]==digest,'Committed optimizer artifact changed')
    state['files'][relative]=digest
    return relative


def publish(folder,state,previous):
    state['step']=0 if previous is None else state['step']+1
    state['previous']=None if previous is None else dict(checkpoint=previous['checkpoint'],sha256=previous['sha256'])
    target=folder/'checkpoints'/f"{state['step']:06d}-{uuid.uuid4().hex}.json"
    fresh_json(target,state)
    receipt=dict(checkpoint=target.relative_to(folder).as_posix(),sha256=sha256(target),phase=state['phase'],
        optimizer_completed=state['phase']=='complete',quality_approved=False,release_approved=False)
    save(folder/'progress.json',receipt)
    return receipt


def seal_geometry(folder,state,journal,receipt,complete):
    """Bind exact files just validated by finalization, without copying arrays."""
    request=read(journal/'request.json');files={'request.json':sha256(journal/'request.json')}
    files.update({snapshot['path']:snapshot['sha256'] for snapshot in request['source_snapshots'].values()})
    files.update({'implementation/'+name:digest for name,digest in request['implementation_sha256'].items()})
    cursor=receipt
    while True:
        path=local(journal,cursor['checkpoint']);require(sha256(path)==cursor['sha256'],'Geometry checkpoint changed before sealing')
        files[cursor['checkpoint']]=cursor['sha256'];row=read(path)
        if row['frame'] is not None:
            entry=row['frame'];relative=entry['directory']+'/receipt.json';files[relative]=entry['receipt_sha256']
            require(sha256(local(journal,relative))==files[relative],'Geometry frame changed before sealing')
            files.update({entry['directory']+'/'+name:digest for name,digest in read(local(journal,relative))['files_sha256'].items()})
        if row['previous'] is None:break
        cursor=row['previous']
    require(all(sha256(local(journal,name))==digest for name,digest in files.items()),'Finalized geometry file changed')
    path=complete/'journal-seal.json'
    fresh_json(path,dict(schema='strep-complete-geometry-file-seal-v1',files_sha256=files,
        checkpoint=receipt['checkpoint'],checkpoint_sha256=receipt['sha256'],request_sha256=files['request.json']))
    return pin(folder,state,path)


def prepare(permissions,policy,folder,*,iterations=4,trust=.02,backtracks=8):
    require(type(iterations) is int and 1<=iterations<=16 and type(backtracks) is int and 1<=backtracks<=12,
            'Choose 1-16 iterations and 1-12 backtracks')
    require(type(trust) in (float,int) and np.isfinite(trust) and 0<trust<=.25,'Choose a positive trust fraction at most .25')
    permissions,policy,folder=[Path(p).resolve() for p in (permissions,policy,folder)]
    require(not folder.exists(),'Fresh optimizer journal required')
    with worker_lock(),threadpool_limits(limits=1):
        problem,spec,digest,times=problem_for(permissions,policy)
        inputs={**problem.inputs,str(policy):digest}
        require(all(not Path(p).is_relative_to(folder) for p in inputs),'Optimizer journal contains an input')
        methods={name:sha256(ROOT/'scripts'/name) for name in METHODS}
        folder.mkdir(parents=True)
        for name in ('checkpoints','work','implementation','input'):(folder/name).mkdir()
        for name in methods:shutil.copyfile(ROOT/'scripts'/name,folder/'implementation'/name)
        snapshots={}
        for i,(path,value) in enumerate(inputs.items()):
            target=folder/'input'/f'{i}{Path(path).suffix}';shutil.copyfile(path,target)
            require(sha256(target)==value,'Input snapshot differs')
            snapshots[path]=dict(path=target.relative_to(folder).as_posix(),sha256=value)
        request=dict(schema='strep-native-mesh-character-recovery-v1',permissions=str(permissions),policy=str(policy),
            inputs_sha256=inputs,implementation_sha256=methods,input_snapshots=snapshots,runtime=runtime(),solver=fit.solver_identity(),
            iterations=iterations,trust=trust,backtracks=backtracks,original_signature=signature(problem,times),
            original_selected=True,quality_approved=False,release_approved=False)
        fresh_json(folder/'request.json',request)
        state=dict(schema='strep-native-mesh-character-state-v1',request_sha256=sha256(folder/'request.json'),phase='original',
            files={},journals={},current=None,pending=None,direction=None,original_geometry=None,
            selected=None,iteration=0,backoff=0,history=[],probes=[],stop_reason=None,
            original_selected=True,quality_approved=False,release_approved=False)
        check_request(folder,request)
        return publish(folder,state,None)


def check_request(folder,request):
    require(request['schema']=='strep-native-mesh-character-recovery-v1' and request['original_selected'] is True
            and request['quality_approved'] is False and request['release_approved'] is False,'Original recovery request required')
    require(request['runtime']==runtime() and request['solver']==fit.solver_identity(),'Numerical runtime or solver changed')
    require(set(request['implementation_sha256'])==set(METHODS),'Complete optimizer method closure required')
    require(all(sha256(ROOT/'scripts'/name)==digest==sha256(folder/'implementation'/name)
        for name,digest in request['implementation_sha256'].items()),'Optimizer implementation changed')
    require(set(request['input_snapshots'])==set(request['inputs_sha256']),'Complete optimizer input snapshots required')
    for path,digest in request['inputs_sha256'].items():
        snapshot=request['input_snapshots'][path]
        require(sha256(path)==digest==snapshot['sha256']==sha256(local(folder,snapshot['path'])),'Original optimizer input changed')


def load(folder,checkpoint,expected_sha256):
    request=read(folder/'request.json');binding=sha256(folder/'request.json')
    check_request(folder,request)
    path=local(folder,checkpoint);rows=[];seen=set()
    while True:
        require(path not in seen and sha256(path)==expected_sha256,'Optimizer checkpoint changed or cyclic chain')
        seen.add(path);state=read(path);rows.append(state)
        require(state['schema']=='strep-native-mesh-character-state-v1' and state['request_sha256']==binding
            and state['phase'] in PHASES and state['original_selected'] is True
            and state['quality_approved'] is False and state['release_approved'] is False,'Pinned optimizer state required')
        require(type(state['step']) is int and 0<=state['step']<=1024,'Bounded optimizer stage number required')
        if state['previous'] is None:break
        require(len(rows)<=1025,'Optimizer checkpoint chain exceeds stage bound')
        expected_sha256=state['previous']['sha256'];path=local(folder,state['previous']['checkpoint'])
    require([row['step'] for row in reversed(rows)]==list(range(len(rows))) and rows[-1]['phase']=='original',
            'Complete ordered optimizer state chain required')
    ordered=list(reversed(rows))
    for before,after in zip(ordered,ordered[1:]):
        require(after['phase'] in TRANSITIONS[before['phase']],'Invalid optimizer phase transition')
        require(all(after['files'].get(name)==digest for name,digest in before['files'].items()),
                'A committed optimizer artifact was removed or rebound')
        require(after['probes'][:len(before['probes'])]==before['probes']
            and len(after['probes'])-len(before['probes'])==(1 if before['phase']=='decision' else 0),
            'Optimizer decisions must commit exactly once')
        require(after['history'][:len(before['history'])]==before['history'],'Committed optimizer history changed')
        for name,entry in before['journals'].items():
            require(name in after['journals'] and all(after['journals'][name].get(k)==v for k,v in entry.items()),
                    'Committed geometry binding changed')
    state=rows[0]
    require(all(sha256(local(folder,path))==digest for path,digest in state['files'].items()),'Committed optimizer artifact changed')
    for relative,entry in state['journals'].items():
        journal=local(folder,relative)
        require(sha256(journal/'request.json')==entry['request_sha256'],'Geometry request changed')
        receipt=read(journal/'progress.json')
        if 'complete' in entry:
            require(all(receipt[k]==v for k,v in entry['complete'].items()),
                    'A committed complete geometry population was rolled back')
            seal=read(local(folder,entry['seal']))
            require(seal['schema']=='strep-complete-geometry-file-seal-v1'
                and seal['request_sha256']==entry['request_sha256']
                and seal['checkpoint']==receipt['checkpoint'] and seal['checkpoint_sha256']==receipt['sha256']
                and all(sha256(local(journal,name))==digest for name,digest in seal['files_sha256'].items()),
                'Previously validated complete geometry files changed')
            continue
        geometry.verify(journal,receipt['checkpoint'],receipt['sha256'])
        cursor=receipt
        while True:
            row=read(local(journal,cursor['checkpoint']))
            if row['previous'] is None:break
            cursor=row['previous']
        require(cursor['checkpoint']==entry['genesis']['checkpoint'] and cursor['sha256']==entry['genesis']['sha256'],
                'Geometry prefix must descend from the optimizer-pinned genesis')
    problem,policy,digest,times=problem_for(request['permissions'],request['policy'])
    require({**problem.inputs,request['policy']:digest}==request['inputs_sha256']
        and signature(problem,times)==request['original_signature'],'Original problem or bounds changed')
    return request,state,problem,policy


def data_write(folder,state,directory,controls,residual,worlds):
    path=directory/'optimizer-arrays.npz'
    np.savez_compressed(path,controls=controls,residual=residual,**{'world_'+name:value for name,value in worlds.items()})
    return pin(folder,state,path)


def data_read(folder,item):
    with np.load(local(folder,item['data']),allow_pickle=False) as data:
        return data['controls'],data['residual'],{name[6:]:data[name] for name in data.files if name.startswith('world_')}


def begin_geometry(folder,state,scene,policy,directory):
    audit=directory/'geometry';audit.mkdir()
    spec=copy.deepcopy(policy);spec['mesh_scene_sha256']=scene._manifest_sha256
    fresh_json(audit/'geometry-policy.json',spec)
    receipt=geometry.prepare(scene._manifest_path,audit/'geometry-policy.json',audit/'geometry-journal')
    journal=audit/'geometry-journal'
    state['journals'][journal.relative_to(folder).as_posix()]=dict(request_sha256=sha256(journal/'request.json'),genesis=receipt)
    for path in (audit/'geometry-policy.json',journal/'request.json',journal/receipt['checkpoint']):pin(folder,state,path)
    return dict(audit=audit.relative_to(folder).as_posix(),scene=str(scene._manifest_path.resolve()))


def terminal(state,residual,geometry_report,reason):
    if np.all(residual<=0):reason='contacts_pass' if geometry_report['sampled_conditions_pass'] else 'contacts_pass_geometry_unresolved'
    state['stop_reason']=reason;state['phase']='complete'


def advance(folder,checkpoint,expected_sha256):
    """Commit at most one optimizer stage; interrupted geometry keeps its frames."""
    folder=Path(folder).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        latest=read(folder/'progress.json')
        require(latest['checkpoint']==checkpoint and latest['sha256']==expected_sha256,
                'Advance requires the current pinned optimizer checkpoint; no rollback')
        request,state,problem,policy=load(folder,checkpoint,expected_sha256)
        require(state['phase']!='complete','Optimizer already complete')
        previous=dict(checkpoint=checkpoint,sha256=expected_sha256)
        phase=state['phase'];state=copy.deepcopy(state)
        if phase=='original':
            directory=folder/'work'/('original-'+uuid.uuid4().hex);directory.mkdir()
            contact,arrays=problem.mesh.contact_audit()
            fresh_json(directory/'contacts.json',contact);np.savez_compressed(directory/'contact-observations.npz',**arrays)
            residual=problem.model(problem.initial)
            require(not np.any(residual[:problem.protected_rows]>0),'Original native source conditions must pass')
            data=data_write(folder,state,directory,problem.initial,residual,problem.source_world)
            contacts=pin(folder,state,directory/'contacts.json');pin(folder,state,directory/'contact-observations.npz')
            state['pending']=dict(role='original',data=data,contacts=contacts,
                **begin_geometry(folder,state,problem.mesh,policy,directory))
            state['phase']='geometry'
        elif phase=='geometry':
            pending=state['pending'];audit=local(folder,pending['audit']);journal=audit/'geometry-journal'
            receipt=read(journal/'progress.json')
            checked=geometry.verify(journal,receipt['checkpoint'],receipt['sha256'])
            if not checked['population_complete']:
                while True:
                    receipt=geometry.advance(journal,receipt['checkpoint'],receipt['sha256'],maximum_samples=4096)
                    if receipt['population_complete']:break
            # Any assembly abandoned before the outer checkpoint remains
            # uncommitted. Reassemble from the pinned frames, never trust a
            # self-asserted geometry result found after a crash.
            complete=audit/('complete-'+uuid.uuid4().hex)
            result=geometry.finalize(journal,receipt['checkpoint'],receipt['sha256'],complete,materialize_observations=False)
            require(sha256(complete/'geometry.json')==result['geometry_sha256']
                and sha256(complete/'observations-index.json')==result['observation_index_sha256'], 'Complete indexed geometry required')
            pending['geometry']=pin(folder,state,complete/'geometry.json')
            for path in (complete/'result.json',complete/'observations-index.json'):pin(folder,state,path)
            entry=state['journals'][journal.relative_to(folder).as_posix()]
            entry['complete']={k:receipt[k] for k in ('checkpoint','sha256')}
            entry['seal']=seal_geometry(folder,state,journal,receipt,complete)
            state['phase']='initialize' if pending['role']=='original' else 'decision'
        elif phase=='initialize':
            state['current']={name:state['pending'][name] for name in ('data','contacts','geometry')}
            state['original_geometry']=state['current']['geometry'];state['pending']=None;state['phase']='direction'
        elif phase=='direction':
            value,current,worlds=data_read(folder,state['current']);report=read(local(folder,state['current']['geometry']))
            if np.all(current<=0) or state['iteration']>=request['iterations']:
                terminal(state,current,report,'iteration_limit')
            else:
                system,jacobian,differences=fit.linearize(problem,value,step=.001,maximum_elements=16_000_000,
                    difference_source='continuous',base_worlds=worlds,difference_scheme='central')
                np.testing.assert_allclose(system.residual(),current,atol=1e-9,rtol=1e-12)
                guarded,derivative,guard=fit.protect_rows(system,jacobian,problem.protected_rows,current[problem.protected_rows:])
                guarded,derivative,hard,floor=fit.add_floor_guards(problem,value,worlds,policy,report,guarded,derivative,guard['hard_rows'],request['trust'])
                delta,solver=fit.direction(guarded,derivative,value,problem.lower,problem.upper,request['trust'],hard_rows=hard)
                record=dict(iteration=state['iteration'],differences=differences,solver=solver,contact_protection=guard,floor_protection=floor,accepted_probe=None)
                if delta is None:
                    state['history'].append(record);terminal(state,current,report,'no_guarded_direction')
                else:
                    directory=folder/'work'/('direction-'+uuid.uuid4().hex);directory.mkdir()
                    np.savez_compressed(directory/'delta.npz',delta=delta)
                    state['direction']=dict(data=pin(folder,state,directory/'delta.npz'),record=record)
                    state['backoff']=0;state['phase']='proposal'
        elif phase=='proposal':
            value,current,worlds=data_read(folder,state['current'])
            with np.load(local(folder,state['direction']['data']),allow_pickle=False) as data:delta=data['delta']
            proposed=value+delta*(.5**state['backoff']);directory=folder/'work'/('probe-'+uuid.uuid4().hex)
            candidate,residual,decoded_worlds,audits=problem.write(proposed,directory)
            row=dict(probe=len(state['probes']),iteration=state['iteration'],fraction=.5**state['backoff'],
                source_rows_pass=bool(np.all(residual[:problem.protected_rows]<=0)),
                strict_edit_caps_pass=all(a['passed'] and a['strict_edit_caps_pass'] for a in audits.values()),
                contact_rows_no_worse=bool(np.all(fit.row_regression(current[problem.protected_rows:],residual[problem.protected_rows:])<=0)),
                contact_merit_improves=fit.merit(residual)<fit.merit(current),geometry_evaluated=False,accepted=False,
                original_selected=True,quality_approved=False,release_approved=False)
            contact,arrays=candidate.contact_audit();fresh_json(directory/'contacts.json',contact)
            np.savez_compressed(directory/'contact-observations.npz',**arrays)
            row['all_declared_point_contacts_pass']=contact['all_declared_point_contacts_pass']
            data=data_write(folder,state,directory,proposed,residual,decoded_worlds)
            for path in directory.iterdir():
                if path.is_file():pin(folder,state,path)
            pending=dict(role='proposal',row=row,data=data,contacts=pin(folder,state,directory/'contacts.json'),
                directory=directory.relative_to(folder).as_posix())
            eligible=all(row[name] for name in ('source_rows_pass','strict_edit_caps_pass','contact_rows_no_worse','contact_merit_improves'))
            if eligible:pending.update(begin_geometry(folder,state,candidate,policy,directory))
            state['pending']=pending;state['phase']='geometry' if eligible else 'decision'
        elif phase=='decision':
            pending=state['pending'];row=pending['row']
            if 'geometry' in pending:
                checked=read(local(folder,pending['geometry']));flags=fit.conditions(checked);measure=fit.metrics(checked)
                original=fit.conditions(read(local(folder,state['original_geometry'])))
                current=read(local(folder,state['current']['geometry']));old_flags=fit.conditions(current);old_metrics=fit.metrics(current)
                require(flags.keys()==original.keys(),'Geometry condition population changed')
                no_new=not any(old_flags[key] and not flags[key] for key in flags)
                no_worse=all(measure[key]<=old_metrics[key] for key in measure)
                depth_check=fit.compare_depths(current,checked)
                depth_path=local(folder,pending['directory'])/'local-depth-regression.json'
                immutable_json(depth_path,depth_check);pin(folder,state,depth_path)
                row.update(geometry_evaluated=True,geometry_conditions_pass=checked['sampled_conditions_pass'],
                    geometry_conditions_no_regression=no_new,geometry_metrics_no_worse=no_worse,geometry_metrics=measure,
                    geometry_local_depths_pass=depth_check['passed'],local_depth_regressions=len(depth_check['regressions']),
                    local_depth_unavailable=len(depth_check['unavailable']),maximum_local_depth_increase_m=depth_check['maximum_increase_m'],
                    accepted=bool(no_new and no_worse and depth_check['passed']))
            directory=local(folder,pending['directory']);immutable_json(directory/'decision.json',row);pin(folder,state,directory/'decision.json')
            state['probes'].append(row)
            if row['accepted']:
                state['current']={name:pending[name] for name in ('data','contacts','geometry')}
                state['selected']=pending['directory'];state['direction']['record']['accepted_probe']=row['probe']
            state['backoff']+=1
            if row['accepted'] or state['backoff']>=request['backtracks']:
                state['history'].append(state['direction']['record']);state['iteration']+=1
                if row['accepted']:state['phase']='direction'
                else:
                    _,current,_=data_read(folder,state['current'])
                    terminal(state,current,read(local(folder,state['current']['geometry'])),'no_decoded_nonregressing_step')
                state['direction']=None
            else:state['phase']='proposal'
            state['pending']=None
        if state['phase']=='complete':
            _,current,_=data_read(folder,state['current']);report=read(local(folder,state['current']['geometry']))
            result=dict(status='complete',stop_reason=state['stop_reason'],candidate=state['selected'],
                accepted_steps=sum(row['accepted'] for row in state['probes']),probes=len(state['probes']),final_contact_merit=list(fit.merit(current)),
                all_native_and_contact_rows_pass=bool(np.all(current<=0)),sampled_geometry_pass=report['sampled_conditions_pass'],
                sampled_candidate_pass=bool(state['selected'] is not None and np.all(current<=0) and report['sampled_conditions_pass']
                    and read(local(folder,state['current']['contacts']))['all_declared_point_contacts_pass']),
                source_rebased=False,props_changed=False,original_selected=True,checkpoint_geometry=True,optimizer_completed=True,
                engine_verified=False,quality_approved=False,release_approved=False,
                scope='Complete pinned optimizer stages using the existing bounded proposal and decoded acceptance. No new collision guidance, continuous collision, dynamics, engine, semantic or animator approval.')
            immutable_json(folder/'result.json',result);pin(folder,state,folder/'result.json')
            immutable_json(folder/'probes.json',state['probes']);pin(folder,state,folder/'probes.json')
            immutable_json(folder/'history.json',state['history']);pin(folder,state,folder/'history.json')
        check_request(folder,request);problem.check_inputs()
        require(sha256(local(folder,checkpoint))==expected_sha256 and sha256(folder/'request.json')==state['request_sha256'],
                'Optimizer anchor changed during stage')
        require(read(folder/'progress.json')==latest,'Optimizer head changed during stage')
        return publish(folder,state,previous)


def verify(folder,checkpoint,expected_sha256):
    folder=Path(folder).resolve()
    with worker_lock(),threadpool_limits(limits=1):
        _,state,_,_=load(folder,checkpoint,expected_sha256)
        return dict(phase=state['phase'],committed_steps=state['step'],committed_probes=len(state['probes']),
            optimizer_completed=state['phase']=='complete',original_selected=True,quality_approved=False,release_approved=False)


def finish(folder,checkpoint,expected_sha256,*,maximum_stages=1024):
    require(type(maximum_stages) is int and 1<=maximum_stages<=1024,'Bounded optimizer stage count required')
    receipt=dict(checkpoint=checkpoint,sha256=expected_sha256)
    for _ in range(maximum_stages):
        # advance performs the full binding/chain check itself. Inspecting this
        # field only chooses which verifier to call; it never approves a state.
        if read(local(Path(folder).resolve(),receipt['checkpoint']))['phase']=='complete':
            verify(folder,receipt['checkpoint'],receipt['sha256'])
            return receipt
        receipt=advance(folder,receipt['checkpoint'],receipt['sha256'])
    return receipt
