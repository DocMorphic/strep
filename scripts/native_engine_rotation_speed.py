"""Actual imported joint-key speed audit; no rendering or physical approval.

Capture each selected joint and its immediate source parent independently.
Never substitute source transforms for an unobserved helper or skeleton bone.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import numpy as np
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_limits
from action_worker_lock import worker_lock
from strep import ROOT, read, save, sha256
from native_scene_contacts import SceneContacts, METHODS as CONTACT_METHODS
from native_rotation_speed_policy import limits_for, METHODS as SPEED_METHODS
from native_engine_clock import clock_wire, check_clock_wire, clock_echo_matches
from native_godot_payload import payload

SCRIPTS=('godot_native_rotation_speed.gd','native_engine_clock.gd',
         'native_godot_tracks.gd','native_godot_preview.gd')
METHODS=tuple(dict.fromkeys(CONTACT_METHODS+SPEED_METHODS+SCRIPTS+(
    'native_engine_rotation_speed.py','native_engine_clock.py','native_godot_payload.py',
    'action_worker_lock.py')))
BASIS_TOLERANCE=2e-6
POSE_TOLERANCE=1e-4
FLAGS=dict(original_selected=True,rendering_verified=False,physics_playback_verified=False,
    continuous_speed_certified=False,quality_approved=False,training_admitted=False,release_approved=False)


def bake_rate(value,mode):
    if type(value) not in (int,float) or value not in (30,60,120,240) or mode not in ('import','native-authoring'):
        raise ValueError('Explicit playback mode and 30, 60, 120 or 240 FPS required')
    if mode=='native-authoring' and value!=30:raise ValueError('Native authoring retains 30 FPS import')
    return float(value)


def plan(scene,policy,digest):
    limits=limits_for(policy,digest);tracks=[];nodes={};clocks=[np.array([0.,scene.duration])]
    for (name,node),maximum in limits.items():
        if name not in scene.actors or node not in scene.actors[name]['rig'].joints:
            raise ValueError('Existing actor and skin joint required for imported speed audit')
        actor=scene.actors[name]
        channel=next((c for c in actor['sampler'].channels if c[:2]==(node,'rotation')),None)
        if channel is None or channel[4]!='LINEAR' or not 2<=len(channel[2])<=20000:
            raise ValueError('Selected speed track requires 2-20000 native LINEAR rotation keys')
        parent=actor['rig'].parents[node]
        nodes.setdefault(name,set()).add(node)
        if parent>=0:nodes[name].add(parent)
        clocks.append(channel[2].astype(float))
        tracks.append(dict(actor=name,node=node,parent=parent,maximum_degrees_per_second=maximum,
            times_s=channel[2].astype(float).tolist()))
    times=np.unique(np.concatenate(clocks))
    if len(times)>20000:raise ValueError('At most 20000 distinct imported audit times supported')
    captures={name:[dict(node=n,parent=scene.actors[name]['rig'].parents[n],
        original_name=scene.actors[name]['rig'].document['nodes'][n].get('name',''))
        for n in sorted(ids)] for name,ids in nodes.items()}
    return tracks,captures,times


def matrices(values):
    value=np.asarray(values,float)
    if value.shape[-2:]!=(4,3) or not np.isfinite(value).all():
        raise ValueError('Complete finite imported basis columns and origin required')
    world=np.zeros(value.shape[:-2]+(4,4));world[...,:3,:]=value.swapaxes(-1,-2);world[...,3,3]=1
    return world


def speeds(q,times):
    # Principal SO(3) displacement / actual native interval, not instantaneous
    # angular speed. Quaternion signs do not change the result.
    q=q/np.linalg.norm(q,axis=1)[:,None];a,b=q[:-1],q[1:]
    vector=a[:,3,None]*b[:,:3]-b[:,3,None]*a[:,:3]-np.cross(a[:,:3],b[:,:3])
    scalar=np.sum(a*b,axis=1)
    with np.errstate(over='raise',divide='raise',invalid='raise'):
        try:return 2*np.rad2deg(np.arctan2(np.linalg.norm(vector,axis=1),abs(scalar)))/np.diff(times)
        except FloatingPointError as error:raise ValueError('Representable imported interval speeds required') from error


def audit(scene,policy,digest,request,actual):
    bake_rate(request['import_bake_fps'],request['playback_mode'])
    tracks,captures,times=plan(scene,policy,digest)
    check_clock_wire(request['sample_clock'],times)
    if request['sample_times_s']!=times.tolist() or request['tracks']!=tracks:
        raise ValueError('Every selected native speed key and unchanged author limit required')
    cases=request['cases']
    if [c['id'] for c in cases]!=list(captures) or [c['id'] for c in actual['cases']]!=list(captures):
        raise ValueError('Complete selected imported actor population required')
    if actual['playback_mode']!=request['playback_mode'] or actual['import_bake_fps']!=request['import_bake_fps']:
        raise ValueError('Executed playback mode and import bake rate differ')
    worlds={};pose={};arrays={'sample_times_s':times};mapping={}
    for case,found in zip(cases,actual['cases']):
        name=case['id'];actor=scene.actors[name];count=len(actor['rig'].document['nodes'])
        if (case['capture_nodes']!=captures[name] or case['source_node_count']!=count
                or case['animation_index']!=actor['animation_index']
                or found['path']!=case['path'] or found['animation_index']!=case['animation_index']
                or found['original_animation_count']!=len(actor['rig'].document['animations'])
                or found['loop_mode']!=0 or type(found['duration_s']) not in (int,float)
                or not np.isfinite(found['duration_s']) or abs(found['duration_s']-scene.duration)>1e-6
                or not isinstance(found['selected_animation'],str) or not found['selected_animation']):
            raise ValueError('Unchanged actor selection, capture hierarchy and finite clip required')
        mapped=found['capture_nodes'];paths=[]
        if len(mapped)!=len(captures[name]):raise ValueError('Missing joint or immediate parent mapping')
        for expected,node in zip(captures[name],mapped):
            parent=node['engine_parent']
            if (any(node[k]!=v for k,v in expected.items()) or type(parent) is not int
                    or (parent!=expected['parent'] and not(expected['parent']==-1 and parent>=count))
                    or not isinstance(node['scene_path'],str) or not node['scene_path']):
                raise ValueError('Imported source-node identity or immediate parent changed')
            paths.append(node['scene_path'])
        if len(set(paths))!=len(paths):raise ValueError('Distinct source nodes require distinct imported paths')
        frames=found['frames']
        if len(frames)!=len(times):raise ValueError('Missing imported native-key observation')
        for time,frame in zip(times,frames):
            if not clock_echo_matches(time,frame['requested_time_s']) or not clock_echo_matches(time,frame['actual_time_s']):
                raise ValueError('Imported seek clock differs from exact declared native clock')
        world=matrices([f['node_worlds'] for f in frames])
        if world.shape!=(len(times),len(mapped),4,4):raise ValueError('Complete joint and parent worlds required')
        ids=[n['node'] for n in captures[name]]
        expected=np.array([actor['sampler'].sample(float(t))[ids] for t in times])
        error=float(abs(world-expected).max())
        pose[name]=dict(maximum_world_element_error=error,tolerance=POSE_TOLERANCE,passed=error<=POSE_TOLERANCE)
        worlds[name]={node:world[:,i] for i,node in enumerate(ids)};mapping[name]=mapped
        arrays[name+'_node_worlds']=world
    rows=[]
    for number,track in enumerate(tracks):
        name,node,parent=track['actor'],track['node'],track['parent'];clock=np.asarray(track['times_s'])
        ids=np.searchsorted(times,clock);world=worlds[name][node][ids]
        try:local=world if parent<0 else np.linalg.solve(worlds[name][parent][ids],world)
        except np.linalg.LinAlgError as error:raise ValueError('Invertible imported parent transforms required') from error
        block=local[:,:3,:3];scale=np.linalg.norm(block,axis=1)
        if not np.isfinite(local).all() or np.any(scale<=0):raise ValueError('Nonzero representable imported local scales required')
        basis=block/scale[:,None,:]
        residual=float(abs(basis.swapaxes(1,2)@basis-np.eye(3)).max())
        determinant=float(abs(np.linalg.det(basis)-1).max())
        if max(residual,determinant)>BASIS_TOLERANCE:raise ValueError('Proper imported local rotations required; reflection or shear rejected')
        rotation=Rotation.from_matrix(basis);projection=float(abs(basis-rotation.as_matrix()).max())
        if projection>BASIS_TOLERANCE:raise ValueError('Imported rotation projection exceeds transport tolerance')
        rates=speeds(rotation.as_quat(),clock);limit=track['maximum_degrees_per_second'];bad=np.flatnonzero(rates>limit)
        rows.append(dict(**track,comparisons=len(rates),maximum_observed_degrees_per_second=float(rates.max()),
            failed_intervals=bad.tolist(),passed=len(bad)==0,maximum_orthogonality_residual=residual,
            maximum_determinant_error=determinant,maximum_basis_projection_error=projection,
            transport_basis_tolerance=BASIS_TOLERANCE,speed_acceptance_allowance=0.))
        arrays[f'track_{number}_local_matrices']=local
        arrays[f'track_{number}_rotations_xyzw']=rotation.as_quat()
        arrays[f'track_{number}_rates_degrees_per_second']=rates
    result=dict(schema='strep-native-engine-rotation-speed-v1',tracks=rows,capture_mapping=mapping,
        source_pose_comparison=pose,samples=len(times),rotation_speed_conditions_pass=all(r['passed'] for r in rows),
        source_pose_conditions_pass=all(r['passed'] for r in pose.values()),
        all_sampled_conditions_pass=all(r['passed'] for r in rows+list(pose.values())),**FLAGS,
        scope='Selected joint local principal-angle speeds between every original LINEAR key, measured from '
              'actual imported joint and immediate-parent worlds. Exact native clock, strict authored limits; '
              'basis normalization/projection is reported separately. No between-key, skin, contact, collision, '
              'physics, real-time playback, rendering or human quality approval.')
    return result,arrays


def run(contacts,policy_path,output,*,engine,playback_mode='import',import_bake_fps=30):
    fps=bake_rate(import_bake_fps,playback_mode)
    contacts,policy_path,output,engine=[Path(p).resolve() for p in (contacts,policy_path,output,engine)]
    if output.exists():raise FileExistsError(output)
    with worker_lock(),threadpool_limits(limits=1):
        scene=SceneContacts(read(contacts),contacts.parent);digest=sha256(contacts);policy=read(policy_path)
        tracks,captures,times=plan(scene,policy,digest)
        bindings={str(contacts):digest,str(policy_path):sha256(policy_path),**scene.inputs}
        methods={n:sha256(ROOT/'scripts'/n) for n in METHODS}
        output.mkdir(parents=True);project=output/'project';project.mkdir();archive=output/'implementation';archive.mkdir()
        for n in METHODS:shutil.copyfile(ROOT/'scripts'/n,archive/n)
        for n in SCRIPTS:shutil.copyfile(ROOT/'scripts'/n,project/n)
        snapshots={}
        for i,(path,h) in enumerate(bindings.items()):
            dest=output/'input'/f'{i}{Path(path).suffix}';dest.parent.mkdir(exist_ok=True);shutil.copyfile(path,dest)
            snapshots[path]=dict(path=dest.relative_to(output).as_posix(),sha256=h)
        cases=[];spec=read(contacts)
        for name,nodes in captures.items():
            actor=scene.actors[name];source=(contacts.parent/spec['actors'][name]['glb']).resolve()
            case=dict(id=name,path=str(output/snapshots[str(source)]['path']),animation_index=actor['animation_index'],
                capture_nodes=nodes,source_node_count=len(actor['rig'].document['nodes']))
            if playback_mode=='native-authoring':
                case.update(native_payload=payload(actor['rig'],actor['sampler'],sha256(source)),
                    animation_output=str(output/(name+'-animation.res')))
            cases.append(case)
        request=dict(cases=cases,tracks=tracks,sample_times_s=times.tolist(),sample_clock=clock_wire(times),
            playback_mode=playback_mode,import_bake_fps=fps,inputs_sha256=bindings,
            engine_path=str(engine),engine_sha256=sha256(engine),implementation_sha256=methods,source_snapshots=snapshots)
        save(output/'request.json',request)
        (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Strep imported speed audit"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
        save(output/'pipeline.json',dict(status='processing',**FLAGS))
        try:
            with (output/'engine.log').open('w',encoding='utf-8') as log:
                finished=subprocess.run([str(engine),'--headless','--path',str(project),'--script',SCRIPTS[0],
                    '--',str(output/'request.json'),str(output/'engine-output.json')],stdout=log,stderr=subprocess.STDOUT,
                    timeout=300,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if finished.returncode:raise ValueError('Imported speed capture failed; inspect engine.log')
            actual=read(output/'engine-output.json');result,arrays=audit(scene,policy,digest,request,actual)
            np.savez_compressed(output/'observations.npz',**arrays)
            resources={} if playback_mode=='import' else {c['id']:sha256(c['animation_output']) for c in cases}
            receipt=dict(returncode=finished.returncode,request_sha256=sha256(output/'request.json'),
                engine_output_sha256=sha256(output/'engine-output.json'),engine_log_sha256=sha256(output/'engine.log'),
                engine_executable_sha256=request['engine_sha256'],animation_resources_sha256=resources,
                executed_scripts_sha256={n:sha256(project/n) for n in SCRIPTS})
            save(output/'raw-engine-receipt.json',receipt)
            result.update(status='complete',engine=actual['engine'],playback_mode=playback_mode,import_bake_fps=fps,
                request_sha256=receipt['request_sha256'],raw_engine_receipt_sha256=sha256(output/'raw-engine-receipt.json'),
                observations_sha256=sha256(output/'observations.npz'))
            # Recheck every original, copied input and executed/archived method.
            check_bindings(output,request,receipt)
            save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete',**FLAGS));return result
        except Exception as exc:
            save(output/'pipeline.json',dict(status='failed',error=str(exc),**FLAGS));raise


def check_bindings(folder,request,receipt):
    if set(request['implementation_sha256'])!=set(METHODS):raise ValueError('Complete speed audit implementation required')
    for n,h in request['implementation_sha256'].items():
        if sha256(ROOT/'scripts'/n)!=h or sha256(folder/'implementation'/n)!=h:raise ValueError('Speed audit implementation changed')
    if set(request['source_snapshots'])!=set(request['inputs_sha256']):raise ValueError('Complete speed input snapshots required')
    for path,h in request['inputs_sha256'].items():
        row=request['source_snapshots'][path];saved=(folder/row['path']).resolve()
        if not saved.is_relative_to(folder) or sha256(path)!=h or sha256(saved)!=h or row['sha256']!=h:
            raise ValueError('Speed audit input changed')
    if sha256(request['engine_path'])!=request['engine_sha256'] or receipt['engine_executable_sha256']!=request['engine_sha256']:
        raise ValueError('Executed speed audit engine changed')
    if set(receipt['executed_scripts_sha256'])!=set(SCRIPTS):raise ValueError('Complete executed speed scripts required')
    for n,h in receipt['executed_scripts_sha256'].items():
        if h!=request['implementation_sha256'][n] or sha256(folder/'project'/n)!=h:raise ValueError('Executed speed script changed')
    for case in request['cases']:
        if case['path'] not in [str(folder/row['path']) for row in request['source_snapshots'].values()]:
            raise ValueError('Imported source is outside bound snapshots')
    resources={} if request['playback_mode']=='import' else {c['id']:sha256(c['animation_output']) for c in request['cases']}
    if resources!=receipt['animation_resources_sha256']:raise ValueError('Imported animation resource changed')


def verify(contacts,policy_path,folder):
    """Recompute from saved actual engine matrices, ignoring summary booleans."""
    with worker_lock(),threadpool_limits(limits=1):
        return replay(contacts,policy_path,folder)


def replay(contacts,policy_path,folder):
    contacts,policy_path,folder=[Path(p).resolve() for p in (contacts,policy_path,folder)]
    request=read(folder/'request.json');receipt=read(folder/'raw-engine-receipt.json');result=read(folder/'result.json')
    if read(folder/'pipeline.json')['status']!='complete' or result['status']!='complete' or receipt['returncode']!=0:
        raise ValueError('Complete actual speed producer required')
    if (request['inputs_sha256'].get(str(contacts))!=sha256(contacts)
            or request['inputs_sha256'].get(str(policy_path))!=sha256(policy_path)):
        raise ValueError('Exact speed contacts and author policy required')
    for name,key in (('request.json','request_sha256'),('engine-output.json','engine_output_sha256'),('engine.log','engine_log_sha256')):
        if sha256(folder/name)!=receipt[key]:raise ValueError('Raw speed receipt changed: '+name)
    check_bindings(folder,request,receipt)
    scene=SceneContacts(read(contacts),contacts.parent)
    spec=read(contacts)
    for case in request['cases']:
        source=(contacts.parent/spec['actors'][case['id']]['glb']).resolve()
        if case['path']!=str(folder/request['source_snapshots'][str(source)]['path']):
            raise ValueError('Selected imported actor differs from its bound source snapshot')
    actual=read(folder/'engine-output.json');replayed,arrays=audit(scene,read(policy_path),sha256(contacts),request,actual)
    replayed.update(status='complete',engine=actual['engine'],playback_mode=request['playback_mode'],import_bake_fps=request['import_bake_fps'],
        request_sha256=sha256(folder/'request.json'),raw_engine_receipt_sha256=sha256(folder/'raw-engine-receipt.json'),
        observations_sha256=sha256(folder/'observations.npz'))
    if replayed!=result:raise ValueError('Imported speed result differs from fresh matrix replay')
    with np.load(folder/'observations.npz',allow_pickle=False) as stored:
        if set(stored.files)!=set(arrays):raise ValueError('Complete imported speed arrays required')
        for name,value in arrays.items():
            if stored[name].dtype!=value.dtype or stored[name].shape!=value.shape or stored[name].tobytes()!=value.tobytes():
                raise ValueError('Imported speed observation array changed: '+name)
    return replayed


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('contacts',type=Path);p.add_argument('policy',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--engine',type=Path);p.add_argument('--verify',action='store_true')
    p.add_argument('--playback-mode',choices=['import','native-authoring'],default='import');p.add_argument('--import-bake-fps',type=int,choices=[30,60,120,240],default=30)
    a=p.parse_args()
    if a.verify:verify(a.contacts,a.policy,a.output)
    else:
        if a.engine is None:p.error('--engine is required for actual capture')
        run(a.contacts,a.policy,a.output,engine=a.engine,playback_mode=a.playback_mode,import_bake_fps=a.import_bake_fps)
