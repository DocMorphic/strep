"""Serial actual-engine ownership fixtures on two native animated rigs/props.

Procedural software fixtures only; no character reconstruction, mocap, model,
GPU renderer, anatomical acceptance or human-quality evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import numpy as np
from scipy.spatial.transform import Rotation
from action_worker_lock import worker_lock
from native_engine_clock import clock_wire,clock_echo_matches
from object_release import ENGINE
from object_geometry import Geometry
from release_geometry import floor_gaps,preview_penetration_bounds,check_installed_geometry
from scene_prop_ownership import compile_plan
from strep import ROOT,now,read,save,sha256
from scene_commit_receipts import audit as audit_commit_receipts

GDS=['godot_scene_prop_ownership_audit.gd','godot_scene_prop_owner.gd','godot_scene_prop_body.gd',
     'godot_native_scene_player.gd','godot_native_root_adapter.gd','godot_native_object_player.gd',
     'godot_scene_game_events.gd','native_engine_clock.gd','native_godot_preview.gd','godot_native_scene_observations.gd']
METHODS=GDS+['study_scene_prop_ownership.py','scene_prop_ownership.py','scene_commit_receipts.py','native_engine_clock.py','object_geometry.py','release_geometry.py','primitive_penetration_bounds.py','action_worker_lock.py','strep.py']


def fixture():
    times=np.array([0.,.2,.6,1.,1.305,2.])
    entries=[('grab','A',1),('other','B',1),('partial','A',2),('giver','A',3),('receiver','B',3),('drop','B',4)]
    events=[dict(id=i,name=i,actor=a,kind='gameplay_intent',sample_index=n,timing_confirmed=True,runtime_dispatch_allowed=True) for i,a,n in entries]
    doc=dict(schema='strep-native-scene-game-events-v1',clock=clock_wire(times),events=events)
    grips={n:dict(actor=a) for n,a in [('AL','A'),('AR','A'),('BL','B'),('BR','B')]}
    commands=[dict(event_id=e,object=o,grip=g,action=a) for e,o,g,a in [('grab','P','AL','acquire'),('grab','P','AR','acquire'),('other','Q','BR','acquire'),
        ('partial','P','AL','release'),('giver','P','AR','release'),('receiver','P','BL','acquire'),('drop','P','BL','release'),('drop','Q','BR','release')]]
    plan=compile_plan(doc,['P','Q'],grips,commands)
    return doc,plan


def reference(id,time):
    phase=max(0.,time-.2);p=np.array([-.7,1.5,0])+phase*np.array([.4,.1,0]);r=Rotation.from_rotvec([0,.3*phase,0]).as_matrix()
    if id=='Q':
        keys=np.arange(61)/30;phase_keys=np.maximum(keys-.2,0);angle=.3*phase_keys
        matrices=Rotation.from_rotvec(np.c_[np.zeros(61),angle,np.zeros(61)]).as_matrix()
        separation=np.c_[1.4-.8*phase_keys,np.zeros(61),np.zeros(61)]
        local=np.einsum('fji,fj->fi',matrices,separation)+[-.2,0,0]
        sampled=np.array([np.interp(time,keys,local[:,axis]) for axis in range(3)])
        p=p+r@(sampled+[.2,0,0])
    result=np.eye(4);result[:3,:3]=r;result[:3,3]=p;return result


def observed_matrix(value):
    """Native observations store four Vector3 columns, unlike pose packets."""
    columns=np.asarray(value,dtype=float)
    if columns.shape!=(4,3) or not np.isfinite(columns).all():raise ValueError('Complete native matrix columns required')
    result=np.eye(4);result[:3,:3]=columns[:3].T;result[:3,3]=columns[3];return result


def verify(request,actual):
    rows=[]
    if len(actual['cases'])!=len(request['cases']):raise ValueError('Complete case population required')
    for case,observed in zip(request['cases'],actual['cases']):
        assert case['id']==observed['id'] and observed['malformed_rejected']==5 and observed['second_owner_rejected']
        records=observed['records'];actions=observed['actions'];fault=case.get('fault','')
        commit_check=audit_commit_receipts(case['plan'],{'A':'embedded','B':'extracted'},observed,physics_fps=request['physics_fps'])
        if fault:
            assert len(observed['faults'])==1
            assert all(not a['last_grip_released'] for a in actions)
            rows.append(dict(id=case['id'],fault_detected=True,fault=observed['faults'][0],records=len(records),commit_check=commit_check,quality_approved=False));continue
        assert observed['faults']==[] and observed['expired_preview_rejected']
        # Six prop transactions per traversal: acquire P/Q, partial P, handoff
        # P, release P/Q. Their exact count is checked below against the plan.
        expected=[(g['time_s'],t['object'],t['before'],t['after']) for g in case['plan']['groups'] for t in g['transitions']]
        assert len(actions)==len(expected)*2
        for id,geometry in {'P':Geometry('cylinder',(.15,.4)),'Q':Geometry('sphere',(.15,))}.items():check_installed_geometry(geometry,observed['installed_geometry'][id])
        assert [e['id'] for e in observed['source_events']]==[e['id'] for e in case['events']['events']]*2
        assert all(clock_echo_matches(e['time_s'],e['pose_time_s']) for e in observed['source_events'])
        pose_errors=[];velocity_errors=[];spin_errors=[];delays=[]
        for session in (0,1):
            selected=[a for a in actions if a['session']==session]
            assert [(a['object'],a['before'],a['after']) for a in selected]==[e[1:] for e in expected]
            assert all(clock_echo_matches(e[0],a['source_time_s']) for e,a in zip(expected,selected))
            for a in selected:
                pose_errors.append(float(np.abs(np.array(a['pose'])-reference(a['object'],a['source_time_s'])).max()))
                assert a['application_delay_s']>=-1e-12 and a['application_delay_s']<1/request['physics_fps']+1e-12
                delays.append(a['application_delay_s'])
                if a['last_grip_released']:
                    prior=max(r['source_time_s'] for r in records if r['session']==session and r['transport']=='live' and r['source_time_s']<a['source_time_s'])
                    p0=reference(a['object'],prior);p1=reference(a['object'],a['source_time_s']);dt=a['source_time_s']-prior
                    velocity_errors.append(float(np.linalg.norm(np.array(a['velocity'])-(p1[:3,3]-p0[:3,3])/dt)))
                    spin=Rotation.from_matrix(p1[:3,:3]@p0[:3,:3].T).as_rotvec()/dt
                    spin_errors.append(float(np.linalg.norm(np.array(a['spin'])-spin)))
        assert max(pose_errors)<=3e-5 and max(velocity_errors)<=1e-3 and max(spin_errors)<=1e-3
        assert all(r['history_size']<=80 for r in records)
        held_errors=[];root_errors=[];previous_roots={n:np.eye(4) for n in ('A','B')}
        for r in records:
            assert set(r['props'])=={'P','Q'} and set(r['scene']['actors'])=={'A','B'}
            assert clock_echo_matches(r['source_time_s'],r['scene']['pose_time_s'])
            assert set(r['physics_root_deltas'])=={'A','B'}
            for actor,a in r['scene']['actors'].items():
                current=observed_matrix(a['root_motion']);before=previous_roots[actor]
                expected_delta=np.linalg.inv(before)@current if r['transport']=='live' and r['command'] not in ('restart','resume') else np.eye(4)
                # A preview does not change the last forward roots.
                if r['transport']=='live':previous_roots[actor]=current
                root_errors.append(float(np.abs(np.array(r['physics_root_deltas'][actor])-expected_delta).max()))
            for id,p in r['props'].items():
                assert abs(p['step_s']-1/request['physics_fps'])<1e-9 and abs(p['inverse_mass']-.5)<1e-6
                assert p['direct_state_class']=='JoltPhysicsDirectBodyState3D'
                geometry=Geometry('cylinder',(.15,.4)) if id=='P' else Geometry('sphere',(.15,))
                np.testing.assert_allclose(p['inverse_inertia'],1/np.diag(geometry.uniform_inertia(2.)),atol=1e-7,rtol=1e-6)
                if r['transport']=='live' and r['modes'][id]=='held':held_errors.append(float(np.abs(np.array(p['pose'])-reference(id,r['source_time_s'])).max()))
                if r['transport']!='live' or r['modes'][id]!='released':assert p['collision_layer']==p['collision_mask']==0
        assert max(held_errors)<=3e-5
        if root_errors:assert max(root_errors)<=3e-5
        for id in ('P','Q'):
            old=observed['live_before_preview']['props'][id];restored=observed['restored']['props'][id]
            for field in ('pose','velocity','spin'):np.testing.assert_allclose(restored[field],old[field],atol=1e-7,rtol=0)
        live=[r for r in records if r['session']==0 and r['transport']=='live']
        assert any('Q' in r['props']['P']['contacts'] or 'P' in r['props']['Q']['contacts'] for r in live)
        released={a['object']:np.array(a['velocity']) for a in actions if a['session']==0 and a['last_grip_released']}
        contacts=[r for r in live if 'Q' in r['props']['P']['contacts'] or 'P' in r['props']['Q']['contacts']]
        assert all(any(abs(r['props'][id]['velocity'][0]-released[id][0])>.01 for r in contacts) for id in ('P','Q'))
        floor_depth={};geometries={'P':Geometry('cylinder',(.15,.4)),'Q':Geometry('sphere',(.15,))}
        bounds=[]
        for id in ('P','Q'):
            transforms=np.array([r['props'][id]['pose'] for r in live]);gaps=floor_gaps(geometries[id],transforms[:,:3,3],transforms[:,:3,:3]);floor_depth[id]=float(max(0.,-gaps.min()))
            assert any('floor' in r['props'][id]['contacts'] for r in live)
        for r in live:
            p,q=np.array(r['props']['P']['pose']),np.array(r['props']['Q']['pose'])
            bounds.append(preview_penetration_bounds(geometries['P'],p[:3,3],Rotation.from_matrix(p[:3,:3]).as_matrix(),geometries['Q'],q[:3,3],Rotation.from_matrix(q[:3,:3]).as_matrix()))
        max_depth=max(b['penetration_upper_m'] for b in bounds)
        rows.append(dict(id=case['id'],records=len(records),actions=len(actions),commit_check=commit_check,held_pose_error=max(held_errors),action_pose_error=max(pose_errors),release_velocity_error_m_s=max(velocity_errors),release_spin_error_rad_s=max(spin_errors),whole_step_root_error=max(root_errors) if root_errors else None,both_dynamic_props_respond_to_contact=True,max_application_delay_s=max(delays),exact_physical_event_timing_passed=all(abs(x)<=1e-12 for x in delays),
                         max_floor_penetration_m=floor_depth,max_interprop_penetration_upper_m=max_depth,discrete_collision_depth_screens_passed=max_depth<=.01 and max(floor_depth.values())<=.01,all_checked_ownership_conditions_passed=True,quality_approved=False,release_approved=False))
    return dict(schema='strep-scene-prop-ownership-study-v1',status='complete',cases=rows,actual_native_actors=True,actual_dynamic_props=True,renderer_executed=False,human_reviewed=False,quality_approved=False,release_approved=False)


def study(output,rate):
    output=Path(output).resolve()
    if not output.is_relative_to((ROOT/'reports').resolve()) or rate not in (60,120,240):raise ValueError('Fresh report path and supported physics rate required')
    with worker_lock():
        output.mkdir(parents=True,exist_ok=False);project=output/'project';project.mkdir()
        hashes={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        methods=output/'methods';methods.mkdir()
        for n in METHODS:shutil.copyfile(ROOT/'scripts'/n,methods/n)
        for n in GDS:shutil.copyfile(ROOT/'scripts'/n,project/n)
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Shared prop ownership audit"\n[physics]\ncommon/physics_ticks_per_second='+str(rate)+'\n3d/physics_engine="Jolt Physics"\n3d/default_gravity=9.81\n3d/default_gravity_vector=Vector3(0,-1,0)\njolt_physics_3d/collisions/collision_margin_fraction=0.0\njolt_physics_3d/simulation/penetration_slop=0.001\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n',encoding='utf8')
        doc,plan=fixture();cases=[dict(id='shared',events=doc,plan=plan),dict(id='reverse-body-order',events=doc,plan=plan,reverse_bodies=True)]
        cases += [dict(id=fault,events=doc,plan=plan,fault=fault) for fault in ('conflict','outside','missing-body','provider-clock')]
        request=dict(physics_fps=rate,cases=cases,methods_sha256=hashes,engine_sha256=sha256(ENGINE),at=now());save(output/'request.json',request)
        env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        save(output/'pipeline.json',dict(status='checking',at=now()))
        with (output/'compile.log').open('w',encoding='utf8') as log:
            check=subprocess.run([str(ENGINE),'--headless','--path',str(project),'--check-only','--script','godot_scene_prop_ownership_audit.gd'],stdout=log,stderr=subprocess.STDOUT,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW,env=env)
        if check.returncode:
            save(output/'pipeline.json',dict(status='failed',stage='script_compile',exit_code=check.returncode));raise RuntimeError('Inspect retained compile.log')
        save(output/'pipeline.json',dict(status='running',at=now()))
        with (output/'engine.log').open('w',encoding='utf8') as log:
            run=subprocess.run([str(ENGINE),'--headless','--path',str(project),'--fixed-fps',str(rate),'--script','godot_scene_prop_ownership_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW,env=env)
        if run.returncode:
            save(output/'pipeline.json',dict(status='failed',stage='engine',exit_code=run.returncode));raise RuntimeError('Inspect retained engine.log')
        assert all(sha256(ROOT/'scripts'/n)==sha256(methods/n)==h for n,h in hashes.items())
        try:result=verify(request,read(output/'engine-output.json'))
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',stage='verification',error=repr(exc)));raise
        result.update(at=now(),methods_sha256=hashes,request_sha256=sha256(output/'request.json'),raw_output_sha256=sha256(output/'engine-output.json'),source_and_copy_current=True)
        save(output/'pipeline.json',dict(status='complete',at=now()))
        save(output/'result.json',result);print(json.dumps(result,indent=2));return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--physics-fps',type=int,default=240)
    args=parser.parse_args();study(args.output,args.physics_fps)
