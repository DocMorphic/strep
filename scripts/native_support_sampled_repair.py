"""Bounded corridor refinement checked against independently decoded GLBs.

Targets finite samples, not continuous feasibility, planted soles or physics.
Original authored constraints and final source-rate selection remain unchanged.
"""
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from native_support_path import propose as smooth_propose,bend_box,restrict_box
from native_support_skin import NativeSupportSkin
from native_leg_floor import foot_region
from contact_rate_path import ProjectedSkin
from native_support_clock import NativeSupportSampler
from native_engine_clock import audit_clock
from paired_temporal_neighbor import rotation_channels
from rig_asset import RigAsset
from strep import save,sha256


def neighbors(clock,time):
    """Exact keys own their sample; fractional samples touch both neighbors."""
    i=int(np.searchsorted(clock,time,side='left'))
    if i<len(clock) and float(clock[i])==time:return [i]
    return [k for k in (i-1,i) if 0<=k<len(clock)]


def tighten(data,observations,limits,fraction=1.):
    if not np.isfinite(fraction) or not 0<fraction<=1:raise ValueError('Bounded tightening fraction required')
    result={}
    for d,o in zip(data,observations):
        row=d['row'];lo,hi=[v.copy() for v in limits[row['id']]]
        lower=np.zeros(len(lo));upper=lower.copy();radius=lower.copy()
        for time,height in zip(o['stance_times'],o['heights']):
            ids=neighbors(d['clock'],float(time))
            if height < -1e-8:
                lower[ids]=np.maximum(lower[ids],row['clearance']-height)
            if height > row['maximum_height']:
                upper[ids]=np.maximum(upper[ids],height-(row['maximum_height']-.00025))
        for time,movement in zip(o['edit_times'],o['movement']):
            if movement>row['displacement']+1e-7:
                ids=neighbors(d['clock'],float(time))
                radius[ids]=np.maximum(radius[ids],movement-row['displacement']+2.5e-7)
        maximum=np.maximum(abs(lo),abs(hi))-fraction*radius
        lo=np.maximum(lo+fraction*lower,-maximum)
        hi=np.minimum(hi-fraction*upper,maximum)
        # A required change at a frozen endpoint is infeasible, not permission
        # to alter the source boundary or silently drop that constraint.
        restrict_box(d['box'],lo,hi)
        result[row['id']]=(lo,hi)
    return result


def improving(new,old):
    return new[0]<old[0]-1e-12 or abs(new[0]-old[0])<=1e-12 and new[1]<old[1]-1e-12


