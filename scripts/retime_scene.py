"""Uniform scene timing with preserved exported curves and precise event times."""
import argparse
import copy
import hashlib
from pathlib import Path
import shutil
import zipfile
import numpy as np
from strep import ROOT, read, save, sha256
from gltf_tools import read_glb, write_glb, accessor, append_accessor
from rig_clip_import import AnimationSampler
from inspect_motion import validate_motion
from scene_runtime import local, write as write_runtime


def frame_scale(source_frames, target_frames):
    if any(type(n) is not int or not 3 <= n <= 901 for n in [source_frames, target_frames]):
        raise ValueError('Choose 3–901 frames (at most 30 seconds of poses)')
    return (target_frames-1)/(source_frames-1)


def map_frame(frame, source_frames, target_frames):
    scale=frame_scale(source_frames,target_frames)
    if type(frame) not in (int,float) or not np.isfinite(frame) or not 0 <= frame <= source_frames:
        raise ValueError('Invalid source event frame')
    # Runtime has a one-frame terminal hold, separate from the animated curve.
    result=frame*scale if frame <= source_frames-1 else target_frames-1+frame-(source_frames-1)
    return int(round(result)) if abs(result-round(result)) < 1e-10 else float(result)


def retime_clock(scene, events, frames, exact_windows=None):
    original=scene['frame_count'];scale=frame_scale(original,frames)
    if scene.get('fps')!=30 or events.get('fps')!=30:
        raise ValueError('Scene and events require 30 fps clocks')
    result=copy.deepcopy(scene);result['frame_count']=frames
    precise={}
    if exact_windows is not None:
        entries=exact_windows.get('windows')
        if not isinstance(entries,list) or len(entries)!=len(scene['contacts']) or {e['id'] for e in entries}!={c['id'] for c in scene['contacts']}:
            raise ValueError('Exact contact windows differ from scene')
        precise={e['id']:e['exact_output_frames'] for e in entries}
    windows=[]
    for contact in result['contacts']:
        a,b=contact['start_frame'],contact['end_frame']
        if type(a) is not int or type(b) is not int or not 0 <= a <= b < original:
            raise ValueError('Invalid source contact interval')
        if contact['id'] in precise:
            interval=precise[contact['id']]
            if not isinstance(interval,list) or len(interval)!=2 or any(type(v) not in (int,float) or not np.isfinite(v) for v in interval) or not 0<=interval[0]<=interval[1]<original:
                raise ValueError('Invalid precise contact clock')
            a,b=interval
        exact=[a*scale,b*scale]
        # Native contact solvers still need integer keys. Enclose the exact
        # interval rather than silently dropping sub-frame contact requests.
        first=max(0,int(np.floor(exact[0]+1e-10)))
        last=min(frames-1,int(np.ceil(exact[1]-1e-10)))
        contact.update(start_frame=first,end_frame=last)
        windows.append(dict(id=contact['id'],source_frames=[a,b],exact_output_frames=exact,
                            native_enclosing_frames=[first,last],
                            maximum_enclosure_seconds=max(exact[0]-first,last-exact[1])/30))
    mapped=copy.deepcopy(events)
    for event in mapped['events']:
        f,t=event.get('frame'),event.get('time_s')
        mapped_frame=map_frame(f,original,frames)
        if type(t) not in (int,float) or not np.isfinite(t) or abs(t-f/30)>1e-8:
            raise ValueError('Invalid source event clock')
        event.update(frame=mapped_frame,time_s=mapped_frame/30)
    return result,mapped,windows


def retime_export(path, source_frames, target_frames):
    """Change time units, including cubic derivatives; keep the actual asset."""
    scale=frame_scale(source_frames,target_frames)
    doc,binary=read_glb(path)
    if len(doc.get('animations',[]))!=1:raise ValueError('One animation per participant required')
    source=AnimationSampler(doc,binary,0)
    if abs(source.duration-(source_frames-1)/30)>1e-5:
        raise ValueError('Export clock differs from native scene duration')
    result=copy.deepcopy(doc);buffer=bytearray(binary);inputs={};outputs={}
    for item in result['animations'][0]['samplers']:
        clock=item['input'];values=item['output']
        if clock not in inputs:
            inputs[clock]=append_accessor(result,buffer,accessor(doc,binary,clock)*scale,'SCALAR')
        item['input']=inputs[clock]
        if item.get('interpolation','LINEAR')=='CUBICSPLINE':
            if values not in outputs:
                data=accessor(doc,binary,values).copy()
                data[0::3]/=scale;data[2::3]/=scale
                outputs[values]=append_accessor(result,buffer,data,doc['accessors'][values]['type'])
            item['output']=outputs[values]
    # Validate the actual float32 clock and tangent representation before writing.
    AnimationSampler(result,buffer,0)
    return result,buffer


