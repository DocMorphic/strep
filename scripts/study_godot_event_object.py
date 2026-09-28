"""Actual engine study of fixed-step authored attachment/release and transport."""
import argparse
from pathlib import Path
import shutil
from functools import lru_cache
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now
from rig_asset import RigAsset
from rig_clip_import import AnimationSampler
from probe_godot_render import run_engine


@lru_cache(maxsize=8)
def reference_source(path, hand):
    rig = RigAsset.load(path)
    sampler = AnimationSampler(rig.document, rig.binary, 0)
    node = next(i for i, n in enumerate(rig.document['nodes']) if n.get('name') == hand)
    return sampler, node


def reference(item, metadata, tick):
    sampler, node = reference_source(item['path'], item['hand'])
    t = tick / 60
    finite = metadata.get('schema') == 'strep-runtime-finite-v1'
    period = metadata['frames' if finite else 'period_frames'] / 30
    cycle = 0 if finite else int(np.floor(t / period))
    world = sampler.sample(min(t,(metadata['frames']-1)/30) if finite else t - cycle * period)[node]
    placement = np.eye(4)
    placement[:3, :3] = Rotation.from_euler('y', .4).as_matrix()
    placement[:3, 3] = [2, 1, -1]
    offset = np.eye(4)
    offset[:3, :3] = Rotation.from_rotvec([0, 0, -.2]).as_matrix()
    offset[:3, 3] = [.06, -.04, .1]
    return placement @ np.linalg.matrix_power(np.array(metadata.get('cycle_transform',np.eye(4))), cycle) @ world @ offset