def propose(rig,reader,rows,path,acceleration_time=.05,reference_weight=.5,*,iterations=8):
    from pathlib import Path
    path=Path(path)
    if type(iterations) is not int or not 1<=iterations<=16:raise ValueError('Choose 1–16 sampled support iterations')
    if path.exists() or any(path.parent.glob(path.stem+'-support-*')):raise ValueError('Fresh sampled support output required')
    channels=rotation_channels(rig.document,rig.binary);skin=NativeSupportSkin(rig)
    uniform=np.arange(int(np.floor(reader.duration*120))+1)/120
    times=audit_clock(reader.duration,[c[2] for c in reader.channels],
        uniform.tolist()+[t for r in rows for t in r['stance_s']+r['edit_s']],rows[0]['stance_s'][0])
    raw=np.array([reader.sample(float(t)) for t in times]);data=[];limits={}
    for row in rows:
        first,last=row['edit_keys'];clock=row['clock'][first:last+1]
        worlds=np.array([reader.sample(float(t)) for t in clock])
        projection=ProjectedSkin(skin,foot_region(skin,rig.parents,row['chain'][-1]),row['up'],row['offset'])
        box=bend_box(worlds,rig.parents,row['chain'],projection.evaluate(worlds).min(axis=1),clock,row)
        data.append(dict(row=row,clock=clock,projection=projection,box=box))
        limits[row['id']]=(box['lower_lift'].copy(),box['upper_lift'].copy())
    def observe(candidate):
        asset=RigAsset.load(candidate);current=NativeSupportSampler(asset.document,asset.binary,0)
        if current.duration!=reader.duration:raise ValueError('Repair changed native duration')
        world=np.array([current.sample(float(t)) for t in times])
        updated=rotation_channels(asset.document,asset.binary);observations=[];excess=[]
        for d in data:
            r=d['row'];stance=(times>=r['stance_s'][0])&(times<=r['stance_s'][1])
            edit=(times>=r['edit_s'][0])&(times<=r['edit_s'][1]);node=r['chain'][-1]
            heights=d['projection'].evaluate(world[stance]).min(axis=1)
            movement=np.linalg.norm(world[edit,node,:3,3]-raw[edit,node,:3,3],axis=1)
            a,b=r['edit_keys']
            angles=np.concatenate([np.rad2deg((Rotation.from_quat(channels[n][2][a:b+1]).inv()*Rotation.from_quat(updated[n][2][a:b+1])).magnitude()) for n in r['chain']])
            v=np.r_[np.maximum(0,-heights-1e-8)/.001,
                np.maximum(0,heights-r['maximum_height'])/.001,
                np.maximum(0,movement-r['displacement']-1e-7)/.001,
                np.maximum(0,angles-r['angle']-1e-4)]
            excess.extend(v)
            observations.append(dict(id=r['id'],stance_times=times[stance],heights=heights,
                edit_times=times[edit],movement=movement,
                minimum_height_m=float(heights.min()),maximum_lowest_height_m=float(heights.max()),
                maximum_ankle_displacement_m=float(movement.max()),maximum_local_angle_degrees=float(angles.max())))
        if not np.isfinite(excess).all():raise ValueError('Nonfinite decoded support constraints')
        return observations,(float(max(excess,default=0)),float(np.sum(excess)))
    def summary(o):return [{k:v for k,v in row.items() if k not in ('stance_times','heights','edit_times','movement')} for row in o]
    seed=path.with_name(path.stem+'-support-seed.glb')
    smooth_propose(rig,reader,rows,seed,acceleration_time,reference_weight)
    observed,score=observe(seed);initial=score;best=seed;history=[]
    for step in range(iterations):
        if score[0]==0:break
        accepted=False
        for fraction in (1.,.5,.25,.125):
            trial=path.with_name(f'{path.stem}-support-step-{step}-{fraction:g}.glb')
            record=dict(step=step,fraction=fraction,status='rejected',previous_score=list(score))
            try:
                candidate_limits=tighten(data,observed,limits,fraction)
                record['lift_limits_m']={name:dict(lower=lo.tolist(),upper=hi.tolist()) for name,(lo,hi) in candidate_limits.items()}
                if all(np.array_equal(a,c) and np.array_equal(b,d) for (a,b),(c,d) in zip(limits.values(),candidate_limits.values())):
                    raise ValueError('No available corridor tightening for decoded violations')
                smooth_propose(rig,reader,rows,trial,acceleration_time,reference_weight,lift_limits=candidate_limits)
                observation,new_score=observe(trial)
                record.update(file=trial.name,sha256=sha256(trial),score=list(new_score),supports=summary(observation))
                if improving(new_score,score):
                    best,observed,score,limits=trial,observation,new_score,candidate_limits
                    accepted=True;record['status']='accepted'
                else:record['reason']='Decoded support excess did not improve'
            except ValueError as exc:record['reason']=str(exc)
            history.append(record)
            save(trial.with_suffix('.json'),record)
            if accepted:break
        if not accepted:break
    shutil.copyfile(best,path)
    report=dict(method='serialized_sampled_support_corridor_refinement',iterations_limit=iterations,
        seed_file=seed.name,seed_sha256=sha256(seed),initial_score=list(initial),final_score=list(score),
        selected_proposal_file=best.name,selected_proposal_sha256=sha256(best),sample_times=len(times),
        sampled_support_pass=score[0]==0,supports=summary(observed),history=history,
        scope='Original bounds retained; only native lift corridors restricted. Independently decoded finite support samples, not source rates, continuous collision, force, planted soles or naturalness.',quality_approved=False)
    save(path.with_name(path.stem+'-support-repair.json'),report)
    return [report]
