"""Bounded native-row recourse; complete decoded retention remains authoritative."""
from pathlib import Path
import re
import numpy as np
from scipy import sparse
from audit_native_key_initializer import require
from native_scene_contacts import fields
from native_scene_norms import NormRows
from native_scene_conic import direction
from strep import read,save,sha256


def validate(config,primary_trust):
    fields(config,('attempts_per_iteration','trust','normalized_reserve','maximum_failed_rows'),'cached native recourse')
    require(type(config['attempts_per_iteration']) is int and 1<=config['attempts_per_iteration']<=4,'Choose 1-4 cached repair attempts per iteration')
    require(type(config['maximum_failed_rows']) is int and 1<=config['maximum_failed_rows']<=64,'Choose 1-64 failed native rows for recourse')
    for key,lo,hi in [('trust',1e-6,min(.001,primary_trust)),('normalized_reserve',1e-8,.01)]:
        require(type(config[key]) in (int,float) and np.isfinite(config[key]) and lo<=config[key]<=hi,'Finite bounded recourse '+key+' required')
    return config


def search_model(before,candidate,edit_count,config):
    """Protect every native row; reserve is dimensionless times its own scale."""
    old,new=before['norms'],candidate['norms']
    np.testing.assert_array_equal(old.caps,new.caps)
    np.testing.assert_array_equal(old.scales,new.scales)
    require(old.vectors.shape==new.vectors.shape and type(edit_count) is int and 0<=edit_count<=len(new.caps),'Complete unchanged native row population required')
    caps=new.caps.copy()
    caps[edit_count:]=np.maximum(caps[edit_count:],np.linalg.norm(old.vectors[edit_count:],axis=1))
    bad=np.flatnonzero(np.linalg.norm(new.vectors,axis=1)>caps)
    details=dict(violating_rows=bad.tolist(),native_rows=len(caps),eligible=bool(0<len(bad)<=config['maximum_failed_rows']))
    # No weakening, row truncation or rounding allowance. These tightened caps
    # guide the search only; original acceptance and source caps stay intact.
    if not details['eligible']:return None,details
    caps[bad]-=config['normalized_reserve']*new.scales[bad]
    details['search_caps'] = caps[bad].tolist()
    return NormRows(new.vectors,caps,new.scales),details


def probe_label(label):
    return type(label) is str and (label in ('start','final') or re.fullmatch(r'[1-9][0-9]*-[0-9]+(?:-repair)?',label) is not None)


def attempt(problem,before,candidate,iteration_folder,output,config):
    """One cached solve, one full export at most; retain every failed attempt."""
    from native_key_interval_restoration import evaluate,retain
    model,details=search_model(before,candidate,problem.edit_count,config)
    require(details['eligible'],'Only eligible native violations may consume repair budget')
    folder=Path(iteration_folder);output=Path(output)
    require(not output.exists(),'Fresh separate repair attempt required');output.mkdir(parents=True)
    native=model.vectors.size
    with np.load(folder/'affine-system.npz',allow_pickle=False) as anchor:
        np.testing.assert_array_equal(anchor['value'],before['record']['controls'])
        np.testing.assert_array_equal(anchor['vectors'][:len(model.caps)],before['norms'].vectors)
        np.testing.assert_array_equal(anchor['scales'][:len(model.caps)],before['norms'].scales)
    jac=sparse.load_npz(folder/'affine-jacobian.npz')[:native]
    value=np.asarray(candidate['record']['controls'],float)
    delta,info=direction(model,jac,value,problem.lower,problem.upper,config['trust'],hard_rows=len(model.caps))
    del model,jac
    save(output/'solver.json',info)
    record=dict(**details,anchor_label=before['record']['label'],candidate_label=candidate['record']['label'],
        affine_jacobian_sha256=sha256(folder/'affine-jacobian.npz'),solver_sha256=sha256(output/'solver.json'),
        solver_status=info['status'],controls_sha256=None,label=None,accepted=False)
    repaired=None
    if delta is not None:
        raw_delta=delta.copy();delta=np.clip(raw_delta,-config['trust'],config['trust'])
        other=np.clip(value+delta,problem.lower,problem.upper)
        np.savez_compressed(output/'controls.npz',before=value,raw_delta=raw_delta,delta=delta,after=other)
        record['controls_sha256']=sha256(output/'controls.npz')
        repaired=evaluate(problem,other,output.parents[2]/'probes'/(candidate['record']['label']+'-repair'))
        record.update(label=repaired['record']['label'],accepted=retain(before,repaired))
    save(output/'attempt.json',record)
    return record,repaired


