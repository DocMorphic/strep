"""Export-aware root correction shared by callers that own immutable exports.

The inspect callback must export each proposal and return its measured slacks,
serialized constraint rows and body flags. No action names, paths, engine clocks
or quality approvals are assumed by this module.
"""
from numbers import Real
import numpy as np
from linear_feasibility_restore import linear_step

def rate_layout(p):
    blocks={};offset=sum((r['last_frame']-r['first_frame'])*4+1 for r in p.position.rows)
    for order in [1,2]:
        for i,(row,masks,caps,scales) in enumerate(zip(p.point_rate.rows,p.masks,p.point_rate.ceilings,p.point_rate.scales)):
            n=int(masks[order-1].sum());rate=np.diff(p.rate_points[:,row['point']],n=order,axis=0)*120**order
            horizontal=float(np.linalg.norm(rate[masks[order-1]][:,[0,2]],axis=1).max())
            blocks[f'point_rate:{i}:{order}']=dict(bounds=[offset,offset+n],cap=float(caps[order-1]),scale=float(scales[order-1]),horizontal=horizontal,index=i,order=order)
            offset+=n
        n=len(p.joints)-order;rate=np.diff(p.joints,n=order,axis=0)*120**order
        blocks[f'global_rate:{order}']=dict(bounds=[offset,offset+n],cap=float(p.global_rate.ceilings[order-1]),scale=float(p.global_rate.scales[order-1]),horizontal=float(np.linalg.norm(rate[...,[0,2]],axis=-1).max()),order=order)
        offset+=n
    assert offset+len(p.heights)==len(p.evaluate(p.start,False)[0])
    return blocks

def exported_measurements(audit_result,blocks):
    peaks={};slacks={}
    for key,g in blocks.items():
        peak=(audit_result['phase_rates'][g['index']]['variants']['candidate'][g['order']-1] if 'index' in g else
          max(r[['peak_speed_m_s','peak_acceleration_m_s2'][g['order']-1]] for r in audit_result['variants']['candidate']['joints']))
        peaks[key]=peak;slacks[key]=(g['cap']-peak)/g['scale']
    for i,row in enumerate(audit_result['contacts']):slacks['pin:'+str(i)]=(.005-row['maximum_error_m'])/.005
    slacks['floor']=-audit_result['floor_nonregression']['maximum_added_depth_m']/.001
    errors=audit_result['preservation']['all_outside_times']['maximum_errors']
    slacks['outside']=-max(errors.values())
    return peaks,slacks

def strengthen(target,values,blocks,peaks,slacks,requirements,margin_fraction):
    updated=target.copy();notes=[]
    for key,g in blocks.items():
        if slacks[key]>=0:continue
        a,b=g['bounds'];proxy=g['cap']-g['scale']*float(values[a:b].min())
        discrepancy=max(requirements.get(key,{}).get('discrepancy',0.),(peaks[key]-proxy)/g['scale']);capacity=(g['cap']-g['horizontal'])/g['scale']
        if capacity<=discrepancy:
            notes.append(dict(group=key,changed=False,reason='No horizontal room beyond observed discrepancy',capacity=capacity,discrepancy=discrepancy));continue
        requirements[key]=dict(discrepancy=discrepancy,optional=min(1e-4,.5*(capacity-discrepancy)))
        margin=discrepancy+margin_fraction*requirements[key]['optional']
        prior=float(target[a:b].max());updated[a:b]=max(prior,margin)
        notes.append(dict(group=key,changed=margin>prior,previous_target=prior,target=float(updated[a:b].max()),proxy_peak=proxy,export_peak=peaks[key],capacity=capacity,discrepancy=discrepancy))
    return updated,notes


def checked_evidence(evidence, expected_keys=None, expected_shape=None):
    """Reject incomplete/nonfinite observations before selecting a proposal."""
    slacks = evidence.get('slacks')
    if not isinstance(slacks, dict) or not slacks:
        raise ValueError('Nonempty exported constraint measurements required')
    if any(not isinstance(k, str) or not k or isinstance(v, bool) or
           not isinstance(v, Real) or not np.isfinite(v) for k, v in slacks.items()):
        raise ValueError('Finite named export slacks required')
    if expected_keys is not None and slacks.keys() != expected_keys:
        raise ValueError('Export constraint groups changed between proposals')
    serial = np.asarray(evidence.get('serial'))
    if serial.ndim != 1 or not serial.size or serial.dtype.kind not in 'fi' or not np.isfinite(serial).all():
        raise ValueError('Finite nonempty serialized constraint rows required')
    if expected_shape is not None and serial.shape != expected_shape:
        raise ValueError('Serialized constraint rows changed between proposals')
    flags = evidence.get('flags')
    if not isinstance(flags, list) or any(not isinstance(flag, str) or not flag for flag in flags):
        raise ValueError('Explicit body flag list required')
    return serial


