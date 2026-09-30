"""Plan a wrist-preserving paired elbow waypoint at an audited collision peak.

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
    clear=sorted([r for r in rows if r['proxy_clearance_m'] >= .002],
                 key=lambda r:(sum(a*a for a in r['angles_degrees']),-r['proxy_clearance_m'],r['id']))
    greatest=sorted(rows,key=lambda r:(-r['proxy_clearance_m'],sum(a*a for a in r['angles_degrees']),r['id']))
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


def run(study,output):
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
    angles=[-45.,-30.,-15.,0.,15.,30.,45.];poses=[];binding=[]
    for actor,record in zip(actors,selected['actors']):
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
        for angle in angles:
            proposed,local=swivel(world,rig.parents,*chain,np.deg2rad(angle))
            replay=world_from_local(local[None],rig.parents)[0]
            error=float(np.abs(replay-proposed).max())
            if error>1e-10: raise ValueError('Native local swivel does not replay')
            points=rig.vertices(replay)@actor['rotation'].T+actor['translation']
            endpoints=replay[[elbow,wrist],:3,3]@actor['rotation'].T+actor['translation']
            edits=Rotation.from_matrix(local_before[:,:3,:3]).inv()*Rotation.from_matrix(local[:,:3,:3])
            variants.append(dict(angle=angle,world=replay,local=local,points=points,endpoints=endpoints,
                radius=capsule_radius(points[forearm],*endpoints),maximum_local_edit_degrees=float(np.rad2deg(edits.magnitude()).max()),
                hand_world_error=float(np.abs(replay[hand_nodes]-world[hand_nodes]).max()),
                hand_vertex_error_m=float(np.abs(points[hand_vertices]-source_points[hand_vertices]).max(initial=0)),fk_error=error))
        poses.append(variants)
        binding.append(dict(actor=actor['name'],rig=rig,world=world,hand_nodes=hand_nodes,hand_vertices=hand_vertices,
            points=source_points,chain=chain))
    rows=[]
    for i,a in enumerate(poses[0]):
        for j,b in enumerate(poses[1]):
            distance=segment_distance(*a['endpoints'],*b['endpoints'])
            rows.append(dict(id=f'{i}-{j}',pose_indices=[i,j],angles_degrees=[a['angle'],b['angle']],
                segment_distance_m=distance,capsule_radii_m=[a['radius'],b['radius']],
                proxy_clearance_m=distance-a['radius']-b['radius'],
                maximum_native_rotation_edits_degrees=[a['maximum_local_edit_degrees'],b['maximum_local_edit_degrees']],
                wrist_and_hand_matrix_errors=[a['hand_world_error'],b['hand_world_error']],
                hand_vertex_errors_m=[a['hand_vertex_error_m'],b['hand_vertex_error_m']],quality_approved=False))
    targets=ranked_candidates(rows)
    output.mkdir();(output/'implementation').mkdir();methods={}
    for name in ['plan_pair_swivel_pose.py','elbow_swivel.py','strep.py','diagnose_scene_pair_limits.py','scene_pair_problem.py',
            'rig_asset.py','rig_clip_import.py','gltf_tools.py','paired_guarded_temporal.py','convex_partner_surface.py']:
        shutil.copyfile(ROOT/'scripts'/name,output/'implementation'/name);methods[name]=sha256(output/'implementation'/name)
    save(output/'request.json',dict(at=now(),study=str(study),inputs=files,implementation=methods,
        sample=peak['sample'],time_s=stamp,starting_peak_depth_m=peak['candidate_depth_m'],
        angles_degrees=angles,chains={b['actor']:b['chain'] for b in binding},selected_proxy_candidates=targets,
        selection='Alternate least squared angle among proxy clearance >=2mm and greatest capsule clearance; four unique candidates.',
        scope='New static approach waypoint targets. Original five-degree edit study is unchanged; these targets allow +/-45-degree swivels and report actual joint edits. Wrist transforms remain fixed. No temporal motion bounds, anatomical/self-collision, whole-clip, engine or naturalness approval. Capsule ranks only cover influenced forearm vertices, not full-body collision.',quality_approved=False))
    save(output/'proxy-candidates.json',rows);audits=[]
    print(dict(phase='ranked',candidates=len(rows),positive_proxy=sum(r['proxy_clearance_m']>=.002 for r in rows),selected=targets),flush=True)
    for identifier in targets:
        row=next(r for r in rows if r['id']==identifier);dest=output/identifier;dest.mkdir()
        points=[];proofs=[]
        for actor,b,variants,ix in zip(actors,binding,poses,row['pose_indices']):
            pose=variants[ix];path=dest/(actor['name']+'.glb')
            rig,world=export_pose(b['rig'],pose['local'],path)
            vertices=rig.vertices(world)@actor['rotation'].T+actor['translation']
            error=float(np.abs(vertices-pose['points']).max())
            hand_error=float(np.abs(world[b['hand_nodes']]-b['world'][b['hand_nodes']]).max())
            skin_hand_error=float(np.abs(vertices[b['hand_vertices']]-b['points'][b['hand_vertices']]).max(initial=0))
            if max(error,hand_error,skin_hand_error)>2e-6: raise ValueError('Decoded pose or fixed hand differs')
            points.append(vertices);proofs.append(dict(actor=actor['name'],path=path.name,sha256=sha256(path),
                skin_error_m=error,hand_matrix_error=hand_error,hand_vertex_error_m=skin_hand_error,
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
        vertex_depth_passes=sum(r['vertex_depth_screen_pass'] for r in audits),
        request_sha256=sha256(output/'request.json'),proxy_sha256=sha256(output/'proxy-candidates.json'),
        audits_sha256=sha256(output/'audits.json'),playback_ready=False,quality_approved=False))
    print(read(output/'result.json'),flush=True)


if __name__=='__main__':
    from action_worker_lock import worker_lock
    from threadpoolctl import threadpool_limits
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('study',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    with worker_lock(),threadpool_limits(limits=1):run(a.study,a.output)
