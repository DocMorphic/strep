"""Plan paired arm waypoints at an audited collision peak.

New static pose targets only: no temporal fit or relaxation of an old edit's
acceptance. Capsule ranking is guidance; selected poses get full-mesh queries.
"""
import argparse
import copy
from pathlib import Path
import shutil
import numpy as np
from scipy.spatial.transform import Rotation
from strep import ROOT,read,save,sha256,now
from elbow_swivel import swivel,descendants,segment_distance,capsule_radius,local_transforms


def ranked_candidates(rows, count=4):
    """Alternate least-displaced clear proxy poses with greatest proxy clearance."""
    if not rows or type(count) is not int or count < 1: raise ValueError('Candidates and positive count required')
    if len({r['id'] for r in rows}) != len(rows): raise ValueError('Distinct candidate identifiers required')
    for row in rows:
        angles=np.asarray(row['angles_degrees'],float)
        if angles.shape!=(2,) or not np.isfinite(angles).all() or not np.isfinite(row['proxy_clearance_m']):
            raise ValueError('Finite paired angles and proxy clearance required')
        if not np.isfinite(row.get('planning_cost',0)) or row.get('planning_cost',0)<0:
            raise ValueError('Finite nonnegative planning cost required')
    cost=lambda r:r.get('planning_cost',sum(a*a for a in r['angles_degrees']))
    clear=sorted([r for r in rows if r['proxy_clearance_m'] >= .002],
                 key=lambda r:(cost(r),-r['proxy_clearance_m'],r['id']))
    greatest=sorted(rows,key=lambda r:(-r['proxy_clearance_m'],cost(r),r['id']))
    chosen=[]
    while len(chosen) < min(count,len(rows)):
        for pool in [clear,greatest]:
            row=next((r for r in pool if r['id'] not in chosen),None)
            if row is not None and len(chosen)<count: chosen.append(row['id'])
    return chosen


def export_pose(rig, local, path):
    from gltf_tools import write_glb
    from rig_asset import RigAsset
    local=np.asarray(local,float)
    local_transforms(local,rig.parents)  # Validate shape and rigid transforms.
    doc=copy.deepcopy(rig.document);doc['animations']=[]
    doc.setdefault('extras',{})['strep_pose_planning_only']=True
    for node,matrix in zip(doc['nodes'],local):
        node.pop('matrix',None)
        node['translation']=matrix[:3,3].astype(np.float32).tolist()
        node['rotation']=Rotation.from_matrix(matrix[:3,:3]).as_quat().astype(np.float32).tolist()
        node['scale']=[1,1,1]
    write_glb(path,doc,rig.binary)
    decoded=RigAsset.load(path)
    return decoded,decoded.reference