def acceptance(current, candidate):
    """A numerical improvement may retain failures; it never approves quality."""
    old = checked_evidence(current)
    new = checked_evidence(candidate, current['slacks'].keys(), old.shape)
    regressions = [k for k, value in current['slacks'].items()
                   if value >= 0 and candidate['slacks'][k] < 0]
    serial_ok = bool((new[old >= 0] >= 0).all())
    body_ok = not (set(candidate['flags'])-set(current['flags']))
    old_min, new_min = min(current['slacks'].values()), min(candidate['slacks'].values())
    improves = new_min > old_min
    if old_min >= 0:
        improves = bool(new_min >= 0 and new.min() > old.min())
    return dict(export_regressions=regressions, serialized_passing_rows_preserved=serial_ok,
                body_flags_preserved=body_ok, export_slacks=dict(candidate['slacks']),
                export_worst_strictly_improved=bool(improves),
                accepted=bool(not regressions and serial_ok and body_ok and improves))


def repair(problem, inspect, *, attempts=8, backtracks=4, trust=1e-5, progress=None):
    """Return the last accepted export and a serializable numerical report.

    inspect(coordinates, label) owns full export/reload and original-budget checks.
    It must retain every proposal, including rejected ones, and provide `peaks`,
    `slacks`, `serial` and `flags` measured against the same immutable references.
    Any inspection exception propagates; a failed export cannot become a pass.
    """
    for name, value in [('attempts', attempts), ('backtracks', backtracks)]:
        if type(value) is not int or value < 1:
            raise ValueError(name+' must be a positive integer')
    if isinstance(trust, bool) or not isinstance(trust, Real) or not np.isfinite(trust) or trust <= 0:
        raise ValueError('Positive finite trust distance required')
    fractions = [1., .1, .01, .001, 0.]
    blocks = rate_layout(problem)
    x = problem.start.copy()
    values, _, _ = problem.evaluate(x)
    target = np.zeros_like(values)
    current = inspect(x.copy(), 'restored-seed')
    checked_evidence(current)
    initial_slacks = dict(current['slacks'])
    requirements, history = {}, []
    margin_index = 0
    target, initial_targets = strengthen(target, values, blocks, current['peaks'],
                                         current['slacks'], requirements, fractions[margin_index])
    for iteration in range(attempts):
        if min(current['slacks'].values()) >= 0 and np.min(current['serial']) >= 0:
            break
        values, jacobian, _ = problem.evaluate(x)
        residual = values-target
        margin_trials = []
        while True:
            delta, info = linear_step(x, residual, jacobian, problem.bounds, trust=trust, margin=0.)
            margin_trials.append(dict(optional_fraction=fractions[margin_index], result=dict(info)))
            if delta is not None or margin_index == len(fractions)-1:
                break
            margin_index += 1
            target = np.zeros_like(target)
            for key, need in requirements.items():
                a, b = blocks[key]['bounds']
                target[a:b] = need['discrepancy']+fractions[margin_index]*need['optional']
            residual = values-target
        info.update(iteration=iteration+1, optional_margin_trials=margin_trials, trials=[])
        accepted = changed = False
        if delta is not None:
            for backtrack in range(backtracks):
                fraction = .5**backtrack
                trial = x+fraction*delta
                constraints, _, _ = problem.evaluate(trial, False)
                native_ok = bool(np.isfinite(constraints).all() and
                                 (constraints[values >= 0] >= 0).all() and
                                 np.all(np.abs(trial) <= problem.bounds) and
                                 (constraints-target).min() > residual.min())
                record = dict(fraction=fraction, native_proposal_passed=native_ok,
                              minimum_original_slack=float(constraints.min()),
                              minimum_target_slack=float((constraints-target).min()), accepted=False)
                if native_ok:
                    label = f'trial-{iteration+1}-{backtrack}'
                    inspected = inspect(trial.copy(), label)
                    record.update(acceptance(current, inspected), export_label=label)
                    new_target, notes = strengthen(target, constraints, blocks, inspected['peaks'],
                                                   inspected['slacks'], requirements, fractions[margin_index])
                    record['feedback'] = notes
                    changed = bool(np.any(new_target > target))
                    target = new_target
                    if record['accepted']:
                        x, current, accepted = trial, inspected, True
                    info['trials'].append(record)
                    if accepted or changed:
                        break
                else:
                    info['trials'].append(record)
        info.update(accepted=accepted, targets_strengthened=changed)
        history.append(info)
        if progress:
            progress(info)
        if not accepted and not changed:
            break
    report = dict(history=history, initial_targets=initial_targets, initial_slacks=initial_slacks,
                  final_coordinates=x.tolist(), maximum_root_step_m=float(np.abs(x-problem.start).max()),
                  serialized_minimum_slack=float(np.min(current['serial'])),
                  final_export_slacks=dict(current['slacks']), requirements=requirements,
                  optional_margin_fraction=fractions[margin_index],
                  export_and_native_screen=bool(min(current['slacks'].values()) >= 0 and
                                               np.min(current['serial']) >= 0), quality_approved=False)
    return x, current, report