def replay_history(problem,recipe,producer,history,fresh,initial,retain):
    """Replay all primary/repair choices without solving or rebuilding a Jacobian."""
    producer=Path(producer);selected=fresh['start'];value=np.asarray(initial,float).copy();visited={'start','final'}
    np.testing.assert_array_equal(selected['record']['controls'],value)
    for number,entry in enumerate(history,1):
        iteration=entry['iteration'];require(type(iteration) is int and iteration==number<=recipe['iterations'],'Ordered bounded original iteration required')
        enabled='native_recourse' in recipe
        fields(entry,('iteration','accepted_fraction','probes','solver_status')+(('selected_label',) if enabled else ()),'iteration history')
        choices=entry['probes'];require(len(choices)<=recipe['backoffs'],'Original backoff budget exceeded');accepted=None;chosen=None;attempts=0
        anchor=selected
        for index,choice in enumerate(choices):
            fields(choice,('label','fraction','accepted')+(('recourse',) if enabled else ()),'primary probe history')
            label=choice['label'];require(label==f'{iteration}-{index}' and label in fresh and label not in visited,'Complete ordered iteration probe required');visited.add(label)
            require(choice['fraction']==.5**index,'Original backoff fraction changed')
            with np.load(producer/'iterations'/str(iteration)/'direction.npz',allow_pickle=False) as data:delta=data['delta']
            expected=np.clip(value+choice['fraction']*delta,problem.lower,problem.upper)
            np.testing.assert_array_equal(fresh[label]['record']['controls'],expected)
            actual=retain(anchor,fresh[label]);require(choice['accepted'] is actual,'Decoded retention decision changed')
            if actual:chosen=label;accepted=choice['fraction']
            if enabled:
                repairs=choice['recourse'];require(isinstance(repairs,list) and len(repairs)<=1 and not (actual and repairs),'At most one repair per rejected primary probe')
                for repair in repairs:
                    attempts+=1;require(attempts<=recipe['native_recourse']['attempts_per_iteration'],'Cached repair budget exceeded')
                    path=producer/'iterations'/str(iteration)/('repair-'+str(index))
                    require(read(path/'attempt.json')==repair,'Recorded repair attempt changed')
                    fields(repair,('violating_rows','native_rows','eligible','search_caps','anchor_label','candidate_label',
                        'affine_jacobian_sha256','solver_sha256','solver_status','controls_sha256','label','accepted'),'cached repair history')
                    _,details=search_model(anchor,fresh[label],problem.edit_count,recipe['native_recourse'])
                    require(details['eligible'] and all(repair[k]==v for k,v in details.items()),'Repair search limits changed')
                    require(repair['anchor_label']==anchor['record']['label'] and repair['candidate_label']==label,'Repair anchor changed')
                    require(sha256(path.parent/'affine-jacobian.npz')==repair['affine_jacobian_sha256']
                        and sha256(path/'solver.json')==repair['solver_sha256'],'Repair model or solver archive changed')
                    info=read(path/'solver.json');require(info['status']==repair['solver_status'],'Repair solver status changed')
                    if repair['label'] is None:
                        require(repair['controls_sha256'] is None and repair['accepted'] is False and not (path/'controls.npz').exists(),'Unreturned repair cannot select controls')
                    else:
                        target=label+'-repair';require(repair['label']==target and target in fresh and target not in visited,'Complete distinct repair export required');visited.add(target)
                        require(sha256(path/'controls.npz')==repair['controls_sha256'],'Repair controls changed')
                        with np.load(path/'controls.npz',allow_pickle=False) as data:
                            require(set(data.files)=={'before','raw_delta','delta','after'},'Complete cached repair controls required')
                            np.testing.assert_array_equal(data['before'],expected)
                            require(data['raw_delta'].shape==expected.shape and np.isfinite(data['raw_delta']).all(),'Finite complete solver repair delta required')
                            np.testing.assert_array_equal(data['delta'],np.clip(data['raw_delta'],-recipe['native_recourse']['trust'],recipe['native_recourse']['trust']))
                            d=data['delta'];require(d.shape==expected.shape and np.isfinite(d).all()
                                and np.all(abs(d)<=recipe['native_recourse']['trust']+1e-15),'Repair exceeds its trust budget')
                            other=np.clip(expected+d,problem.lower,problem.upper)
                            np.testing.assert_array_equal(data['after'],other)
                            np.testing.assert_array_equal(fresh[target]['record']['controls'],other)
                        decision=retain(anchor,fresh[target]);require(repair['accepted'] is decision,'Decoded repair retention changed')
                        if decision:chosen=target;accepted=choice['fraction']
            if chosen is not None:
                require(index==len(choices)-1,'Search continued after accepted primary or repair')
                selected=fresh[chosen];value=np.asarray(selected['record']['controls'],float)
        require(entry['accepted_fraction']==accepted,'Accepted iteration fraction changed')
        if enabled:require(entry['selected_label']==chosen,'Selected primary or repaired clip changed')
    require(visited==set(fresh),'Returned probe missing from retention history')
    return value
