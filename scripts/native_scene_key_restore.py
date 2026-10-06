"""Bounded native-only restoration anchored to complete decoded assets.

All original norms are hard in each local solve. This repairs native feasibility,
not geometry, transitions or motion quality; callers retain independent audits.
The decode callback must export and read every selected actor and retain probes.
Existing jobs and acceptance rules are unchanged.
"""
import numpy as np
from native_scene_norms import rows,linearize
from native_scene_conic import direction
from native_support_feasibility import merit


def restore(problem,start,decode,*,steps=3,trust=.0001,difference_step=1e-5):
    if (type(steps) is not int or not 1<=steps<=4
            or type(trust) not in (int,float) or not np.isfinite(trust) or not 1e-6<=trust<=.02
            or type(difference_step) not in (int,float) or not np.isfinite(difference_step)
            or not 1e-6<=difference_step<=.01 or not callable(decode)):
        raise ValueError('Bounded explicit native-key restoration settings required')
    value=problem.edits.controls(start).copy();history=[];radius=float(trust)
    if np.any(value<problem.lower) or np.any(value>problem.upper):
        raise ValueError('Restoration start must lie within original control boxes')
    original=rows(problem,value);caps=original.caps.copy();scales=original.scales.copy()
    def observe(other,label):
        reported,worlds=decode(other.copy(),label)
        if not isinstance(worlds,dict) or set(worlds)!=set(problem.scene.actors):
            raise ValueError('Complete decoded actor population required')
        for name,actor in problem.scene.actors.items():
            expected=(len(problem.times),len(actor['rig'].parents),4,4)
            if np.shape(worlds[name])!=expected or not np.isfinite(worlds[name]).all():
                raise ValueError('Complete finite decoded native worlds required')
        current=problem.constraints(other,worlds)
        if not np.array_equal(reported,current):
            raise ValueError('Decoded residual differs from unchanged native conditions')
        system=rows(problem,other,worlds)
        if not np.array_equal(system.caps,caps) or not np.array_equal(system.scales,scales):
            raise ValueError('Original native caps, scales or population changed')
        np.testing.assert_allclose(system.residual(),current,atol=1e-9,rtol=1e-12)
        return current,worlds
    current,worlds=observe(value,'start')
    initial_merit=list(merit(current))
    for iteration in range(steps):
        if np.all(current<=0):break
        system,jac,identity=linearize(problem,value,step=difference_step,difference_source='continuous',
            difference_scheme='central',base_worlds=worlds)
        if not np.array_equal(system.caps,caps) or not np.array_equal(system.scales,scales):
            raise ValueError('Restoration model changes original native norms')
        np.testing.assert_allclose(system.residual(),current,atol=1e-9,rtol=1e-12)
        delta,solver=direction(system,jac,value,problem.lower,problem.upper,radius,hard_rows=len(caps))
        record=dict(iteration=iteration,anchor_controls=value.tolist(),before=list(merit(current)),
            trust=radius,differences=identity,solver=solver,all_native_norms_hard=True,probes=[])
        history.append(record)
        if delta is None:break
        best=None;before=merit(current)
        for fraction in (1.,.5,.25,.125):
            other=np.clip(value+fraction*delta,problem.lower,problem.upper)
            label=f'restore-{iteration}-{fraction}'
            residual,decoded=observe(other,label);score=merit(residual);passed=bool(np.all(residual<=0))
            record['probes'].append(dict(label=label,fraction=fraction,controls=other.tolist(),merit=list(score),
                failed_native_rows=int((residual>0).sum()),native_conditions_pass=passed))
            improves=score[0]<before[0]-1e-12 or abs(score[0]-before[0])<=1e-12 and score[1]<before[1]-1e-15
            if passed or improves and (best is None or tuple(score)<tuple(best[3])):
                best=(other,residual,decoded,score,label)
            if passed:break
        if best is not None:
            value,current,worlds,_,label=best
            record.update(selected_native_anchor=label,after=list(merit(current)))
        else:
            radius*=.25;record.update(selected_native_anchor=None,after=list(merit(current)))
            if radius<1e-6:break
    return value,dict(schema='strep-native-scene-key-restore-v1',history=history,
        original_norm_rows=len(caps),initial_merit=initial_merit,final_merit=list(merit(current)),
        native_conditions_pass=bool(np.all(current<=0)),failed_native_rows=int((current>0).sum()),
        original_native_caps_scales_unchanged=True,geometry_assessed=False,
        quality_approved=False,release_approved=False,
        scope='Bounded local recentered native feasibility restoration with complete decoded anchors and all original norms protected. '
            'Every observed probe is rechecked against original conditions. No native-key insertion, changed acceptance, '
            'cumulative external-reference, geometry, transition, engine or animation-quality approval.')