def run(study,output,wrist_waypoints=False):
    from diagnose_scene_pair_limits import load_bound_study
    from scene_pair_problem import load_actors
    from rig_asset import RigAsset
    from rig_clip_import import AnimationSampler
    from convex_partner_surface import penetration
    from paired_guarded_temporal import world_from_local
    study,output=Path(study).resolve(),Path(output).resolve()
    if output.exists(): raise ValueError('Fresh waypoint study required')
    request,_,files=load_bound_study(study);result=read(study/'result.json')
    if sha256(study/'trials.json') != result['trials_sha256']: raise ValueError('Bound selected trial required')
    files[str(study/'trials.json')]=result['trials_sha256']
    matches=[r for r in read(study/'trials.json') if r['folder']==result['selected']]
    if len(matches)!=1 or matches[0]['accepted_local_step'] is not True or matches[0]['reasons']:
        raise ValueError('One accepted local starting correction required')
    selected=matches[0];folder=(study/selected['folder']).resolve()
    if not folder.is_relative_to(study): raise ValueError('Selected trial escapes study')
    geometry=folder/'geometry.json'
    if sha256(geometry)!=selected['geometry']['geometry_sha256']: raise ValueError('Selected geometry changed')
    files[str(geometry)]=sha256(geometry);measured=read(geometry)
    peak=max(measured,key=lambda r:r['candidate_depth_m']);stamp=peak['time_s']
    if peak['candidate_depth_m']!=selected['geometry']['candidate_peak_m']: raise ValueError('Peak report differs')
    _,actors=load_actors(Path(request['prepared_request']).parent)
    if [a['name'] for a in actors]!=[r['actor'] for r in selected['actors']]: raise ValueError('Actor order differs')
    angles=[-45.,-30.,0.,30.,45.] if wrist_waypoints else [-45.,-30.,-15.,0.,15.,30.,45.]
    offsets=[np.zeros(3)]
    if wrist_waypoints:
        offsets += [axis*sign*distance for axis in np.eye(3) for sign in [-1,1] for distance in [.02,.04,.06]]
    poses=[];binding=[]
    for actor_index,(actor,record) in enumerate(zip(actors,selected['actors'])):
        path=(folder/record['path']).resolve()
        if path.parent!=folder or sha256(path)!=record['sha256']: raise ValueError('Starting clip changed')
        files[str(path)]=record['sha256'];rig=RigAsset.load(path)
        world=AnimationSampler(rig.document,rig.binary,0).sample(stamp)
        names=[n.get('name') for n in rig.document['nodes']]
        chain=[names.index(n) for n in ['LeftArm','LeftForeArm','LeftHand']]
        upper,elbow,wrist=chain;primitive=rig.primitives[0]
        skin_nodes=np.asarray(rig.joints)[primitive['joints']]
        forearm=np.flatnonzero(np.any((skin_nodes==elbow)&(primitive['weights']>0),axis=1))
        hand_nodes=descendants(rig.parents,wrist)
        hand_vertices=np.flatnonzero(np.all(hand_nodes[skin_nodes]|(primitive['weights']==0),axis=1))
        source_points=rig.vertices(world)@actor['rotation'].T+actor['translation']
        local_before=local_transforms(world,rig.parents);variants=[]
        for offset_index,offset in enumerate(offsets):
            delta=offset*(1 if actor_index==0 else -1);native_delta=delta@actor['rotation']
            for angle in angles:
                descriptor=dict(angle=angle,offset_index=offset_index,world_delta=delta,native_delta=native_delta)
                try:
                    if wrist_waypoints:
                        from two_bone_waypoint import reach
                        proposed,local=reach(world,rig.parents,*chain,world[wrist,:3,3]+native_delta,np.deg2rad(angle))
                    else:proposed,local=swivel(world,rig.parents,*chain,np.deg2rad(angle))
                except ValueError as error:
                    if 'outside two-bone reach' not in str(error):raise
                    variants.append(dict(**descriptor,rejected=str(error)));continue
                replay=world_from_local(local[None],rig.parents)[0]
                error=float(np.abs(replay-proposed).max())
                if error>1e-10: raise ValueError('Native local arm pose does not replay')
                edits=Rotation.from_matrix(local_before[:,:3,:3]).inv()*Rotation.from_matrix(local[:,:3,:3])
                max_edit=float(np.rad2deg(edits.magnitude()).max())
                if max_edit>45.+1e-4:
                    variants.append(dict(**descriptor,rejected='native_rotation_budget',maximum_local_edit_degrees=max_edit));continue
                points=rig.vertices(replay)@actor['rotation'].T+actor['translation']
                endpoints=replay[[elbow,wrist],:3,3]@actor['rotation'].T+actor['translation']
                expected=world[hand_nodes].copy();expected[:,:3,3]+=native_delta
                variants.append(dict(**descriptor,world=replay,local=local,points=points,endpoints=endpoints,
                    radius=capsule_radius(points[forearm],*endpoints),maximum_local_edit_degrees=max_edit,
                    hand_world_error=float(np.abs(replay[hand_nodes]-expected).max()),
                    hand_vertex_error_m=float(np.abs(points[hand_vertices]-source_points[hand_vertices]-delta).max(initial=0)),fk_error=error))
        poses.append(variants)
        binding.append(dict(actor=actor['name'],rig=rig,world=world,hand_nodes=hand_nodes,hand_vertices=hand_vertices,
            points=source_points,chain=chain))
    rows=[];rejected=[]
    for i,a in enumerate(poses[0]):
        for j,b in enumerate(poses[1]):
            if a['offset_index']!=b['offset_index']:continue
            if a.get('rejected') or b.get('rejected'):
                rejected.append(dict(id=f'{i}-{j}',angles_degrees=[a['angle'],b['angle']],
                    world_wrist_offsets_m=[a['world_delta'].tolist(),b['world_delta'].tolist()],
                    reasons=[a.get('rejected'),b.get('rejected')],
                    maximum_native_rotation_edits_degrees=[a.get('maximum_local_edit_degrees'),b.get('maximum_local_edit_degrees')]))
                continue
            distance=segment_distance(*a['endpoints'],*b['endpoints'])
            rows.append(dict(id=f'{i}-{j}',pose_indices=[i,j],angles_degrees=[a['angle'],b['angle']],
                world_wrist_offsets_m=[a['world_delta'].tolist(),b['world_delta'].tolist()],
                planning_cost=sum((p['angle']/45.)**2+(np.linalg.norm(p['world_delta'])/.06)**2 for p in [a,b]),
                segment_distance_m=distance,capsule_radii_m=[a['radius'],b['radius']],
                proxy_clearance_m=distance-a['radius']-b['radius'],
                maximum_native_rotation_edits_degrees=[a['maximum_local_edit_degrees'],b['maximum_local_edit_degrees']],
                wrist_and_hand_matrix_errors=[a['hand_world_error'],b['hand_world_error']],
                hand_vertex_errors_m=[a['hand_vertex_error_m'],b['hand_vertex_error_m']],quality_approved=False))
    targets=ranked_candidates(rows)
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in ['plan_pair_swivel_pose.py','elbow_swivel.py','strep.py','diagnose_scene_pair_limits.py','scene_pair_problem.py',
            'rig_asset.py','rig_clip_import.py','gltf_tools.py','paired_guarded_temporal.py','convex_partner_surface.py','two_bone_waypoint.py']:
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),study=str(study),inputs=files,implementation=methods,
        sample=peak['sample'],time_s=stamp,starting_peak_depth_m=peak['candidate_depth_m'],
        angles_degrees=angles,wrist_waypoints=wrist_waypoints,actor_a_wrist_offsets_m=[d.tolist() for d in offsets],
        chains={b['actor']:b['chain'] for b in binding},selected_proxy_candidates=targets,
        native_joint_edit_budget_degrees=45.,
        selection='Alternate smallest planning cost among proxy clearance >=2mm and greatest capsule clearance; four unique candidates. Cost is summed squared angle/45deg and wrist displacement/60mm for both actors.',
        scope='New static approach waypoint targets with a 45-degree native joint edit cap relative to current input. Original five-degree request is unchanged. Optional symmetric pre-contact wrist displacements preserve hand orientation and rigid bone lengths. No temporal motion bounds, anatomical/self-collision, whole-clip, engine or naturalness approval. Capsule ranks cover influenced forearm vertices only.',quality_approved=False))
    save(output/'proxy-candidates.json',rows);save(output/'rejected-candidates.json',rejected);audits=[]
    print(dict(phase='ranked',candidates=len(rows),positive_proxy=sum(r['proxy_clearance_m']>=.002 for r in rows),selected=targets),flush=True)
    for identifier in targets:
        row=next(r for r in rows if r['id']==identifier);dest=output/identifier;dest.mkdir()
        points=[];proofs=[]
        for actor,b,variants,ix in zip(actors,binding,poses,row['pose_indices']):
            pose=variants[ix];path=dest/(actor['name']+'.glb')
            rig,world=export_pose(b['rig'],pose['local'],path)
            vertices=rig.vertices(world)@actor['rotation'].T+actor['translation']
            error=float(np.abs(vertices-pose['points']).max())
            expected=b['world'][b['hand_nodes']].copy();expected[:,:3,3]+=pose['native_delta']
            hand_error=float(np.abs(world[b['hand_nodes']]-expected).max())
            skin_hand_error=float(np.abs(vertices[b['hand_vertices']]-b['points'][b['hand_vertices']]-pose['world_delta']).max(initial=0))
            if max(error,hand_error,skin_hand_error)>2e-6: raise ValueError('Decoded pose or fixed hand differs')
            decoded_local=local_transforms(world,rig.parents);original_local=local_transforms(b['world'],b['rig'].parents)
            edits=Rotation.from_matrix(original_local[:,:3,:3]).inv()*Rotation.from_matrix(decoded_local[:,:3,:3])
            decoded_edit=float(np.rad2deg(edits.magnitude()).max())
            if decoded_edit>45.+1e-4:raise ValueError('Decoded native joint budget exceeded')
            points.append(vertices);proofs.append(dict(actor=actor['name'],path=path.name,sha256=sha256(path),
                skin_error_m=error,hand_matrix_error=hand_error,hand_vertex_error_m=skin_hand_error,
                decoded_maximum_joint_edit_degrees=decoded_edit,
                fully_hand_influenced_vertices=len(b['hand_vertices'])))
        directions=[]
        for s,t in [(0,1),(1,0)]:
            directions.append(dict(source=s,target=t,**penetration(points[s],points[t],actors[t]['faces'])))
            save(dest/'geometry.json',directions);print(dict(phase='geometry',candidate=identifier,directions=len(directions)),flush=True)
        floor=[max(0.,-float(p[:,1].min())) for p in points]
        depth=max(d['max_depth_m'] for d in directions)
        record=dict(**row,actors=proofs,full_mesh_depth_m=depth,floor_depth_m=floor,
            vertex_depth_screen_pass=depth<=.005,floor_screen_pass=max(floor)<=.005,
            floor_increase_m=max(f-s for f,s in zip(floor,peak['floor_depth_m'])),
            geometry_sha256=sha256(dest/'geometry.json'),playback_ready=False)
        audits.append(record);save(output/'audits.json',audits)
        print(dict(phase='audited',candidate=identifier,depth_mm=depth*1000,floor_mm=max(floor)*1000),flush=True)
    for path,digest in files.items():
        if sha256(path)!=digest: raise ValueError('Pose planning input changed')
    for name,digest in methods.items():
        if sha256(ROOT/'scripts'/name)!=digest: raise ValueError('Pose planning method changed')
    save(output/'result.json',dict(at=now(),status='complete',proxy_candidates=len(rows),audited_candidates=len(audits),
        declared_candidates=len(offsets)*len(angles)**2,rejected_candidates=len(rejected),
        vertex_depth_passes=sum(r['vertex_depth_screen_pass'] for r in audits),
        request_sha256=sha256(output/'request.json'),proxy_sha256=sha256(output/'proxy-candidates.json'),
        rejected_sha256=sha256(output/'rejected-candidates.json'),
        audits_sha256=sha256(output/'audits.json'),playback_ready=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--wrist-waypoints',action='store_true');a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(a.study,a.output,a.wrist_waypoints)