def verify(request, actual, output):
    checks = []
    if len(actual['cases']) != len(request['cases']): raise ValueError('Incomplete engine population')
    for item, case in zip(request['cases'], actual['cases']):
        if item['id'] != case['id']: raise ValueError('Engine case order changed')
        metadata = read(item['metadata'])
        actions = case['actions']
        frames = [item['attach_frame'] * 2, item['release_frame'] * 2]
        timing = [(a['session'], a['action'], a['tick']) for a in actions] == [(s, a, t) for s in (0, 1) for a, t in zip(('attach', 'release'), frames)]
        errors = []
        velocities = []
        spins = []
        for action in actions:
            expected = reference(item, metadata, action['tick'])
            errors.append(float(np.max(np.abs(np.array(action['pose']) - expected))))
            if action['action'] == 'release':
                before = reference(item, metadata, action['tick'] - 1)
                velocity = (expected[:3, 3] - before[:3, 3]) * 60
                spin = Rotation.from_matrix(expected[:3, :3] @ before[:3, :3].T).as_rotvec() * 60
                velocities.append(float(np.linalg.norm(np.array(action['velocity']) - velocity)))
                spins.append(float(np.linalg.norm(np.array(action['spin']) - spin)))
        records = case['records']
        poses = []
        indexed = {}
        held_error = 0.
        free_steps = []
        for r in records:
            if r['transport'] != 'live': continue
            indexed[(r['session'], r['tick'])] = r
            poses.append(float(np.max(np.abs(np.array(r['grip']) - reference(item, metadata, r['tick'])))))
            if r['mode'] == 'held':
                held_error = max(held_error, float(np.max(np.abs(np.array(r['pose']) - r['grip']))))
            previous = indexed.get((r['session'], r['tick']-1))
            # Independent semi-implicit Euler check only before first possible floor collision.
            if previous and previous['mode']=='released' and min(np.array(r['pose'])[1,3], np.array(previous['pose'])[1,3]) > .3 and not previous['contacts'] and not r['contacts']:
                velocity = np.array(previous['velocity']) + np.array(previous['gravity']) / 60
                position = np.array(previous['pose'])[:3,3] + velocity / 60
                free_steps.append(max(float(np.linalg.norm(velocity-r['velocity'])), float(np.linalg.norm(position-np.array(r['pose'])[:3,3]))))
        paused = [r for r in records if r['transport']=='paused']
        preview = [r for r in records if r['transport']=='preview']
        resumed = [r for r in records if r['command']=='resume']
        anchor = indexed.get((0, frames[1]+6))
        transport_ok = len(paused)==5 and len(preview)==3 and len(resumed)==1 and anchor is not None
        transport_pose_limit=request['limits'].get('transport_matrix',1e-7)
        transport_pose_error=0.
        if transport_ok:
            transport_pose_error=max(float(np.max(np.abs(np.array(r['pose'])-indexed[(0,r['tick'])]['pose']))) for r in paused+preview+resumed)
            transport_ok = all(r['tick']==anchor['tick'] and np.allclose(r['pose'],anchor['pose'],atol=transport_pose_limit,rtol=0) and r['collision_layer']==0 and r['collision_mask']==0 for r in paused)
            transport_ok &= all(np.allclose(r['pose'],indexed[(0,r['tick'])]['pose'],atol=transport_pose_limit,rtol=0) and r['collision_layer']==0 and r['collision_mask']==0 for r in preview)
            transport_ok &= resumed[0]['tick']==anchor['tick'] and np.allclose(resumed[0]['pose'],anchor['pose'],atol=transport_pose_limit,rtol=0) and all(np.allclose(resumed[0][k],anchor[k],atol=1e-7,rtol=0) for k in ('velocity','spin'))
            transport_ok &= [r['mode'] for r in preview]==['held','released','parked']
        floor = any('floor' in r['contacts'] for r in records if r['mode']=='released' and r['transport']=='live')
        replay = [(r['tick'],r['mode']) for r in records if r['session']==1 and r['transport']=='live']
        replay_ok = replay == [(i, 'parked' if i<frames[0] else 'held' if i<frames[1] else 'released') for i in range(item['end_tick']+1)]
        passed = bool(timing and errors and max(errors)<request['limits']['matrix'] and max(poses)<request['limits']['matrix'] and max(velocities)<request['limits']['velocity_m_s'] and max(spins)<request['limits']['spin_rad_s'] and held_error<request['limits']['held_matrix'] and len(free_steps)>5 and max(free_steps)<request['limits']['physics_step'] and transport_ok and floor and replay_ok and not case['faults'] and case['retained_history_samples']==128 and all(v!=0 for v in case['rejections'].values()))
        checks.append(dict(id=item['id'],passed=passed,event_timing_passed=timing,actions=len(actions),records=len(records),maximum_event_matrix_error=max(errors,default=None),maximum_grip_matrix_error=max(poses,default=None),maximum_release_velocity_error_m_s=max(velocities,default=None),maximum_release_spin_error_rad_s=max(spins,default=None),maximum_held_pose_error=held_error,free_flight_steps=len(free_steps),maximum_free_step_error=max(free_steps,default=None),maximum_transport_pose_error=transport_pose_error,transport_passed=bool(transport_ok),floor_contact_observed=floor,replay_passed=replay_ok,rejections=case['rejections'],faults=case['faults']))
    passed=all(c['passed'] for c in checks)
    if request.get('omit_release_velocity_control'):
        passed=bool(len(checks)==1 and not checks[0]['passed'] and checks[0]['maximum_release_velocity_error_m_s']>request['limits']['velocity_m_s'] and checks[0]['event_timing_passed'] and checks[0]['transport_passed'])
    save(output/'verification.json',dict(at=now(),passed=passed,checks=checks,deliberately_broken_velocity=request.get('omit_release_velocity_control',False),quality_approved=False,request_sha256=sha256(output/'request.json'),engine_output_sha256=sha256(output/'engine-output.json')))
    return passed,checks