def native_motion(motion, document, binary, source_frames, target_frames):
    names,parents,_=validate_motion(motion,30)
    allowed={'root_positions','posed_joints','local_rot_mats','global_rot_mats',
             'foot_contacts','smooth_root_pos','global_root_heading'}
    if len(names)!=77 or set(motion)-allowed or any(v.ndim<1 or len(v)!=source_frames or not np.isfinite(v).all() for v in motion.values()):
        raise ValueError('Native SOMA77 arrays on one clock required; unknown channels cannot be retimed implicitly')
    ids=document['skins'][0]['joints']
    if [document['nodes'][j].get('name') for j in ids]!=names:
        raise ValueError('Actor export joint identities differ from native motion')
    sampler=AnimationSampler(document,binary,0)
    world=np.array([sampler.sample(f/30)[ids] for f in range(target_frames)])
    rotations=world[:,:,:3,:3];local_rot=rotations.copy()
    for j,p in enumerate(parents):
        if p>=0:local_rot[:,j]=rotations[:,p].transpose(0,2,1)@rotations[:,j]
    source_times=np.linspace(0,source_frames-1,target_frames)
    hold=np.floor(source_times+1e-10).astype(int)
    result=dict(root_positions=world[:,0,:3,3],posed_joints=world[:,:,:3,3],
                global_rot_mats=rotations,local_rot_mats=local_rot,
                foot_contacts=motion['foot_contacts'][hold].copy())
    if 'smooth_root_pos' in motion:
        if motion['smooth_root_pos'].shape!=(source_frames,3):raise ValueError('Invalid smoothed root channel')
        result['smooth_root_pos']=np.stack([np.interp(source_times,np.arange(source_frames),motion['smooth_root_pos'][:,i]) for i in range(3)],1)
    if 'global_root_heading' in motion:
        h=motion['global_root_heading']
        if h.shape!=(source_frames,2) or not np.isfinite(h).all() or np.any(np.linalg.norm(h,axis=1)<1e-6):
            raise ValueError('Invalid root heading channel')
        angles=np.unwrap(np.arctan2(h[:,1],h[:,0]));a=np.interp(source_times,np.arange(source_frames),angles)
        result['global_root_heading']=np.stack([np.cos(a),np.sin(a)],1)
    validate_motion(result,30)
    return result


def curve_audit(original, retimed, source_frames, target_frames):
    """Compare identical motion phases at 120 Hz in the source clock."""
    source_doc,source_binary=read_glb(original);doc,binary=retimed
    a=AnimationSampler(source_doc,source_binary,0);b=AnimationSampler(doc,binary,0)
    scale=frame_scale(source_frames,target_frames)
    time=np.arange((source_frames-1)*4+1)/120
    first=np.array([a.sample(float(t)) for t in time])
    second=np.array([b.sample(float(t*scale)) for t in time])
    error=float(np.abs(first-second).max())
    if error>1e-5:raise ValueError('Retimed export differs from source curve')
    peaks={}
    for name,world,dt in [('source',first,1/120),('retimed',second,scale/120)]:
        positions=world[:,:,:3,3]
        speed=np.linalg.norm(np.diff(positions,axis=0)/dt,axis=-1)
        acceleration=np.linalg.norm(np.diff(positions,n=2,axis=0)/dt**2,axis=-1)
        peaks[name]=dict(peak_node_speed_m_s=float(speed.max()),peak_node_acceleration_m_s2=float(acceleration.max()))
    return dict(source_curve_samples=len(time),maximum_matrix_error=error,rates=peaks,
                expected_speed_multiplier=1/scale,expected_acceleration_multiplier=1/scale**2,
                dynamics_approved=False,
                scope='Same-phase decoded export comparison; rates over node origins. Retiming preserves the path but scales velocity and acceleration. Gravity, force, balance and collision safety are not re-simulated or approved.')


