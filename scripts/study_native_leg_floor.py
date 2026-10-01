"""Experimental native leg-only floor correction with unchanged contact intent."""
import argparse
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT, read, save, sha256, now


def run(source, output):
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from paired_temporal_neighbor import rotation_channels
    from paired_approach_basis import BoundSkin
    from contact_rate_path import ProjectedSkin
    from native_leg_floor import foot_region, lift_pose, export_rotations
    from native_engine_clock import audit_clock
    from scene_pair_problem import load_actors
    from sampled_motion_caps import SampledMotionCaps, features, measures
    from absolute_rate_peaks import compare
    from triangle_crossing import audit
    from convex_partner_surface import penetration
    from native_finger_motion import palm_geometry
    from shared_palm_meeting import measure
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output.parent != ROOT/'reports':
        raise ValueError('Fresh immediate reports output required')
    sq, sr = read(source/'request.json'), read(source/'result.json')
    if sr['status'] != 'complete' or not sr['native_animation_exported'] or not sr['contact_target_pass']:
        raise ValueError('Completed native contact source required')
    if sq.get('protected_spans'):
        raise ValueError('Full-clip leg correction cannot preserve protected whole-body spans')
    files = dict(sq['inputs'])
    for name in ('request.json','result.json'): files[str(source/name)] = sha256(source/name)
    for directory, entries in [(source,sr['outputs']),(source/'implementation',sq['implementation'])]:
        for name,digest in entries.items():
            path=(directory/name).resolve()
            if path.parent != directory: raise ValueError('Escaping source evidence')
            if str(path) in files and files[str(path)] != digest: raise ValueError('Conflicting source evidence')
            files[str(path)]=digest
    def unchanged():
        for path,digest in files.items():
            if sha256(path) != digest: raise ValueError('Changed floor-study evidence')
    def bound(path):
        path=Path(path).resolve()
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound floor-study input')
        return read(path)
    unchanged()
    pose=sq;seen=set()
    while 'baseline' not in pose:
        path=Path(pose['source'])/'request.json'
        if path in seen or len(seen)>=32: raise ValueError('Invalid provenance chain')
        seen.add(path);pose=bound(path)
    region=bound(Path(pose['source'])/'request.json')
    _,actors=load_actors(region['prepared'])
    baseline=Path(pose['baseline']);br=bound(baseline/'result.json')
    trial=next(t for t in bound(baseline/'trials.json') if t['folder']==br['selected'])
    references=[]
    for entry in trial['actors']:
        path=baseline/br['selected']/entry['path']
        if files.get(str(path)) != sha256(path): raise ValueError('Unbound original reference')
        references.append(RigAsset.load(path))
    output.mkdir();archive=output/'implementation';archive.mkdir();methods={}
    names=set(sq['implementation'])|{'native_leg_floor.py',Path(__file__).name,'native_engine_clock.py','absolute_rate_peaks.py'}
    names |= {'two_bone_waypoint.py','elbow_swivel.py','paired_guarded_temporal.py'}
    for name in sorted(names):
        path=ROOT/'scripts'/name;methods[name]=sha256(path);shutil.copyfile(path,archive/name)
    request={key:sq[key] for key in ('target','selected_contact','event_time_s','window_s','protected_spans',
                                      'guard_times_s','uniform_times_s','original_bins_s','plane_times_s')}
    request.update(at=now(),source=str(source),inputs=files,implementation=methods,
        floor_condition=dict(plane_height_m=0.,clearance_m=.00025,maximum_lift_m=.03,maximum_local_angle_degrees=45.,
            scope='New full-clip leg-only authoring condition, including endpoint keys. Root, arm and other channels remain exact. Preserve foot orientation at native keys; between-key behavior independently decoded. Does not promise planted feet or balance.'),
        solver='Exact two-bone reach at original common leg rotation keys; no model inference or retiming',
        policy='New full-clip bounded leg-only floor correction. Existing window metadata describes the original contact/rate audit interval. Lower-body endpoint poses may change; root and all non-leg animation channels and transforms remain exact. Original motion caps remain unchanged and may fail. No whole-body protected spans are supported.',
        quality_approved=False)
    save(output/'request.json',request);save(output/'pipeline.json',dict(status='processing'))
    decoded=[];before=[];rigs=[];readers=[];clips=[];floors=[];full_clocks=[];uniform=np.asarray(sq['uniform_times_s'])
    try:
        for i,actor in enumerate(actors):
            rig=RigAsset.load(source/f'candidate-{i}.glb');reader=AnimationSampler(rig.document,rig.binary,0)
            chains=[[next(n for n in rig.joints if rig.document['nodes'][n]['name']==side+name) for name in ('Leg','Shin','Foot')] for side in ('Left','Right')]
            channels=rotation_channels(rig.document,rig.binary)
            nodes=[n for chain in chains for n in chain]
            key_times=channels[nodes[0]][1]
            for node in nodes: np.testing.assert_array_equal(channels[node][1],key_times)
            if not key_times[0]==0 or not float(key_times[-1])==reader.duration: raise ValueError('Full-clip common native leg keys required')
            # Stage floor normal in this actor's rig coordinates.
            up=actor['rotation'].T@np.array([0.,1.,0.]);offset=float(actor['translation'][1])
            skin=BoundSkin(rig);regions=[foot_region(skin,rig.parents,chain[-1]) for chain in chains]
            projections=[ProjectedSkin(skin,vertices,up,offset) for vertices in regions]
            values={n:channels[n][2].copy() for n in nodes};corrections=[]
            for key,time in enumerate(key_times):
                world=reader.sample(float(time));row=[]
                for chain,projection in zip(chains,projections):
                    height=float(projection.evaluate(world[None]).min())
                    world,local,report=lift_pose(world,rig.parents,chain,height,up=up)
                    report.update(source_minimum_height_m=height,foot=rig.document['nodes'][chain[-1]]['name']);row.append(report)
                    if report['lift_m']:
                        q=Rotation.from_matrix(local[chain,:3,:3]).as_quat()
                        for node,quat in zip(chain,q): values[node][key]=quat if quat@channels[node][2][key]>=0 else -quat
                corrections.append(dict(time_s=float(time),feet=row))
            save(output/f'actor-{i}-key-lifts.json',corrections)
            path=output/f'candidate-{i}.glb';export_rotations(rig.document,rig.binary,values,path)
            exported=RigAsset.load(path);current=AnimationSampler(exported.document,exported.binary,0)
            for old,new in zip(reader.channels,current.channels):
                assert old[:2]==new[:2] and old[4]==new[4];np.testing.assert_array_equal(old[2],new[2])
                if old[1]!='rotation' or old[0] not in nodes:np.testing.assert_array_equal(old[3],new[3])
            if len(reader.channels)!=len(current.channels) or reader.duration!=current.duration:raise ValueError('Native channel population/duration changed')
            decoded_channels=rotation_channels(exported.document,exported.binary)
            decoded_angles=[float(np.rad2deg((Rotation.from_quat(channels[n][2]).inv()*Rotation.from_quat(decoded_channels[n][2])).magnitude()).max()) for n in nodes]
            if max(decoded_angles)>45.+1e-4:raise ValueError('Serialized leg angle exceeds source-relative authoring bound')
            times=audit_clock(reader.duration,[c[2] for c in reader.channels],sq['guard_times_s']+sq['plane_times_s']+sq['uniform_times_s']+sq['window_s'],sq['event_time_s'])
            raw=np.array([reader.sample(t) for t in times]);world=np.array([current.sample(t) for t in times])
            moving=np.zeros(len(rig.parents),bool)
            from elbow_swivel import descendants
            for chain in chains:moving|=descendants(rig.parents,chain[0])
            np.testing.assert_array_equal(raw[:,~moving],world[:,~moving])
            all_vertices=np.arange(len(skin.nodes));projected=ProjectedSkin(skin,all_vertices,up,offset)
            source_heights=projected.evaluate(raw);exported_heights=projected.evaluate(world)
            floor_rows=[dict(time_s=float(t),source_depth_m=max(0.,-float(a.min())),exported_depth_m=max(0.,-float(b.min())),
                            source_lowest_vertex=int(a.argmin()),exported_lowest_vertex=int(b.argmin()),minimum_exported_height_m=float(b.min()))
                        for t,a,b in zip(times,source_heights,exported_heights)]
            save(output/f'actor-{i}-full-floor.json',floor_rows)
            floor_summary=dict(actor=i,samples=len(times),source_maximum_depth_m=max(r['source_depth_m'] for r in floor_rows),
                exported_maximum_depth_m=max(r['exported_depth_m'] for r in floor_rows),minimum_exported_height_m=min(r['minimum_exported_height_m'] for r in floor_rows),
                maximum_lift_m=max(f['lift_m'] for r in corrections for f in r['feet']),
                maximum_angle_degrees=max(max(f['angles_degrees']) for r in corrections for f in r['feet']),
                floor_samples_pass=all(r['exported_depth_m']<=1e-8 for r in floor_rows))
            floors.append(floor_summary);save(output/f'actor-{i}-floor-summary.json',floor_summary)
            positions=np.searchsorted(times,uniform)
            absolute=compare(measures(features(raw[positions],rig.joints),float(uniform[1]-uniform[0])),measures(features(world[positions],rig.joints),float(uniform[1]-uniform[0])))
            clips.append(dict(path=path.name,sha256=sha256(path),edited_nodes=nodes,unedited_channels_and_native_clocks_exact=True,
                non_leg_world_transforms_exact=True,decoded_leg_angles_degrees=decoded_angles,absolute_peak_comparison=absolute))
            decoded.append(world);before.append(raw);full_clocks.append(times);rigs.append(exported);readers.append(current)
            print(dict(phase='native_leg_floor',**floor_summary),flush=True)
        def payload(worlds):
            parts=[features(w,r.joints) for w,r in zip(worlds,rigs)]
            return {k:np.concatenate([p[k] for p in parts],axis=1) for k in ('positions','rotations')}
        original=[np.array([AnimationSampler(r.document,r.binary,0).sample(t) for t in uniform]) for r in references]
        caps=SampledMotionCaps(payload(original),uniform,sq['original_bins_s'])
        rate_values=measures(payload([w[np.searchsorted(ts,uniform)] for w,ts in zip(decoded,full_clocks)]),caps.dt)
        rate_rows=[dict(kind=kind,failed_rows=int(np.count_nonzero(v-c-caps.tolerance>0)),maximum_excess=float((v-c-caps.tolerance).max()))
            for kind,v,c in zip(('position_speed','position_acceleration','angular_speed','angular_acceleration'),rate_values,caps.caps)]
        geometry=[];floor=[];contact=None
        for index,time in enumerate(sq['guard_times_s']):
            points=[r.vertices(w[int(np.searchsorted(ts,time))])@a['rotation'].T+a['translation'] for r,w,ts,a in zip(rigs,decoded,full_clocks,actors)]
            surface=audit(points[0],actors[0]['faces'],points[1],actors[1]['faces'])
            depths=[penetration(points[a],points[b],actors[b]['faces'],tolerance_m=1e-8) for a,b in ((0,1),(1,0))]
            passed=not any(v for k,v in surface['counts'].items() if k!='disjoint') and not any(surface['degenerate_faces']) and max(d['max_depth_m'] for d in depths)<=1e-8
            row=dict(time_s=float(time),surface=surface,depths=depths,inter_actor_pose_screen_pass=bool(passed));geometry.append(row)
            if time==sq['event_time_s']:
                centers=[];normals=[]
                for i,(p,a) in enumerate(zip(points,actors)):
                    vertex=sq['selected_contact']['effector' if i==0 else 'target']['surface_vertex'];patch=a['faces'][np.any(a['faces']==vertex,axis=1)]
                    c,n=palm_geometry(p,patch,vertex);centers.append(c);normals.append(n)
                contact=measure(centers,normals,sq['target']);row['contact']=contact
            save(output/f'geometry-{index:02d}.json',row)
            old_points=[r.vertices(w[int(np.searchsorted(ts,time))])@a['rotation'].T+a['translation'] for r,w,ts,a in zip(rigs,before,full_clocks,actors)]
            floor.append(dict(time_s=float(time),source_m=[max(0.,-float(p[:,1].min())) for p in old_points],exported_m=[max(0.,-float(p[:,1].min())) for p in points]))
            print(dict(phase='native_leg_geometry',completed=index+1,total=len(sq['guard_times_s']),passed=bool(passed)),flush=True)
        if contact is None:raise ValueError('Contact guard missing')
        save(output/'decoded.json',dict(clips=clips,contact=contact,motion_rates=rate_rows,floor=floors));save(output/'floor.json',floor)
        unchanged()
        for name,digest in methods.items():
            if sha256(ROOT/'scripts'/name)!=digest:raise ValueError('Method changed during floor study')
        result=dict(at=now(),status='complete',contact_target_pass=contact['contact_target_pass'],
            contact_mesh_screen_pass=next(g['inter_actor_pose_screen_pass'] for g in geometry if g['time_s']==sq['event_time_s']),
            guard_samples=len(geometry),failed_geometry_samples=sum(not g['inter_actor_pose_screen_pass'] for g in geometry),
            maximum_vertex_depth_m=max(d['max_depth_m'] for g in geometry for d in g['depths']),
            original_motion_caps_pass=all(r['failed_rows']==0 for r in rate_rows),floor_samples_pass=all(r['floor_samples_pass'] for r in floors),
            native_animation_exported=True,continuous_collision_certified=False,selected_for_studio=False,quality_approved=False)
        result['outputs']={p.name:sha256(p) for p in output.iterdir() if p.is_file() and p.name!='pipeline.json'}
        save(output/'result.json',result);save(output/'pipeline.json',dict(status='complete'))
        print({k:v for k,v in result.items() if k!='outputs'},flush=True)
    except Exception as error:
        save(output/'pipeline.json',dict(status='failed',reason=str(error)));raise


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(args.source,args.output)