def run(output, omit_release_velocity_control=False):
    output.mkdir(parents=True,exist_ok=False)
    project=output/'project';project.mkdir()
    (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep gameplay event audit"\n[physics]\n3d/physics_engine="GodotPhysics3D"\ncommon/physics_ticks_per_second=60\n',encoding='utf-8')
    sources=('godot_cycle_adapter.gd','godot_event_object_body.gd','godot_event_object_audit.gd')
    for name in sources: shutil.copyfile(ROOT/'scripts'/name,project/name)
    if omit_release_velocity_control:
        target=project/'godot_event_object_body.gd'
        original=target.read_text(encoding='utf-8')
        needle='state.linear_velocity=velocity if action=="release" else Vector3.ZERO'
        if original.count(needle)!=1: raise ValueError('Negative control patch target changed')
        target.write_text(original.replace(needle,'state.linear_velocity=Vector3.ZERO # DELIBERATE TEST FAULT'),encoding='utf-8')
    cases=[]
    frozen=ROOT/'reports/runtime-reverse-v2/request.json'
    for item in read(frozen)['cases']:
        if omit_release_velocity_control and cases: break
        folder=output/item['id'];folder.mkdir()
        if sha256(item['path'])!=item['glb_sha256'] or sha256(item['metadata'])!=item['metadata_sha256']: raise ValueError('Frozen fixture changed')
        shutil.copyfile(item['path'],folder/'character.glb')
        metadata=read(item['metadata']);period=metadata['period_frames']
        attach=max(1,period//5);release=period*3//5
        metadata['markers']=[metadata['markers'][0]]
        for id, frame in [('test-grasp',attach),('test-release',release)]:
            source=dict(id=id,name=id,kind='authored',requires_review=False,frame=frame,provenance='Explicit software-mechanism fixture. No developer/animator review or grasp quality approval.')
            metadata['markers'].append(dict(name=id,phase_frame=frame,first_cycle=0,event_id=id,source_event=source))
        metadata['gameplay_test_fixture']='Test-authored event intent; original clip is NOT asserted to grasp this prop.'
        save(folder/'runtime-cycle.json',metadata)
        rig=RigAsset.load(folder/'character.glb')
        names=[n.get('name') for n in rig.document['nodes']]
        hand='hand_r' if 'hand_r' in names else 'Skeleton_arm_joint_R__3_'
        cases.append(dict(id=item['id'],path=str(folder/'character.glb'),metadata=str(folder/'runtime-cycle.json'),hand=hand,attach_frame=attach,release_frame=release,end_tick=max(210,period*4+4),glb_sha256=sha256(folder/'character.glb'),metadata_sha256=sha256(folder/'runtime-cycle.json'),source_metadata_sha256=item['metadata_sha256']))
    engine=ROOT/'.cache/godot/4.7.2-stable/Godot_v4.7.2-stable_win64_console.exe'
    if sha256(engine)!=read(engine.parent/'acquisition.json')['executables'][engine.name]: raise ValueError('Engine executable changed')
    command=[str(engine),'--headless','--path',str(project),'--fixed-fps','60','--script','godot_event_object_audit.gd','--',str(output/'request.json'),str(output/'engine-output.json')]
    request=dict(at=now(),cases=cases,physics_fps=60,command=command,engine_sha256=sha256(engine),source_request_sha256=sha256(frozen),implementation={n:sha256(ROOT/'scripts'/n) for n in (*sources,'study_godot_event_object.py')},executed_scripts={n:sha256(project/n) for n in sources},omit_release_velocity_control=omit_release_velocity_control,limits=dict(matrix=2e-5,held_matrix=1e-6,velocity_m_s=.002,spin_rad_s=.002,physics_step=.0001),scope='Four frozen rig fixtures with test-authored event bindings; attachment mechanism, physics and transport only. No grasp/contact quality or human approval.',preflight_note='v1 held matrix tolerance 1e-7 failed on float32 engine basis roundoff (max 5.514e-7); v2 freezes explicit 1e-6. Other limits unchanged. v1 retained.')
    save(output/'request.json',request)
    shutil.copyfile(__file__,output/'study_godot_event_object.py')
    save(output/'pipeline.json',dict(at=now(),status='engine_running'))
    run_engine(command,output/'engine.log',timeout=120)
    passed,checks=verify(request,read(output/'engine-output.json'),output)
    save(output/'pipeline.json',dict(at=now(),status='complete' if passed else 'failed_comparison',passed=passed))
    print(dict(passed=passed,checks=checks))
    if not passed: raise ValueError('Event/physics checks failed; evidence retained')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    parser.add_argument('--omit-release-velocity-control',action='store_true')
    args=parser.parse_args();run(args.output.resolve(),args.omit_release_velocity_control)