def run(source, output, frames):
    source,output=Path(source).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'reports'):
        raise ValueError('Fresh output directory under reports required')
    scene=read(source/'portable-scene.json');events=read(source/'events.json');runtime=read(source/'scene-runtime.json')
    original=scene['frame_count'];scale=frame_scale(original,frames)
    if runtime['source_scene_sha256']!=sha256(source/'portable-scene.json') or runtime['source_events_sha256']!=sha256(source/'events.json'):
        raise ValueError('Source scene/events changed')
    if runtime['fps']!=30 or runtime['frames']!=original or set(runtime['actors'])!=set(scene['actors']) or set(runtime['objects'])!=set(scene.get('objects',{})):
        raise ValueError('Runtime clock/participants differ from scene')
    if any(runtime['actors'][n]['placement']!=a['transform'] for n,a in scene['actors'].items()):
        raise ValueError('Runtime actor placement differs')
    if any(o.get('ownership')!='baked_track' for o in runtime['objects'].values()):
        raise ValueError('Retiming requires baked object ownership')
    exact_path=source/'retime-contact-windows.json'
    transformed,mapped,windows=retime_clock(scene,events,frames,read(exact_path) if exact_path.exists() else None)
    inputs={str(source/n):sha256(source/n) for n in ['portable-scene.json','events.json','scene-runtime.json','SOMA-LICENSE.txt']}
    if exact_path.exists():inputs[str(exact_path)]=sha256(exact_path)
    motions={};exports={};audits={}
    for name,actor in scene['actors'].items():
        motion=local(source,actor['motion']);glb=local(source,actor['preview_glb'])
        if sha256(motion)!=actor['source_sha256'] or sha256(glb)!=runtime['actors'][name]['sha256']:
            raise ValueError('Source actor changed')
        data=dict(np.load(motion,allow_pickle=False))
        exports[name]=retime_export(glb,original,frames)
        motions[name]=native_motion(data,*exports[name],original,frames)
        audits[name]=curve_audit(glb,exports[name],original,frames)
        inputs.update({str(motion):sha256(motion),str(glb):sha256(glb)})
    object_export=None
    if scene.get('objects'):
        path=local(source,scene['objects_glb'])
        if sha256(path)!=runtime['object_clip']['sha256']:raise ValueError('Source object export changed')
        inputs[str(path)]=sha256(path);object_export=retime_export(path,original,frames)
        audits['objects']=curve_audit(path,object_export,original,frames)
        doc,binary=object_export;sampler=AnimationSampler(doc,binary,0)
        from scipy.spatial.transform import Rotation
        worlds=np.array([sampler.sample(f/30) for f in range(frames)])
        for name,obj in transformed['objects'].items():
            ids=[i for i,n in enumerate(doc['nodes']) if n.get('extras',{}).get('strep_object_id')==name]
            if len(ids)!=1:raise ValueError('Object export identity missing/ambiguous')
            world=worlds[:,ids[0]]
            # Baked object nodes can contain their geometry scale. Pose rotation
            # is the orthonormal part, while geometry stays in the original GLB.
            basis=world[:,:3,:3];length=np.linalg.norm(basis,axis=1)
            rotation=basis/length[:,None,:]
            if np.max(abs(rotation.transpose(0,2,1)@rotation-np.eye(3)))>1e-5 or np.any(np.linalg.det(rotation)<0):
                raise ValueError('Sheared/reflected object track unsupported')
            quats=Rotation.from_matrix(rotation).as_quat()
            obj['keyframes']=[dict(frame=i,translation_m=w[:3,3].tolist(),rotation_xyzw=q.tolist()) for i,(w,q) in enumerate(zip(world,quats))]
    # Source snapshots must remain unchanged through all sampling and validation.
    for name,digest in inputs.items():
        if sha256(name)!=digest:raise ValueError('Source changed during retiming')
    output.mkdir(parents=True)
    for index,(name,motion) in enumerate(motions.items()):
        folder=output/'actors'/str(index);folder.mkdir(parents=True)
        np.savez_compressed(folder/'motion.npz',**motion);write_glb(folder/'actor.glb',*exports[name])
        transformed['actors'][name].update(motion=f'actors/{index}/motion.npz',preview_glb=f'actors/{index}/actor.glb',source_sha256=sha256(folder/'motion.npz'))
    if object_export:
        write_glb(output/'objects.glb',*object_export);transformed['objects_glb']='objects.glb'
    transformed['id']+=f'-retime-{frames}'
    save(output/'portable-scene.json',transformed);save(output/'events.json',mapped)
    save(output/'source-scene.json',scene);save(output/'source-events.json',events)
    save(output/'retime-contact-windows.json',dict(windows=windows,scope='Exact mapped authored intervals plus conservative integer windows for native contact solvers; these are not detected contacts.'))
    save(output/'retime-audit.json',dict(participants=audits,quality_approved=False))
    shutil.copyfile(source/'SOMA-LICENSE.txt',output/'SOMA-LICENSE.txt')
    save(output/'retime-recipe.json',dict(inputs=inputs,source_frames=original,target_frames=frames,time_scale=scale,speed_multiplier=1/scale,
         implementation={n:sha256(ROOT/'scripts'/n) for n in ['retime_scene.py','scene_runtime.py','godot_scene_clock.gd','rig_clip_import.py','gltf_tools.py']},quality_approved=False,
         scope='Uniform scaling of all actor/prop export key times; source mesh, rig and path retained. Exact fractional event timing, one output frame terminal hold. Native poses sampled at 30fps; predicted foot contacts use source previous-sample hold, heading uses unwrapped angle interpolation. Integer contact windows enclose exact intervals. No physics rebake, naturalness claim or copied quality approval.'))
    write_runtime(output)
    files={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()}
    save(output/'package-manifest.json',dict(files=files,quality_approved=False))
    with zipfile.ZipFile(output/'scene-runtime.zip','x',zipfile.ZIP_DEFLATED) as archive:
        for name in [*files,'package-manifest.json']:archive.write(output/name,name)
    with zipfile.ZipFile(output/'scene-runtime.zip') as archive:
        if archive.testzip() or any(hashlib.sha256(archive.read(n)).hexdigest()!=d for n,d in files.items()):raise ValueError('Retimed archive verification failed')
    print(dict(frames=frames,speed_multiplier=1/scale,actors=len(motions),objects=len(transformed.get('objects',{})),events=len(mapped['events']),quality_approved=False),flush=True)
    return transformed


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--frames',type=int,required=True)
    args=parser.parse_args();run(args.source,args.output,args.frames)
